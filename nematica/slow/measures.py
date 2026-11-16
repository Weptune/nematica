"""Study 2 measures (docs/SLOW.md, section 3), computed from activity during R repeats of the same input.

Y: array (R, T, N): repeats x time (samples) x units (or unit groups). Everything is pooled over units like
the map study's population timescale: autocovariances are averaged over standardised units.

C_same(k)  = mean over r of cov(Y_r(t), Y_r(t+k))          (all activity)
C_cross(k) = mean over r != r' of cov(Y_r(t), Y_r'(t+k))   (stimulus-locked: repeats in common)
C_int(k)   = C_same(k) - C_cross(k)                        (internal: what differs between repeats)
White noise sits only at lag 0 of C_same and is removed by extrapolating lags 1..4 (cubic), as in
nematica.map.measures._signal_var. Independent noise has no cross-repeat covariance, so C_cross(0) needs
no correction.
"""
from __future__ import annotations

import numpy as np

from ..map.measures import _half_life, _signal_var


def repeat_autocov(Y, max_lag, chunk=64, center="all"):
    """(C_same, C_cross), each of length max_lag + 1, averaged over units. Units are standardised over all
    repeats and time; constant units are dropped. Computed with FFTs, a chunk of units at a time (memory and
    speed, SLOW_LOG 00:05); equal to the direct lag-by-lag sums (`_repeat_autocov_direct`) to rounding."""
    Y = np.asarray(Y)
    R, T, N = Y.shape
    nfft = 1 << int(np.ceil(np.log2(2 * T)))
    n = (T - np.arange(max_lag + 1)).astype(float)
    same = np.zeros(max_lag + 1)
    cross = np.zeros(max_lag + 1)
    used = 0
    for a in range(0, N, chunk):
        Z = np.asarray(Y[:, :, a:a + chunk], float)
        if center == "repeat":                            # review S-R1 finding 3: centre within each repeat
            Z = Z - Z.mean(1, keepdims=True)
            sd = np.sqrt((Z ** 2).mean((0, 1)))
            keep = sd > 1e-9
            if not keep.any():
                continue
            Z = Z[:, :, keep] / sd[keep]
        else:
            flat = Z.reshape(R * T, -1)
            sd = flat.std(0)
            keep = sd > 1e-9
            if not keep.any():
                continue
            Z = (Z[:, :, keep] - flat[:, keep].mean(0)) / sd[keep]
        F = np.fft.rfft(Z, nfft, axis=1)                          # R x f x n
        s_same = np.fft.irfft((F * F.conj()).real.sum(0), nfft, axis=0)[: max_lag + 1]   # lags x n
        G = F.sum(0)
        s_all = np.fft.irfft((G * G.conj()).real, nfft, axis=0)[: max_lag + 1]
        same += (s_same / (R * n[:, None])).sum(1)
        cross += ((s_all - s_same) / (R * (R - 1) * n[:, None])).sum(1)
        used += int(keep.sum())
    return same / used, cross / used


def lag_measures(Y, k0=2, max_lag=None, center="repeat"):
    """Draft primary after review S-R1 (findings 1 and 3): measures that start at lag k0 (k0 = 2 bins = 40 ms
    for 20 ms spike bins), past single-unit spike-train structure (refractoriness, bursts), with units centred
    within each repeat (rate drift between blocks removed).
    M1 = C_int(k0) / C_same(k0); M2 = T_int / T_lock, T = sum over k >= k0 of C(k)/C(k0) up to the first
    lag where C falls to zero or below. Flags as in `pair_measures`."""
    Y = np.asarray(Y)
    T = Y.shape[1]
    L = int(max_lag or max(min(T // 4, 4000), k0 + 8))
    same, cross = repeat_autocov(Y, L, center=center)
    return measures_from_autocov(same, cross, k0, L)


def measures_from_autocov(same, cross, k0, L):
    """The lag-k0 measures from (C_same, C_cross) up to lag L (shared by `lag_measures` and the streaming
    recorder, `nematica.slow.stream`)."""
    inter = same - cross
    s0, c0, i0 = float(same[k0]), float(cross[k0]), float(inter[k0])
    out = {"k0": k0, "max_lag": L, "no_shared": bool(not s0 > 0), "no_locked": bool(not c0 > 0)}
    out["M1"] = float(np.clip(i0 / s0, -1, 1)) if s0 > 0 else 0.0
    tsum = lambda c, c_k0: float(1.0 + integral_time(c[k0:], c_k0) - 0.5)
    out["ti"] = tsum(inter, i0) if i0 > 0 else np.nan
    out["tl"] = tsum(cross, c0) if c0 > 0 else np.nan
    out["M2"] = float(out["ti"] / out["tl"]) if np.isfinite(out["ti"]) and np.isfinite(out["tl"]) else np.nan
    out["int_ceiling"] = bool(i0 > 0 and np.all(inter[k0:] > 0))
    out["lock_ceiling"] = bool(c0 > 0 and np.all(cross[k0:] > 0))
    return out


def pair_autocov(Y, max_lag, center="repeat", chunk=64):
    """Review S-R1 findings 1 and 3. Autocovariances averaged over pairs of DISTINCT units only, so that each
    unit's own spike-train structure (refractoriness, bursting, Poisson noise) is excluded at every lag,
    including lag 0. Units are centred within each repeat (center="repeat"; "all" centres over all
    repeats, as `repeat_autocov`) and scaled by their pooled within-repeat SD.
    Returns (same, cross, self_same, self_cross): the distinct-pair autocovariances (same repeat; different
    repeats) and, for reference, the single-unit (self) ones."""
    Y = np.asarray(Y)
    R, T, N = Y.shape
    nfft = 1 << int(np.ceil(np.log2(2 * T)))
    n = (T - np.arange(max_lag + 1)).astype(float)
    FP = None                                             # FFT of the population sum per repeat: R x f
    s_self_same = np.zeros(max_lag + 1)                   # sums of self terms, before normalising
    s_self_all = np.zeros(max_lag + 1)
    used = 0
    for a in range(0, N, chunk):
        Z = np.asarray(Y[:, :, a:a + chunk], float)
        Z = Z - (Z.mean(1, keepdims=True) if center == "repeat" else Z.reshape(R * T, -1).mean(0))
        sd = np.sqrt((Z ** 2).mean((0, 1)))
        keep = sd > 1e-9
        if not keep.any():
            continue
        Z = Z[:, :, keep] / sd[keep]
        F = np.fft.rfft(Z, nfft, axis=1)                  # R x f x n
        s_self_same += np.fft.irfft((F * F.conj()).real.sum((0, 2)), nfft)[: max_lag + 1]
        G = F.sum(0)                                      # f x n: per unit, summed over repeats
        s_self_all += np.fft.irfft((G * G.conj()).real.sum(1), nfft)[: max_lag + 1]
        FP = F.sum(2) if FP is None else FP + F.sum(2)
        used += int(keep.sum())
    if used < 2:
        nan = np.full(max_lag + 1, np.nan)
        return nan, nan, nan, nan
    s_pop_same = np.fft.irfft((FP * FP.conj()).real.sum(0), nfft)[: max_lag + 1]
    GP = FP.sum(0)
    s_pop_all = np.fft.irfft((GP * GP.conj()).real, nfft)[: max_lag + 1]
    pairs = used * (used - 1)
    same = (s_pop_same - s_self_same) / (R * n * pairs)
    cross = (s_pop_all - s_pop_same - (s_self_all - s_self_same)) / (R * (R - 1) * n * pairs)
    self_same = s_self_same / (R * n * used)
    self_cross = (s_self_all - s_self_same) / (R * (R - 1) * n * used)
    return same, cross, self_same, self_cross


def pair_measures(Y, max_lag=None, center="repeat"):
    """Primary measures after review S-R1 (draft): from distinct-unit pairs, so lag 0 is noise-free and no
    extrapolation is needed.
    M1 = C_int(0) / C_same(0); M2 = T_int / T_lock with T = 0.5 + sum over k >= 1 of C(k)/C(0) up to the
    first lag where C falls to zero or below. Flags: `no_shared` (C_same(0) <= 0: no shared covariance),
    `no_locked` (C_cross(0) <= 0: no locked part to time against), `int_ceiling` / `lock_ceiling` (the
    autocovariance stays positive up to the largest lag, a quarter of the clip)."""
    Y = np.asarray(Y)
    T = Y.shape[1]
    L = int(max_lag or max(min(T // 4, 4000), 8))
    same, cross, ss, sc = pair_autocov(Y, L, center=center)
    inter = same - cross
    out = {"C_same0": float(same[0]), "C_cross0": float(cross[0]), "self_same0": float(ss[0]),
           "self_cross0": float(sc[0]), "max_lag": L}
    out["no_shared"] = bool(not same[0] > 0)
    out["no_locked"] = bool(not cross[0] > 0)
    out["M1"] = float(np.clip(inter[0] / same[0], -1, 1)) if same[0] > 0 else 0.0
    out["ti"] = integral_time(inter, inter[0]) if inter[0] > 0 else np.nan
    out["tl"] = integral_time(cross, cross[0]) if cross[0] > 0 else np.nan
    out["M2"] = float(out["ti"] / out["tl"]) if np.isfinite(out["ti"]) and np.isfinite(out["tl"]) else np.nan
    out["int_ceiling"] = bool(inter[0] > 0 and np.all(inter[1:] > 0))
    out["lock_ceiling"] = bool(cross[0] > 0 and np.all(cross[1:] > 0))
    # reported: the single-unit (self) internal share, which includes each unit's own spike-train structure
    out["M1_self"] = float((ss[0] - sc[0]) / ss[0]) if ss[0] > 0 else np.nan
    return out


def _repeat_autocov_direct(Y, max_lag):
    """The original lag-by-lag version, kept as the reference for the FFT version."""
    Y = np.asarray(Y, float)
    R, T, N = Y.shape
    flat = Y.reshape(R * T, N)
    sd = flat.std(0)
    keep = sd > 1e-9
    Y = (Y[:, :, keep] - flat[:, keep].mean(0)) / sd[keep]
    S = Y.sum(0)
    same = np.zeros(max_lag + 1)
    cross = np.zeros(max_lag + 1)
    for k in range(max_lag + 1):
        a, b = Y[:, : T - k], Y[:, k:]
        s_same = (a * b).sum((0, 1))
        s_all = (S[: T - k] * S[k:]).sum(0)
        n = T - k
        same[k] = np.mean(s_same / (R * n))
        cross[k] = np.mean((s_all - s_same) / (R * (R - 1) * n))
    return same, cross


def internal_measures(Y, max_lag=None):
    """M1 (internal share) and M2 (internal half-life over stimulus-locked half-life), with the pieces."""
    Y = np.asarray(Y)
    T = Y.shape[1]
    L = int(max_lag or max(min(T // 4, 4000), 8))
    same, cross = repeat_autocov(Y, L)
    s0 = float(_signal_var(same[:, None])[0])            # noise-free lag-0 variance of all activity
    c0 = float(cross[0])
    i0 = s0 - c0
    out = {"signal_var": s0, "locked_var": c0, "internal_var": i0, "noise_share": float(1 - s0 / same[0])}
    # lag-1 share: needs no extrapolation, since spike noise is white (F2 note, SLOW_LOG)
    # no positive one-bin covariance at all (e.g. the LIF network, SLOW_LOG 18:30): nothing slow to share out;
    # M1_lag1 is set to 0 and flagged
    out["no_lag1_cov"] = bool(not same[1] > 0)
    out["M1_lag1"] = float((same[1] - cross[1]) / same[1]) if same[1] > 0 else 0.0
    # lag-1 versions (no extrapolation): integral times from lag 1, normalised by lag 1
    i1, c1 = float(same[1] - cross[1]), float(cross[1])
    out["ti_lag1"] = integral_time((same - cross)[1:], i1) - 0.5 + 1.0 if i1 > 0 else np.nan
    out["tl_lag1"] = integral_time(cross[1:], c1) - 0.5 + 1.0 if c1 > 0 else np.nan
    out["M2_lag1"] = float(out["ti_lag1"] / out["tl_lag1"]) if np.isfinite(out["ti_lag1"]) and \
        np.isfinite(out["tl_lag1"]) else np.nan
    # ceiling (SLOW_LOG 17:05): the internal autocovariance never reached zero within the largest lag, so the
    # integral time, and M2, are lower bounds set by the clip
    out["M2_ceiling"] = bool(i1 > 0 and np.all((same - cross)[1:] > 0))
    if not (np.isfinite(s0) and s0 > 0):
        return out | {"M1": np.nan, "M2": np.nan, "t_internal": np.nan, "t_locked": np.nan, "ti_int": np.nan,
                      "tl_int": np.nan, "M2_int": np.nan}
    out["M1"] = float(np.clip(i0 / s0, -1, 2))
    internal = same - cross
    t_int = _half_life(np.concatenate([[1.0], internal[1:] / i0])) if i0 > 0 else np.nan
    t_lock = _half_life(np.concatenate([[1.0], cross[1:] / c0])) if c0 > 0 else np.nan
    out.update(t_internal=float(t_int) if t_int is not None else np.nan,
               t_locked=float(t_lock) if t_lock is not None else np.nan)
    out["ti_int"] = integral_time(internal, i0) if i0 > 0 else np.nan
    out["tl_int"] = integral_time(cross, c0) if c0 > 0 else np.nan
    out["M2_int"] = float(out["ti_int"] / out["tl_int"]) if np.isfinite(out["ti_int"]) and np.isfinite(out["tl_int"]) \
        and out["tl_int"] > 0 else np.nan
    out["M2"] = float(out["t_internal"] / out["t_locked"]) if np.isfinite(out["t_internal"]) and \
        np.isfinite(out["t_locked"]) and out["t_locked"] > 0 else np.nan
    return out


def integral_time(c, c0, max_k=None):
    """Integrated autocorrelation time: sum of c(k)/c0 over lags 1.. until the first lag where it falls
    below zero (or max_k). More robust than the half-life when timescales are only a few samples."""
    r = np.asarray(c[1:], float) / c0
    if max_k:
        r = r[:max_k]
    neg = np.flatnonzero(r <= 0)
    r = r[: neg[0]] if len(neg) else r
    return float(0.5 + r.sum())


def carry_over(Y, edge):
    """M3: correlation, over units and repeat boundaries, of the internal component averaged over the last
    `edge` samples of a repeat and the first `edge` samples of the next."""
    Y = np.asarray(Y, float)
    E = Y - Y.mean(0, keepdims=True)                     # internal component (minus the repeat average)
    a = E[:-1, -edge:].mean(1).ravel()
    b = E[1:, :edge].mean(1).ravel()
    return float(np.corrcoef(a, b)[0, 1])


def unit_internal_shares(Y):
    """Reported extras (SLOW.md section 3), on native activity (R, T, N): per unit, the share of its variance
    that differs between repeats (mean over time of the across-repeat variance, over its total variance);
    the variance-weighted share over units; and the fraction of units whose share exceeds 0.5."""
    Y = np.asarray(Y, np.float64)
    within = Y.var(0).mean(0)
    total = Y.reshape(-1, Y.shape[2]).var(0)
    ok = total > 1e-12
    sh = within[ok] / total[ok]
    return {"weighted_share": float(within[ok].sum() / total[ok].sum()),
            "frac_units_above_half": float((sh > 0.5).mean()), "n_units": int(ok.sum())}


def silent_units(A, frac=0.01):
    """SLOW.md section 5: AI units whose SD is below `frac` of the median unit SD (boolean mask of silent)."""
    sd = np.asarray(A).std(0)
    return sd < frac * np.median(sd)
