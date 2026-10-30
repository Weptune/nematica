"""Loader for the copper-boundary dataset (Baskoylu et al. 2026, Dryad 10.5061/dryad.w9ghx3g4v).

The .h5 files were written from Julia, which is column-major, so h5py returns every
matrix transposed relative to the README: traces come out as (frames, neurons) and are
transposed back here. Julia indices are 1-based and are converted to 0-based.

Units after loading:
    t                    seconds from the first confocal frame
    velocity             mm/s (positive forward)
    head_angle           rad; sign convention may differ between animals (README)
    dist_from_center_mm  distance of the head from the arena centre, mm [M]
    dist_to_boundary_mm  arena radius minus dist_from_center_mm, mm; positive inside the
                         arena, 0 at the copper boundary. Uses the per-worm fitted circle
                         (behavior/circle_radius) when present, else 4 mm (README) [I]
    posture['segment_angle']   (T, 62) absolute direction of each body segment, rad;
                               NaN beyond the tail
    posture['stage_xy_mm']     (T, 2) stage position plus start offset, mm
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import h5py
import numpy as np

from .jld2_labels import load_neuropal_labels
from .recording import Recording, RoiLabel

STAGE_UNIT_MM = 1e-4        # stage and distance values are in units of 0.1 um
SEGMENT_LENGTH_MM = 0.0177  # body segment length used by the Flavell posture pipeline [I]
DEFAULT_ARENA_RADIUS_MM = 4.0  # copper boundary radius stated in the Dryad README [M]


def _arr(g, key):
    return np.asarray(g[key][()])


def uid_from_filename(path: Path) -> str:
    return path.name.replace("-cudata.h5", "")


def _load_flavell_h5(path: Path, labels, dataset: str, conditions: tuple, uid: str) -> Recording:
    """Shared reader for Flavell-lab processed HDF5 files (copper set and Atanas 2023)."""
    with h5py.File(path, "r") as f:
        traces = _arr(f, "gcamp/trace_array_original").T        # -> (neurons, frames)
        ts = _arr(f, "timing/timestamp_confocal").astype(float)
        n_frames = traces.shape[1]
        if ts.shape != (n_frames,):
            raise ValueError(f"{path.name}: {ts.shape} timestamps for {n_frames} frames")

        b = f["behavior"]
        behaviour = {
            "velocity": _arr(b, "velocity").astype(float),
            "head_angle": _arr(b, "head_angle").astype(float),
            "angular_velocity": _arr(b, "angular_velocity").astype(float),
            "pumping": _arr(b, "pumping").astype(float),
            "reversing": _arr(b, "reversal_vec").astype(float),
            "body_curvature": _arr(b, "worm_curvature").astype(float),
        }
        if "dist_from_cuCenter" in b:
            behaviour["dist_from_center_mm"] = _arr(b, "dist_from_cuCenter").astype(float) * STAGE_UNIT_MM

        ev = _arr(b, "reversal_events")
        if ev.ndim == 2 and ev.shape[0] == 2 and ev.shape[1] != 2:
            ev = ev.T                                                # -> (events, 2)
        reversals = [(int(a) - 1, int(e) - 1) for a, e in ev.reshape(-1, 2)]

        seg = _arr(b, "body_angle_absolute").astype(float)
        if seg.shape[0] != n_frames:
            seg = seg.T
        if "stage_x" in b:                                           # copper set
            x0 = float(_arr(b, "stage_xStart_nir"))
            y0 = float(_arr(b, "stage_yStart_nir"))
            stage = np.stack([_arr(b, "stage_x") + x0, _arr(b, "stage_y") + y0], axis=1) * STAGE_UNIT_MM
        else:                                                        # Atanas 2023
            stage = np.stack([_arr(b, "zeroed_x_confocal"), _arr(b, "zeroed_y_confocal")], axis=1) * STAGE_UNIT_MM
        posture = {
            "segment_angle": seg,
            "stage_xy_mm": stage,
            "segment_length_mm": np.array(SEGMENT_LENGTH_MM),
        }
        meta = {"source_file": path.name}
        if "circle_center" in b:
            meta["arena"] = {
                "center_mm": (_arr(b, "circle_center") * STAGE_UNIT_MM).tolist(),
                "radius_mm": float(_arr(b, "circle_radius")) * STAGE_UNIT_MM,
            }
        if "dist_from_center_mm" in behaviour:
            radius = meta.get("arena", {}).get("radius_mm", DEFAULT_ARENA_RADIUS_MM)
            behaviour["dist_to_boundary_mm"] = radius - behaviour["dist_from_center_mm"]

    return Recording(
        uid=uid,
        dataset=dataset,
        t=ts - ts[0],
        traces=traces,
        traces_kind="trace_array_original (Flavell pipeline)",
        labels=labels or {},
        behaviour=behaviour,
        events={},
        reversals=reversals,
        valid=np.ones(n_frames, dtype=bool),
        posture=posture,
        conditions=conditions,
        provenance="M",
        meta=meta,
    )


def load_copper_h5(path: str | Path, labels: Optional[dict[int, RoiLabel]] = None) -> Recording:
    path = Path(path)
    return _load_flavell_h5(path, labels, "copper2026", ("copper", "neuropal"), uid_from_filename(path))


def load_copper_dir(folder: str | Path, labels_file: Optional[str | Path] = None) -> list[Recording]:
    folder = Path(folder)
    files = sorted(folder.glob("*-cudata.h5"))
    if not files:
        raise FileNotFoundError(f"No *-cudata.h5 files in {folder}")
    labels_file = Path(labels_file) if labels_file else folder / "NeuroPAL_labels.jld2"
    all_labels = load_neuropal_labels(labels_file) if labels_file.exists() else {}
    recs = []
    for f in files:
        uid = uid_from_filename(f)
        recs.append(load_copper_h5(f, all_labels.get(uid)))
    return recs
