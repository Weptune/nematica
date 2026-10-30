"""Calcium-aware dynamics: model the deconvolved drive with per-worm VAR(3), rebuild calcium.

Compares, on the rotating reference pools, the per-worm VAR(3) at lambda = 300 on the raw
traces against the same model on the drive, for three a-priori decay factors gamma
(0.5, 0.7, 0.85: tau = 0.9, 1.7, 3.7 s at 0.6 s frames).

Usage:
  python scripts/run_calcium.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
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
from nematica.systems.forecasters import (CalciumStateSpace, Forecaster, IndividualVAR,  # noqa: E402
                                          LagFeatures, StateSpace)


def build(train):
    out = {}
    sp = StateSpace.from_train(train)
    out["indiv_var3_lam300"] = IndividualVAR(Forecaster("var3", sp, LagFeatures(sp.k, 3, False)), fixed_lam=300)
    for g in (0.5, 0.7, 0.85):
        cs = CalciumStateSpace.from_train(train, gamma=g)
        out[f"calcium_g{g}_indiv_lam300"] = IndividualVAR(Forecaster("var3", cs, LagFeatures(cs.k, 3, False)),
                                                           fixed_lam=300)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="results/calcium")
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()
    recs = load_copper_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    combined, flat = cv_score(recs, classes, load_folds(args.folds)["folds"], build, args.seeds)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, data in [("calcium_combined.csv", combined), ("calcium_per_fold.csv", flat)]:
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
