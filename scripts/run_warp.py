"""Does a Gaussian-copula warp fix the activity-distribution level?

Same rotating pools and refitting as run_cv.py. Compares each model with and without the
warp at identical settings, so the only difference is the marginal transform.

Usage:
  python scripts/run_warp.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --folds configs/splits/copper2026_cv3.yaml [--out results/warp]
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
from nematica.data import load_copper_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.forecasters import (Forecaster, IndividualVAR, LagFeatures,  # noqa: E402
                                          StateSpace, WarpedStateSpace)


def systems(train):
    out = {}
    for warp, Space in (("", StateSpace), ("warp_", WarpedStateSpace)):
        sp = Space.from_train(train)
        out[f"{warp}var3"] = Forecaster("var3", sp, LagFeatures(sp.k, 3, False))
        for lam in (300, 3000):
            out[f"{warp}indiv_var3_lam{lam}"] = IndividualVAR(Forecaster("var3", sp, LagFeatures(sp.k, 3, False)),
                                                               fixed_lam=lam)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="results/warp")
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()
    recs = load_copper_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    by = {r.uid: r for r in recs}
    folds = load_folds(args.folds)["folds"]
    per = {}
    for fi, pool_uids in enumerate(folds):
        t0 = time.time()
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        val_uids = [rest[len(rest) // 3], rest[2 * len(rest) // 3]]
        train_uids = [u for u in rest if u not in val_uids]
        S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
        pool, train, val = S(pool_uids), S(train_uids), S(val_uids)
        ref = build_reference(pool)
        for name, m in systems(train).items():
            m.fit(train, val)
            samples = []
            for seed in range(args.seeds):
                rng = np.random.default_rng(1000 * seed + 7 + fi)
                if isinstance(m, IndividualVAR):
                    samples += [m.generate(s, rng, which=seed * len(pool) + i) for i, s in enumerate(pool)]
                else:
                    samples += [m.generate(s, rng) for s in pool]
            per.setdefault(name, []).append(score_system(name, samples, pool, ref, return_boot=True))
        print(f"fold {fi} done ({time.time() - t0:.0f} s)", flush=True)
    combined = []
    for name, rows in per.items():
        combined += combine_folds(rows)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in combined for k in r))
    with (out / "warp_combined.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(combined)
    metrics = list(dict.fromkeys(r["metric"] for r in combined))
    short = {"inside": "in", "outside": "OUT", "too typical": "typ", "not scored": "-"}
    print("\nsystem".ljust(26) + "".join(m.split(".")[1][:10].rjust(12) for m in metrics) + "  inside")
    for name in per:
        line, n_in = name.ljust(25), 0
        for m in metrics:
            r = next(x for x in combined if x["system"] == name and x["metric"] == m)
            n_in += r["verdict"] == "inside"
            line += f"{short[r['verdict']]} {r['distance_ratio']:.2f}".rjust(12)
        print(line + f"  {n_in}/8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
