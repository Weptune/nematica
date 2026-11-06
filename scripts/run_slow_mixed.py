"""Slow units in only some places (pre-registered 6 Nov 2026). Output: docs/figures/slow_mixed.csv"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_ladder as LD  # noqa: E402
import run_week1 as W1  # noqa: E402
import run_echo_matched as EM  # noqa: E402
from nematica import annlab as L  # noqa: E402

OUT = ROOT / "docs" / "figures" / "slow_mixed.csv"
PR = {"share": 0.4, "g": 0.75, "spread": 0.15, "quiet": 0.3, "mod": 0}


def leak_vec(kind, seed):
    if kind == "quiet":     # the same draw param_recs uses for its quiet units
        slow = np.random.default_rng(seed + 900).random(120) < PR["quiet"]
    else:
        slow = np.random.default_rng(seed + 4242).random(120) < 0.3
    return np.where(slow, 0.1, 0.5)


def main():
    worm = {k: float(v) for k, v in next(csv.DictReader((LD.FIG / "ladder_worms.csv").open())).items()}
    rows = []
    rec0 = LD.record
    for seed in (0, 1):
        for kind in ("quiet", "random"):
            L.LEAK = leak_vec(kind, seed)
            LD.KICK_HOLD["frames"] = 6
            LD.record = rec0
            ws = [W1.Worm(r, valid_fn=lambda c: True) for r in LD.param_recs(PR, seed, sigma=0.8)]
            fp = LD.fingerprint(ws)
            EM.TAU["t"] = 1.5
            LD.record = EM.record_ca
            M = EM.per_rec(EM.paired(LD.param_recs(PR, seed, n_ind=30, sigma=0.8)))
            LD.record = rec0
            L.LEAK = 0.5
            LD.KICK_HOLD["frames"] = LD.KICK_FRAMES
            rel = [abs(fp[a] - worm[a]) / abs(worm[a]) for a in LD.FIT_AXES]
            med = np.median(M, axis=0)
            rows.append({"brain": seed, "slow": kind, **{a: round(fp[a], 4) for a in LD.AXES},
                         "rel_err": round(float(np.sqrt(np.mean(np.square(rel)))), 4),
                         "ever": round(float(med[0]), 3), "mean_run": round(float(med[1]), 3), "change": round(float(med[2]), 3)})
            print(rows[-1], flush=True)
            with OUT.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)


if __name__ == "__main__":
    main()
