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
    """W, P, the measured profile, split-half reliability c and the best reachable r, sqrt(2c/(1+c)) (A10.4).
    Class rates are built from per-unit counts divided by each unit's 1 s spontaneous SD, and the copies'
    predictions are rescaled to those units (A10.1)."""
    cls, n = rec["cls"], rec["n_classes"]
    sd = np.maximum(spont_sd(rec["spont"]), 1e-9)
    resp = unit_responses(rec["block"], rec["on_test"], sd)
    keep = cls >= 0
    classes = np.arange(n)
    prof = core.profile(resp[:, keep], cls[keep], classes)
    c = core.agree(core.profile(resp[0::2][:, keep], cls[keep], classes),
                   core.profile(resp[1::2][:, keep], cls[keep], classes))
    spont = [x / sd for x in rec["spont"]]
    block = rec["block"] / sd
    W = fit_watch(spont, cls, n)
    scale = W[2][1:] * core.TEST_BINS             # z units -> per-unit SD units of a 1 s count
    te = courses(block, cls, n, rec["on_test"], W[2])
    tr = courses(block, cls, n, rec["on_train"], W[2])
    trs = [tr] + ([courses(block, cls, n, rec["on_train2"], W[2])] if len(rec["on_train2"]) else [])
    pw = core.predict_watch(W, te[:, 0], 0)[1:] * scale
    pp = core.predict_poke(fit_poke2(trs), te[:, 0]) * scale
    out = {"c": c, "ceiling": float(np.sqrt(2 * c / (1 + c))) if c > 0 else np.nan,
           "W": core.agree(pw, prof), "P": core.agree(pp, prof), "profile": prof}
    if len(rec["on_train2"]):
        out["train2_baseline"] = core.agree(core.profile(unit_responses(rec["block"], rec["on_train2"], sd)[:, keep],
                                                         cls[keep], classes), prof)
    return out


def rest_score(rec, z_thr=2.0):
    """A10.8: W fitted on the first half of each spontaneous block predicts, on the second halves, each
    class's average change in the 1 s after the tagged class rises above 2 SD, clamped to its own course."""
    cls, n = rec["cls"], rec["n_classes"]
    sd = np.maximum(spont_sd(rec["spont"]), 1e-9)
    first = [x[: len(x) // 2] / sd for x in rec["spont"]]
    second = [x[len(x) // 2:] / sd for x in rec["spont"]]
    W = fit_watch([f for f in first if len(f) > 2], cls, n)
    M, mu, s = W
    segs = []
    for x in second:
        Z = (class_rates(x, cls, n) - mu) / s
        up = np.flatnonzero((Z[1:, 0] > z_thr) & (Z[:-1, 0] <= z_thr)) + 1
        last = -10 ** 9
        for o in up:
            if o - BASE_BINS >= 0 and o + core.TEST_BINS <= len(Z) and o - last >= core.TEST_BINS:
                segs.append(Z[o:o + core.TEST_BINS] - Z[o - BASE_BINS:o].mean(0)); last = o
    if len(segs) < 20:
        return {"rest_score": np.nan, "rest_events": len(segs)}
    avg = np.mean(segs, 0)
    pred = core.predict_watch(W, avg[:, 0], 0)[1:]
    return {"rest_score": core.agree(pred, avg[:, 1:].mean(0)), "rest_events": len(segs)}


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


def tag_registered(d):
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


def tag(d):
    """A11: the registered rule, screened for light artefacts. Odd-numbered 10 ms square-pulse trials only;
    spikes 2 to 9 ms after onset against the 7 ms before; one-sided Wilcoxon p < 0.001 and >= 0.3 extra spikes
    per trial. The window avoids the onset and offset of the light, where wild-type units fire artefactually."""
    tr = square_pulses(d)
    tr = tr[np.isclose(d["opto_duration"][tr], 0.01)]
    tr = tr[np.argsort(d["opto_start"][tr])][0::2]
    on = d["opto_start"][tr]
    out = np.zeros(len(d["trains"]), bool)
    for i, s in enumerate(d["trains"]):
        post = np.searchsorted(s, on + 0.009) - np.searchsorted(s, on + 0.002)
        pre = np.searchsorted(s, on) - np.searchsorted(s, on - 0.007)
        diff = post - pre
        if diff.mean() < 0.3 or not np.any(diff):
            continue
        if wilcoxon(post, pre, alternative="greater", zero_method="wilcox").pvalue < 0.001:
            out[i] = True
    return out


def classes(d, tagged, min_units=5):
    """Class = area x waveform group (narrow < 0.4 ms). Used if >= 5 non-tagged units. Returns cls, names."""
    lab = np.array([f"{a}|{'n' if w < 0.4 else 'b'}" for a, w in zip(d["area"], d["waveform_ms"])])
    ok = ~tagged & ~np.isin(d["area"], ["", "grey", "root"])          # A10.6
    names = sorted(k for k in set(lab[ok]) if (lab[ok] == k).sum() >= min_units)
    cls = np.full(len(lab), -2)
    for j, k in enumerate(names):
        cls[(lab == k) & ok] = j
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
def synthetic(rng, inst, silent, coupling, A, gain=0.5, mis=False):
    """As core.synthetic, but with the instrument's classes, units, rates, spontaneous blocks and its own
    trial schedule (A7): square pulses as one bin at 8 resting SDs, the half-cosine as in the pilot, and the
    10 Hz train as ten bins at 4 resting SDs. mis=True (A10.7, links visible): W is the wrong model, with a
    shared slow driver of every class and the tagged class, two lags of dynamics, and a saturating link."""
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
    if mis:
        A2 = -0.35 * A
        comp = np.block([[A, A2], [np.eye(K), np.zeros((K, K))]])
        f = 0.85 / max(abs(np.linalg.eigvals(comp)))
        A, A2 = A * f, A2 * f * f
        g = np.zeros(T); eg = rng.normal(0, 0.06, T); wg = rng.normal(0, 1, K)
    for t in range(2, T):
        if not mis:
            tau[t] = rho * tau[t - 1] + et[t] + stim[t]
            drive = tau[t - 1] if not silent else max(0.0, tau[t - 1] - thr) * 3
            z[t] = A @ z[t - 1] + e[t] + 0.25 * coupling * drive
        else:
            g[t] = 0.995 * g[t - 1] + eg[t]
            tau[t] = rho * tau[t - 1] + et[t] + stim[t] + 0.1 * g[t]
            drive = 2 * tag_sd * np.tanh(tau[t - 1] / (2 * tag_sd))
            z[t] = A @ z[t - 1] + A2 @ z[t - 2] + e[t] + 0.25 * coupling * drive + 0.1 * wg * g[t]
    zs = z / z[:T_sp].std(0)
    taus = tau / tau[:T_sp].std()
    lat = np.where(cls[None, :] == -1, taus[:, None], zs[:, np.clip(cls, 0, None)])
    base = np.maximum(inst["rate_hz"], 0.05) * BIN
    lat = np.minimum(lat, 6.0)                   # firing saturates at e^3 (about 20x) the resting rate
    counts = rng.poisson(base * np.exp(gain * lat - gain ** 2 / 2)).astype(np.float32)
    edges = np.r_[0, np.cumsum(seg)]
    return {"spont": [counts[a:b] for a, b in zip(edges[:-1], edges[1:])], "block": counts[T_sp:],
            "on_train": onsets[kinds == 0] - T_sp, "on_test": onsets[kinds == 1] - T_sp,
            "on_train2": onsets[kinds == 2] - T_sp, "cls": cls, "n_classes": K}
