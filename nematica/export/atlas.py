"""Neuron soma positions from the Skuhersky et al. 2022 atlas (see data_assets/README.md)."""

from __future__ import annotations

import csv
import re
from pathlib import Path

ATLAS_FILE = Path(__file__).resolve().parents[2] / "data_assets" / "skuhersky2022_atlas.csv"
FLIPPED_LR = ("ALM", "BDU", "HSN", "PDE", "PVD", "SDQ")
NOSE_OFFSET_UM = 20.0   # [A] distance from nose tip to the atlas origin (near I1L)


def load_atlas(path: Path = ATLAS_FILE) -> dict[str, tuple[float, float, float]]:
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing: run `python scripts/fetch_atlas.py` first "
                                "(the atlas is downloaded from its source, not shipped)")
    """{neuron name: (um from nose tip along the body, dorsal-ventral um, left-right um)}."""
    out = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) < 4:
                continue
            name, ap, dv, lr = row[0].strip(), float(row[1]), float(row[2]), float(row[3])
            if any(name.startswith(p) for p in FLIPPED_LR):
                lr = -lr
            out[name] = (ap + NOSE_OFFSET_UM, dv, lr)
    return out


def position_for(label_name: str, neuron_class: str, side, atlas: dict) -> tuple[float, float, float] | None:
    """Atlas position for a labelled ROI; side-unresolved labels use the class mean."""
    if label_name in atlas:
        return atlas[label_name]
    unpadded = re.sub(r"^([A-Z]+)0(\d)$", r"\1\2", label_name)      # VB01 -> VB1
    if unpadded in atlas:
        return atlas[unpadded]
    members = [v for k, v in atlas.items() if k.startswith(neuron_class)
               and len(k) - len(neuron_class) <= 2 and k[len(neuron_class):].strip("DVLR") == ""]
    if not members:
        return None
    if side in ("L", "R"):
        sided = [v for k, v in atlas.items() if k.startswith(neuron_class) and k.endswith(side)
                 and k[len(neuron_class):].strip("DVLR") == ""]
        members = sided or members
    n = len(members)
    ap = sum(m[0] for m in members) / n
    dv = sum(m[1] for m in members) / n
    lr = sum(m[2] for m in members) / n if side in ("L", "R") else 0.0
    return (ap, dv, lr)
