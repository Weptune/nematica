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


def repeat_autocov(Y, max_lag, chunk=64):
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
    out["M1_lag1"] = float((same[1] - cross[1]) / same[1]) if same[1] > 0 else np.nan
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
