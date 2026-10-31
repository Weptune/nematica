"""Arc 3, what the wiring buys: the per-worm calcium-drive VAR(10) with hysteresis
reversals, refitted with its neuron-to-neuron weights restricted to the connectome, to
shuffled wiring with the same number of inputs per class (3 seeds), or to no coupling.
Design and expectations: README, "Arc 3".

Writes wiring_combined.csv (pairwise levels on the rotating pools) and wiring_forecast.csv
(one-step and 30 s ahead R^2 of each pooled model on the held-out worms).

Usage:
  python scripts/run_wiring.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \\
      --folds configs/splits/copper2026_cv3.yaml [--out results/wiring]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import from_recording  # noqa: E402
from nematica.bench.cv import cv_score, print_table  # noqa: E402
from nematica.data import load_copper_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.forecasters import CalciumStateSpace, Debounced, LagFeatures  # noqa: E402
from nematica.systems.wiring import (MaskedForecaster, WiredVAR, class_wiring, diagonal_wiring,  # noqa: E402
                                     shuffled_wiring)

LAGS = 10
WIRINGS = {
    "full": lambda names: np.ones((len(names), len(names)), dtype=bool),
    "connectome": class_wiring,
    **{f"shuffled{s}": (lambda names, s=s: shuffled_wiring(class_wiring(names), 100 + s)) for s in range(3)},
    "diagonal": lambda names: diagonal_wiring(len(names)),
}


def wired(label, train):
    cs = CalciumStateSpace.from_train(train, gamma=0.5)
    return WiredVAR(MaskedForecaster(f"var{LAGS}", cs, LagFeatures(cs.k, LAGS, False)), fixed_lam=300,
                    wiring=WIRINGS[label], label=label)


def build(train):
    return {"real_other_worms": None, **{f"wired_{k}": Debounced(wired(k, train)) for k in WIRINGS}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="results/wiring")
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()
    recs = load_copper_dir(Path(args.data))
    by = {r.uid: r for r in recs}
    classes = tuple(canonical_classes(recs, 0.25))
    folds = load_folds(args.folds)["folds"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # forecasting on held-out worms (pooled model, which is what a new worm gets)
    rows = []
    for fi, pool_uids in enumerate(folds):
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        val_uids = [rest[len(rest) // 3], rest[2 * len(rest) // 3]]
        S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
        pool, train, val = S(pool_uids), S([u for u in rest if u not in val_uids]), S(val_uids)
        for label in WIRINGS:
            m = wired(label, train).fit(train, val)
            rows.append({"wiring": label, "rotation": fi, **m.connections,
                         "one_step_r2": round(m.pooled.one_step_r2(pool), 4),
                         "r2_30s": round(m.pooled.multi_step_r2(pool, horizon=50, stride=25, context=50), 4)})
            print(rows[-1], flush=True)
    with (out / "wiring_forecast.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    combined, flat = cv_score(recs, classes, folds, build, args.seeds)
    for name, data in [("wiring_combined.csv", combined), ("wiring_per_fold.csv", flat)]:
        keys = list(dict.fromkeys(k for r in data for k in r))
        with (out / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(data)
    print()
    print_table(combined)
    print("\nForecasting on held-out worms (mean over rotations):")
    for label in WIRINGS:
        v = [r for r in rows if r["wiring"] == label]
        print(f"  {label:11s} one-step R2 {np.mean([r['one_step_r2'] for r in v]):.4f}   "
              f"30 s R2 {np.mean([r['r2_30s'] for r in v]):.4f}   inputs/class {v[0]['inputs_per_class_mean']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
