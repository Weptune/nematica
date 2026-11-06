"""Slow units in the closest network, re-run after review 5 (exploratory correction): run_slow_units.py
set the leak before building the brain, and make_brain scales the hidden drives by the leak, so at
leak 0.1 the drives were about four times stronger. Here the brain is built with the ordinary leak
(0.5) and the slow leak applies only while recording, as in run_slow_mixed.py. Same measures: the six
ladder axes, and the matched-readout echo (decay 1.5 s, paired units, 30 individuals).
Output: docs/figures/slow_units_fixed.csv"""
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
import run_slow_mixed as SM  # noqa: E402

OUT = ROOT / "docs" / "figures" / "slow_units_fixed.csv"


def main():
    worm = {k: float(v) for k, v in next(csv.DictReader((LD.FIG / "ladder_worms.csv").open())).items()}
    rows, rec0 = [], LD.record
    for seed in (0, 1):
        for leak in (0.5, 0.25, 0.1):
            LD.KICK_HOLD["frames"] = 6
            LD.record = SM.with_leak(rec0, leak)
            ws = [W1.Worm(r, valid_fn=lambda c: True) for r in LD.param_recs(SM.PR, seed, sigma=0.8)]
            fp = LD.fingerprint(ws)
            EM.TAU["t"] = 1.5
            LD.record = SM.with_leak(EM.record_ca, leak)
            M = EM.per_rec(EM.paired(LD.param_recs(SM.PR, seed, n_ind=30, sigma=0.8)))
            LD.record = rec0
            LD.KICK_HOLD["frames"] = LD.KICK_FRAMES
            rel = [abs(fp[a] - worm[a]) / abs(worm[a]) for a in LD.FIT_AXES]
            med = np.median(M, axis=0)
            rows.append({"brain": seed, "leak": leak, **{a: round(fp[a], 4) for a in LD.AXES},
                         "rel_err": round(float(np.sqrt(np.mean(np.square(rel)))), 4),
                         "ever": round(float(med[0]), 3), "mean_run": round(float(med[1]), 3), "change": round(float(med[2]), 3)})
            print(rows[-1], flush=True)
            with OUT.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)


if __name__ == "__main__":
    main()
