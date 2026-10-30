"""Kunert 2014 connectome model as a benchmark system (driving condition D1: noise drive).

Pipeline: simulate 279 neurons -> activation phi(V) = 1 / (1 + exp(-0.125 V)), the model's
own synaptic activation [A: chosen as the drive for calcium] -> average neurons of each
canonical class -> forward imaging model with a real template worm -> BenchSample.
The model has no behaviour output, so Level 5 is not scored for it.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from ..bench.sample import BenchSample
from ..forward.imaging import ImagingParams, image
from .kunert import BETA, KunertModel, coloured_noise_drive


def class_members(model: KunertModel, classes: tuple[str, ...], known_names: dict[str, set]) -> dict:
    """Map canonical classes to model neuron indices, using names seen in real labels.

    known_names: class -> set of neuron names observed for that class in real NeuroPAL labels.
    Falls back to the standard naming rule (class + optional D/V + optional L/R).
    """
    out = {}
    for c in classes:
        names = set(known_names.get(c, set()))
        idx = [i for i, n in enumerate(model.names)
               if n in names or (n.startswith(c) and n[len(c):].strip("DVLR") == "" and len(n) - len(c) <= 2)]
        if idx:
            out[c] = idx
    return out


SIM_DURATION_S = 1000.0     # long enough for every 16-minute template (after warm-up)
WARMUP_S = 30.0


def kunert_activation(model: KunertModel, amplitude: float, seed: int, cache_dir: Path | None = None,
                      tau_drive_s: float = 1.0, dt: float = 0.01, record_every_s: float = 0.1):
    """Simulate (or load from cache) phi(V) for all neurons after warm-up: (t, act)."""
    key = f"a{amplitude:g}_s{seed}_tau{tau_drive_s:g}_dt{dt:g}_r{record_every_s:g}_T{SIM_DURATION_S:g}"
    path = None
    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / f"kunert_{hashlib.sha1(key.encode()).hexdigest()[:10]}.npz"
        if path.exists():
            z = np.load(path)
            return z["t"], z["act"].astype(float)
    total = SIM_DURATION_S + WARMUP_S
    drive = coloured_noise_drive(model.n, amplitude, tau_drive_s, total, seed=seed)
    t, V = model.simulate(total, dt=dt, drive=drive, record_every_s=record_every_s, seed=seed)
    keep = t >= WARMUP_S
    t, V = t[keep] - WARMUP_S, V[:, keep]
    act = 1.0 / (1.0 + np.exp(-BETA * V))
    if path is not None:
        np.savez_compressed(path, t=t, act=act.astype(np.float16), key=key)
    return t, act


def simulate_kunert_sample(model: KunertModel, classes: tuple[str, ...], members: dict,
                           template: BenchSample, t_frames: np.ndarray, amplitude: float,
                           seed: int, params: ImagingParams, cache_dir: Path | None = None) -> BenchSample:
    t, act = kunert_activation(model, amplitude, seed, cache_dir)
    drive_cls = np.full((len(classes), act.shape[1]), np.nan)
    for i, c in enumerate(classes):
        if c in members:
            drive_cls[i] = act[members[c]].mean(axis=0)
    rng = np.random.default_rng(10_000 + seed)
    s = image(f"kunert_noise:a{amplitude:g}:{template.origin}", classes, drive_cls, t,
              template, t_frames - t_frames[0], params, rng)
    return s
