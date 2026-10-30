"""BenchSample: the minimal, measurement-space view of a recording that the benchmark scores.

Every source, real or artificial, is reduced to the same thing: z-scored class traces on
the canonical index (NaN rows where a class is not observed), at the source's own frame
times. Nothing else is visible to the metrics, so no level can be passed by reading
metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

from ..data.canonical import class_matrix, zscore_rows
from ..data.recording import Recording


@dataclass
class BenchSample:
    name: str                      # e.g. "real:2023-08-14-01" or "shuffle:2023-08-14-01"
    classes: tuple[str, ...]
    x: np.ndarray                  # (C, T) z-scored, NaN rows for unobserved classes
    dt: float                      # median frame interval, s
    origin: Optional[str] = None   # uid of the real worm this was derived from, if any
    behaviour: dict = field(default_factory=dict)

    @property
    def observed(self) -> np.ndarray:
        return np.isfinite(self.x).all(axis=1)

    def half(self, which: int) -> "BenchSample":
        t = self.x.shape[1] // 2
        sl = slice(0, t) if which == 0 else slice(t, 2 * t)
        beh = {k: v[sl] for k, v in self.behaviour.items()}
        return BenchSample(f"{self.name}[{which}]", self.classes, zscore_rows(self.x[:, sl]),
                           self.dt, self.origin, beh)


def from_recording(rec: Recording, classes: Sequence[str], min_confidence: float = 2.0,
                   name: Optional[str] = None) -> BenchSample:
    x = zscore_rows(class_matrix(rec, classes, min_confidence))
    beh = {k: np.asarray(v, float) for k, v in rec.behaviour.items()
           if k in ("velocity", "reversing", "head_angle", "head_curvature")}
    if "dist_to_boundary_mm" in rec.behaviour:          # arena experiments only
        beh["dist_to_boundary"] = np.asarray(rec.behaviour["dist_to_boundary_mm"], float)
    if "reversing" not in beh and rec.reversals:
        rv = np.zeros(rec.n_frames)
        for a, b in rec.reversals:
            rv[a: b + 1] = 1
        beh["reversing"] = rv
    return BenchSample(name or f"real:{rec.uid}", tuple(classes), x, rec.frame_interval,
                       origin=rec.uid, behaviour=beh)
