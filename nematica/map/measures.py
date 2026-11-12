"""The map's eight core measurements (docs/MAP.md), the same for any system.

Input: activity X, shape (time, units), already passed through a recording model (recording.py). Time is
in samples; every measurement is dimensionless (time enters only through tau_med, the system's own median
unit timescale). Each function returns a float (nan when the recording cannot support it).
"""
from __future__ import annotations

import numpy as np

MEASURES = ("spectrum_exponent", "shared_dim", "shared_fraction", "slow_fraction", "timescale_spread",
            "coupling_spread", "drift", "sparsity")


def _z(X):
    X = np.asarray(X, float)
    sd = X.std(0)
    keep = sd > 1e-9
    return (X[:, keep] - X[:, keep].mean(0)) / sd[keep]


def unit_timescales(X, max_lag=None):
    """Half-life (samples) of each unit's autocorrelation, measured from lag 1 so that white measurement
    noise (which only affects lag 0) does not shorten it: the lag beyond 1 at which ac(k)/ac(1) first
    falls below 0.5, plus 1 (nan if ac(1) <= 0 or it never falls)."""
    Z = _z(X)
    T, N = Z.shape
    max_lag = max_lag or min(T // 4, 2000)
    F = np.fft.rfft(Z, n=2 * T, axis=0)
    ac = np.fft.irfft(F * np.conj(F), axis=0)[:max_lag + 1] / T
    out = np.full(N, np.nan)
    ok = ac[1] > 0.02 * ac[0]
    r = ac[1:] / np.where(ok, ac[1], 1.0)
    below = r < 0.5
    for i in np.where(ok & below.any(0))[0]:
        k = int(below[:, i].argmax())                # index in r; lag = k + 1
        a0, a1 = r[k - 1, i], r[k, i]
        out[i] = 1 + (k - 1) + (a0 - 0.5) / (a0 - a1)
    return out


def tau_med(X):
    t = unit_timescales(X)
    return float(np.nanmedian(t)) if np.isfinite(t).any() else np.nan


def _halves(N, rng):
    p = rng.permutation(N)
    return p[: N // 2], p[N // 2: 2 * (N // 2)]


def svca(X, rng, n_comp=None):
    """Shared variance component analysis (Stringer et al. 2019): reliable variance per shared dimension.

    Units split in two halves, time in alternating chunks (train/test); components from the train
    cross-covariance, variance measured as test covariance between the two halves' projections."""
    Z = _z(X)
    T, N = Z.shape
    a, b = _halves(N, rng)
    chunk = max(int(10 * max(tau_med(Z), 1.0)), 20)       # chunks long against the timescale
    idx = np.arange(T) // chunk
    train, test = idx % 2 == 0, idx % 2 == 1
    k = n_comp or min(len(a), len(b), train.sum() // 4, 512)
    C = Z[train][:, a].T @ Z[train][:, b] / train.sum()
    U, S, Vt = np.linalg.svd(C, full_matrices=False)
    U, V = U[:, :k], Vt[:k].T
    pa, pb = Z[test][:, a] @ U, Z[test][:, b] @ V
    shared = (pa * pb).mean(0)
    var = 0.5 * (pa.var(0) + pb.var(0))
    return shared, var, len(a)


def spectrum_exponent(X, rng=None, fit=(2, None)):
    """Power-law slope of the reliable (shared) spectrum, fitted on ranks fit[0] .. K/2 with positive variance."""
    rng = rng or np.random.default_rng(0)
    shared, _, n = svca(X, rng)
    pos = shared > 0
    K = int(np.argmin(pos)) if not pos.all() else len(pos)   # ranks up to the first non-positive one
    hi = fit[1] or max(K // 2, 6)
    r = np.arange(1, len(shared) + 1)
    sel = (r >= fit[0]) & (r <= hi) & pos
    if sel.sum() < 4:
        return np.nan
    return float(-np.polyfit(np.log(r[sel]), np.log(shared[sel]), 1)[0])


def shared_dim(X, rng=None):
    """Participation ratio of the reliable shared spectrum (positive SVCA variances), as a share of the
    half-population size (amendment 1: replaces the count above a shuffle null, which fell with weaker
    dimensions rather than rising with more of them at 50 units)."""
    rng = rng or np.random.default_rng(0)
    shared, _, n = svca(X, rng)
    lam = np.clip(shared, 0, None)
    if lam.sum() <= 0:
        return np.nan
    return float(lam.sum() ** 2 / (lam ** 2).sum() / n)


def shared_fraction(X, rng=None, n_target=300, n_pc=64, ridge=1.0):
    """Median share of a unit's held-out variance predicted from the other units (ridge on their top PCs)."""
    rng = rng or np.random.default_rng(0)
    Z = _z(X)
    T, N = Z.shape
    chunk = max(int(10 * max(tau_med(Z), 1.0)), 20)
    idx = np.arange(T) // chunk
    tr, te = idx % 2 == 0, idx % 2 == 1
    targets = rng.choice(N, size=min(n_target, N), replace=False)
    r2 = []
    for g in np.array_split(targets, max(1, int(np.ceil(len(targets) / max(1, N // 10))))):
        others = np.setdiff1d(np.arange(N), g)
        U, S, Vt = np.linalg.svd(Z[tr][:, others], full_matrices=False)
        k = min(n_pc, len(S), max(1, tr.sum() // 4))
        P = Vt[:k].T
        A_tr, A_te = Z[tr][:, others] @ P, Z[te][:, others] @ P
        G = A_tr.T @ A_tr
        W = np.linalg.solve(G + ridge * 1e-2 * np.trace(G) / k * np.eye(k), A_tr.T @ Z[tr][:, g])
        pred = A_te @ W
        y = Z[te][:, g]
        r2.extend(1 - ((y - pred) ** 2).sum(0) / ((y - y.mean(0)) ** 2).sum(0))
    return float(np.median(r2))


def slow_fraction(X, factor=10.0, t=None):
    """Median share of a unit's signal power at frequencies below 1 / (factor * tau_med).

    Amendment 1 (12 Nov, before any new data): the white measurement-noise floor, estimated as the
    median power in the top quarter of frequencies, is subtracted first, so Poisson or camera noise does
    not count as fast signal."""
    Z = _z(X)
    t = t if t is not None else tau_med(Z)
    if not np.isfinite(t):
        return np.nan
    T = len(Z)
    seg = int(min(T, 2 ** np.ceil(np.log2(max(32 * factor * t, 256)))))
    hop = max(seg // 2, 1)
    P = 0
    win = np.hanning(seg)[:, None]
    for s0 in range(0, T - seg + 1, hop):
        F = np.fft.rfft(Z[s0:s0 + seg] * win, axis=0)
        P = P + np.abs(F) ** 2
    f = np.fft.rfftfreq(seg)
    P = P[1:]
    f = f[1:]
    floor = np.median(P[f >= np.quantile(f, 0.75)], axis=0)
    S = np.clip(P - floor, 0, None)
    low = f < 1.0 / (factor * t)
    tot = S.sum(0)
    ok = tot > 0
    return float(np.median(S[low][:, ok].sum(0) / tot[ok])) if ok.any() else np.nan


def timescale_spread(X):
    """Interquartile range of log10 unit timescales."""
    t = unit_timescales(X)
    t = t[np.isfinite(t) & (t > 0)]
    if len(t) < 5:
        return np.nan
    q1, q3 = np.percentile(np.log10(t), [25, 75])
    return float(q3 - q1)


def coupling_spread(X):
    """Interquartile range of population coupling (each unit's correlation with the mean of the others)."""
    Z = _z(X)
    tot = Z.sum(1)
    c = np.array([np.corrcoef(Z[:, i], tot - Z[:, i])[0, 1] for i in range(Z.shape[1])])
    q1, q3 = np.nanpercentile(c, [25, 75])
    return float(q3 - q1)


def drift(X, block_tau=25.0, t=None, max_units=400, rng=None):
    """Drift rate of the correlation structure (amendment 1): the recording is cut into blocks of
    block_tau * tau_med; dissimilarity 1 - r(off-diagonal correlations) between every pair of blocks is
    regressed on their separation; returns the slope per 100 tau_med. Needs at least 4 blocks."""
    rng = rng or np.random.default_rng(0)
    Z = _z(X)
    t = t if t is not None else tau_med(Z)
    if not np.isfinite(t):
        return np.nan
    L = int(round(block_tau * t))
    nb = len(Z) // max(L, 1)
    if nb < 4:
        return np.nan
    if Z.shape[1] > max_units:
        Z = Z[:, rng.choice(Z.shape[1], max_units, replace=False)]
    iu = np.triu_indices(Z.shape[1], 1)
    C = [np.nan_to_num(np.corrcoef(Z[k * L:(k + 1) * L].T)[iu]) for k in range(nb)]
    sep, dis = [], []
    for i in range(nb):
        for j in range(i + 1, nb):
            sep.append((j - i) * block_tau)
            dis.append(1 - np.corrcoef(C[i], C[j])[0, 1])
    return float(np.polyfit(sep, dis, 1)[0] * 100)


def sparsity(X):
    """Median excess kurtosis of unit activity."""
    Z = _z(X)
    return float(np.median((Z ** 4).mean(0) - 3))


def measure_all(X, seed=0):
    rng = lambda k: np.random.default_rng(seed * 100 + k)
    return {"spectrum_exponent": spectrum_exponent(X, rng(1)), "shared_dim": shared_dim(X, rng(2)),
            "shared_fraction": shared_fraction(X, rng(3)), "slow_fraction": slow_fraction(X),
            "timescale_spread": timescale_spread(X), "coupling_spread": coupling_spread(X),
            "drift": drift(X, rng=rng(4)), "sparsity": sparsity(X), "tau_med": tau_med(X)}


# ---------------------------------------------------------------- the matched protocol (amendment 1)
N_UNITS, N_DRAWS, WINDOW_TAU = 50, 40, 150


def measure_matched(X, seed=0, n_units=N_UNITS, n_draws=N_DRAWS, window_tau=WINDOW_TAU, only=None):
    """Every system measured the same way: tau_med from all units; then n_draws random draws of n_units
    units and a window of window_tau * tau_med samples; each measurement averaged over draws.
    Returns {measure: mean} plus {measure + '_sd': SD over draws} and tau_med, window."""
    X = np.asarray(X, float)
    X = X[:, X.std(0) > 1e-9]
    rng = np.random.default_rng(seed)
    t = tau_med(X)
    if not np.isfinite(t) or X.shape[1] < n_units:
        return {"tau_med": t, "error": "too few units or no timescale"}
    W = int(round(window_tau * t))
    if W > len(X):
        return {"tau_med": t, "error": f"recording shorter than {window_tau} tau_med"}
    names = only or MEASURES
    vals = {m: [] for m in names}
    for d in range(n_draws):
        u = rng.choice(X.shape[1], n_units, replace=False)
        s0 = int(rng.integers(0, len(X) - W + 1))
        Y = X[s0:s0 + W, u]
        r = np.random.default_rng(seed * 1000 + d)
        for m in names:
            f = globals()[m]
            try:
                if m == "drift":                      # a rate over the whole recording, matched units
                    v = f(X[:, u], t=t, rng=r)
                elif m == "slow_fraction":            # Welch segments of fixed length in tau_med over the whole recording
                    v = f(X[:, u], t=t)
                elif m == "slow_fraction":
                    v = f(Y, t=t)
                elif "rng" in f.__code__.co_varnames:
                    v = f(Y, rng=r)
                else:
                    v = f(Y)
            except Exception:  # noqa: BLE001
                v = np.nan
            vals[m].append(v)
    out = {"tau_med": t, "window": W}
    for m in names:
        a = np.array(vals[m], float)
        out[m] = float(np.nanmean(a)) if np.isfinite(a).any() else np.nan
        out[m + "_sd"] = float(np.nanstd(a)) if np.isfinite(a).sum() > 1 else np.nan
    return out
