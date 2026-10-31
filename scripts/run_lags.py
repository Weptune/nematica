"""Memory length of the calcium-drive model (VAR lag order 3, 6, 10) on the rotating pools.

Chosen for testing because, in-sample on one rotation's training worms, 3 lags make 30 s
windows smoother than the worms they imitate (lag-1 autocorrelation 0.747 vs 0.707; too
little power at 1 to 5 s periods), while 6 lags match (0.709) and 10 slightly overshoot.
Selected without the reference pools; scored here on them.

(Script derived from run_reversals.py.)

The two behaviour metrics were added after the closed-loop work showed that thresholding a
noisy reversal channel can double the onset rate unnoticed. This rescoring checks which of
the earlier models (raw and calcium per-worm VAR, switching VAR) actually make reversals at
the right rate and of the right length, and whether decoding the calcium model's reversal
channel with hysteresis (thresholds fitted on training worms) repairs it.

Usage:
  python scripts/run_lags.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
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
    out = {"real_other_worms": None}
    for lags in (3, 6, 10):
        cs = CalciumStateSpace.from_train(train, gamma=0.5)
        out[f"calcium_var{lags}_hyst"] = Debounced(IndividualVAR(Forecaster(f"var{lags}", cs,
                                                                           LagFeatures(cs.k, lags, False)), fixed_lam=300))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="results/lags")
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()
    recs = load_copper_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    combined, flat = cv_score(recs, classes, load_folds(args.folds)["folds"], build, args.seeds)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, data in [("lags_combined.csv", combined), ("lags_per_fold.csv", flat)]:
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
