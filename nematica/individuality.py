"""Individual routing (pre-registered 8 Nov 2026, README "Do worms with the same wiring route signals
differently, and do neuropeptides carry it?").

A half-map is {(stimulated class, responding class): amplitude}, amplitude = mean response over the first
15 s after onset in units of pre-stimulus fluctuations (as nematica.bench.causal), averaged over the
half's pokes, with spillover neighbours and the target's own class excluded. Each map is decomposed by
least squares into grand mean + source effect + responder effect + routing residual.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from .bench import causal

MIN_SHARED = 15


def half_map(rec, stims, near=None, exclude_same_class=True):
    """near: list (per neuron index) of sets of excluded neighbours, or None for no exclusion. An event
    is dropped when near is given and either neuron has no position (None)."""
    n_amp = int(round(causal.AMP_S / rec.dt)) + 1
    acc = defaultdict(list)
    for k, ci, j, cj, tr in causal.event_responses(rec, stims, norm="fluct"):
        if exclude_same_class and ci == cj:
            continue
        if near is not None:
            if near[k] is None or near[j] is None or j in near[k] or k in near[j]:
                continue
        seg = tr[:n_amp]
        fin = np.isfinite(seg)
        if fin.any():
            acc[(ci, cj)].append(float(seg[fin].mean()))
    return {key: float(np.mean(v)) for key, v in acc.items()}


def decompose(m, iters=25):
    """Additive fit a = mu + s[source] + r[responder]; returns (s, r, routing residual dict)."""
    keys = list(m)
    if not keys:
        return {}, {}, {}
    a = np.array([m[k] for k in keys])
    src = sorted({k[0] for k in keys})
    rsp = sorted({k[1] for k in keys})
    si = np.array([src.index(k[0]) for k in keys])
    ri = np.array([rsp.index(k[1]) for k in keys])
    mu = a.mean()
    s = np.zeros(len(src))
    r = np.zeros(len(rsp))
    for _ in range(iters):
        res = a - mu - r[ri]
        s = np.bincount(si, res, len(src)) / np.maximum(np.bincount(si, minlength=len(src)), 1)
        res = a - mu - s[si]
        r = np.bincount(ri, res, len(rsp)) / np.maximum(np.bincount(ri, minlength=len(rsp)), 1)
    resid = a - mu - s[si] - r[ri]
    return dict(zip(src, s)), dict(zip(rsp, r)), dict(zip(keys, resid))


def corr_shared(x: dict, y: dict, min_shared=MIN_SHARED):
    keys = [k for k in x if k in y]
    if len(keys) < min_shared:
        return np.nan
    u = np.array([x[k] for k in keys])
    v = np.array([y[k] for k in keys])
    if u.std() == 0 or v.std() == 0:
        return np.nan
    return float(np.corrcoef(u, v)[0, 1])


PARTS = ("raw", "source", "responder", "routing")


def parts(m):
    s, r, e = decompose(m)
    return {"raw": m, "source": s, "responder": r, "routing": e}


def agreement_matrix(A, B, part, min_shared=MIN_SHARED):
    """A, B: lists of parts() dicts (first and second halves); returns S[i, j] = corr(A_i, B_j)."""
    ms = 5 if part in ("source", "responder") else min_shared
    n = len(A)
    S = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            S[i, j] = corr_shared(A[i][part], B[j][part], ms)
    return S


def excess(S):
    """Per worm: within (diagonal) minus median between (its first half against others' second halves)."""
    n = len(S)
    out = np.full(n, np.nan)
    for i in range(n):
        b = np.delete(S[i], i)
        b = b[np.isfinite(b)]
        if np.isfinite(S[i, i]) and len(b):
            out[i] = S[i, i] - np.median(b)
    return out


def index_I(S):
    w = np.diag(S)
    b = S[~np.eye(len(S), dtype=bool)]
    w, b = w[np.isfinite(w)], b[np.isfinite(b)]
    if not len(w) or not len(b) or np.median(w) == 0:
        return np.nan
    return float(1 - np.median(b) / np.median(w))
