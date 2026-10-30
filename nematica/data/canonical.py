"""Canonical neuron-class index shared by every dataset and every artificial system.

NEMATICA compares worms at the level of neuron classes (AVA, not AVAL/AVAR), because
the Flavell datasets often leave the side unresolved and pool bilateral pairs. Class
names come from the NeuroPAL annotations themselves, which use one naming scheme
across Flavell-lab datasets.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence

import numpy as np

from .recording import Recording


def class_frequency(recs: Iterable[Recording], min_confidence: float = 2.0) -> Counter:
    freq: Counter = Counter()
    for r in recs:
        freq.update(set(r.classes(min_confidence)))
    return freq


def canonical_classes(recs: Sequence[Recording], min_fraction: float = 0.0,
                      min_confidence: float = 2.0) -> list[str]:
    """Sorted classes labelled in at least `min_fraction` of the recordings."""
    freq = class_frequency(recs, min_confidence)
    need = min_fraction * len(recs)
    return sorted(c for c, n in freq.items() if n >= need)


def class_matrix(rec: Recording, classes: Sequence[str], min_confidence: float = 2.0) -> np.ndarray:
    """(len(classes), T) class-averaged traces on the canonical index; NaN rows where unlabelled."""
    names, traces = rec.class_traces(min_confidence)
    lookup = {n: i for i, n in enumerate(names)}
    out = np.full((len(classes), rec.n_frames), np.nan)
    for j, c in enumerate(classes):
        if c in lookup:
            out[j] = traces[lookup[c]]
    return out


def zscore_rows(x: np.ndarray) -> np.ndarray:
    """Per-row z-score over the recording, ignoring NaN rows.

    This is the benchmark's measurement convention and is applied identically to real
    and artificial recordings. (Models are trained with training-period statistics
    instead; whole-recording statistics are only used for comparing whole recordings.)
    """
    z = np.full_like(x, np.nan, dtype=float)
    rows = np.isfinite(x).any(axis=1)
    if rows.any():
        mu = np.nanmean(x[rows], axis=1, keepdims=True)
        sd = np.nanstd(x[rows], axis=1, keepdims=True)
        with np.errstate(invalid="ignore", divide="ignore"):
            z[rows] = (x[rows] - mu) / sd
    z[~np.isfinite(z)] = np.nan
    return z
