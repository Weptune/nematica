"""Windowed internal-state measures for Study 3 (docs/PERSIST.md section 4).

Each repeat is cut into W equal windows. In each window, as Study 2's half-clip measures do for halves
(`nematica.slow.stream.Recorder.pass2`): units are centred within the window on each repeat, lag-k0
same-repeat and cross-repeat products are summed over bin pairs inside the window, and each unit is
normalised by its pooled within-repeat variance in that window. M1_w = C_int / C_same at lag k0.
For the amplitude index the same internal covariance is normalised instead by each unit's pooled
within-repeat variance over the whole clip, so windows are comparable in size;
P_amp = (I_late - I_early) / (|I_late| + |I_early|).
"""
from __future__ import annotations

import numpy as np


def window_edges(n, W):
    return np.linspace(0, n, W + 1).astype(int)


class _Acc:
    def __init__(self, W):
        self.same = np.zeros(W)
        self.cross = np.zeros(W)
        self.int_amp = np.zeros(W)
        self.same_amp = np.zeros(W)
        self.units = np.zeros(W)
        self.units_amp = 0


def _accumulate(acc, ys, edges, k0):
    """ys: list over repeats of (n, u) counts for one block of units."""
    R = len(ys)
    W = len(edges) - 1
    n = ys[0].shape[0]
    # whole-clip pooled within-repeat variance per unit (amplitude normaliser)
    ssq_all = sum(((y - y.mean(0)) ** 2).sum(0) for y in ys)
    var_all = ssq_all / (R * n)
    keep_all = var_all > 1e-18
    acc.units_amp += int(keep_all.sum())
    for w in range(W):
        a, b = edges[w], edges[w + 1]
        m = b - a
        if m <= k0:
            continue
        G = None
        s_same = 0.0
        ssq = 0.0
        for y in ys:
            z = y[a:b] - y[a:b].mean(0)
            ssq = ssq + (z ** 2).sum(0)
            s_same = s_same + (z[:-k0] * z[k0:]).sum(0)
            G = z if G is None else G + z
        s_all = (G[:-k0] * G[k0:]).sum(0)
        nk = m - k0
        var = ssq / (R * m)
        keep = var > 1e-18
        same_u = s_same / (R * nk)
        cross_u = (s_all - s_same) / (R * (R - 1) * nk)
        acc.same[w] += (same_u[keep] / var[keep]).sum()
        acc.cross[w] += (cross_u[keep] / var[keep]).sum()
        acc.units[w] += keep.sum()
        acc.int_amp[w] += ((same_u - cross_u)[keep_all] / var_all[keep_all]).sum()
        acc.same_amp[w] += (same_u[keep_all] / var_all[keep_all]).sum()


def _finish(acc, edges, k0):
    W = len(edges) - 1
    same = acc.same / np.maximum(acc.units, 1)
    cross = acc.cross / np.maximum(acc.units, 1)
    inter = same - cross
    m1 = np.where(same > 0, np.clip(inter / np.where(same > 0, same, 1), -1, 1), 0.0)
    ia = acc.int_amp / max(acc.units_amp, 1)
    sa = acc.same_amp / max(acc.units_amp, 1)
    q = max(W // 4, 1)
    early, late = slice(0, q), slice(W - q, W)
    p_share = float(m1[late].mean() - m1[early].mean())
    ie, il = ia[early].mean(), ia[late].mean()
    # bounded in [-1, 1]; a log ratio was undefined when a faded internal part estimated at or below 0
    p_amp = float((il - ie) / (abs(il) + abs(ie))) if (abs(il) + abs(ie)) > 0 else np.nan
    fit = drive_time_fit(ia, sa - ia)
    return {"W": W, "k0": k0, "edges": [int(x) for x in edges], "M1_w": m1.tolist(), "same_w": same.tolist(),
            "c_time": fit["c"], "b_drive": fit["b"], "fit": fit,
            "cross_w": cross.tolist(), "int_amp_w": ia.tolist(), "same_amp_w": sa.tolist(),
            "P_share": p_share, "P_amp": p_amp, "amp_nonpositive": bool(not (ie > 0 and il > 0))}


def windowed_from_counts(Y, W=8, k0=2):
    """Y: (R, n, units) counts, materialised. Returns the windowed measures."""
    Y = np.asarray(Y, float)
    edges = window_edges(Y.shape[1], W)
    acc = _Acc(W)
    _accumulate(acc, list(Y), edges, k0)
    return _finish(acc, edges, k0)


def windowed_stream(rec, positions, W=8, k0=2):
    """The same, streamed over unit blocks of a `nematica.slow.stream.Recorder` (same spikes as its passes)."""
    from ..slow.stream import BLOCK
    edges = window_edges(rec.n, W)
    acc = _Acc(W)
    for bid, pos in rec.blocks(positions):
        full = np.arange(bid * BLOCK, min((bid + 1) * BLOCK, len(rec.cols)))
        C = rec._cum(full)
        sel = np.searchsorted(full, pos)
        ys = [rec._repeat(C, r, bid)[:, sel] for r in range(rec.R)]
        _accumulate(acc, ys, edges, k0)
    return _finish(acc, edges, k0)


def drive_time_fit(I, L):
    """Draft v0.2 primary (docs/PERSIST.md section 4): across windows, internal amplitude I_w modelled as
    a * L_w^b * exp(c * t_w), with L_w the locked (cross-repeat) amplitude in the window and t_w the window's
    centre as a fraction of the clip. c: change of internal amplitude per clip length at fixed drive (below 0:
    the internal part fades; a carried state). b: how internal amplitude scales with drive (about 0 for an
    additive internal part, about 1 or more for gain-type variability, below 0 if drive suppresses it).
    Fitted by least squares on I itself (no logarithm, so windows whose internal amplitude is estimated at
    or below 0 need no floor), started from a log-linear fit; windows with L_w <= 0 are left out."""
    from scipy.optimize import least_squares
    I = np.asarray(I, float)
    L = np.asarray(L, float)
    W = len(I)
    t = (np.arange(W) + 0.5) / W
    ok = L > 0
    out = {"n_windows": int(ok.sum()), "b": np.nan, "c": np.nan, "converged": False}
    if ok.sum() < 4 or not np.any(I[ok] > 0):
        return out
    It, Lt, tt = I[ok], L[ok], t[ok]
    eps = 1e-3 * np.abs(It).max()
    X = np.c_[np.ones(len(tt)), np.log(Lt), tt]
    p0 = np.linalg.lstsq(X, np.log(np.clip(It, eps, None)), rcond=None)[0]
    scale = np.abs(It).mean() + 1e-15
    res = lambda p: (It - np.exp(p[0] + p[1] * np.log(Lt) + p[2] * tt)) / scale
    try:
        r = least_squares(res, p0, method="lm", max_nfev=2000)
        out.update({"b": float(r.x[1]), "c": float(r.x[2]), "converged": bool(r.success),
                    "b_loglinear": float(p0[1]), "c_loglinear": float(p0[2])})
    except Exception as e:  # noqa: BLE001
        out.update({"error": f"{type(e).__name__}: {e}", "b_loglinear": float(p0[1]), "c_loglinear": float(p0[2])})
    return out
