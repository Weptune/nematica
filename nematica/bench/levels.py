"""Benchmark metrics. Each is a distance d(a, b) between two BenchSamples (lower = more alike),
computed only on neuron classes observed in both. One metric per level is primary.

Level 1, single neuron:
    L1.distribution  median over shared classes of the Wasserstein-1 distance between
                     z-scored activity distributions                         (primary)
    L1.timescale     median over shared classes of |log(tau_a / tau_b)|, tau = time for the
                     autocorrelation to fall to 0.5
Level 2, population:
    L2.correlation   1 - Pearson r between the off-diagonal entries of the two class
                     correlation matrices                                     (primary)
    L2.dimension     |log(PR_a / PR_b)|, PR = participation ratio of the covariance spectrum
Level 4, dynamics:
    L4.leadlag       which neuron classes lead and which follow: 1 - Pearson r between the
                     antisymmetric parts of the lagged cross-correlation matrices,
                     C(tau) - C(tau)^T, at lags of about 2 and 6 s              (primary)
                     (One-step VAR "transfer" was tried first and dropped: on real worms a
                     VAR(1) predicts held-out frames worse than independent AR(1) fits, so
                     frame-to-frame interactions do not generalise at 1.67 Hz.)
    L4.dwell         Kolmogorov-Smirnov distance between durations of high-AVA bouts
                     (the reversal command state), pooled per sample
Level 5, behaviour coupling:
    L5.encoding      1 - Pearson r between per-class correlations with velocity (primary)
    L5.reversal      1 - Pearson r between per-class activity differences during vs outside
                     reversals
Levels 4 and 5 need enough shared classes; L4.dwell needs AVA; Level 5 needs behaviour.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import ks_2samp, wasserstein_distance

from .sample import BenchSample

MIN_SHARED = 8          # fewer shared classes than this -> the pair is not scored
MAX_LAG_S = 120.0


def shared(a: BenchSample, b: BenchSample) -> np.ndarray:
    if a.classes != b.classes:
        raise ValueError("samples are on different canonical indices")
    return np.flatnonzero(a.observed & b.observed)


def half_decay_time(z: np.ndarray, dt: float, max_lag_s: float = MAX_LAG_S) -> float:
    z = z - z.mean()
    n = z.size
    f = np.fft.rfft(z, 2 * n)
    acf = np.fft.irfft(f * np.conj(f))[:n]
    if acf[0] <= 0:
        return np.nan
    acf = acf / acf[0]
    max_lag = min(n - 1, int(max_lag_s / dt))
    below = np.flatnonzero(acf[: max_lag + 1] < 0.5)
    if below.size == 0:
        return max_lag * dt
    k = below[0]
    # linear interpolation between lag k-1 and k
    a0, a1 = acf[k - 1], acf[k]
    frac = (a0 - 0.5) / (a0 - a1) if a0 != a1 else 0.0
    return (k - 1 + frac) * dt


def participation_ratio(x: np.ndarray) -> float:
    c = np.cov(x)
    ev = np.clip(np.linalg.eigvalsh(c), 0, None)
    return float(ev.sum() ** 2 / (ev ** 2).sum()) if ev.sum() > 0 else np.nan


def l1_distribution(a: BenchSample, b: BenchSample) -> float:
    idx = shared(a, b)
    if idx.size < MIN_SHARED:
        return np.nan
    return float(np.median([wasserstein_distance(a.x[i], b.x[i]) for i in idx]))


def l1_timescale(a: BenchSample, b: BenchSample) -> float:
    idx = shared(a, b)
    if idx.size < MIN_SHARED:
        return np.nan
    ta = np.array([half_decay_time(a.x[i], a.dt) for i in idx])
    tb = np.array([half_decay_time(b.x[i], b.dt) for i in idx])
    ok = (ta > 0) & (tb > 0)
    return float(np.median(np.abs(np.log(ta[ok] / tb[ok])))) if ok.any() else np.nan


def _corr_offdiag(x: np.ndarray) -> np.ndarray:
    c = np.corrcoef(x)
    iu = np.triu_indices_from(c, k=1)
    return c[iu]


def l2_correlation(a: BenchSample, b: BenchSample) -> float:
    idx = shared(a, b)
    if idx.size < MIN_SHARED:
        return np.nan
    ca, cb = _corr_offdiag(a.x[idx]), _corr_offdiag(b.x[idx])
    return float(1.0 - np.corrcoef(ca, cb)[0, 1])


def l2_dimension(a: BenchSample, b: BenchSample) -> float:
    idx = shared(a, b)
    if idx.size < MIN_SHARED:
        return np.nan
    pa, pb = participation_ratio(a.x[idx]), participation_ratio(b.x[idx])
    return float(abs(np.log(pa / pb)))


# ----------------------------------------------------------------------------- Level 4

LEAD_LAGS_S = (1.8, 6.0)


def _lagged_antisym(x: np.ndarray, dt: float) -> np.ndarray:
    """Concatenated upper-triangle entries of C(tau) - C(tau)^T for each lag."""
    T = x.shape[1]
    iu = np.triu_indices(x.shape[0], k=1)
    out = []
    for lag_s in LEAD_LAGS_S:
        k = max(1, int(round(lag_s / dt)))
        a, b = x[:, : T - k], x[:, k:]
        a = (a - a.mean(1, keepdims=True)) / a.std(1, keepdims=True)
        b = (b - b.mean(1, keepdims=True)) / b.std(1, keepdims=True)
        C = a @ b.T / a.shape[1]            # C[i, j] = corr(x_i(t), x_j(t + lag)): i leads j
        out.append((C - C.T)[iu])
    return np.concatenate(out)


def l4_leadlag(a: BenchSample, b: BenchSample) -> float:
    idx = shared(a, b)
    if idx.size < MIN_SHARED:
        return np.nan
    la, lb = _lagged_antisym(a.x[idx], a.dt), _lagged_antisym(b.x[idx], b.dt)
    if np.std(la) == 0 or np.std(lb) == 0:
        return np.nan
    return float(1 - np.corrcoef(la, lb)[0, 1])


def ava_bouts(s: BenchSample, threshold: float = 0.75) -> np.ndarray:
    """Durations (s) of bouts where z-scored AVA exceeds `threshold` (reversal command state)."""
    if "AVA" not in s.classes:
        return np.array([])
    i = s.classes.index("AVA")
    if not s.observed[i]:
        return np.array([])
    high = s.x[i] > threshold
    edges = np.diff(np.concatenate([[0], high.astype(int), [0]]))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    return (ends - starts) * s.dt


def l4_dwell(a: BenchSample, b: BenchSample) -> float:
    ba, bb = ava_bouts(a), ava_bouts(b)
    if ba.size < 5 or bb.size < 5:
        return np.nan
    return float(ks_2samp(ba, bb).statistic)


# ----------------------------------------------------------------------------- Level 5

def _encoding(s: BenchSample, key: str, idx: np.ndarray, kind: str) -> np.ndarray | None:
    beh = s.behaviour.get(key)
    if beh is None or len(beh) != s.x.shape[1] or not np.isfinite(beh).all() or np.std(beh) == 0:
        return None
    if kind == "corr":
        bz = (beh - beh.mean()) / beh.std()
        return (s.x[idx] * bz).mean(axis=1)
    on = beh > 0.5
    if on.sum() < 5 or (~on).sum() < 5:
        return None
    return s.x[idx][:, on].mean(axis=1) - s.x[idx][:, ~on].mean(axis=1)


def _l5(a: BenchSample, b: BenchSample, key: str, kind: str) -> float:
    idx = shared(a, b)
    if idx.size < MIN_SHARED:
        return np.nan
    ea, eb = _encoding(a, key, idx, kind), _encoding(b, key, idx, kind)
    if ea is None or eb is None:
        return np.nan
    return float(1 - np.corrcoef(ea, eb)[0, 1])


def l5_encoding(a: BenchSample, b: BenchSample) -> float:
    return _l5(a, b, "velocity", "corr")


def l5_reversal(a: BenchSample, b: BenchSample) -> float:
    return _l5(a, b, "reversing", "diff")




# ---- behaviour: reversal statistics ------------------------------------------------------
# Added after closed-loop work showed that thresholding a noisy reversal channel doubles the
# onset rate without any level noticing. Needs behaviour["reversing"] (0/1 per frame).

def _reversal_bouts(s: BenchSample):
    rv = s.behaviour.get("reversing")
    if rv is None or len(rv) < 10:
        return None
    r = (np.asarray(rv) > 0.5).astype(int)
    edges = np.diff(np.concatenate([[0], r, [0]]))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    minutes = len(r) * s.dt / 60
    return len(starts) / minutes, (ends - starts) * s.dt


def b_reversal_rate(a: BenchSample, b: BenchSample) -> float:
    """|log ratio| of reversal onsets per minute."""
    ra, rb = _reversal_bouts(a), _reversal_bouts(b)
    if ra is None or rb is None or ra[0] == 0 or rb[0] == 0:
        return np.nan
    return float(abs(np.log(ra[0] / rb[0])))


def b_reversal_duration(a: BenchSample, b: BenchSample) -> float:
    """KS distance between reversal duration distributions (>= 5 reversals each)."""
    from scipy.stats import ks_2samp
    ra, rb = _reversal_bouts(a), _reversal_bouts(b)
    if ra is None or rb is None or len(ra[1]) < 5 or len(rb[1]) < 5:
        return np.nan
    return float(ks_2samp(ra[1], rb[1]).statistic)


# Level 6 (environment) is tested at the population level: see environment.py.

LEVELS = {
    "L1.distribution": {"level": 1, "fn": l1_distribution, "primary": True,
                        "what": "activity value distributions per neuron class"},
    "L1.timescale": {"level": 1, "fn": l1_timescale, "primary": False,
                     "what": "autocorrelation half-decay time per neuron class"},
    "L2.correlation": {"level": 2, "fn": l2_correlation, "primary": True,
                       "what": "which neuron classes move together"},
    "L2.dimension": {"level": 2, "fn": l2_dimension, "primary": False,
                     "what": "dimensionality (participation ratio)"},
    "L4.leadlag": {"level": 4, "fn": l4_leadlag, "primary": True,
                   "what": "which neuron classes lead and which follow"},
    "L4.dwell": {"level": 4, "fn": l4_dwell, "primary": False,
                 "what": "durations of the AVA-high (reversal command) state"},
    "L5.encoding": {"level": 5, "fn": l5_encoding, "primary": True,
                    "what": "which neuron classes track velocity"},
    "L5.reversal": {"level": 5, "fn": l5_reversal, "primary": False,
                    "what": "which neuron classes change during reversals"},
    "B.rev_rate": {"level": 5, "fn": b_reversal_rate, "primary": False,
                   "what": "how often the worm starts a reversal"},
    "B.rev_duration": {"level": 5, "fn": b_reversal_duration, "primary": False,
                       "what": "how long reversals last"},
}
