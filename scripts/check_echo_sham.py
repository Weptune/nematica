"""Exploratory check (7 Nov 2026, after the transformer echo test): does the echo measure respond to the
poke at all? The worm echo measure (run_echo_sparse.measures, threshold 3) is applied at sham onsets:
each real stimulation keeps its target but is moved to a random frame whose 5 s before and 15 s after
are at least 30 s from any real stimulation. Worms (113 atlas worms) and the base lab brain (40
individuals, as run_echo_sparse.py).

Usage:  python scripts/check_echo_sham.py
Output: docs/figures/echo_sham.csv
"""
from __future__ import annotations

import csv
import dataclasses
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica.bench.causal import window  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.systems.causal_models import spontaneous_mask  # noqa: E402
from run_echo_sparse import measures  # noqa: E402
import run_ladder as LD  # noqa: E402


def sham(recs, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for r in recs:
        npre, npost = window(r.dt)
        sp = spontaneous_mask(r)
        ok = [f for f in range(npre, r.n_frames - npost) if sp[f - npre:f + npost].all()]
        if ok:
            out.append(dataclasses.replace(r, stims=[(k, int(rng.choice(ok))) for k, _ in r.stims]))
    return out


def main():
    rows = []
    worms = load_pumpprobe_dir(str(ROOT / "data" / "raw" / "randi2023_wt_npz"))
    lab = LD.variant_recs("", 0, n_ind=40)
    for name, recs in (("worms", worms), ("lab base", lab)):
        for kind, rr in (("real", recs), ("sham", sham(recs))):
            m = measures(rr)
            rows.append({"system": name, "onsets": kind, "sparseness": round(m["ever_respond"], 4),
                         "persistence": round(m["mean_run"], 3), "median_run": m["median_run"], "events": m["pokes"]})
            print(rows[-1], flush=True)
    out = ROOT / "docs" / "figures" / "echo_sham.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
