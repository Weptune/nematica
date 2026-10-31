"""Nonlinear rung (arc 1): GRU with and without per-worm identity, on the rotating pools,
plus Level 8 on the frozen test split. Training stops at the step with the lowest
negative log-likelihood on the validation worms (never on the ruler); hidden size 64 and
identity size 8 were chosen the same way (validation NLL 0.086 vs 0.097 for 64/32 and
128/32 on the frozen split's validation worms).

Usage (needs PyTorch; uses the GPU if available):
  python scripts/run_gru.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --folds configs/splits/copper2026_cv3.yaml --split configs/splits/copper2026.yaml \
      [--steps 2000] [--hidden 64] [--out results/gru]
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
from nematica.bench.discriminability import core_classes, discriminability  # noqa: E402
from nematica.data import load_copper_dir, load_split  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.gru import GRUWorms  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--out", default="results/gru")
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--skip-cv", action="store_true")
    args = ap.parse_args()
    import torch
    print(f"PyTorch {torch.__version__}; CUDA available: {torch.cuda.is_available()}", flush=True)

    recs = load_copper_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    variants = {"shared": 0, "identity": 8}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if not args.skip_cv:
        def build(train):
            return {f"gru{args.hidden}_{n}": GRUWorms(hidden=args.hidden, emb=e, steps=args.steps)
                    for n, e in variants.items()}
        combined, flat = cv_score(recs, classes, load_folds(args.folds)["folds"], build, args.seeds)
        for name, data in [("gru_combined.csv", combined), ("gru_per_fold.csv", flat)]:
            keys = list(dict.fromkeys(k for r in data for k in r))
            with (out / name).open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=keys)
                w.writeheader()
                w.writerows(data)
        print()
        print_table(combined)

    # Level 8 on the frozen test split
    split = load_split(args.split)
    by = {r.uid: r for r in recs}
    S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
    train, val, test = S(split["train"]), S(split["val"]), S(split["test"])
    core = core_classes(test + train + val, 12)
    rows = []
    for n, e in variants.items():
        m = GRUWorms(hidden=args.hidden, emb=e, steps=args.steps).fit(train, val)
        sims = [m.generate(s, np.random.default_rng(1000 * seed + i), which=seed * len(test) + i)
                for seed in range(args.seeds) for i, s in enumerate(test)]
        r = discriminability(test, sims, core, n_perm=100, seed=0)
        rows.append({"system": m.name, **r, **m.info})
        print(f"Level 8, frozen split: {m.name} AUC {r['auc']} p {r['p']} {r['verdict']} | {m.info}", flush=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (out / "gru_l8.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
