"""The Recording: the one object every real or artificial source becomes.

Provenance tags used throughout NEMATICA:
    M  measured   (recorded data, EM wiring)
    I  inferred   (synapse signs, fitted kernels, atlas positions)
    L  learned    (model output)
    A  assumed    (modelling or display choice)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class RoiLabel:
    """NeuroPAL identity of one region of interest (ROI)."""

    name: str                 # e.g. "AVAL", "AIA?" when the side is unresolved
    neuron_class: str         # e.g. "AVA"
    side: Optional[str]       # "L", "R", or None when unresolved / unpaired
    dv: Optional[str]         # "D", "V", or None
    confidence: float         # NeuroPAL confidence, 1 (low) to 5 (high)

    @property
    def side_resolved(self) -> bool:
        return self.side in ("L", "R") and not self.name.endswith("?")


@dataclass
class Recording:
    """Named-neuron traces in measurement space, plus behaviour and stimuli.

    All frame indices are 0-based. Arrays indexed by frame have length n_frames.
    """

    uid: str
    dataset: str
    t: np.ndarray                         # (T,) seconds from the first frame
    traces: np.ndarray                    # (N_roi, T) activity, measurement space
    traces_kind: str                      # e.g. "F/F20 original (Flavell pipeline)"
    labels: dict[int, RoiLabel]           # ROI row index -> identity (labelled ROIs only)
    behaviour: dict[str, np.ndarray] = field(default_factory=dict)
    events: dict[str, list[int]] = field(default_factory=dict)       # stimulus name -> frames
    reversals: list[tuple[int, int]] = field(default_factory=list)   # (start, end) inclusive
    valid: Optional[np.ndarray] = None    # (T,) bool; False where frames are excluded
    posture: dict[str, np.ndarray] = field(default_factory=dict)     # e.g. segment angles, stage path
    conditions: tuple[str, ...] = ()      # e.g. ("heat", "neuropal")
    provenance: str = "M"
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.t = np.asarray(self.t, dtype=float)
        self.traces = np.asarray(self.traces, dtype=float)
        if self.traces.ndim != 2:
            raise ValueError(f"{self.uid}: traces must be 2-D (rois x frames)")
        n_frames = self.traces.shape[1]
        if self.t.shape != (n_frames,):
            raise ValueError(f"{self.uid}: t has {self.t.shape}, traces have {n_frames} frames")
        for key, arr in self.behaviour.items():
            if np.asarray(arr).shape != (n_frames,):
                raise ValueError(f"{self.uid}: behaviour '{key}' length mismatch")
        if self.valid is None:
            self.valid = np.ones(n_frames, dtype=bool)
        for row in self.labels:
            if not 0 <= row < self.traces.shape[0]:
                raise ValueError(f"{self.uid}: label row {row} outside traces")

    # ------------------------------------------------------------------ basics
    @property
    def n_frames(self) -> int:
        return self.traces.shape[1]

    @property
    def n_rois(self) -> int:
        return self.traces.shape[0]

    @property
    def frame_interval(self) -> float:
        """Median time between frames, in seconds."""
        return float(np.median(np.diff(self.t)))

    @property
    def duration(self) -> float:
        return float(self.t[-1] - self.t[0])

    # --------------------------------------------------------------- identity
    def labelled(self, min_confidence: float = 2.0) -> dict[int, RoiLabel]:
        return {r: lab for r, lab in self.labels.items() if lab.confidence >= min_confidence}

    def classes(self, min_confidence: float = 2.0) -> list[str]:
        return sorted({lab.neuron_class for lab in self.labelled(min_confidence).values()})

    def class_traces(self, min_confidence: float = 2.0) -> tuple[list[str], np.ndarray]:
        """Average traces over all labelled ROIs of each neuron class.

        Left and right members (and side-unresolved ROIs) are pooled, which is
        how NEMATICA compares across worms and datasets.
        """
        groups: dict[str, list[int]] = {}
        for row, lab in self.labelled(min_confidence).items():
            groups.setdefault(lab.neuron_class, []).append(row)
        names = sorted(groups)
        out = np.empty((len(names), self.n_frames))
        for i, name in enumerate(names):
            out[i] = self.traces[groups[name]].mean(axis=0)
        return names, out

    def neuron_traces(self, min_confidence: float = 2.0) -> tuple[list[str], np.ndarray]:
        """Traces of side-resolved neurons only (e.g. AVAL, AVAR); duplicates averaged."""
        groups: dict[str, list[int]] = {}
        for row, lab in self.labelled(min_confidence).items():
            if lab.side_resolved or lab.side is None and not lab.name.endswith("?"):
                groups.setdefault(lab.name, []).append(row)
        names = sorted(groups)
        out = np.empty((len(names), self.n_frames))
        for i, name in enumerate(names):
            out[i] = self.traces[groups[name]].mean(axis=0)
        return names, out

    def find(self, name: str, min_confidence: float = 2.0) -> Optional[np.ndarray]:
        """Trace for a neuron ('AVAL') or a class ('AVA'), or None if not labelled."""
        rows = [r for r, lab in self.labelled(min_confidence).items()
                if lab.name == name or lab.neuron_class == name]
        if not rows:
            return None
        return self.traces[rows].mean(axis=0)

    # --------------------------------------------------------------- summary
    def summary(self, min_confidence: float = 2.0) -> dict:
        lab = self.labelled(min_confidence)
        return {
            "uid": self.uid,
            "dataset": self.dataset,
            "conditions": "+".join(self.conditions),
            "frames": self.n_frames,
            "duration_min": round(self.duration / 60, 2),
            "frame_interval_s": round(self.frame_interval, 3),
            "rois": self.n_rois,
            "labelled": len(lab),
            "classes": len({x.neuron_class for x in lab.values()}),
            "side_resolved": sum(x.side_resolved for x in lab.values()),
            "reversals": len(self.reversals),
            "valid_frames": int(self.valid.sum()),
            "provenance": self.provenance,
        }
