"""The sparse, sustained echo: worms against artificial networks, one measure (pre-registered 6 Nov
2026; README section of the same name).

Usage: python scripts/run_echo_sparse.py
Output: docs/figures/echo_sparse.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica.bench.perturbational import event_matrices  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
import run_ladder as LD  # noqa: E402

OUT = ROOT / "docs" / "figures" / "echo_sparse.csv"


def measures(recs):
    ever, runs, change = [], [], []
    for r in recs:
        for e in event_matrices(r, keep=True):
            B = np.abs(np.nan_to_num(e["R"])) > 3
            ever.append(B.any(axis=1).mean())
            change.append(np.mean(np.any(B[:, 1:] != B[:, :-1], axis=0)))
            for row in B:
                n = 0
                for v in row:
                    if v:
                        n += 1
                    elif n:
                        runs.append(n); n = 0
                if n:
                    runs.append(n)
    return {"ever_respond": float(np.median(ever)), "median_run": float(np.median(runs)) if runs else 0.0,
            "mean_run": float(np.mean(runs)) if runs else 0.0, "change_share": float(np.median(change)), "pokes": len(ever)}


def main():
    rows = []
    worms = load_pumpprobe_dir(str(ROOT / "data" / "raw" / "randi2023_wt_npz"))
    rows.append({"system": "worms", **measures(worms)})
    print(rows[-1], flush=True)
    for code in ["base", "D", "G", "Q", "DG", "DGQ"]:
        recs = LD.variant_recs("" if code == "base" else code, 0, n_ind=40)
        rows.append({"system": code, **measures(recs)})
        print(rows[-1], flush=True)
    LD.KICK_HOLD["frames"] = 6
    recs = LD.param_recs({"share": 0.4, "g": 0.75, "spread": 0.15, "quiet": 0.3, "mod": 0}, 0, n_ind=40, sigma=0.8)
    LD.KICK_HOLD["frames"] = LD.KICK_FRAMES
    rows.append({"system": "round9_best", **measures(recs)})
    print(rows[-1], flush=True)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
