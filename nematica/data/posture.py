"""Rebuild a worm's centreline from tracked segment angles (Flavell posture pipeline).

body_angle_absolute[t, i] is the absolute direction of body segment i at frame t,
starting at the nose. Each segment is about 17.7 um long; NaNs mark segments past the
tail. Integrating the directions from the nose gives the centreline in mm, in the
camera's image frame, relative to the nose.
"""

from __future__ import annotations

import numpy as np

from .copper import SEGMENT_LENGTH_MM


def valid_segments(angles: np.ndarray) -> int:
    """Length of the leading run of non-NaN angles."""
    bad = np.flatnonzero(~np.isfinite(angles))
    return int(bad[0]) if bad.size else int(angles.size)


def centreline(angles: np.ndarray, segment_length_mm: float = SEGMENT_LENGTH_MM) -> np.ndarray:
    """(n_valid + 1, 2) points from nose to tail, in mm, nose at the origin."""
    n = valid_segments(angles)
    theta = angles[:n]
    steps = segment_length_mm * np.stack([np.cos(theta), np.sin(theta)], axis=1)
    return np.vstack([np.zeros((1, 2)), np.cumsum(steps, axis=0)])


def body_length_mm(angles: np.ndarray, segment_length_mm: float = SEGMENT_LENGTH_MM) -> float:
    return valid_segments(angles) * segment_length_mm


def curvature_wave(seg: np.ndarray) -> np.ndarray:
    """(T, n-1) curvature along the body: change in angle between neighbouring segments."""
    return np.diff(seg, axis=1)
