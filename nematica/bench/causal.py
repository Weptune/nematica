"""Arc 4: the causal levels. Responses to optogenetic stimulation, scored in units of
worm-to-worm variation (see README, "Arc 4").

A *response set* holds, for one worm (or one model's prediction for that worm's
stimulations), the mean response of each class j to stimulating class i:

    r_ij(t) = (F_j(f + t) - mean F_j over the 5 s before f) / SD of F_j over the recording,
    t = 0 .. 30 s, averaged over events and over the members of class j (the stimulated
    neuron itself excluded).

Levels (distances between two response sets, over the pairs both measured):

    C1.pattern     1 - Pearson correlation of mean responses (0 to 15 s)
    C2.magnitude   |log ratio| of the median absolute mean response
    C3.kinetics    RMS difference of the mean normalised time course of the strongest
                   shared responses
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Callable, Sequence

import numpy as np
from scipy.stats import mannwhitneyu

from ..data.pumpprobe import PumpProbe
from .reference import worm_bootstrap

PRE_S = 5.0
POST_S = 30.0
AMP_S = 15.0
MIN_SHARED = 15


@dataclass
class ResponseSet:
    name: str
    group: str                                   # the real worm it belongs to or predicts
    traces: dict = field(default_factory=dict)   # (stim class, response class) -> (n_t,) mean trace
    counts: dict = field(default_factory=dict)   # same keys -> number of neuron-events
    dt: float = 0.5

    def amp(self, key) -> float:
        n = int(round(AMP_S / self.dt)) + 1
        return float(np.nanmean(self.traces[key][:n]))


def window(dt: float) -> tuple[int, int]:
    return int(round(PRE_S / dt)), int(round(POST_S / dt)) + 1


NORM = "recording"   # response units: "recording" = SD over the recording; "fluct" = SD of
                     # fluctuations within the 5 s pre-stimulus windows (insensitive to slow drift)


def unit_sd(rec: PumpProbe, norm: str | None = None) -> np.ndarray:
    norm = norm or NORM
    if norm == "recording":
        return np.nanstd(rec.x, axis=1)
    npre, _ = window(rec.dt)
    devs = [[] for _ in range(rec.x.shape[0])]
    for _, f in rec.stims:
        if f - npre < 0:
            continue
        pre = rec.x[:, f - npre:f]
        d = pre - np.nanmean(pre, axis=1, keepdims=True)
        for j in range(len(devs)):
            devs[j].append(d[j])
    return np.array([np.nanstd(np.concatenate(d)) if d else np.nan for d in devs])


def event_responses(rec: PumpProbe, stims: Sequence[tuple[int, int]] | None = None, x: np.ndarray | None = None,
                    min_pre: int = 5, min_post_frac: float = 0.8, norm: str | None = None):
    """Yields (stim neuron, stim class, response neuron, response class, trace) for every named
    neuron and stimulation, from `x` (default the recording; same shape)."""
    x = rec.x if x is None else x
    stims = rec.stims if stims is None else stims
    npre, npost = window(rec.dt)
    sd = unit_sd(rec, norm)
    named = [j for j, c in enumerate(rec.classes) if c]
    T = x.shape[1]
    for k, f in stims:
        ci = rec.classes[k]
        if not ci or f - npre < 0 or f + npost > T:
            continue
        for j in named:
            if j == k or not sd[j] > 0:
                continue
            pre = x[j, f - npre:f]
            post = x[j, f:f + npost]
            if np.isfinite(pre).sum() < min_pre or np.isfinite(post).mean() < min_post_frac:
                continue
            yield k, ci, j, rec.classes[j], (post - np.nanmean(pre)) / sd[j]


def response_set(rec: PumpProbe, name: str | None = None, stims=None, x: np.ndarray | None = None,
                 transform: Callable | None = None, norm: str | None = None) -> ResponseSet:
    acc: dict = {}
    for _, ci, _, cj, tr in event_responses(rec, stims, x, norm=norm):
        a = acc.setdefault((ci, cj), [])
        a.append(tr)
    rs = ResponseSet(name or rec.uid, rec.uid, dt=rec.dt)
    for key, trs in acc.items():
        m = np.nanmean(np.vstack(trs), axis=0)
        rs.traces[key] = transform(m) if transform else m
        rs.counts[key] = len(trs)
    return rs


def _shared(a: ResponseSet, b: ResponseSet):
    return sorted(set(a.traces) & set(b.traces))


def c_pattern(a: ResponseSet, b: ResponseSet) -> float:
    keys = _shared(a, b)
    if len(keys) < MIN_SHARED:
        return np.nan
    x = np.array([a.amp(k) for k in keys])
    y = np.array([b.amp(k) for k in keys])
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < MIN_SHARED or np.std(x[ok]) == 0 or np.std(y[ok]) == 0:
        return np.nan
    return float(1 - np.corrcoef(x[ok], y[ok])[0, 1])


def c_magnitude(a: ResponseSet, b: ResponseSet) -> float:
    keys = _shared(a, b)
    if len(keys) < MIN_SHARED:
        return np.nan
    x = np.nanmedian(np.abs([a.amp(k) for k in keys]))
    y = np.nanmedian(np.abs([b.amp(k) for k in keys]))
    if not (x > 0 and y > 0):
        return np.nan
    return float(abs(np.log(x / y)))


def _profile(rs: ResponseSet, keys) -> np.ndarray:
    out = []
    for k in keys:
        tr = rs.traces[k]
        m = np.nanmax(np.abs(tr))
        if m > 0 and np.isfinite(m):
            out.append(tr * np.sign(rs.amp(k) or 1.0) / m)
    return np.nanmean(np.vstack(out), axis=0)


def c_kinetics(a: ResponseSet, b: ResponseSet, top: float = 0.25) -> float:
    keys = _shared(a, b)
    if len(keys) < MIN_SHARED:
        return np.nan
    # strongest in both, by rank within each set, so the choice does not depend on scale
    from scipy.stats import rankdata
    ra = rankdata(np.nan_to_num(np.abs([a.amp(k) for k in keys]), nan=-1.0))
    rb = rankdata(np.nan_to_num(np.abs([b.amp(k) for k in keys]), nan=-1.0))
    s = np.minimum(ra, rb)
    n = max(5, int(top * len(keys)))
    chosen = [keys[i] for i in np.argsort(-s)[:n]]
    pa, pb = _profile(a, chosen), _profile(b, chosen)
    return float(np.sqrt(np.nanmean((pa - pb) ** 2)))


CAUSAL_LEVELS = {"C1.pattern": c_pattern, "C2.magnitude": c_magnitude, "C3.kinetics": c_kinetics}


def score_sets(name: str, system: Sequence[ResponseSet], real: Sequence[ResponseSet], alpha: float = 0.05,
               n_boot: int = 2000, levels: dict = CAUSAL_LEVELS) -> list[dict]:
    """The ruler's verdict rules (nematica.bench.reference.score_system) applied to response
    sets: a system set is compared with every real worm except the one it predicts."""
    rows = []
    groups = np.array([s.group for s in system])
    _, gidx = np.unique(groups, return_inverse=True)
    n = len(real)
    for m, fn in levels.items():
        d_bio = np.full((n, n), np.nan)
        for i, j in combinations(range(n), 2):
            d_bio[i, j] = d_bio[j, i] = fn(real[i], real[j])
        bio = d_bio[np.triu_indices(n, 1)]
        bio = bio[np.isfinite(bio)]
        d_sys = np.array([[fn(s, r) if s.group != r.group else np.nan for r in real] for s in system], float)
        d = d_sys[np.isfinite(d_sys)]
        if d.size == 0 or bio.size == 0:
            rows.append({"system": name, "metric": m, "verdict": "not scored"})
            continue
        boot = worm_bootstrap(d_sys, gidx, d_bio, n_boot=n_boot, seed=0)
        lo, hi = np.percentile(boot, [100 * alpha, 100 * (1 - alpha)]) if boot.size else (np.nan, np.nan)
        med = float(np.median(d))
        p05, p95 = float(np.percentile(bio, 5)), float(np.percentile(bio, 95))
        verdict = "outside" if (lo > 0 or med > p95) else "too typical" if (hi < 0 or med < p05) else "inside"
        rows.append({"system": name, "metric": m, "system_median": round(med, 4),
                     "bio_median": round(float(np.median(bio)), 4), "bio_p05": round(p05, 4),
                     "bio_p95": round(p95, 4), "percentile_of_bio": round(float(np.mean(bio <= med)), 3),
                     "shift_lo": round(float(lo), 4), "shift_hi": round(float(hi), 4),
                     "p_greater": round(float(mannwhitneyu(d, bio, alternative="greater").pvalue), 4),
                     "n_pairs": int(d.size), "verdict": verdict})
    return rows


# ------------------------------------------------------------------ calibrations
def shuffled_times(rec: PumpProbe, rng: np.random.Generator) -> ResponseSet:
    """Responses read at random frames instead of the stimulation frames (targets kept)."""
    npre, npost = window(rec.dt)
    fr = rng.integers(npre, rec.n_frames - npost, len(rec.stims))
    return response_set(rec, f"shuffled_times:{rec.uid}", stims=[(k, int(f)) for (k, _), f in zip(rec.stims, fr)])


def permuted_targets(rec: PumpProbe, rng: np.random.Generator) -> ResponseSet:
    """Which neuron was stimulated, permuted across this worm's stimulations."""
    ks = [k for k, _ in rec.stims]
    perm = rng.permutation(len(ks))
    return response_set(rec, f"permuted_targets:{rec.uid}", stims=[(ks[p], f) for p, (_, f) in zip(perm, rec.stims)])


def scaled(rec: PumpProbe, factor: float = 3.0) -> ResponseSet:
    return response_set(rec, f"scaled:{rec.uid}", transform=lambda m: factor * m)


def time_reversed(rec: PumpProbe) -> ResponseSet:
    return response_set(rec, f"time_reversed:{rec.uid}", transform=lambda m: m[::-1].copy())


CALIBRATIONS = {
    "real": lambda r, rng: response_set(r, f"real:{r.uid}"),
    "shuffled_times": shuffled_times,
    "permuted_targets": permuted_targets,
    "scaled_x3": lambda r, rng: scaled(r),
    "time_reversed": lambda r, rng: time_reversed(r),
}

EXPECTED = {   # designed outcomes (README, Arc 4); "either" = not designed
    "real": {"C1.pattern": "inside", "C2.magnitude": "inside", "C3.kinetics": "inside"},
    "shuffled_times": {"C1.pattern": "outside", "C2.magnitude": "either", "C3.kinetics": "either"},
    "permuted_targets": {"C1.pattern": "outside", "C2.magnitude": "inside", "C3.kinetics": "either"},
    "scaled_x3": {"C1.pattern": "inside", "C2.magnitude": "outside", "C3.kinetics": "inside"},
    "time_reversed": {"C1.pattern": "either", "C2.magnitude": "inside", "C3.kinetics": "outside"},
}


# ------------------------------------------------------------------ baselines
def atlas_mean(train: Sequence[ResponseSet], target: ResponseSet, min_worms: int = 2) -> ResponseSet:
    """Predicts each of `target`'s measured pairs by the mean trace over training worms."""
    out = ResponseSet(f"atlas_mean:{target.group}", target.group, dt=target.dt)
    for key in target.traces:
        trs = [s.traces[key] for s in train if key in s.traces]
        if len(trs) >= min_worms:
            out.traces[key] = np.nanmean(np.vstack(trs), axis=0)
            out.counts[key] = len(trs)
    return out
