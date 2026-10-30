"""Loader for WormWideWeb / Flavell-lab JSON exports (Atanas et al. 2023 format).

Each JSON file is one worm. Fields used:
    trace_original      (N_roi, T) activity from the Flavell pipeline. Used as-is.
    trace_array         (N_roi, T) the same, z-scored over the WHOLE recording.
                        Not used: whole-recording statistics leak test-period
                        information into any model trained on part of it.
    labeled             {roi index (1-based, string): {label, neuron_class, LR, DV, confidence}}
    timestamp_confocal  (T,) seconds
    velocity, head_curvature, body_curvature, angular_velocity, pumping   (T,)
    reversal_events     [[start, end], ...] 1-based inclusive frames
    ranges              valid frame ranges, 1-based inclusive
    events              {"heat": [frame]} for heat-pulse sessions, absent otherwise
    dataset_type        e.g. ["heat", "neuropal"] or ["baseline", "neuropal"]

Frame indices are converted to 0-based on load.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

import numpy as np

from .recording import Recording, RoiLabel

BEHAVIOUR_KEYS = ("velocity", "head_curvature", "body_curvature", "angular_velocity", "pumping")


def _side(value) -> Optional[str]:
    return value if value in ("L", "R") else None


def _dv(value) -> Optional[str]:
    return value if value in ("D", "V") else None


def load_wormwideweb_json(path: str | Path, dataset: str = "atanas2023") -> Recording:
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        d = json.load(fh)

    traces = np.asarray(d["trace_original"], dtype=float)
    n_rois, n_frames = traces.shape

    ts = np.asarray(d["timestamp_confocal"], dtype=float)
    if ts.shape != (n_frames,):
        raise ValueError(f"{path.name}: {ts.shape[0]} timestamps for {n_frames} frames")
    t = ts - ts[0]

    labels: dict[int, RoiLabel] = {}
    for key, info in d.get("labeled", {}).items():
        row = int(key) - 1
        if not 0 <= row < n_rois:
            raise ValueError(f"{path.name}: label index {key} outside {n_rois} ROIs")
        labels[row] = RoiLabel(
            name=str(info["label"]),
            neuron_class=str(info.get("neuron_class") or info["label"]).rstrip("?"),
            side=_side(info.get("LR")),
            dv=_dv(info.get("DV")),
            confidence=float(info.get("confidence", 0.0)),
        )

    behaviour = {}
    for key in BEHAVIOUR_KEYS:
        if key in d:
            arr = np.asarray(d[key], dtype=float)
            if arr.shape != (n_frames,):
                raise ValueError(f"{path.name}: '{key}' has {arr.shape}, expected ({n_frames},)")
            behaviour[key] = arr

    valid = np.zeros(n_frames, dtype=bool)
    for rng in d.get("ranges", [[1, n_frames]]):
        lo, hi = int(rng[0]) - 1, int(rng[-1]) - 1
        valid[max(lo, 0): min(hi, n_frames - 1) + 1] = True

    events = {k: [int(f) - 1 for f in v] for k, v in (d.get("events") or {}).items()}
    reversals = [(int(a) - 1, int(b) - 1) for a, b in d.get("reversal_events", [])]

    return Recording(
        uid=str(d.get("uid", path.stem)),
        dataset=dataset,
        t=t,
        traces=traces,
        traces_kind="trace_original (Flavell pipeline)",
        labels=labels,
        behaviour=behaviour,
        events=events,
        reversals=reversals,
        valid=valid,
        conditions=tuple(d.get("dataset_type", [])),
        provenance="M",
        meta={"source_file": path.name, "num_neurons_field": d.get("num_neurons")},
    )


def load_wormwideweb_dir(folder: str | Path, dataset: str = "atanas2023",
                         uids: Optional[Iterable[str]] = None) -> list[Recording]:
    folder = Path(folder)
    files = sorted(folder.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No .json recordings in {folder}")
    wanted = set(uids) if uids is not None else None
    recs = []
    for f in files:
        if wanted is not None and f.stem not in wanted:
            continue
        recs.append(load_wormwideweb_json(f, dataset=dataset))
    return recs
