"""Level 8, reported fairly: separate model error from individuality between worm groups.

Design (fixed before the first run, Oct 31): for each of the three rotating pools
(configs/splits/copper2026_cv3.yaml), with the same classifier and settings as run_l8.py:

  held_out   model samples on the pool worms' templates (sample j from training worm j's
             model) vs the real pool worms                      -> the usual Level 8
  in_sample  model samples from each training worm's own model on its own template vs those
             same training worms                                -> model error alone
  control    real training + validation worms vs the real pool worms
                                                                -> individuality alone
Expectations: a model whose only error were individuality would score held_out close to
control and in_sample near the real-vs-real level; a genuine giveaway keeps in_sample high
and held_out above control. AUCs are averaged over the rotations, with the per-rotation
values kept.

Usage:
  python scripts/run_l8_fair.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \\
      --folds configs/splits/copper2026_cv3.yaml [--models hyst,heavy] [--out results/l8_fair]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import from_recording  # noqa: E402
from nematica.bench.discriminability import core_classes, discriminability  # noqa: E402
from nematica.data import load_copper_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.forecasters import CalciumStateSpace, Debounced, Forecaster, IndividualVAR, LagFeatures  # noqa: E402


def build(name, train):
    cs = CalciumStateSpace.from_train(train, gamma=0.5)
    if name.startswith("hyst"):                       # hyst, hyst6, hyst10: lag order
        lags = int(name[4:] or 3)
        return Debounced(IndividualVAR(Forecaster(f"var{lags}", cs, LagFeatures(cs.k, lags, False)), fixed_lam=300))
    if name == "heavy":
        return Debounced(IndividualVAR(Forecaster("var3", cs, LagFeatures(cs.k, 3, False)), fixed_lam=300,
                                       innovations="student"))
    raise ValueError(name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--models", default="hyst")
    ap.add_argument("--perm", type=int, default=60)
    ap.add_argument("--out", default="results/l8_fair")
    args = ap.parse_args()
    recs = load_copper_dir(Path(args.data))
    by = {r.uid: r for r in recs}
    classes = tuple(canonical_classes(recs, 0.25))
    folds = load_folds(args.folds)["folds"]
    allS = [from_recording(r, classes) for r in recs]
    core = core_classes(allS, 12)
    rows = []
    for fi, pool_uids in enumerate(folds):
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        val_uids = [rest[len(rest) // 3], rest[2 * len(rest) // 3]]
        train_uids = [u for u in rest if u not in val_uids]
        S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
        pool, train, val = S(pool_uids), S(train_uids), S(val_uids)
        c = discriminability(pool, train + val, core, n_perm=args.perm, seed=fi)
        rows.append({"model": "real", "rotation": fi, "comparison": "control", "auc": c["auc"], "p": c["p"]})
        print(f"rotation {fi} control AUC {c['auc']:.3f}", flush=True)
        for name in args.models.split(","):
            m = build(name, train).fit(train, val)
            held = [m.generate(s, np.random.default_rng(100 * fi + i), which=i) for i, s in enumerate(pool)]
            own = [m.generate(s, np.random.default_rng(500 * fi + i), which=i) for i, s in enumerate(train)]
            for comp, real, sims in (("held_out", pool, held), ("in_sample", train, own)):
                r = discriminability(real, sims, core, n_perm=args.perm, seed=fi)
                rows.append({"model": name, "rotation": fi, "comparison": comp, "auc": r["auc"], "p": r["p"]})
                print(f"rotation {fi} {name} {comp} AUC {r['auc']:.3f}", flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "l8_fair.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\nmean AUC over rotations:")
    for model in dict.fromkeys(r["model"] for r in rows):
        for comp in dict.fromkeys(r["comparison"] for r in rows if r["model"] == model):
            v = [r["auc"] for r in rows if r["model"] == model and r["comparison"] == comp]
            print(f"  {model:6s} {comp:10s} {np.mean(v):.3f}  ({', '.join(f'{x:.3f}' for x in v)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
