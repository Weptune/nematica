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


def bin_spikes(times_by_unit, duration_s, bin_s=None):
    """Spike times (s) per unit -> counts per bin (time x units). Amendment 4 (F3): every spiking preparation
    is binned at instrument.SPIKE_BIN_S (20 ms)."""
    from .instrument import SPIKE_BIN_S
    bin_s = bin_s or SPIKE_BIN_S
    nb = int(duration_s / bin_s)
    X = np.zeros((nb, len(times_by_unit)), np.float32)
    for i, tt in enumerate(times_by_unit):
        b = (np.asarray(tt) / bin_s).astype(int)
        b = b[(b >= 0) & (b < nb)]
        np.add.at(X[:, i], b, 1)
    return X


def culture_session(path, bin_s=None, min_spikes=200):
    """Rat cortical culture on an HD-MEA (DANDI 002020): detected spikes per electrode (the registered unit for
    R9 is the electrode, amendment 4) -> counts per 20 ms bin."""
    import h5py
    with h5py.File(path, "r") as f:
        g = f["processing/ecephys/detected_spikes"]
        ch = g["source_channel"][:]
        t = g["time_from_first_spike_seconds"][:]
        dur = float(f["processing/ecephys/conversion_provenance/duration_s"][0])
    from .instrument import SPIKE_BIN_S
    bin_s = bin_s or SPIKE_BIN_S
    chans, counts = np.unique(ch, return_counts=True)
    keep = chans[counts >= min_spikes]
    X = bin_spikes([t[ch == c] for c in keep], dur, bin_s)
    return {"activity": X, "dt": bin_s, "recording": "spikes", "duration_s": dur, "units_total": len(chans)}
