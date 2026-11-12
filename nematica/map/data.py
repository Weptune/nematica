"""Loaders for the map's real preparations (docs/MAP.md). Each returns a list of individuals, each a dict
with `activity` (time, units), `dt` (seconds per sample), `recording` ('calcium' | 'spikes' | 'field'),
and identifiers. Data is downloaded or streamed by script into data/external/map (gitignored) and never
redistributed. Rule: a loader is checked on shapes only before the measurement code is frozen.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/external/map"
DANDI = "https://api.dandiarchive.org/api"


def dandi_assets(dandiset, version="draft"):
    out, url = [], f"{DANDI}/dandisets/{dandiset}/versions/{version}/assets/?page_size=400"
    while url:
        d = json.loads(subprocess.run(["curl", "-sSfL", url], capture_output=True, check=True).stdout)
        out += d["results"]
        url = d.get("next")
    return out


def dandi_get(asset, dest):
    dest = Path(dest)
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-sSfL", "-o", str(dest), f"{DANDI}/assets/{asset['asset_id']}/download/"], check=True)
    return dest


def culture_session(path, bin_s=0.05, min_spikes=200):
    """Rat cortical culture on an HD-MEA (DANDI 002020): detected spikes per electrode -> counts per bin."""
    import h5py
    with h5py.File(path, "r") as f:
        g = f["processing/ecephys/detected_spikes"]
        ch = g["source_channel"][:]
        t = g["time_from_first_spike_seconds"][:]
        dur = float(f["processing/ecephys/conversion_provenance/duration_s"][0])
    chans, counts = np.unique(ch, return_counts=True)
    keep = chans[counts >= min_spikes]
    nb = int(dur / bin_s)
    X = np.zeros((nb, len(keep)), np.float32)
    col = {c: i for i, c in enumerate(keep)}
    for c, tt in zip(ch, t):
        i = col.get(c)
        b = int(tt / bin_s)
        if i is not None and b < nb:
            X[b, i] += 1
    return {"activity": X, "dt": bin_s, "recording": "spikes", "duration_s": dur, "units_total": len(chans)}
