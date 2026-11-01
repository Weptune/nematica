"""Score the gallery of artificial network families (nematica/gallery.py, plus published
and in-house models) on every held-out pool, one cached CSV per (split, fold, family), so
runs resume. Then gather everything into docs/figures/gallery.csv.

Usage:
  python scripts/run_gallery.py --split cv3 [--families linear-rest,random-wiring,kunert2014,creamer-native]
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.scorecard import SPLITS, SPLITS_DIR, FoldRuler, fold_parts, set_norm  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.score import CopyAdapter  # noqa: E402


def family(name: str):
    from nematica import gallery
    from nematica.systems.causal_models import CreamerCausal
    from nematica.taskworm import TaskNet
    return {
        "linear-rest": gallery.LinearRest,
        "random-wiring": gallery.RandomNet,
        "kunert2014": gallery.KunertNet,
        "creamer-native": lambda: CreamerCausal("connectome_constrained", protocol="native"),
        "creamer-shuffled-native": lambda: CreamerCausal("shuffled_constrained", protocol="native"),
        "task-dense": lambda: TaskNet("dense"),
        "task-wired": lambda: TaskNet("wired"),
    }[name]()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw/randi2023_wt_npz")
    ap.add_argument("--split", choices=tuple(SPLITS), default="cv3")
    ap.add_argument("--families", default="linear-rest,random-wiring,creamer-native,task-dense,task-wired,kunert2014")
    ap.add_argument("--cache", default="results/gallery")
    ap.add_argument("--pci", action="store_true")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    folds = load_folds(SPLITS_DIR / SPLITS[args.split])["folds"]
    for fi in range(len(folds)):
        todo = [f for f in args.families.split(",") if not (cache / f"{args.split}_f{fi}_{f}.csv").exists()]
        if not todo:
            continue
        ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=args.pci)
        for fam in todo:
            t0 = time.time()
            m = family(fam)
            model = m if hasattr(m, "simulate") else CopyAdapter(m)
            rows = ruler.score(fam, model, seed_base=1000 * fi)
            with (cache / f"{args.split}_f{fi}_{fam}.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
                w.writeheader()
                w.writerows(rows)
            print(f"{args.split} fold {fi} {fam:24s} " + "  ".join(f"{r['metric']}={r['verdict']}" for r in rows)
                  + f"  ({time.time() - t0:.0f} s)", flush=True)
    rows = []
    for f in sorted(cache.glob("*.csv")):
        split, fold, fam = f.stem.split("_", 2)
        rows += [dict(r, split=split, fold=fold[1:]) for r in csv.DictReader(f.open(encoding="utf-8"))]
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with Path("docs/figures/gallery.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
