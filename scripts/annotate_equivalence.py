"""Apply the poke-level equivalence check (nematica.bench.scorecard) to cached results of
scripts/run_same_worms.py: per pool, the tolerance from a known-wrong copy built from the
same held-out worms, then "agrees" / "not shown" for every cached copy.

Usage:
  python scripts/annotate_equivalence.py --folds configs/splits/pumpprobe_cv3.yaml --cache results/fixed_cv3
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.scorecard import POKE_LEVELS, TOL_CONTROL_V2, equivalence, fold_parts, poke_tolerances, set_norm  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw/randi2023_wt_npz")
    ap.add_argument("--folds", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--norm", default="fluct")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    set_norm(args.norm)
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    folds = load_folds(args.folds)["folds"]
    out_rows = []
    for fi in range(len(folds)):
        files = sorted(Path(args.cache).glob(f"{args.norm}_f{fi}_*.csv"))
        if not files:
            continue
        _, _, pool = fold_parts(recs, folds, fi)
        tol = poke_tolerances(pool)
        tol2 = poke_tolerances(pool, controls=TOL_CONTROL_V2)
        for level, t in tol.items():
            print(f"fold {fi} {level}: control {t['control']} shift {t['control_shift']}, tolerance {t['tolerance']}")
        for f in files:
            for r in csv.DictReader(f.open(encoding="utf-8")):
                if r["metric"] in POKE_LEVELS:
                    t = tol[r["metric"]]["tolerance"]
                    t2 = tol2.get(r["metric"], {}).get("tolerance")
                    out_rows.append({"fold": fi, "system": r["system"], "metric": r["metric"], "verdict": r["verdict"],
                                     "shift_lo": r["shift_lo"], "shift_hi": r["shift_hi"], "tolerance": t,
                                     "equivalence": equivalence(r, t),
                                     "tolerance_v2": t2, "equivalence_v2": equivalence(r, t2) if t2 is not None else ""})
    out = Path(args.out or Path(args.cache) / "equivalence.csv")
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    for r in out_rows:
        print(f"fold {r['fold']} {r['system']:34s} {r['metric']:13s} {r['verdict']:12s} {r['equivalence']}  "
              f"[{r['shift_lo']}, {r['shift_hi']}] vs +/-{r['tolerance']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
