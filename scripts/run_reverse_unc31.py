"""The reverse test: unc-31 worms (no neuropeptide release) scored as a copy against each
wild-type held-out pool, on every level, with the poke-level equivalence check. Each pool
worm is matched to one unc-31 worm in turn (its activity and its own pokes are used as they
were recorded; the pool worm only supplies the slot).

Usage:
  python scripts/run_reverse_unc31.py --split cv3
"""

from __future__ import annotations

import argparse
import csv
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.scorecard import SPLITS, SPLITS_DIR, FoldRuler, fold_parts, set_norm  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402


class Replay:
    """Returns recorded worms in turn instead of simulating."""

    def __init__(self, worms):
        self.worms, self.k = worms, 0

    def fit(self, train, val):
        return self

    def simulate(self, rec, rng):
        w = self.worms[self.k % len(self.worms)]
        self.k += 1
        return w


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw/randi2023_wt_npz")
    ap.add_argument("--unc31", default="data/raw/randi2023_unc31_npz")
    ap.add_argument("--split", choices=tuple(SPLITS), default="cv3")
    ap.add_argument("--out", default="results/reverse_unc31")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    unc = [r for r in load_pumpprobe_dir(args.unc31) if sum(1 for c in r.classes if c) >= 20]
    print(f"{len(unc)} unc-31 worms with identities", flush=True)
    folds = load_folds(SPLITS_DIR / SPLITS[args.split])["folds"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for fi in range(len(folds)):
        f = out / f"{args.split}_f{fi}.csv"
        if f.exists():
            continue
        ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=True)
        rows = ruler.score("unc31", Replay(unc), seed_base=1000 * fi)
        with f.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
            w.writeheader()
            w.writerows(rows)
        print(f"{args.split} fold {fi} " + "  ".join(f"{r['metric']}={r['verdict']}" + (f"/{r['equivalence']}" if 'equivalence' in r else "")
                                               for r in rows), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
