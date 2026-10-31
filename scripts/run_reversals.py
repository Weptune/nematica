"""Reversal statistics (B.rev_rate, B.rev_duration) for the main models on the rotating pools.

The two behaviour metrics were added after the closed-loop work showed that thresholding a
noisy reversal channel can double the onset rate unnoticed. This rescoring checks which of
the earlier models (raw and calcium per-worm VAR, switching VAR) actually make reversals at
the right rate and of the right length, and whether decoding the calcium model's reversal
channel with hysteresis (thresholds fitted on training worms) repairs it.

Usage:
  python scripts/run_reversals.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --folds configs/splits/copper2026_cv3.yaml [--out results/calcium]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.cv import cv_score, print_table  # noqa: E402
from nematica.data import load_copper_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.forecasters import (CalciumStateSpace, Debounced, Forecaster,  # noqa: E402
                                          IndividualVAR, LagFeatures, StateSpace)
from nematica.systems.switching import SwitchingVAR  # noqa: E402


def build(train):
    sp = StateSpace.from_train(train)
    cs = CalciumStateSpace.from_train(train, gamma=0.5)
    cs2 = CalciumStateSpace.from_train(train, gamma=0.5)     # own space: Debounced sets its thresholds
    return {
        "real_other_worms": None,
        "indiv_var3_lam300": IndividualVAR(Forecaster("var3", sp, LagFeatures(sp.k, 3, False)), fixed_lam=300),
        "calcium_g0.5_indiv_lam300": IndividualVAR(Forecaster("var3", cs, LagFeatures(cs.k, 3, False)),
                                                   fixed_lam=300),
        "switch_var3_indiv_lam300": SwitchingVAR(sp, lam=300),
        "calcium_g0.5_indiv_lam300_hyst": Debounced(IndividualVAR(Forecaster("var3", cs2, LagFeatures(cs2.k, 3, False)),
                                                                  fixed_lam=300)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="results/reversals")
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()
    recs = load_copper_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    combined, flat = cv_score(recs, classes, load_folds(args.folds)["folds"], build, args.seeds)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, data in [("reversals_combined.csv", combined), ("reversals_per_fold.csv", flat)]:
        keys = list(dict.fromkeys(k for r in data for k in r))
        with (out / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(data)
    print()
    print_table(combined)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
