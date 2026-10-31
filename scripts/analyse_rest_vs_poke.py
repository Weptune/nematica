"""Experiment B (README, "Can you verify a brain copy by watching it?"): does a brain model's
realism at rest predict its realism under a poke? Reads the per-fold, per-model results of
scripts/run_same_worms.py (norm "fluct") and, for each brain and pool:

    rest score   median |log(system_median / bio_median)| over the six activity levels
                 (0 = as far from real worms as real worms are from each other)
    poke score   C1.pattern distance (system median)

then the Spearman correlation across brains, per pool and pooled over pools.

Usage:
  python scripts/analyse_rest_vs_poke.py [--extra results/same_worms_pci]
"""

from __future__ import annotations

import argparse
import csv
import glob
import re
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ACTIVITY = ("L1.distribution", "L1.timescale", "L2.correlation", "L2.dimension", "L4.leadlag", "L4.dwell")


def load(folder: str) -> dict:
    out = {}
    for f in sorted(glob.glob(f"{folder}/fluct_f*_*.csv")):
        m = re.match(r"fluct_f(\d+)_(.+)\.csv", Path(f).name)
        fold, name = int(m.group(1)), m.group(2)
        with open(f, encoding="utf-8") as fh:
            rows = {r["metric"]: r for r in csv.DictReader(fh)}
        out[(fold, name)] = rows
    return out


def scores(rows: dict) -> tuple[float, float, int]:
    logs, inside = [], 0
    for m in ACTIVITY:
        r = rows.get(m)
        if r and r.get("system_median") and r.get("bio_median"):
            s, b = float(r["system_median"]), float(r["bio_median"])
            if s > 0 and b > 0:
                logs.append(abs(np.log(s / b)))
            inside += r.get("verdict") == "inside"
    pat = rows.get("C1.pattern", {}).get("system_median")
    return (float(np.median(logs)) if logs else np.nan, float(pat) if pat else np.nan, inside)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", default="results/same_worms")
    ap.add_argument("--extra", default="results/same_worms_pci")
    ap.add_argument("--out", default="docs/figures/rest_vs_poke.csv")
    args = ap.parse_args()
    res = load(args.main)
    extra = load(args.extra) if args.extra else {}
    table = []
    for (fold, name), rows in {**res, **{k: v for k, v in extra.items() if k not in res}}.items():
        rest, poke, n_in = scores(rows)
        table.append({"fold": fold, "brain": name, "source": "B" if (fold, name) in res else "D",
                      "rest_score": round(rest, 4), "rest_inside": n_in, "poke_pattern": round(poke, 4),
                      "pattern_verdict": rows.get("C1.pattern", {}).get("verdict")})
    for subset, label in ((["B"], "pre-registered 16 brains"), (["B", "D"], "plus ingredient-hunt brains")):
        print(f"\n{label}:")
        allr, allp = [], []
        for fold in sorted({t["fold"] for t in table}):
            t = [x for x in table if x["fold"] == fold and x["source"] in subset
                 and np.isfinite(x["rest_score"]) and np.isfinite(x["poke_pattern"])]
            if len(t) < 5:
                continue
            rho, p = spearmanr([x["rest_score"] for x in t], [x["poke_pattern"] for x in t])
            allr += [x["rest_score"] for x in t]
            allp += [x["poke_pattern"] for x in t]
            print(f"  pool {fold + 1}: {len(t)} brains, Spearman rho = {rho:+.3f} (p = {p:.3f})")
        if len(allr) >= 5:
            rho, p = spearmanr(allr, allp)
            print(f"  all pools: {len(allr)} brain-pools, rho = {rho:+.3f} (p = {p:.3g})")
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(sorted(table, key=lambda x: (x["fold"], x["rest_score"])))
    print("\nper brain (pool 1):")
    for x in sorted([x for x in table if x["fold"] == 0], key=lambda x: x["rest_score"]):
        print(f"  {x['brain']:42s} rest {x['rest_score']:.3f} ({x['rest_inside']}/6 inside)  pattern {x['poke_pattern']:.4f} {x['pattern_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
