"""Recording models (docs/MAP.md, amendment 2): an artificial network (or a synthetic system) recorded the way
a brain preparation was. Units are standardised and multiplied by a registered gain before rectification, so
the share of signal that survives does not depend on a network's native activation scale.

`match_calcium` and `match_spikes` set the knobs from a preparation's own summary numbers (the registered
matching rule); the knobs are then swept around the matched values for the mismatch budget.
"""
from __future__ import annotations

import numpy as np

GAIN = 1.0


def softplus(x):
    return np.logaddexp(0, x)


def _std(A):
    A = np.asarray(A, float)
    return (A - A.mean(0)) / (A.std(0) + 1e-12)


def native(A, rng=None):
    return np.asarray(A, float)


def calcium(A, decay=8.0, frame=2, snr=4.0, gain=GAIN, rng=None):
    """Standardise, rectify (softplus of gain x), convolve with an exponential indicator kernel (decay in
    native steps), keep every `frame`-th step, add white noise at the given signal-to-noise ratio (SD of
    signal / SD of noise, per unit)."""
    rng = rng or np.random.default_rng(0)
    R = softplus(gain * _std(A))
    k = np.exp(-np.arange(int(6 * max(decay, 0.2)) + 1) / max(decay, 1e-3))
    k /= k.sum()
    T = len(R)
    F = np.fft.irfft(np.fft.rfft(R, n=2 * T, axis=0) * np.fft.rfft(k, n=2 * T)[:, None], axis=0)[:T]
    if frame > 1:                                       # fractional frames: sample by linear interpolation
        pos = np.arange(0, T - 1, frame)
        i0 = pos.astype(int)
        w = (pos - i0)[:, None]
        F = F[i0] * (1 - w) + F[np.minimum(i0 + 1, T - 1)] * w
    sd = F.std(0) + 1e-12
    return F + rng.standard_normal(F.shape) * sd / snr


def spikes(A, mean_count=0.5, bin_steps=1, gain=GAIN, rng=None):
    """Standardise, rectify (softplus of gain x), scale each unit to a mean Poisson count per native step,
    integrate the rate over bins of `bin_steps` native steps (fractional allowed: the cumulative rate is
    interpolated at bin edges) and draw each bin's count from a Poisson distribution."""
    rng = rng or np.random.default_rng(0)
    R = softplus(gain * _std(A))
    R = R / (R.mean(0) + 1e-12) * mean_count
    b = max(float(bin_steps), 1.0)
    C = np.vstack([np.zeros((1, R.shape[1])), np.cumsum(R, 0)])
    edges = np.arange(0, len(R) + 1e-9, b)
    i0 = np.minimum(edges.astype(int), len(R) - 1)
    w = (edges - i0)[:, None]
    lam = np.diff(C[i0] * (1 - w) + C[i0 + 1] * w, axis=0)
    return rng.poisson(np.clip(lam, 0, None)).astype(float)


RECORDINGS = {"native": native, "calcium": calcium, "spikes": spikes}


def match_calcium(A, prep, rng=None, n_iter=12):
    """Registered rule (amendment 2). From the preparation: `decay_over_tau` (indicator decay / recorded
    tau_med), `frames_per_tau` (frames per recorded tau_med), `noise` (median white-noise share,
    measures.noise_fraction). Chooses decay, frame and snr for this network so that, recorded, it has the
    same three numbers. Returns the knobs."""
    from .measures import noise_fraction, tau_med
    rng = rng or np.random.default_rng(0)
    t0 = tau_med(_std(A))
    lo, hi = 0.05, 200.0                                   # decay in native steps; tau_rec grows with decay
    for _ in range(n_iter):
        d = np.sqrt(lo * hi)
        rec = calcium(A, decay=d, frame=1, snr=1e6, rng=rng)
        if d / tau_med(rec) < prep["decay_over_tau"]:
            lo = d
        else:
            hi = d
    d = np.sqrt(lo * hi)
    t_rec = tau_med(calcium(A, decay=d, frame=1, snr=1e6, rng=rng))
    frame = max(t_rec / prep["frames_per_tau"], 1.0)
    lo, hi = 0.3, 100.0                                    # snr; noise share falls as snr rises
    for _ in range(n_iter):
        s = np.sqrt(lo * hi)
        nf = np.median(noise_fraction(calcium(A, decay=d, frame=frame, snr=s, rng=rng)))
        if nf > prep["noise"]:
            lo = s
        else:
            hi = s
    return {"decay": float(d), "frame": float(frame), "snr": float(np.sqrt(lo * hi)), "native_tau": float(t0)}


def match_spikes(A, prep, rng=None, n_iter=12):
    """Registered rule (amendment 2). From the preparation (binned at 20 ms): `bins_per_tau` (bins per
    recorded tau_med), `count_per_bin` (mean spikes per bin per unit) and `noise` (median white-noise share).
    Chooses bin_steps so bins per recorded tau_med match, mean_count so counts per bin match, and gain so the
    white-noise share matches (more gain, more rate modulation, less relative Poisson noise)."""
    from .measures import noise_fraction, tau_med
    rng = rng or np.random.default_rng(0)
    t_nat = tau_med(softplus(_std(A)))
    b = max(t_nat / prep["bins_per_tau"], 1.0)
    mc = prep["count_per_bin"] / b
    lo, hi = 0.1, 20.0
    for _ in range(n_iter):
        g = np.sqrt(lo * hi)
        nf = np.median(noise_fraction(spikes(A, mean_count=mc, bin_steps=b, gain=g, rng=rng)))
        if nf > prep["noise"]:
            lo = g
        else:
            hi = g
    return {"bin_steps": float(b), "mean_count": float(mc), "gain": float(np.sqrt(lo * hi)), "native_tau": float(t_nat)}
