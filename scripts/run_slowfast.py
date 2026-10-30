"""Multi-timescale memory and a per-worm slow brain state, on the rotating reference pools.

Usage:
  python scripts/run_slowfast.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --folds configs/splits/copper2026_cv3.yaml [--out results/slowfast]
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
                                          LagFeatures, MultiScaleFeatures, SlowFastVAR)


def build(train):
    cs1 = CalciumStateSpace.from_train(train, gamma=0.5)
    cs2 = CalciumStateSpace.from_train(train, gamma=0.5)
    return {
        "calcium_lags3": IndividualVAR(Forecaster("var3", cs1, LagFeatures(cs1.k, 3, False)), fixed_lam=300),
        "calcium_multiscale": IndividualVAR(Forecaster("ms", cs2, MultiScaleFeatures(cs2.k)), fixed_lam=300),
        "slowfast_lags3": SlowFastVAR(gamma=0.5, lam=300, feats="lags3"),
        "slowfast_multiscale": SlowFastVAR(gamma=0.5, lam=300, feats="multiscale"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="results/slowfast")
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()
    recs = load_copper_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    combined, flat = cv_score(recs, classes, load_folds(args.folds)["folds"], build, args.seeds)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, data in [("slowfast_combined.csv", combined), ("slowfast_per_fold.csv", flat)]:
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
