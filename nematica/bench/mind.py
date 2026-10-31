"""Signatures of a mind in ongoing activity: measures from consciousness science, applied to
real and artificial worm brains at rest. None of them shows that anything is conscious; in
people they separate wakeful brains from sleeping, anaesthetised or unresponsive ones.

    M1.complexity   Lempel-Ziv complexity of ongoing activity (Schartner et al. 2015 style):
                    each class binarised at its own median, the binary pattern read time
                    point by time point, LZ76 phrases normalised by L / log2 L. Computed in
                    60 s windows; distance = Kolmogorov-Smirnov between window distributions.
                    Falls under anaesthesia and in deep sleep in people.
    M2.integration  Gaussian total correlation (multi-information) per class,
                    -0.5 log det(correlation) / n, in 60 s windows: how much the parts share
                    rather than act independently. KS distance between window distributions.
    M3.repertoire   Entropy of the brain's coarse global states: the sign pattern of the top
                    four principal components (16 possible states), per 60 s window, in bits.
                    How many different whole-brain states the brain visits. KS distance.

Classes compared are those observed in both samples, as for the other levels.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import ks_2samp

from .levels import shared
from .perturbational import lz76
from .sample import BenchSample

WINDOW_S = 60.0


def _windows(x: np.ndarray, dt: float):
    n = max(int(round(WINDOW_S / dt)), 10)
    for a in range(0, x.shape[1] - n + 1, n):
        yield x[:, a:a + n]


def lz_complexity(w: np.ndarray) -> float:
    b = (w > np.median(w, axis=1, keepdims=True)).astype(np.uint8)
    s = b.T.ravel()
    L = s.size
    return float(lz76(s) * np.log2(L) / L) if L > 1 else np.nan


def total_correlation(w: np.ndarray) -> float:
    C = np.corrcoef(w)
    if not np.all(np.isfinite(C)):
        return np.nan
    sign, logdet = np.linalg.slogdet(C + 1e-6 * np.eye(len(C)))
    return float(-0.5 * logdet / len(C)) if sign > 0 else np.nan


def repertoire(w: np.ndarray, k: int = 4) -> float:
    z = w - w.mean(axis=1, keepdims=True)
    try:
        u, s, vt = np.linalg.svd(z, full_matrices=False)
    except np.linalg.LinAlgError:
        return np.nan
    pcs = vt[:k]                                  # (k, T)
    codes = (pcs > 0).astype(int).T @ (1 << np.arange(k))
    p = np.bincount(codes, minlength=1 << k) / len(codes)
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def _per_window(s: BenchSample, idx, fn) -> np.ndarray:
    x = s.x[idx]
    return np.array([fn(w) for w in _windows(x, s.dt)])


def _ks(a: BenchSample, b: BenchSample, fn) -> float:
    idx = shared(a, b)
    if len(idx) < 8:
        return np.nan
    va = _per_window(a, idx, fn)
    vb = _per_window(b, idx, fn)
    va, vb = va[np.isfinite(va)], vb[np.isfinite(vb)]
    if len(va) < 3 or len(vb) < 3:
        return np.nan
    return float(ks_2samp(va, vb).statistic)


def m_complexity(a, b):
    return _ks(a, b, lz_complexity)


def m_integration(a, b):
    return _ks(a, b, total_correlation)


def m_repertoire(a, b):
    return _ks(a, b, repertoire)


MIND_LEVELS = {
    "M1.complexity": {"level": 9, "fn": m_complexity, "primary": True,
                      "what": "how complex and unpredictable ongoing activity is (Lempel-Ziv)"},
    "M2.integration": {"level": 9, "fn": m_integration, "primary": True,
                       "what": "how much the brain's parts share (total correlation)"},
    "M3.repertoire": {"level": 9, "fn": m_repertoire, "primary": False,
                      "what": "how many whole-brain states it visits (entropy of global states)"},
}


def summary(s: BenchSample) -> dict:
    """The raw measures of one sample (all its observed classes), for reporting directions."""
    idx = np.flatnonzero(s.observed)
    return {k: float(np.nanmedian(_per_window(s, idx, fn)))
            for k, fn in (("lzc", lz_complexity), ("tc", total_correlation), ("repertoire", repertoire))}
