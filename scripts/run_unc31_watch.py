"""Hidden-drive test: does watching do better in worms without neuropeptide release?

The synthetic worm says a copy that learns by watching fails because slow drives shared by
many neurons, and not recorded, contaminate what watching sees. Neuropeptides are a prime
suspect for such drives. unc-31 worms cannot release them, so the theory predicts that in
unc-31 worms the watching copy should get closer to the real worm-to-worm agreement, and the
gap to the poke-trained copy should shrink.

Both conditions get the same, small design: 15 worms, split 3 ways (train on 10, test on 5),
copies fitted and scored within the condition. unc-31 has exactly 15 identified worms, so it is
re-split several times; wild type is re-drawn (15 of 113 worms) several times to match.

Reported per split: echo agreement of each copy, the real worm-to-worm echo agreement of the
held-out 5, and the ratio copy / real.

Usage:  python scripts/run_unc31_watch.py [--repeats 6]
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
from nematica.bench.scorecard import FoldRuler, fold_parts, set_norm  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from run_same_worms import make_model  # noqa: E402

N_WORMS, N_FOLDS = 15, 3
OUT = Path("docs/figures/unc31_watch.csv")


def identified(recs, k=20):
    return [r for r in recs if sum(1 for c in r.classes if c) >= k]


def splits(uids, rng):
    perm = list(rng.permutation(sorted(uids)))
    return [sorted(perm[i::N_FOLDS]) for i in range(N_FOLDS)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=6)
    ap.add_argument("--models", default="var3_spontaneous,hybrid_kernels")
    ap.add_argument("--conditions", default="unc31,wt")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    data = {"wt": {r.uid: r for r in identified(load_pumpprobe_dir("data/raw/randi2023_wt_npz"))},
            "unc31": {r.uid: r for r in identified(load_pumpprobe_dir("data/raw/randi2023_unc31_npz"))}}
    print({k: len(v) for k, v in data.items()}, flush=True)
    rows = []
    if OUT.exists():
        with OUT.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    done = {(r["condition"], r["repeat"], r["fold"], r["model"]) for r in rows}
    for rep in range(args.repeats):
        for cond in args.conditions.split(","):
            rng = np.random.default_rng(1000 * rep + (7 if cond == "wt" else 0))
            uids = sorted(data[cond])
            if len(uids) > N_WORMS:
                uids = sorted(rng.choice(uids, N_WORMS, replace=False))
            folds = splits(uids, rng)
            for fi in range(N_FOLDS):
                todo = [m for m in args.models.split(",") if (cond, str(rep), str(fi), m) not in done]
                if not todo:
                    continue
                ruler = FoldRuler(*fold_parts(data[cond], folds, fi), pci=False, equivalence=True)
                for spec in todo:
                    res = ruler.score(spec, make_model(spec), seed_base=1000 * rep + 100 * fi)
                    c1 = next(r for r in res if r["metric"] == "C1.pattern")
                    copy, real = 1 - c1["system_median"], 1 - c1["bio_median"]
                    rows.append({"condition": cond, "repeat": rep, "fold": fi, "model": spec,
                                 "train_worms": len(ruler.train), "test_worms": len(ruler.pool),
                                 "echo_agreement": round(copy, 4), "real_agreement": round(real, 4),
                                 "ratio": round(copy / real, 4) if real > 0 else "",
                                 "verdict": c1["verdict"], "equivalence": c1.get("equivalence", "")})
                    print(rows[-1], flush=True)
                    with OUT.open("w", newline="", encoding="utf-8") as fh:
                        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                        w.writeheader()
                        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
