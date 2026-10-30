"""Export one recording as a compact replay bundle for the web lab.

Everything the browser shows comes from this file. Provenance per field:
    body.angles          [M] tracked segment angles, resampled to K points        (resampling [A])
    body.length_mm       [M] median tracked body length
    path_mm              [M] stage path; world frame = stage rotated 180 deg      (verified: heading
                         aligns with motion in all 27 copper worms, mean cosine 0.92), shifted
                         by a fitted constant offset so the head matches the recorded
                         distance to the arena centre [fit A]
    neurons[].pos_um     [I] atlas average positions (Skuhersky et al. 2022)
    neurons[].level      [M] recorded activity, display-scaled to 0..1 per neuron [A]
    behaviour.*          [M]
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from ..data.copper import SEGMENT_LENGTH_MM
from ..data.posture import valid_segments
from ..data.recording import Recording
from .atlas import load_atlas, position_for

K_POINTS = 48
MIN_SEGMENTS, MAX_SEGMENTS = 10, 70


def _resample_posture(seg: np.ndarray, k: int = K_POINTS):
    """Fixed-length, time-continuous body angles (T, k) from NaN-padded tracked angles."""
    n_frames = seg.shape[0]
    n_valid = np.array([valid_segments(seg[t]) for t in range(n_frames)])
    good = (n_valid >= MIN_SEGMENTS) & (n_valid <= MAX_SEGMENTS)
    if good.sum() < 10:
        raise ValueError("too few frames with usable posture")
    length_mm = float(np.median(n_valid[good])) * SEGMENT_LENGTH_MM
    s_target = (np.arange(k) + 0.5) / k * length_mm

    out = np.full((n_frames, k), np.nan)
    for t in np.flatnonzero(good):
        n = n_valid[t]
        theta = np.unwrap(seg[t, :n])
        s_src = (np.arange(n) + 0.5) * SEGMENT_LENGTH_MM
        out[t] = np.interp(s_target, s_src, theta)          # holds end values beyond the tail

    # make the whole body continuous in time: unwrap the head angle across good frames
    idx = np.flatnonzero(good)
    head = out[idx, 0]
    shift = np.unwrap(head) - head
    out[idx] += shift[:, None]

    # fill unusable frames by linear interpolation in time, per body point
    for j in range(k):
        out[:, j] = np.interp(np.arange(n_frames), idx, out[idx, j])
    return out, length_mm, good


def _display_level(trace: np.ndarray) -> np.ndarray:
    lo, hi = np.nanpercentile(trace, [5, 99])
    if not np.isfinite(hi - lo) or hi - lo <= 0:
        return np.zeros_like(trace)
    return np.clip((trace - lo) / (hi - lo), 0, 1)


def export_replay(rec: Recording, out_path: str | Path, min_confidence: float = 2.0,
                  split: str = "unknown") -> dict:
    seg = rec.posture["segment_angle"]
    angles, length_mm, good = _resample_posture(seg)
    path_world = -rec.posture["stage_xy_mm"]                 # world frame (see module doc)
    path_world = path_world - path_world[0]                  # start at the origin
    arena = rec.meta.get("arena", {})
    centre = (-np.asarray(arena["center_mm"]) + rec.posture["stage_xy_mm"][0]) if arena else None
    calibration = None
    if centre is not None and "dist_from_center_mm" in rec.behaviour:
        # The stage reference point is offset from the head by a constant camera calibration.
        # Fit that offset so the replayed head matches the recorded head-to-centre distance.
        dist = rec.behaviour["dist_from_center_mm"]
        ok = np.isfinite(dist)

        def residual(x):
            return np.hypot(*(path_world[ok] + x - centre).T) - dist[ok]

        fit = least_squares(residual, x0=np.zeros(2))
        path_world = path_world + fit.x
        err = np.abs(fit.fun)
        calibration = {"offset_mm": np.round(fit.x, 4).tolist(),
                       "head_distance_error_mm": {"mean": round(float(err.mean()), 4),
                                                  "p95": round(float(np.percentile(err, 95)), 4)}}
    centre = centre.tolist() if centre is not None else None

    atlas = load_atlas()
    neurons, missing = [], []
    for row, lab in sorted(rec.labelled(min_confidence).items(), key=lambda x: x[1].name):
        pos = position_for(lab.name, lab.neuron_class, lab.side, atlas)
        if pos is None:
            missing.append(lab.name)
            continue
        neurons.append({
            "name": lab.name,
            "cls": lab.neuron_class,
            "conf": lab.confidence,
            "pos_um": [round(p, 2) for p in pos],
            "level": np.round(_display_level(rec.traces[row]), 3).tolist(),
        })

    bundle = {
        "format": "nematica-replay/1",
        "uid": rec.uid,
        "dataset": rec.dataset,
        "split": split,
        "source": "real recording",
        "n_frames": rec.n_frames,
        "t": np.round(rec.t, 3).tolist(),
        "body": {
            "k": K_POINTS,
            "length_mm": round(length_mm, 4),
            "angles": np.round(angles, 4).ravel().tolist(),
            "tracked": good.astype(int).tolist(),
        },
        "path_mm": np.round(path_world, 4).ravel().tolist(),
        "arena": {"centre_mm": centre, "radius_mm": arena.get("radius_mm"),
                  "calibration": calibration} if centre else None,
        "behaviour": {
            "velocity": np.round(rec.behaviour["velocity"], 4).tolist(),
            "reversing": rec.behaviour["reversing"].astype(int).tolist(),
            "dist_from_centre_mm": np.round(rec.behaviour["dist_from_center_mm"], 3).tolist(),
        },
        "neurons": neurons,
        "notes": {
            "positions": "atlas average (Skuhersky et al. 2022), not this worm's own [I]",
            "activity": "recorded trace_array_original, scaled 5th to 99th percentile for display [M, scaling A]",
            "posture": "tracked at the neural frame rate (about 1.67 Hz) and interpolated between frames [M, interpolation A]",
            "dorsal_side": "dorsal-ventral side of the body in the image is not yet determined [A]",
        },
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    return {"uid": rec.uid, "neurons": len(neurons), "missing_positions": missing,
            "tracked_fraction": round(float(good.mean()), 3), "length_mm": round(length_mm, 3),
            "calibration": calibration,
            "bytes": out_path.stat().st_size}
