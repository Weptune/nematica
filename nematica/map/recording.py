"""Recording models: how an artificial network (or a synthetic system) is recorded the way a brain was.

Each takes native activity A (time, units) at the native step and returns what the instrument would see.
"""
from __future__ import annotations

import numpy as np


def softplus(x):
    return np.logaddexp(0, x)


def calcium(A, decay=8.0, frame=2, snr=4.0, rng=None):
    """Rectify, convolve with an exponential indicator kernel (decay in native steps), sample every `frame`
    steps, add white noise at the given signal-to-noise ratio (SD of signal / SD of noise, per unit)."""
    rng = rng or np.random.default_rng(0)
    R = softplus(np.asarray(A, float))
    k = np.exp(-np.arange(int(6 * decay) + 1) / decay)
    k /= k.sum()
    T = len(R)
    F = np.fft.irfft(np.fft.rfft(R, n=2 * T, axis=0) * np.fft.rfft(k, n=2 * T)[:, None], axis=0)[:T]
    F = F[::frame]
    sd = F.std(0) + 1e-12
    return F + rng.standard_normal(F.shape) * sd / snr


def spikes(A, mean_count=0.5, bin_steps=1, rng=None):
    """Rectify, scale each unit to a mean Poisson count per native step, draw spikes, sum in bins."""
    rng = rng or np.random.default_rng(0)
    R = softplus(np.asarray(A, float))
    R = R / (R.mean(0) + 1e-12) * mean_count
    S = rng.poisson(R)
    T = (len(S) // bin_steps) * bin_steps
    return S[:T].reshape(-1, bin_steps, S.shape[1]).sum(1).astype(float)


def native(A, rng=None):
    return np.asarray(A, float)


RECORDINGS = {"native": native, "calcium": calcium, "spikes": spikes}
