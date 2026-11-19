"""Study O on recordings (docs/OPTO.md): one code path for real mice and for synthetic systems recorded
through a real mouse's instrument. A recording is a dict:
  spont: list of (T_i, N) 20 ms count arrays, one per spontaneous block
  block: (T_b, N) 20 ms counts over the optogenetic block
  on_train, on_test: onset bins into `block`
  cls: (N,) class index per unit; -1 tagged; -2 unused
  n_classes: number of classes"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

from . import core

CACHE = Path(__file__).resolve().parents[2] / "data/cache/opto"
BIN = core.BIN


# ------------------------------------------------------------------ the shared analysis
def spont_sd(spont):
    """Per unit, SD of spike counts in 1 s windows within spontaneous blocks."""
    w = [s[: (len(s) // 50) * 50].reshape(-1, 50, s.shape[1]).sum(1) for s in spont if len(s) >= 50]
    return np.concatenate(w).std(0)


def class_rates(Y, cls, n):
    """(T, N) -> (T, 1 + n): tagged class first, then classes 0..n-1 (mean count per unit)."""
    return np.stack([Y[:, cls == k].mean(1) for k in [-1] + list(range(n))], 1)


def fit_watch(spont, cls, n):
    """W: VAR(1) on z-scored class rates, lag pairs taken within blocks only."""
    Xs = [class_rates(s, cls, n) for s in spont]
    X = np.concatenate(Xs)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    A = np.concatenate([(x[:-1] - mu) / sd for x in Xs])
    B = np.concatenate([(x[1:] - mu) / sd for x in Xs])
    M, *_ = np.linalg.lstsq(A, B, rcond=None)
    return M.T, mu, sd


BASE_BINS = 12   # amendment A7: baseline is the 0.24 s before onset (at least 0.45 s after any earlier light)


def unit_responses(block, onsets, sd):
    """Per trial and unit: spikes in the 1 s after onset minus the baseline rate times 1 s, in units of the
    SD of 1 s spontaneous counts (A7 baseline)."""
    out = []
    for o in onsets:
        post = block[o:o + core.TEST_BINS].sum(0)
        pre = block[o - BASE_BINS:o].mean(0) * core.TEST_BINS
        out.append((post - pre) / np.maximum(sd, 1e-9))
    return np.asarray(out)


def courses(block, cls, n, onsets, s):
    """Trial-averaged class-rate change after onset (50 bins) minus the A7 baseline, in spontaneous SD units."""
    X = class_rates(block, cls, n)
    tr = np.stack([X[o:o + core.TEST_BINS] - X[o - BASE_BINS:o].mean(0) for o in onsets]).mean(0)
    return tr / s


def analyse(rec):
    cls, n = rec["cls"], rec["n_classes"]
    sd = spont_sd(rec["spont"])
    resp = unit_responses(rec["block"], rec["on_test"], sd)
    keep = cls >= 0
    classes = np.arange(n)
    prof = core.profile(resp[:, keep], cls[keep], classes)
    ceil = core.agree(core.profile(resp[0::2][:, keep], cls[keep], classes),
                      core.profile(resp[1::2][:, keep], cls[keep], classes))
    W = fit_watch(rec["spont"], cls, n)
    te = courses(rec["block"], cls, n, rec["on_test"], W[2])
    tr = courses(rec["block"], cls, n, rec["on_train"], W[2])
    pw = core.predict_watch(W, te[:, 0], 0)[1:]
    tr2 = courses(rec["block"], cls, n, rec["on_train2"], W[2])
    pp = core.predict_poke(fit_poke2([tr, tr2]), te[:, 0])
    return {"ceiling": ceil, "W": core.agree(pw, prof), "P": core.agree(pp, prof), "profile": prof}


def fit_poke2(course_list, L=core.TEST_BINS):
    """A8: one set of FIR kernels fitted jointly to several training conditions (square pulses and the
    10 Hz train), each a (50, 1 + K) trial-averaged course with the tagged class first."""
    Ds, Ys = [], []
    for c in course_list:
        x = c[:, 0]
        D = np.zeros((len(x), L))
        for j in range(L):
            D[j:, j] = x[:len(x) - j]
        Ds.append(D); Ys.append(c[:, 1:])
    H, *_ = np.linalg.lstsq(np.concatenate(Ds), np.concatenate(Ys), rcond=None)
    return H


# ------------------------------------------------------------------ real mice
def load(mouse):
    z = np.load(CACHE / f"{mouse}.npz", allow_pickle=False)
    d = {k: z[k] for k in z.files}
    d["info"] = json.loads(str(d["info"]))
    idx = np.r_[0, d["spikes_index"]]
    d["trains"] = [d["spikes_10us"][a:b] / 1e5 for a, b in zip(idx[:-1], idx[1:])]
    return d


def square_pulses(d):
    return np.flatnonzero((d["opto_name"] == "pulse") & np.isin(np.round(d["opto_duration"], 3), [0.005, 0.01]))


def half_cosine(d):
    return np.flatnonzero(d["opto_name"] == "raised_cosine")


def tag(d):
    """Registered rule: odd-numbered square-pulse trials (1st, 3rd, ... in time order), spikes 1 to 11 ms
    after onset against the 10 ms before; one-sided Wilcoxon p < 0.001 and >= 0.3 extra spikes per trial."""
    tr = square_pulses(d)
    tr = tr[np.argsort(d["opto_start"][tr])][0::2]
    on = d["opto_start"][tr]
    out = np.zeros(len(d["trains"]), bool)
    for i, s in enumerate(d["trains"]):
        post = np.searchsorted(s, on + 0.011) - np.searchsorted(s, on + 0.001)
        pre = np.searchsorted(s, on) - np.searchsorted(s, on - 0.010)
        diff = post - pre
        if diff.mean() < 0.3 or not np.any(diff):
            continue
        if wilcoxon(post, pre, alternative="greater", zero_method="wilcox").pvalue < 0.001:
            out[i] = True
    return out


def classes(d, tagged, min_units=5):
    """Class = area x waveform group (narrow < 0.4 ms). Used if >= 5 non-tagged units. Returns cls, names."""
    lab = np.array([f"{a}|{'n' if w < 0.4 else 'b'}" for a, w in zip(d["area"], d["waveform_ms"])])
    names = sorted(k for k in set(lab[~tagged]) if (lab[~tagged] == k).sum() >= min_units)
    cls = np.full(len(lab), -2)
    for j, k in enumerate(names):
        cls[(lab == k) & ~tagged] = j
    cls[tagged] = -1
    return cls, names


def _bin(trains, t0, t1):
    edges = np.arange(t0, t1 + 1e-9, BIN)
    return np.stack([np.histogram(s[(s >= t0) & (s < t1)], edges)[0] for s in trains], 1).astype(np.float32)


def recording(d, cls, n):
    use = cls != -2
    trains = [s for s, u in zip(d["trains"], use) if u]
    spont = [_bin(trains, a, b) for a, b in d["spont"] if b - a >= 2.0]
    lo = d["opto_start"].min() - 1.5
    block = _bin(trains, lo, d["opto_stop"].max() + 1.5)
    on = lambda ix: np.floor((d["opto_start"][ix] - lo) / BIN).astype(int)  # noqa: E731
    other = np.setdiff1d(np.arange(len(d["opto_start"])), np.r_[square_pulses(d), half_cosine(d)])
    return {"spont": spont, "block": block, "on_train": on(square_pulses(d)), "on_test": on(half_cosine(d)),
            "on_train2": on(other),
            "cls": cls[use], "n_classes": n}


def instrument(d, cls, n):
    """What a synthetic system needs to be recorded through this mouse's instrument (no responses)."""
    use = cls != -2
    rate = d["firing_rate"][use]
    return {"cls": cls[use], "n_classes": n, "rate_hz": rate,
            "spont_s": [float(b - a) for a, b in d["spont"] if b - a >= 2.0],
            "n_train": len(square_pulses(d)), "n_test": len(half_cosine(d)), "schedule": schedule(d)}


def schedule(d):
    """The mouse's own trial order and timing (A7): (onset s from the first onset, kind) with kind 0 square
    pulse, 1 half-cosine, 2 anything else (the 10 Hz train)."""
    o = np.argsort(d["opto_start"])
    kind = np.full(len(o), 2)
    kind[np.isin(o, square_pulses(d))] = 0
    kind[np.isin(o, half_cosine(d))] = 1
    return d["opto_start"][o] - d["opto_start"][o[0]], kind


# ------------------------------------------------------------------ synthetic systems through an instrument
def synthetic(rng, inst, silent, coupling, A, gain=0.5):
    """As core.synthetic, but with the instrument's classes, units, rates, spontaneous blocks and its own
    trial schedule (A7): square pulses as one bin at 8 resting SDs, the half-cosine as in the pilot, and the
    10 Hz train as ten bins at 4 resting SDs."""
    cls, K = inst["cls"], inst["n_classes"]
    A = A * (0.85 / max(abs(np.linalg.eigvals(A))))
    rho, sig = 0.9, 0.3
    tag_sd = sig / np.sqrt(1 - rho ** 2)
    thr = 4 * tag_sd
    seg = [int(s / BIN) for s in inst["spont_s"]]
    T_sp = sum(seg)
    t_on, kinds = inst["schedule"]
    onsets = T_sp + 75 + np.round(t_on / BIN).astype(int)
    T = onsets[-1] + 2 * core.TEST_BINS
    stim = np.zeros(T)
    hc = np.sin(np.pi * np.arange(core.TEST_BINS) / core.TEST_BINS)
    for o, k in zip(onsets, kinds):
        if k == 0:
            stim[o] += 8 * tag_sd
        elif k == 1:
            stim[o:o + core.TEST_BINS] += 1.2 * tag_sd * hc
        else:
            stim[o:o + core.TEST_BINS:5] += 4 * tag_sd
    z = np.zeros((T, K)); tau = np.zeros(T)
    e = rng.normal(0, sig, (T, K)); et = rng.normal(0, sig, T)
    for t in range(1, T):
        tau[t] = rho * tau[t - 1] + et[t] + stim[t]
        drive = tau[t - 1] if not silent else max(0.0, tau[t - 1] - thr) * 3
        z[t] = A @ z[t - 1] + e[t] + 0.25 * coupling * drive
    zs = z / z[:T_sp].std(0)
    taus = tau / tau[:T_sp].std()
    lat = np.where(cls[None, :] == -1, taus[:, None], zs[:, np.clip(cls, 0, None)])
    base = np.maximum(inst["rate_hz"], 0.05) * BIN
    counts = rng.poisson(base * np.exp(gain * lat - gain ** 2 / 2)).astype(np.float32)
    edges = np.r_[0, np.cumsum(seg)]
    return {"spont": [counts[a:b] for a, b in zip(edges[:-1], edges[1:])], "block": counts[T_sp:],
            "on_train": onsets[kinds == 0] - T_sp, "on_test": onsets[kinds == 1] - T_sp,
            "on_train2": onsets[kinds == 2] - T_sp, "cls": cls, "n_classes": K}
