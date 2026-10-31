"""Arc 4: stimulable models scored on the causal levels. For each rotation, models are fitted
on the training worms (the other pools; a fifth of them for choosing the ridge), each pool
worm is simulated with the model's own noise and stimulated on its own schedule (see
nematica/systems/causal_models.py), and the simulated responses are scored against the pool.

Usage:
  python scripts/run_causal_models.py --data data/raw/2025_creamer_lds_npz --folds configs/splits/pumpprobe_cv3.yaml
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.causal import response_set, score_sets  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.causal_models import ClassVAR  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="docs/figures")
    ap.add_argument("--models", default="var3_spontaneous,var3_all")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    folds = load_folds(args.folds)["folds"]
    makers = {f"var{L}_{fr}": (lambda L=L, fr=fr: ClassVAR(lags=L, frames=fr))
              for L in (1, 3, 6) for fr in ("spontaneous", "all")}
    rows = []
    for fi, pool_uids in enumerate(folds):
        t0 = time.time()
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        val_uids = rest[::5]
        train = [recs[u] for u in rest if u not in val_uids]
        val = [recs[u] for u in val_uids]
        pool = [recs[u] for u in pool_uids]
        real = [response_set(r) for r in pool]
        for name in args.models.split(","):
            m = makers[name]().fit(train, val)
            sims = [response_set(m.simulate(r, np.random.default_rng(1000 * fi + i)), f"{name}:{r.uid}")
                    for i, r in enumerate(pool)]
            for s, r in zip(sims, pool):
                s.group = r.uid
            for row in score_sets(name, sims, real):
                rows.append({"fold": fi, **row, **{f"info_{k}": v for k, v in m.info.items()}})
                print(f"fold {fi} {name:18s} {row['metric']:13s} {row['verdict']:11s} median {row.get('system_median')} "
                      f"vs real {row.get('bio_median')} [{row.get('bio_p05')}, {row.get('bio_p95')}] "
                      f"pct {row.get('percentile_of_bio')}  {m.info}", flush=True)
        print(f"fold {fi} done ({time.time() - t0:.0f} s)", flush=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (Path(args.out) / f"causal_models{args.tag}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
