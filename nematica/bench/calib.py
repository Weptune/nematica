"""Calibration systems: artificial data with known answers, used to test the ruler itself.

Each is derived from one real test worm and keeps exactly some of its structure:

    independent_shift   each class circularly shifted by its own random offset (>= 60 s)
                        keeps: single-neuron distributions and timescales
                        breaks: correlations between neurons             -> should fail L2
    frame_shuffle       all classes' frames permuted together
                        keeps: distributions, zero-lag correlations
                        breaks: temporal structure                       -> should fail L1.timescale
    phase_randomised    Fourier phases randomised, the same random phases for all classes
                        keeps: power spectra and cross-spectra (timescales, correlations)
                        breaks: non-Gaussian value distributions         -> may fail L1.distribution
    gaussian_noise      independent unit Gaussian noise
                        keeps: nothing                                   -> should fail everything
"""

from __future__ import annotations

import numpy as np

from ..data.canonical import zscore_rows
from .sample import BenchSample


def _like(s: BenchSample, kind: str, x: np.ndarray, behaviour: dict | None = None) -> BenchSample:
    x = np.where(s.observed[:, None], x, np.nan)
    return BenchSample(f"{kind}:{s.origin}", s.classes, zscore_rows(x), s.dt, origin=s.origin,
                       behaviour=behaviour or {})


def independent_shift(s: BenchSample, rng: np.random.Generator, min_shift_s: float = 60.0) -> BenchSample:
    T = s.x.shape[1]
    lo = int(min_shift_s / s.dt)
    out = s.x.copy()
    for i in np.flatnonzero(s.observed):
        out[i] = np.roll(s.x[i], int(rng.integers(lo, T - lo)))
    # behaviour stays on the original timeline, so neuron-behaviour coupling is broken
    return _like(s, "independent_shift", out, dict(s.behaviour))


def frame_shuffle(s: BenchSample, rng: np.random.Generator) -> BenchSample:
    perm = rng.permutation(s.x.shape[1])
    # behaviour shuffled with the frames, so zero-lag coupling is kept
    return _like(s, "frame_shuffle", s.x[:, perm], {k: v[perm] for k, v in s.behaviour.items()})


def phase_randomised(s: BenchSample, rng: np.random.Generator) -> BenchSample:
    obs = s.observed
    x = np.nan_to_num(s.x)
    T = x.shape[1]
    f = np.fft.rfft(x, axis=1)
    phase = rng.uniform(0, 2 * np.pi, f.shape[1])
    phase[0] = 0
    if T % 2 == 0:
        phase[-1] = 0
    y = np.fft.irfft(f * np.exp(1j * phase)[None, :], n=T, axis=1)
    y[~obs] = np.nan
    beh = {}
    for k_, v in s.behaviour.items():          # same phases, so behaviour coupling is kept
        fb = np.fft.rfft(v - v.mean())
        beh[k_] = np.fft.irfft(fb * np.exp(1j * phase), n=T) + v.mean()
    if "reversing" in beh:
        beh["reversing"] = (beh["reversing"] > 0.5).astype(float)
    return _like(s, "phase_randomised", y, beh)


def gaussian_noise(s: BenchSample, rng: np.random.Generator) -> BenchSample:
    return _like(s, "gaussian_noise", rng.standard_normal(s.x.shape), dict(s.behaviour))


CALIBRATIONS = {
    "independent_shift": independent_shift,
    "frame_shuffle": frame_shuffle,
    "phase_randomised": phase_randomised,
    "gaussian_noise": gaussian_noise,
}

# What each calibration system is designed to do at each metric. "either" = no firm design.
EXPECTED = {
    "independent_shift": {"L1.distribution": "inside", "L1.timescale": "inside",
                          "L2.correlation": "outside", "L2.dimension": "outside",
                          "L4.leadlag": "outside", "L4.dwell": "inside",
                          "L5.encoding": "outside", "L5.reversal": "outside"},
    "frame_shuffle": {"L1.distribution": "inside", "L1.timescale": "outside",
                      "L2.correlation": "inside", "L2.dimension": "inside",
                      "L4.leadlag": "outside", "L4.dwell": "outside",
                      "L5.encoding": "inside", "L5.reversal": "inside"},
    "phase_randomised": {"L1.distribution": "either", "L1.timescale": "inside",
                         "L2.correlation": "inside", "L2.dimension": "inside",
                         "L4.leadlag": "inside", "L4.dwell": "either",
                         "L5.encoding": "inside", "L5.reversal": "either"},
    "gaussian_noise": {"L1.distribution": "either", "L1.timescale": "outside",
                       "L2.correlation": "outside", "L2.dimension": "outside",
                       "L4.leadlag": "outside", "L4.dwell": "outside",
                       "L5.encoding": "outside", "L5.reversal": "outside"},
}

# Level 6 (population-level environment test, environment.py), designed before running.
EXPECTED_ENV = {
    "independent_shift": {"L6.encounter": "outside", "L6.approach": "inside", "L6.occupancy": "inside"},
    "frame_shuffle": {"L6.encounter": "outside", "L6.approach": "either", "L6.occupancy": "inside"},
    "phase_randomised": {"L6.encounter": "either", "L6.approach": "either", "L6.occupancy": "either"},
    "gaussian_noise": {"L6.encounter": "outside", "L6.approach": "inside", "L6.occupancy": "inside"},
}
