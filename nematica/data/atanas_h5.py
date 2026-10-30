"""Atanas et al. 2023 processed HDF5 files (Zenodo 10.5281/zenodo.8150514, processed_h5),
joined with neuron names and conditions from the WormWideWeb JSON exports.

The processed files carry posture and position but no neuron names; the JSON files carry
names. Their trace rows are identical (verified: max absolute difference 0.0), so labels,
heat-pulse frames and valid ranges are taken from the JSON and everything else from the h5.
Positions (zeroed_x/y_confocal) are in units of 0.1 um, like the copper stage.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .copper import _load_flavell_h5
from .recording import Recording
from .wormwideweb import load_wormwideweb_json


def load_atanas_h5(h5_path: str | Path, json_path: str | Path) -> Recording:
    h5_path, json_path = Path(h5_path), Path(json_path)
    meta = load_wormwideweb_json(json_path)
    rec = _load_flavell_h5(h5_path, meta.labels, "atanas2023", meta.conditions, meta.uid)
    if rec.traces.shape != meta.traces.shape or not np.allclose(rec.traces, meta.traces, equal_nan=True):
        raise ValueError(f"{meta.uid}: h5 and JSON traces differ; refusing to join labels")
    rec.events = meta.events
    rec.valid = meta.valid
    rec.meta["json_file"] = json_path.name
    return rec


def load_atanas_dir(h5_folder: str | Path, json_folder: str | Path) -> list[Recording]:
    """Only recordings present in both folders (i.e. with neuron names) are loaded."""
    h5_folder, json_folder = Path(h5_folder), Path(json_folder)
    recs = []
    for j in sorted(json_folder.glob("*.json")):
        h = h5_folder / f"{j.stem}-data.h5"
        if h.exists():
            recs.append(load_atanas_h5(h, j))
    if not recs:
        raise FileNotFoundError(f"No recordings found in both {h5_folder} and {json_folder}")
    return recs
