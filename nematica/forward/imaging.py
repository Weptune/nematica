"""Measurement-space forward model: how a microscope would see an artificial brain.

Every artificial system is passed through the same steps before it is compared with
real worms (plan section 6):

  1. activity -> non-negative drive          (system-specific; e.g. synaptic activation)
  2. drive -> calcium -> indicator           two first-order filters, tau_ca and tau_ind
  3. sample at a real worm's frame times      average over each frame's exposure window
  4. add noise                                Gaussian, per class, at a fraction of the
                                              signal SD estimated from real traces
  5. mask                                     keep only the classes the template worm labelled
  6. normalise                                the benchmark's own z-scoring (BenchSample)

Parameter provenance: kernel time constants [A] (defaults near jGCaMP7f nuclear kinetics,
refined later by fitting real traces), noise fraction [I] (estimated from real traces).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..bench.sample import BenchSample
from ..data.canonical import zscore_rows


@dataclass
class ImagingParams:
    tau_ca_s: float = 0.5        # calcium dynamics [A]
    tau_ind_s: float = 1.0       # indicator (nuclear GCaMP7f) kinetics [A]
    noise_fraction: float = 0.3  # noise SD as a fraction of signal SD [I, see estimate_noise_fraction]
    exposure_s: float = 0.6      # integration window per volume [A, about one frame]


def first_order(x: np.ndarray, dt: float, tau: float) -> np.ndarray:
    """Causal first-order low-pass along the last axis."""
    a = np.exp(-dt / tau)
    y = np.empty_like(x)
    y[..., 0] = x[..., 0]
    for k in range(1, x.shape[-1]):
        y[..., k] = a * y[..., k - 1] + (1 - a) * x[..., k]
    return y


def sample_frames(x: np.ndarray, t_src: np.ndarray, t_frames: np.ndarray, exposure_s: float) -> np.ndarray:
    """Average x (C, N) over [t - exposure/2, t + exposure/2] for every frame time."""
    cs = np.concatenate([np.zeros((x.shape[0], 1)), np.cumsum(x, axis=1)], axis=1)
    lo = np.searchsorted(t_src, t_frames - exposure_s / 2)
    hi = np.searchsorted(t_src, t_frames + exposure_s / 2)
    hi = np.maximum(hi, lo + 1)
    lo = np.clip(lo, 0, x.shape[1] - 1)
    hi = np.clip(hi, 1, x.shape[1])
    return (cs[:, hi] - cs[:, lo]) / (hi - lo)


def estimate_noise_fraction(real: list[BenchSample]) -> float:
    """Rough noise-to-signal SD ratio from frame-to-frame differences of real traces.

    For white measurement noise of variance s2 on a slow signal, var(diff) ~ 2 s2, so
    s ~ sqrt(var(diff) / 2). Slow signals contribute too, so this is an upper bound [I].
    """
    vals = []
    for s in real:
        for i in np.flatnonzero(s.observed):
            d = np.diff(s.x[i])
            vals.append(np.sqrt(np.var(d) / 2) / np.std(s.x[i]))
    return float(np.median(vals))


def image(name: str, classes: tuple[str, ...], drive: np.ndarray, t_src: np.ndarray,
          template: BenchSample, t_frames: np.ndarray, params: ImagingParams,
          rng: np.random.Generator, behaviour: dict | None = None) -> BenchSample:
    """drive: (C, N) non-negative activity on the canonical index (NaN rows = not simulated)."""
    dt = float(np.median(np.diff(t_src)))
    sim = np.isfinite(drive).all(axis=1)
    x = np.nan_to_num(drive)
    x = first_order(first_order(x, dt, params.tau_ca_s), dt, params.tau_ind_s)
    y = sample_frames(x, t_src, t_frames, params.exposure_s)
    sd = y.std(axis=1, keepdims=True)
    y = y + params.noise_fraction * sd * rng.standard_normal(y.shape)
    keep = sim & template.observed
    y[~keep] = np.nan
    return BenchSample(name, classes, zscore_rows(y), float(np.median(np.diff(t_frames))),
                       origin=None, behaviour=behaviour or {})
