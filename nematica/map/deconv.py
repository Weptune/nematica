"""The deconvolved calcium instrument (docs/MAP.md, amendment 15), as suite2p processes two-photon data:
calcium recording (recording.calcium), a rolling maximin baseline subtracted, then non-negative AR(1)
deconvolution without a sparsity penalty: OASIS (Friedrich, Zhou and Paninski 2017, PLoS Comput Biol),
written here from the paper's pool-merging algorithm."""
from __future__ import annotations

import numpy as np
from numba import njit
from scipy.ndimage import gaussian_filter1d, maximum_filter1d, minimum_filter1d


@njit(cache=True)
def _oasis_unit(y, g):
    """Non-negative deconvolution of one trace with decay factor g per frame: pools of constant
    (exponentially decaying) value are merged backwards whenever the decay constraint is violated."""
    n = len(y)
    v = np.empty(n)
    w = np.empty(n)
    t = np.empty(n, np.int64)
    ln = np.empty(n, np.int64)
    i = 0
    for k in range(n):
        v[i], w[i], t[i], ln[i] = y[k], 1.0, k, 1
        while i > 0 and v[i - 1] * g ** ln[i - 1] > v[i]:
            f = g ** ln[i - 1]
            wn = w[i - 1] + w[i] * f * f
            v[i - 1] = (w[i - 1] * v[i - 1] + w[i] * f * v[i]) / wn
            w[i - 1] = wn
            ln[i - 1] += ln[i]
            i -= 1
        i += 1
    s = np.zeros(n)
    for j in range(1, i):
        s[t[j]] = max(v[j] - v[j - 1] * g ** ln[j - 1], 0.0)
    return s


def oasis(F, decay_frames):
    """F: frames x units. Returns the deconvolved activity (same shape)."""
    g = float(np.exp(-1.0 / decay_frames))
    F = np.asarray(F, np.float64)
    return np.column_stack([_oasis_unit(F[:, j].copy(), g) for j in range(F.shape[1])])


def maximin(F, win, sig=10.0):
    """Rolling maximin baseline (Gaussian smoothing, minimum then maximum filter over `win` frames)."""
    Fl = gaussian_filter1d(F, sig, axis=0)
    Fl = minimum_filter1d(Fl, win, axis=0)
    return F - maximum_filter1d(Fl, win, axis=0)


def deconvolved(A, indicator_frames, kernel_frames, frame, snr, fs, gain=None, rng=None, win_s=60.0):
    """Record A (native steps) through calcium imaging (indicator 1/e decay `indicator_frames` frames, one
    frame = `frame` native sub-steps, white noise at `snr`), subtract the maximin baseline (60 s), deconvolve
    with an AR(1) kernel of `kernel_frames` frames (amendment 16: the data authors' fixed 2 s, which need not
    equal the indicator's own decay)."""
    from .recording import calcium
    F = calcium(A, decay=indicator_frames * frame, frame=frame, snr=snr, gain=gain, rng=rng)
    F = F - F.min(0) + 1.0                                     # fluorescence is positive
    return oasis(maximin(F, max(int(win_s * fs), 3)), kernel_frames).astype(np.float32)
