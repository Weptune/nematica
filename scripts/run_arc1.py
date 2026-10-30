"""Arc 1: is forecasting skill the same thing as fidelity?

Fits the forecaster ladder (nematica/systems/forecasters.py) on training worms, measures
forecasting skill on test worms, then runs each model as a simulator and scores it on the
ruler (pairwise levels, individuality, Level 8).

Usage:
  python scripts/run_arc1.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --split configs/splits/copper2026.yaml [--out results/arc1] [--seeds 2] [--models var1,esn400]

Writes arc1_summary.csv (one row per model), arc1_levels.csv (one row per model and metric),
arc1_l8.csv and arc1.png.

Prediction written before running: models with higher forecasting skill sit closer to the
average worm, so individuality falls and "too typical" verdicts rise with skill.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import LEVELS, build_reference, from_recording, score_system  # noqa: E402
from nematica.bench.discriminability import core_classes, discriminability  # noqa: E402
from nematica.data import load_copper_dir, load_split  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.systems.forecasters import Forecaster, IndividualVAR, LagFeatures, StateSpace, ladder  # noqa: E402


def summarise(name, rows, extra):
    scored = [r for r in rows if r["verdict"] != "not scored"]
    prim = [r for r in scored if r.get("primary")]
    ratio = [r["system_median"] / r["bio_median"] for r in scored if r["bio_median"] > 0]
    spread = [r["self_spread_ratio"] for r in prim if r.get("self_spread_ratio") is not None]
    return {
        "system": name, **extra,
        "inside": sum(r["verdict"] == "inside" for r in scored),
        "too_typical": sum(r["verdict"] == "too typical" for r in scored),
        "outside": sum(r["verdict"] == "outside" for r in scored),
        "scored": len(scored),
        "distance_ratio_median": round(float(np.median(ratio)), 3) if ratio else None,
        "individuality": round(float(np.median(spread)), 3) if spread else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--out", default="results/arc1")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--models", default="")
    ap.add_argument("--perm", type=int, default=60)
    args = ap.parse_args()

    recs = load_copper_dir(Path(args.data))
    split = load_split(args.split)
    classes = tuple(canonical_classes(recs, 0.25))
    by = {r.uid: r for r in recs}
    S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
    train, val, test = S(split["train"]), S(split["val"]), S(split["test"])
    others = train + val
    space = StateSpace.from_train(train)
    print(f"{len(train)} train, {len(val)} val, {len(test)} test worms; state = {space.core.size} core classes + velocity + reversal")

    ref = build_reference(test)
    core = core_classes(test + others, 12)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    level_rows, summary, l8_rows = [], [], []
    rows = score_system("real_other_worms", others, test, ref)
    level_rows += rows
    l8 = discriminability(test, others, core, n_perm=args.perm, seed=0)
    summary.append(summarise("real_other_worms", rows, {"r2_1step": None, "r2_5step": None,
                                                         "l8_auc": l8.get("auc")}))
    l8_rows.append({"system": "real_other_worms", **l8})

    wanted = set(args.models.split(",")) if args.models else None
    models = ladder(space)
    for lags in (1, 3):
        for mode in ("full", "noise_only", "shuffled"):
            models.append(IndividualVAR(Forecaster(f"var{lags}", space, LagFeatures(space.k, lags, False)), mode=mode))
    for m in models:
        if wanted and m.name not in wanted:
            continue
        t0 = time.time()
        m.fit(train, val)
        r1 = m.one_step_r2(test)
        r5 = m.multi_step_r2(test, horizon=5, stride=20)
        t_fit = time.time() - t0
        samples = []
        for seed in range(args.seeds):
            rng = np.random.default_rng(1000 * seed + 7)
            if isinstance(m, IndividualVAR):           # each sample from a different individual
                samples += [m.generate(s, rng, which=seed * len(test) + i) for i, s in enumerate(test)]
            else:
                samples += [m.generate(s, rng) for s in test]
        rows = score_system(m.name, samples, test, ref)
        level_rows += rows
        l8 = discriminability(test, samples, core, n_perm=args.perm, seed=0)
        l8_rows.append({"system": m.name, **l8})
        row = summarise(m.name, rows, {"r2_1step": round(r1, 4), "r2_5step": round(r5, 4),
                                       "l8_auc": l8.get("auc"), **m.info})
        summary.append(row)
        print(f"{m.name:9s} R2 1-step {r1:.3f}  5-step {r5:.3f} | inside {row['inside']}, too typical "
              f"{row['too_typical']}, outside {row['outside']} of {row['scored']} | distance ratio "
              f"{row['distance_ratio_median']} | individuality {row['individuality']} | L8 AUC "
              f"{l8.get('auc')} ({time.time() - t0:.0f} s, fit+forecast {t_fit:.0f} s)", flush=True)

    for name, data in [("arc1_summary.csv", summary), ("arc1_levels.csv", level_rows), ("arc1_l8.csv", l8_rows)]:
        keys = list(dict.fromkeys(k for r in data for k in r))
        with (out / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(data)
    print(f"Wrote {out}/arc1_summary.csv, arc1_levels.csv, arc1_l8.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
