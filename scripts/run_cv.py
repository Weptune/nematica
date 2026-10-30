"""Robustness: score systems against rotating reference pools instead of one frozen pool.

For each frozen fold (configs/splits/copper2026_cv3.yaml), that fold's worms are the
reference pool; every system is refitted on the other worms (2 of them held out for
ridge selection) and scored against the pool. Evidence is combined across folds with
reference.combine_folds. The frozen test split remains the headline evaluation; this is
the check that verdicts do not hinge on which worms happened to be in it.

Usage:
  python scripts/run_cv.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --folds configs/splits/copper2026_cv3.yaml [--out results/cv] [--seeds 2]
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import build_reference, combine_folds, from_recording, score_system  # noqa: E402
from nematica.bench.calib import gaussian_noise  # noqa: E402
from nematica.data import load_copper_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.data.splits import _date_key, load_folds  # noqa: E402
from nematica.systems.forecasters import (ESNFeatures, Forecaster, IndividualVAR,  # noqa: E402
                                          LagFeatures, StateSpace)


def build_systems(space):
    k = space.k
    sys_ = {
        "diag_ar4": Forecaster("diag_ar4", space, LagFeatures(k, 4, True), diagonal=True),
        "var1": Forecaster("var1", space, LagFeatures(k, 1, False)),
        "var3": Forecaster("var3", space, LagFeatures(k, 3, False)),
        "esn400": Forecaster("esn400", space, ESNFeatures(k, 400, seed=0)),
    }
    for mode in ("full", "noise_only", "shuffled"):
        m = IndividualVAR(Forecaster("var3", space, LagFeatures(k, 3, False)), mode=mode)
        sys_[m.name] = m
    return sys_


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="results/cv")
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()

    recs = load_copper_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    by = {r.uid: r for r in recs}
    folds = load_folds(args.folds)["folds"]
    per_system: dict[str, list] = {}
    fold_rows_all = []
    for fi, pool_uids in enumerate(folds):
        t0 = time.time()
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        # 2 validation worms from different dates, the rest train
        val_uids = [rest[len(rest) // 3], rest[2 * len(rest) // 3]]
        train_uids = [u for u in rest if u not in val_uids]
        S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
        pool, train, val = S(pool_uids), S(train_uids), S(val_uids)
        ref = build_reference(pool)
        space = StateSpace.from_train(train)

        def add(name, samples):
            rows = score_system(name, samples, pool, ref, return_boot=True)
            for r in rows:
                r["fold"] = fi
            per_system.setdefault(name, []).append(rows)
            fold_rows_all.extend({k: v for k, v in r.items() if k != "_boot"} for r in rows)

        add("real_other_worms", train + val)
        rng = np.random.default_rng(7)
        add("gaussian_noise", [gaussian_noise(s, rng) for s in pool])
        for name, m in build_systems(space).items():
            m.fit(train, val)
            samples = []
            for seed in range(args.seeds):
                rng = np.random.default_rng(1000 * seed + 7 + fi)
                if isinstance(m, IndividualVAR):
                    samples += [m.generate(s, rng, which=seed * len(pool) + i) for i, s in enumerate(pool)]
                else:
                    samples += [m.generate(s, rng) for s in pool]
            add(name, samples)
        print(f"fold {fi}: pool {len(pool)} worms, train {len(train)}, val {len(val)} ({time.time() - t0:.0f} s)",
              flush=True)

    combined = []
    for name, folds_rows in per_system.items():
        combined += combine_folds(folds_rows)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for fname, data in [("cv_combined.csv", combined), ("cv_per_fold.csv", fold_rows_all)]:
        keys = list(dict.fromkeys(k for r in data for k in r))
        with (out / fname).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(data)

    metrics = list(dict.fromkeys(r["metric"] for r in combined))
    short = {"inside": "in", "outside": "OUT", "too typical": "typ", "not scored": "-"}
    print("\nCombined over folds (verdict, mean distance ratio; per-fold verdicts in cv_combined.csv)")
    print("system".ljust(18) + "".join(m.split(".")[1][:10].rjust(12) for m in metrics) + "  indiv")
    for name in per_system:
        line = name.ljust(18)
        ind = []
        for m in metrics:
            r = next(x for x in combined if x["system"] == name and x["metric"] == m)
            line += (f"{short[r['verdict']]} {r['distance_ratio']:.2f}" if r["verdict"] != "not scored" else "-").rjust(12)
            if r.get("primary") and r.get("self_spread_ratio") is not None:
                ind.append(r["self_spread_ratio"])
        print(line + (f"  {np.median(ind):.2f}" if ind else ""))
    print(f"\nWrote {out}/cv_combined.csv and cv_per_fold.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
