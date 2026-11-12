"""The map's core measurements (docs/MAP.md, as amended 12 Nov 2026, amendment 2), the same for any system.

Input: activity X, shape (time, units), already passed through a recording model (recording.py). Time is in
samples. Every measurement is dimensionless: time enters only through tau_med, the system's median unit
timescale (an exponential fit to the autocorrelation from lag 1, so white measurement noise does not shorten
it; floored at TAU_FLOOR samples, the sampling resolution). Shared measurements are compared with a
circular-shift null that keeps each unit's own timescale but breaks timing between units.

`segments` (optional): sample indices where a recording restarts (e.g. a language model's context); windows
never straddle them.
"""
from __future__ import annotations

import numpy as np

MEASURES = ("spectrum_steepness", "shared_fraction", "slow_fraction", "timescale_spread",
            "coupling_spread", "drift", "sparsity")          # shared_dim dropped (amendment 2): never recovered its property
TAU_FLOOR = 2.0                     # samples; below this a system is resolution-limited (flagged)
N_UNITS, N_DRAWS, WINDOW_TAU = 50, 40, 150
NULL_SHIFT_TAU = 20                 # circular shifts of at least this many tau_med


def _z(X):
    X = np.asarray(X, float)
    sd = X.std(0)
    keep = sd > 1e-9
    return (X[:, keep] - X[:, keep].mean(0)) / sd[keep]


def _acov(Z, max_lag):
    T = len(Z)
    F = np.fft.rfft(Z, n=2 * T, axis=0)
    return np.fft.irfft(F * np.conj(F), axis=0)[:max_lag + 1] / T


def unit_timescales(X, max_lag=None):
    """Autocorrelation half-life of each unit (samples), robust to white measurement noise: the signal's
    lag-0 autocovariance is extrapolated from lags 1 and 2 (an exponential through them), and the half-life
    is the first lag at which the autocovariance falls below half of it (linear interpolation; lag 0 counts
    as the extrapolated value). nan if ac(1) <= 0.01 ac(0) or it never falls."""
    Z = _z(X)
    T, N = Z.shape
    max_lag = max_lag or min(T // 4, 4000)
    ac = _acov(Z, max_lag)
    out = np.full(N, np.nan)
    for i in np.where(ac[1] > 0.01 * ac[0])[0]:
        a1, a2 = ac[1, i], ac[2, i]
        rho = min(max(a2 / a1, 1e-3), 0.999) if a1 > 0 else 1e-3
        s0 = min(a1 / rho, ac[0, i])                     # extrapolated signal variance (never above total)
        r = np.concatenate([[1.0], ac[1:, i] / s0])
        below = r < 0.5
        if not below.any():
            continue
        k = int(np.argmax(below))
        out[i] = (k - 1) + (r[k - 1] - 0.5) / (r[k - 1] - r[k])
    return out


def tau_med(X):
    t = unit_timescales(X)
    return float(np.nanmedian(t)) if np.isfinite(t).any() else np.nan


def noise_fraction(X):
    """Share of each unit's variance that is white: lag-0 excess over the exponential through lags 1 and 2."""
    Z = _z(X)
    ac = _acov(Z, 3)
    rho = np.clip(ac[2] / np.where(ac[1] > 0, ac[1], np.nan), 1e-3, 0.999)
    signal0 = np.where(ac[1] > 0, ac[1] / rho, 0.0)
    return np.nan_to_num(np.clip(1 - signal0 / ac[0], 0, 1), nan=1.0)


def _shift(Z, rng, min_shift):
    T = len(Z)
    lo = int(min(max(min_shift, 1), T // 3))
    return np.column_stack([np.roll(Z[:, i], rng.integers(lo, T - lo)) for i in range(Z.shape[1])])


def _chunks(T, t):
    chunk = max(int(10 * max(t, 1.0)), 10)
    idx = np.arange(T) // chunk
    return idx % 2 == 0, idx % 2 == 1


def svca(Z, t, rng, n_comp=None):
    """Shared variance component analysis (Stringer et al. 2019): reliable variance per shared dimension."""
    T, N = Z.shape
    p = rng.permutation(N)
    a, b = p[: N // 2], p[N // 2: 2 * (N // 2)]
    train, test = _chunks(T, t)
    k = n_comp or min(len(a), len(b), max(train.sum() // 4, 1))
    C = Z[train][:, a].T @ Z[train][:, b] / max(train.sum(), 1)
    U, S, Vt = np.linalg.svd(C, full_matrices=False)
    pa, pb = Z[test][:, a] @ U[:, :k], Z[test][:, b] @ Vt[:k].T
    return (pa * pb).mean(0)


def _shared_with_null(X, t, rng, n_null=3):
    Z = _z(X)
    shared = svca(Z, t, np.random.default_rng(int(rng.integers(1 << 30))))
    null = np.concatenate([svca(_shift(Z, rng, NULL_SHIFT_TAU * t), t, np.random.default_rng(int(rng.integers(1 << 30))),
                                n_comp=len(shared)) for _ in range(n_null)])
    return shared, float(np.quantile(null, 0.95))


def spectrum_steepness(X, t=None, rng=None, ranks=3):
    """Slope of log reliable shared variance against log rank over ranks 1..`ranks` (fixed). nan unless every
    one of those ranks beats the shift null (no shared spectrum to describe)."""
    rng = rng or np.random.default_rng(0)
    t = t if t is not None else max(tau_med(X), TAU_FLOOR)
    shared, thr = _shared_with_null(X, t, rng)
    if len(shared) < ranks or not (shared[:ranks] > max(thr, 0)).all():
        return np.nan
    r = np.arange(1, ranks + 1)
    return float(-np.polyfit(np.log(r), np.log(shared[:ranks]), 1)[0])


def shared_dim(X, t=None, rng=None):
    """Participation ratio of the shared dimensions that beat the shift null, as a share of half-population
    size; 0 when none do."""
    rng = rng or np.random.default_rng(0)
    t = t if t is not None else max(tau_med(X), TAU_FLOOR)
    shared, thr = _shared_with_null(X, t, rng)
    lam = shared[shared > max(thr, 0)]
    if len(lam) == 0:
        return 0.0
    return float(lam.sum() ** 2 / (lam ** 2).sum() / (X.shape[1] // 2))


def _pred_r2(Z, tr, te, k):
    N = Z.shape[1]
    r2 = []
    for g in np.array_split(np.arange(N), max(1, int(np.ceil(N / max(1, N // 10))))):
        others = np.setdiff1d(np.arange(N), g)
        Vt = np.linalg.svd(Z[tr][:, others], full_matrices=False)[2]
        P = Vt[:k].T
        A_tr, A_te = Z[tr][:, others] @ P, Z[te][:, others] @ P
        W = np.linalg.lstsq(A_tr, Z[tr][:, g], rcond=None)[0]
        y = Z[te][:, g]
        r2.extend(1 - ((y - A_te @ W) ** 2).sum(0) / ((y - y.mean(0)) ** 2).sum(0))
    return np.array(r2)


def shared_fraction(X, t=None, rng=None, k=5):
    """Median held-out share of a unit's variance predicted from the top `k` patterns of the other units,
    minus the same with every unit circularly shifted against the others (the overfitting baseline)."""
    rng = rng or np.random.default_rng(0)
    Z = _z(X)
    t = t if t is not None else max(tau_med(Z), TAU_FLOOR)
    tr, te = _chunks(len(Z), t)
    real = np.median(_pred_r2(Z, tr, te, k))
    null = np.median(np.concatenate([_pred_r2(_shift(Z, rng, NULL_SHIFT_TAU * t), tr, te, k) for _ in range(3)]))
    return float(real - null)


def slow_fraction(X, t=None, lag_tau=10.0):
    """Slow memory (amendment 2; replaces the spectral slow share, which a single fast process already put
    near 0.45): the median over units of the autocorrelation at lag `lag_tau` x tau_med, relative to the
    unit's signal variance (extrapolated from lags 1 and 2, so white noise does not count). About 0.001 for
    a single-timescale process; large when activity carries components far slower than the typical unit."""
    Z = _z(X)
    t = t if t is not None else max(tau_med(Z), TAU_FLOOR)
    L = int(round(lag_tau * t))
    if L < 2 or len(Z) < 5 * L:
        return np.nan
    ac = _acov(Z, L + 1)
    rho = np.clip(ac[2] / np.where(ac[1] > 0, ac[1], np.nan), 1e-3, 0.999)
    s0 = np.minimum(ac[1] / rho, ac[0])
    v = ac[L] / s0
    return float(np.nanmedian(v))


def timescale_spread(X):
    """Interquartile range of log10 unit timescales."""
    tt = unit_timescales(X)
    tt = tt[np.isfinite(tt) & (tt > 0)]
    if len(tt) < 5:
        return np.nan
    q1, q3 = np.percentile(np.log10(tt), [25, 75])
    return float(q3 - q1)


def coupling_spread(X):
    """Interquartile range of population coupling (each unit's correlation with the sum of the others)."""
    Z = _z(X)
    tot = Z.sum(1)
    c = np.array([np.corrcoef(Z[:, i], tot - Z[:, i])[0, 1] for i in range(Z.shape[1])])
    q1, q3 = np.nanpercentile(c, [25, 75])
    return float(q3 - q1)


def drift(X, t=None, blocks=8):
    """Drift inside a window: the window is cut into `blocks` equal blocks; dissimilarity 1 - r(off-diagonal
    correlations) between every pair of blocks is regressed on their separation in tau_med; returns the slope
    per 100 tau_med."""
    Z = _z(X)
    t = t if t is not None else max(tau_med(Z), TAU_FLOOR)
    L = len(Z) // blocks
    if L < 8:
        return np.nan
    iu = np.triu_indices(Z.shape[1], 1)
    C = np.array([np.nan_to_num(np.corrcoef(Z[k * L:(k + 1) * L].T)[iu]) for k in range(blocks)])
    C = C - C.mean(1, keepdims=True)
    C /= np.linalg.norm(C, axis=1, keepdims=True) + 1e-12
    R = C @ C.T
    i, j = np.triu_indices(blocks, 1)
    return float(np.polyfit((j - i) * L / t, 1 - R[i, j], 1)[0] * 100)


def sparsity(X):
    """Median excess kurtosis of unit activity."""
    Z = _z(X)
    return float(np.median((Z ** 4).mean(0) - 3))


def _spans(T, segments):
    b = sorted(set([0] + [s for s in (segments or []) if 0 < s < T] + [T]))
    return list(zip(b[:-1], b[1:]))


def measure_matched(X, seed=0, n_units=N_UNITS, n_draws=N_DRAWS, window_tau=WINDOW_TAU, only=None,
                    segments=None, tau_floor=TAU_FLOOR):
    """Every system measured the same way: tau_med from all units (floored at tau_floor samples); then n_draws
    draws of n_units units and one window of window_tau * tau_med samples inside one segment; window
    measurements averaged over draws. Slow fraction uses the drawn units over the longest segment.
    Returns means, SDs over draws, tau_med and flags."""
    X = np.asarray(X, float)
    X = X[:, X.std(0) > 1e-9]
    rng = np.random.default_rng(seed)
    t_raw = tau_med(X)
    if not np.isfinite(t_raw) or X.shape[1] < n_units:
        return {"tau_med": t_raw, "error": "too few units or no timescale"}
    t = max(t_raw, tau_floor)
    W = int(round(window_tau * t))
    spans = [(a, b) for a, b in _spans(len(X), segments) if b - a >= W]
    if not spans:
        return {"tau_med": t_raw, "error": f"no stretch of {window_tau} tau_med"}
    longest = max(_spans(len(X), segments), key=lambda ab: ab[1] - ab[0])
    names = only or MEASURES
    vals = {m: [] for m in names}
    for d in range(n_draws):
        u = rng.choice(X.shape[1], n_units, replace=False)
        a, b = spans[int(rng.integers(len(spans)))]
        s0 = int(rng.integers(a, b - W + 1))
        Y = X[s0:s0 + W, u]
        r = np.random.default_rng(seed * 1000 + d)
        for m in names:
            try:
                if m == "slow_fraction":
                    v = slow_fraction(X[longest[0]:longest[1], u], t=t)
                elif m in ("spectrum_steepness", "shared_dim", "shared_fraction"):
                    v = globals()[m](Y, t=t, rng=r)
                elif m == "drift":
                    v = drift(Y, t=t)
                else:
                    v = globals()[m](Y)
            except Exception:  # noqa: BLE001
                v = np.nan
            vals[m].append(v)
    out = {"tau_med": t_raw, "tau_used": t, "resolution_limited": bool(t_raw < tau_floor), "window": W}
    for m in names:
        a_ = np.array(vals[m], float)
        out[m] = float(np.nanmean(a_)) if np.isfinite(a_).sum() >= max(n_draws // 2, 1) else np.nan
        out[m + "_sd"] = float(np.nanstd(a_)) if np.isfinite(a_).sum() > 1 else np.nan
    return out
