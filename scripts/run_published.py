"""Published models on the rotating reference pools (leaderboard, and arc 3: what the wiring
buys). Scores the three Creamer, Leifer & Pillow (2024) linear dynamical systems, run with
their stimulation input off, at the neural pairwise levels; behaviour levels are not
scored (the models make no behaviour).

Caveat built into the comparison: these models were fitted to immobilised worms (Randi et
al. 2023, optogenetic atlas); the reference worms here crawl freely in the copper arena.

Usage:
  python scripts/fetch_creamer_lds.py
  python scripts/run_published.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \\
      --folds configs/splits/copper2026_cv3.yaml [--out results/published]
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
from nematica.systems.published import CreamerLDS  # noqa: E402


def build(train):
    return {"real_other_worms": None,
            **{f"creamer2024_{v}": CreamerLDS(v) for v in
               ("connectome_constrained", "fully_connected", "shuffled_constrained")}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="results/published")
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()
    recs = load_copper_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    combined, flat = cv_score(recs, classes, load_folds(args.folds)["folds"], build, args.seeds)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, data in [("published_combined.csv", combined), ("published_per_fold.csv", flat)]:
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
