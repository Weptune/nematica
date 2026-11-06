"""Slow units in the closest network (pre-registered 6 Nov 2026). Output: docs/figures/slow_units.csv"""
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
from nematica import annlab as L  # noqa: E402

OUT = ROOT / "docs" / "figures" / "slow_units.csv"


def main():
    worm = {k: float(v) for k, v in next(csv.DictReader((LD.FIG / "ladder_worms.csv").open())).items()}
    pr = {"share": 0.4, "g": 0.75, "spread": 0.15, "quiet": 0.3, "mod": 0}
    rows = []
    for seed in (0, 1):
        for leak in (0.5, 0.25, 0.1):
            L.LEAK = leak
            LD.KICK_HOLD["frames"] = 6
            ws = [W1.Worm(r, valid_fn=lambda c: True) for r in LD.param_recs(pr, seed, sigma=0.8)]
            fp = LD.fingerprint(ws)
            L.LEAK = 0.5
            LD.KICK_HOLD["frames"] = LD.KICK_FRAMES
            rel = [abs(fp[a] - worm[a]) / abs(worm[a]) for a in LD.FIT_AXES]
            rows.append({"brain": seed, "leak": leak, **{a: round(fp[a], 4) for a in LD.AXES},
                         "rel_err": round(float(np.sqrt(np.mean(np.square(rel)))), 4), "within25": int(sum(r <= 0.25 for r in rel))})
            print(rows[-1], flush=True)
            with OUT.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)


if __name__ == "__main__":
    main()
