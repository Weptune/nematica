"""The full ruler on ingredient-ladder variants (README "The ingredient ladder"): checks that the
cheap watching-share axis agrees with the expensive one. Recordings are exactly those of
scripts/run_ladder.py; folds and copies as in the artificial lab's ruler runs (no true-K
computation, which the check does not need).

Usage:  python scripts/run_ladder_ruler.py --variant SH --seed 0 [--folds 0,1,2]
Output: docs/figures/ladder_ruler.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_ann_ruler as R  # noqa: E402
import run_ladder as LD  # noqa: E402
from run_worm_stitch import StitchedVAR  # noqa: E402
from nematica.bench.scorecard import FoldRuler, fold_parts, set_norm  # noqa: E402

OUT = ROOT / "docs" / "figures" / "ladder_ruler.csv"


def make(name):
    return StitchedVAR(True, True) if name == "stitch3_hp" else R.make_model(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--folds", default="0,1,2")
    ap.add_argument("--copies", default="var3_spontaneous,stitch3_hp,hybrid_kernels")
    a = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    code = "" if a.variant == "base" else a.variant
    recs = {r.uid: r for r in LD.variant_recs(code, a.seed)}
    uids = sorted(recs)
    perm = np.random.default_rng(1).permutation(uids)
    folds = [sorted(perm[i::3]) for i in range(3)]
    rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
    done = {(r["variant"], r["seed"], r["fold"], r["copy"]) for r in rows}
    for fi in [int(f) for f in a.folds.split(",")]:
        todo = [c for c in a.copies.split(",") if (a.variant, str(a.seed), str(fi), c) not in done]
        if not todo:
            continue
        ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=False)
        for c in todo:
            res = ruler.score(c, make(c), seed_base=1000 * fi)
            c1 = next(r for r in res if r["metric"] == "C1.pattern")
            rows.append({"variant": a.variant, "seed": a.seed, "fold": fi, "copy": c,
                         "echo_agreement": round(1 - c1["system_median"], 4),
                         "real_agreement": round(1 - c1["bio_median"], 4), "verdict": c1["verdict"]})
            print(rows[-1], flush=True)
            with OUT.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)


if __name__ == "__main__":
    main()
