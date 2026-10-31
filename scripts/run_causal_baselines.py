"""Arc 4: baselines scored on the causal levels. For each rotation, response sets of the
training worms (other pools) build the prediction; the pool is the reference.

Usage:
  python scripts/run_causal_baselines.py --data data/raw/2025_creamer_lds_npz --folds configs/splits/pumpprobe_cv3.yaml
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.causal import atlas_mean, response_set, score_sets  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="docs/figures")
    args = ap.parse_args()
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    sets = {u: response_set(r) for u, r in recs.items()}
    folds = load_folds(args.folds)["folds"]
    rows = []
    for fi, pool_uids in enumerate(folds):
        train = [sets[u] for f in folds if f is not pool_uids for u in f]
        real = [sets[u] for u in pool_uids]
        systems = {"atlas_mean": [atlas_mean(train, s) for s in real]}
        for name, ss in systems.items():
            for row in score_sets(name, ss, real):
                rows.append({"fold": fi, **row})
                print(f"fold {fi} {name:12s} {row['metric']:13s} {row['verdict']:11s} median {row.get('system_median')} "
                      f"vs real {row.get('bio_median')} [{row.get('bio_p05')}, {row.get('bio_p95')}] "
                      f"pct {row.get('percentile_of_bio')}", flush=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (Path(args.out) / "causal_baselines.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
