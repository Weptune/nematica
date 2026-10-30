"""Arc 1, single-knob version: how much should each worm's dynamics be shrunk toward the
shared model? Sweeps the shrinkage lam of IndividualVAR (VAR(3)) and records, for every
value, forecasting skill (within-worm: fit on each training worm's first half, predict its
second half) and fidelity (rotating reference pools, combined over folds).

Prediction written before running: the lam that forecasts best is larger (more shrinkage,
more average) than the lam whose samples look most like real worms.

Usage:
  python scripts/run_shrinkage.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --folds configs/splits/copper2026_cv3.yaml [--out results/shrinkage]
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
from nematica.systems.forecasters import Forecaster, IndividualVAR, LagFeatures, StateSpace  # noqa: E402

LAMS = (30, 100, 300, 1000, 3000, 10000, 100000)
KEY = ("L2.correlation", "L4.leadlag", "L5.encoding", "L5.reversal")
ALL = ("L1.distribution", "L1.timescale", "L2.correlation", "L2.dimension", "L4.leadlag", "L4.dwell",
       "L5.encoding", "L5.reversal")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="results/shrinkage")
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()

    recs = load_copper_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    by = {r.uid: r for r in recs}
    folds = load_folds(args.folds)["folds"]
    per_lam = {lam: [] for lam in LAMS}
    r2 = {lam: [] for lam in LAMS}
    for fi, pool_uids in enumerate(folds):
        t0 = time.time()
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        val_uids = [rest[len(rest) // 3], rest[2 * len(rest) // 3]]
        train_uids = [u for u in rest if u not in val_uids]
        S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
        pool, train, val = S(pool_uids), S(train_uids), S(val_uids)
        ref = build_reference(pool)
        space = StateSpace.from_train(train)
        for lam in LAMS:
            m = IndividualVAR(Forecaster("var3", space, LagFeatures(space.k, 3, False)), fixed_lam=lam)
            m.fit(train, val)
            r2[lam].append(m.info["within_worm_r2_individual"])
            samples = []
            for seed in range(args.seeds):
                rng = np.random.default_rng(1000 * seed + 7 + fi)
                samples += [m.generate(s, rng, which=seed * len(pool) + i) for i, s in enumerate(pool)]
            per_lam[lam].append(score_system(f"lam{lam}", samples, pool, ref, return_boot=True))
        print(f"fold {fi} done ({time.time() - t0:.0f} s)", flush=True)

    rows = []
    for lam in LAMS:
        comb = {r["metric"]: r for r in combine_folds(per_lam[lam])}
        row = {"lam": lam, "within_worm_r2": round(float(np.mean(r2[lam])), 4)}
        for m in ALL:
            row[f"{m}_ratio"] = comb[m]["distance_ratio"]
            row[f"{m}_verdict"] = comb[m]["verdict"]
        prim = [r["self_spread_ratio"] for r in comb.values() if r.get("primary") and r.get("self_spread_ratio")]
        row["individuality"] = round(float(np.median(prim)), 3)
        row["mean_abs_log_ratio_key"] = round(float(np.mean([abs(np.log(row[f"{m}_ratio"])) for m in KEY])), 4)
        rows.append(row)
    # nested check: choose lam on two folds (realism on KEY levels), score it on the held-out fold
    nested = []
    for held in range(len(folds)):
        def realism(lam, use):
            comb = {r["metric"]: r for r in combine_folds([per_lam[lam][f] for f in use])}
            return float(np.mean([abs(np.log(comb[m]["distance_ratio"])) for m in KEY]))
        use = [f for f in range(len(folds)) if f != held]
        lam_sel = min(LAMS, key=lambda l: realism(l, use))
        held_rows = {r["metric"]: r for r in per_lam[lam_sel][held]}
        nested.append({"held_out_fold": held, "lam_chosen_on_other_folds": lam_sel,
                       **{f"{m}_verdict": held_rows[m]["verdict"] for m in ALL},
                       **{f"{m}_ratio": round(held_rows[m]["system_median"] / held_rows[m]["bio_median"], 3)
                          for m in ALL}})
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "shrinkage_nested.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(nested[0]))
        w.writeheader()
        w.writerows(nested)
    print("\nNested: lam chosen on two folds, verdicts on the held-out fold")
    for n in nested:
        print(f"  fold {n['held_out_fold']}: lam {n['lam_chosen_on_other_folds']} -> " + ", ".join(
            f"{m.split('.')[1]} {n[f'{m}_verdict']} {n[f'{m}_ratio']:.2f}" for m in ALL))
    with (out / "shrinkage.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\nlam      R2(within)  corr  leadlag  encoding  reversal  individuality  |log ratio|")
    for r in rows:
        print(f"{r['lam']:<8} {r['within_worm_r2']:.4f}     " + "  ".join(
            f"{r[f'{m}_ratio']:.2f}{'*' if r[f'{m}_verdict'] != 'inside' else ' '}" for m in KEY)
            + f"     {r['individuality']:.2f}          {r['mean_abs_log_ratio_key']:.3f}")
    best_f = max(rows, key=lambda r: r["within_worm_r2"])["lam"]
    best_r = min(rows, key=lambda r: r["mean_abs_log_ratio_key"])["lam"]
    print(f"\nbest for forecasting: lam={best_f}; most realistic on these levels: lam={best_r} "
          "(* = not inside, combined over folds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
