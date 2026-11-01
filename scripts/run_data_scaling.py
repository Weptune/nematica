"""Real-data check of the synthetic-worm prediction: a copy that learns by watching should be
at its ceiling already (more training worms do not help), while a copy that learns from
pokes should keep improving with more worms. Each copy is fitted on a fraction of the
training worms and scored on held-out pools; reported: echo agreement with real worms.

Usage:  python scripts/run_data_scaling.py [--folds 0,1]
"""

from __future__ import annotations

import argparse
import csv
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nematica.bench.scorecard import SPLITS, SPLITS_DIR, FoldRuler, fold_parts, set_norm  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from run_same_worms import make_model  # noqa: E402


class Subsampled:
    def __init__(self, spec, frac, seed):
        self.m, self.frac, self.seed = make_model(spec), frac, seed

    def fit(self, train, val):
        rng = np.random.default_rng(self.seed)
        k = max(3, int(round(self.frac * len(train))))
        pick = sorted(rng.choice(len(train), k, replace=False))
        self.m.fit([train[i] for i in pick], val)
        return self

    def simulate(self, rec, rng):
        return self.m.simulate(rec, rng)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", default="0,1")
    ap.add_argument("--fracs", default="0.1,0.25,0.5,1.0")
    ap.add_argument("--models", default="var3_spontaneous,hybrid_kernels")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
    folds = load_folds(SPLITS_DIR / SPLITS["cv3"])["folds"]
    rows = []
    out = Path("docs/figures/data_scaling.csv")
    for fi in [int(f) for f in args.folds.split(",")]:
        ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=False)
        for spec in args.models.split(","):
            for frac in [float(f) for f in args.fracs.split(",")]:
                res = ruler.score(f"{spec}@{frac}", Subsampled(spec, frac, seed=fi), seed_base=1000 * fi)
                c1 = next(r for r in res if r["metric"] == "C1.pattern")
                rows.append({"fold": fi, "model": spec, "fraction": frac, "train_worms": int(round(frac * len(ruler.train))),
                             "echo_agreement": round(1 - c1["system_median"], 4),
                             "real_agreement": round(1 - c1["bio_median"], 4), "verdict": c1["verdict"]})
                print(rows[-1], flush=True)
                with out.open("w", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                    w.writeheader()
                    w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
