"""The map's core measurements (docs/MAP.md, amendments 2 to 5), the same for any system.

Input: activity X, shape (time, units), already passed through a recording model (recording.py). Time is in
samples. Every measurement is dimensionless: time enters only through tau_med, the system's timescale (the
half-life of the population autocorrelation relative to the extrapolated signal variance, so white
measurement noise does not shorten it; floored at TAU_FLOOR samples, the sampling resolution). Shared
measurements are compared with a circular-shift null that keeps each unit's own timescale but breaks timing
between units.

`segments` (optional): sample indices where a recording restarts (e.g. a language model's context, a gap
between rest stretches); windows never straddle them and autocovariances never cross them.
"""
from __future__ import annotations

import numpy as np

MEASURES = ("spectrum_steepness", "shared_fraction", "slow_fraction", "timescale_spread",
            "coupling_spread", "drift", "sparsity")          # shared_dim dropped (amendment 2): never recovered its property
TAU_FLOOR = 2.0                     # samples; below this a system is resolution-limited (flagged)
N_UNITS, N_DRAWS, WINDOW_TAU = 50, 40, 150
SPIKE_WINDOW_TAU = 1000             # amendment 11: windows for spike counts (about 90 to 460 spikes per unit)
NULL_SHIFT_TAU = 20                 # circular shifts of at least this many tau_med


def _z(X):
    X = np.asarray(X, float)
    sd = X.std(0)
    keep = sd > 1e-9
    return (X[:, keep] - X[:, keep].mean(0)) / sd[keep]


def _acov(Z, max_lag, block=256):
    """Autocovariance by FFT, computed for blocks of units (memory; the same values as all units at once)."""
    T = len(Z)
    out = np.empty((max_lag + 1, Z.shape[1]))
    for a in range(0, Z.shape[1], block):
        F = np.fft.rfft(Z[:, a:a + block], n=2 * T, axis=0)
        out[:, a:a + block] = np.fft.irfft(F * np.conj(F), axis=0)[:max_lag + 1] / T
    return out


def _acov_seg(Z, max_lag, segments=None):
    """Autocovariance pooled over segments (amendment 5): each segment is demeaned, lag products are summed
    over every segment longer than the lag, and each lag is divided by its own number of pairs, so every
    stretch contributes and lags never cross a boundary. Lags with no pairs are nan."""
    spans = _spans(len(Z), segments)
    num = np.zeros((max_lag + 1, Z.shape[1]))
    pairs = np.zeros(max_lag + 1)
    for a, b in spans:
        n = b - a
        if n < 2:
            continue
        Y = Z[a:b] - Z[a:b].mean(0)
        L = min(max_lag, n - 1)
        num[:L + 1] += _acov(Y, L) * n                  # _acov divides by n; undo to get sums of products
        pairs[:L + 1] += n - np.arange(L + 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return num / np.where(pairs > 0, pairs, np.nan)[:, None]


def detrend(X, segments=None):
    """Amendment 5: remove each unit's least-squares linear trend within each segment (bleaching and slow
    baseline drift). Applied in the calcium group to every recording, brain and AI alike, before instrument
    numbers and measures."""
    X = np.asarray(X, float).copy()
    for a, b in _spans(len(X), segments):
        if b - a < 3:
            continue
        t = np.arange(b - a, dtype=float)
        t -= t.mean()
        Y = X[a:b]
        X[a:b] = Y - np.outer(t, (t @ (Y - Y.mean(0))) / (t @ t))
    return X


def _signal_var(ac):
    """Amendment 5 (F1 again): each unit's signal variance (autocovariance at lag 0 without white noise),
    from the cubic through lags 1 to 4 extrapolated to lag 0, capped at the total variance. On calcium-shaped,
    AR and Poisson test signals the resulting noise share is within 0.035 of the truth (worst: calcium whose
    indicator decay is comparable to the native timescale, read low). Used by the timescale, the noise share
    and slow memory, so they agree."""
    V = np.vander(np.array([1.0, 2.0, 3.0, 4.0]), 4)     # columns x^3, x^2, x, 1
    coef = np.linalg.solve(V, ac[1:5])
    return np.minimum(coef[3], ac[0])


def unit_timescales(X, max_lag=None, segments=None):
    """Autocorrelation half-life of each unit (samples), robust to white measurement noise: autocovariance is
    divided by the extrapolated signal variance (_signal_var) and the half-life is the first lag at which it
    falls below 0.5 (linear interpolation; lag 0 counts as 1). nan if ac(1) <= 0.01 ac(0), the extrapolated
    signal variance is not positive, or it never falls."""
    Z = _z(X)
    T, N = Z.shape
    longest = max(b - a for a, b in _spans(T, segments))
    max_lag = max(min(max_lag or longest // 4, 4000), 5)
    ac = _acov_seg(Z, max_lag, segments)
    s0 = _signal_var(ac)
    out = np.full(N, np.nan)
    for i in np.where((ac[1] > 0.01 * ac[0]) & (s0 > 0))[0]:
        out[i] = _half_life(np.concatenate([[1.0], ac[1:, i] / s0[i]]))
    return out


def _half_life(r):
    below = r < 0.5
    if not below.any():
        return np.nan
    k = int(np.argmax(below))
    return (k - 1) + (r[k - 1] - 0.5) / (r[k - 1] - r[k])


def tau_med(X, segments=None):
    """The system's timescale (amendment 4): half-life of the population autocorrelation, i.e. the
    autocovariance of the standardised units averaged over units, divided by the averaged extrapolated signal
    variance. It replaces the median of per-unit half-lives, which reads 5 to 20 times too short on sparse
    spike counts at real noise levels (white share 0.95 to 0.99) because each unit's own estimate is then
    mostly noise; on clean or moderately noisy data the two agree within a few percent. The name is kept."""
    Z = _z(X)
    T = len(Z)
    longest = max(b - a for a, b in _spans(T, segments))
    L = max(min(longest // 4, 4000), 5)
    ac = _acov_seg(Z, L, segments).mean(1)
    s0 = float(_signal_var(ac[:, None])[0])
    if not np.isfinite(s0) or s0 <= 0 or ac[1] <= 0:
        return np.nan
    return float(_half_life(np.concatenate([[1.0], ac[1:] / s0])))


def noise_fraction(X, segments=None):
    """Share of each unit's variance that is white (amendment 4): 1 - _signal_var / total. On synthetic tests
    the error is at most about 0.02 to 0.04 for smooth (calcium-like), held and fast signals and Poisson
    counts (MAP.md, amendment 4)."""
    Z = _z(X)
    ac = _acov_seg(Z, 5, segments)
    return np.nan_to_num(np.clip(1 - _signal_var(ac) / ac[0], 0, 1), nan=1.0)


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


def slow_fraction(X, t=None, lag_tau=10.0, segments=None, min_tau=100.0):
    """Slow memory (amendment 2, restated in amendment 3): the median over units of the autocorrelation at
    lag `lag_tau` x tau_med, relative to the signal variance (extrapolated from lags 1 to 4, amendment 5). It measures a
    *mixture of timescales*: about 0.001 for a single timescale, larger when components far slower than the
    median unit are present. A system dominated by one slow timescale scores like a fast one (the slow
    timescale then is the median). Autocovariances are pooled over segments (pair-weighted); needs at
    least `min_tau` tau_med of data in segments longer than 5 x the lag."""
    Z = _z(X)
    t = t if t is not None else max(tau_med(Z), TAU_FLOOR)
    L = int(round(lag_tau * t))
    if L < 2:
        return np.nan
    spans = [(a, b) for a, b in _spans(len(Z), segments) if b - a >= 5 * L]
    if sum(b - a for a, b in spans) < min_tau * t:
        return np.nan
    starts = list(np.cumsum([b - a for a, b in spans])[:-1])
    ac = _acov_seg(np.vstack([Z[a:b] for a, b in spans]), max(L + 1, 5), starts)
    s0 = _signal_var(ac)                                 # amendment 4: same estimator as the timescales
    s0 = np.where(s0 > 0, s0, np.nan)
    return float(np.nanmedian(ac[L] / s0))


def timescale_spread(X):
    """Interquartile range of log10 unit timescales."""
    tt = unit_timescales(X)
    tt = tt[np.isfinite(tt) & (tt > 0)]
    if len(tt) < 5:
        return np.nan
    q1, q3 = np.percentile(np.log10(tt), [25, 75])
    return float(q3 - q1)


MAX_NOISE_FOR_DISATTENUATION = 0.8


def coupling_spread(X):
    """Interquartile range of population coupling (each unit's correlation with the sum of the others),
    disattenuated for each unit's white-noise share (divided by sqrt(1 - noise), amendment 4); nan when the
    median noise share is above MAX_NOISE_FOR_DISATTENUATION."""
    Z = _z(X)
    nf = noise_fraction(Z)
    if np.median(nf) > MAX_NOISE_FOR_DISATTENUATION:
        return np.nan
    tot = Z.sum(1)
    c = np.array([np.corrcoef(Z[:, i], tot - Z[:, i])[0, 1] for i in range(Z.shape[1])])
    c = c / np.sqrt(np.clip(1 - nf, 1e-3, None))
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


def _is_counts(X):
    X = np.asarray(X)
    return bool(X.size and (X >= 0).all() and np.allclose(X, np.round(X)))


def sparsity(X):
    """Median excess kurtosis of unit activity, disattenuated for white noise (the excess kurtosis of signal
    plus independent Gaussian noise is the signal's times (1 - noise share)^2); nan when the median noise share
    is above MAX_NOISE_FOR_DISATTENUATION. Amendment 10: **not defined for spike counts** (nan): the
    factorial-moment estimate of amendment 4 was unusable at 0.1 to 0.5 spikes per bin and depended on the
    spread of rates (review 13, item 5)."""
    X = np.asarray(X, float)
    if _is_counts(X):
        return np.nan
    Z = _z(X)
    nf = noise_fraction(Z)
    if np.median(nf) > MAX_NOISE_FOR_DISATTENUATION:
        return np.nan
    k = (Z ** 4).mean(0) - 3
    return float(np.median(k / np.clip(1 - nf, 0.2, None) ** 2))


def _spans(T, segments):
    b = sorted(set([0] + [s for s in (segments or []) if 0 < s < T] + [T]))
    return list(zip(b[:-1], b[1:]))


def measure_matched(X, seed=0, n_units=N_UNITS, n_draws=N_DRAWS, window_tau=None, only=None,
                    segments=None, tau_floor=TAU_FLOOR):
    """Every system measured the same way: tau_med from all units (floored at tau_floor samples); then n_draws
    draws of n_units units and one window of window_tau * tau_med samples inside one segment; window
    measurements averaged over draws. Slow fraction uses the drawn units over the longest segment.
    Returns means, SDs over draws, tau_med and flags."""
    X = np.asarray(X, float)
    if window_tau is None:                               # amendment 11: spike counts get longer windows
        window_tau = SPIKE_WINDOW_TAU if _is_counts(X) else WINDOW_TAU
    X = X[:, X.std(0) > 1e-9]
    rng = np.random.default_rng(seed)
    t_raw = tau_med(X, segments=segments)
    if not np.isfinite(t_raw) or X.shape[1] < n_units:
        return {"tau_med": t_raw, "error": "too few units or no timescale"}
    t = max(t_raw, tau_floor)
    W = int(round(window_tau * t))
    spans = [(a, b) for a, b in _spans(len(X), segments) if b - a >= W]
    if not spans:
        return {"tau_med": t_raw, "error": f"no stretch of {window_tau} tau_med"}
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
                    v = slow_fraction(X[:, u], t=t, segments=segments)
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
        out[m] = float(np.nanmean(a_)) if np.isfinite(a_).sum() >= max(int(0.8 * n_draws), 1) else np.nan
        out[m + "_sd"] = float(np.nanstd(a_)) if np.isfinite(a_).sum() > 1 else np.nan
    return out


def split_half_se(X, seed=0, n_splits=5, segments=None, **kw):
    """C3 (amendments 4 and 10): standard error of each matched value from disjoint halves, SE^2 = mean over
    n_splits random splits of (a - b)^2 / 4. Halves: two unit pools when there are at least 2 x n_units
    units; otherwise the first and second half of the recording when each half is at least
    1.2 x window_tau timescales; otherwise (amendment 10, review 13 item 9) two unit pools of h = floor(n/2)
    units each (at least 20), measured with n_units = h, and the SE scaled by sqrt(h / n_units) (the SE of a
    mean over units shrinks as 1/sqrt(units)). Missing values are nan (they fail the gate)."""
    X = np.asarray(X, float)
    X = X[:, X.std(0) > 1e-9]
    n = kw.get("n_units", N_UNITS)
    w = kw.get("window_tau") or (SPIKE_WINDOW_TAU if _is_counts(X) else WINDOW_TAU)
    t = tau_med(X, segments=segments)
    sq = {m: [] for m in MEASURES}
    scale = 1.0
    for k in range(n_splits):
        rng = np.random.default_rng(seed + 991 + k)
        kw2 = dict(kw)
        if X.shape[1] >= 2 * n:
            p = rng.permutation(X.shape[1]); h = X.shape[1] // 2
            A, Bm = X[:, p[:h]], X[:, p[h:2 * h]]
            sa = sb = segments
        elif np.isfinite(t) and len(X) / 2 >= 1.2 * w * t:
            h = len(X) // 2
            A, Bm = X[:h], X[h:2 * h]
            sa = [s_ for s_ in (segments or []) if s_ < h]
            sb = [s_ - h for s_ in (segments or []) if s_ > h]
        else:
            h = X.shape[1] // 2
            if h < 20:
                return {m: np.nan for m in MEASURES}
            p = rng.permutation(X.shape[1])
            A, Bm = X[:, p[:h]], X[:, p[h:2 * h]]
            sa = sb = segments
            kw2["n_units"] = h
            scale = np.sqrt(h / n)
        a = measure_matched(A, seed=seed + 10 * k, segments=sa, **kw2)
        b = measure_matched(Bm, seed=seed + 10 * k + 1, segments=sb, **kw2)
        for m in MEASURES:
            sq[m].append((a.get(m, np.nan) - b.get(m, np.nan)) ** 2 / 4)
    return {m: float(np.sqrt(np.mean(v)) * scale) if np.isfinite(v).all() else np.nan for m, v in sq.items()}
