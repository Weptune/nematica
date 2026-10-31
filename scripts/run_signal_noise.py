"""Signal or noise (README): each model's echo averaged over repeated simulations, correlated
with the training worms' atlas average, against the same for single real worms.

Usage:
  python scripts/run_signal_noise.py --data data/raw/randi2023_wt_npz --folds configs/splits/pumpprobe_cv3.yaml --fold 0
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import nematica.bench.causal as causal  # noqa: E402
from nematica.bench.causal import ResponseSet, atlas_mean, c_pattern, response_set  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from run_same_worms import make_model  # noqa: E402


def mean_set(sets, group):
    out = ResponseSet("avg", group)
    keys = set().union(*[s.traces for s in sets])
    for k in keys:
        trs = [s.traces[k] for s in sets if k in s.traces]
        out.traces[k] = np.nanmean(np.vstack(trs), axis=0)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--models", default="var3_spontaneous,var3_stim,var3_all_relu,creamer2024_fully_connected")
    ap.add_argument("--repeats", type=int, default=10)
    ap.add_argument("--out", default="docs/figures")
    args = ap.parse_args()
    causal.NORM = "fluct"
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    folds = load_folds(args.folds)["folds"]
    pool = [recs[u] for u in folds[args.fold]]
    rest = sorted(u for i, f in enumerate(folds) if i != args.fold for u in f)
    val_uids = rest[::5]
    train = [recs[u] for u in rest if u not in val_uids]
    val = [recs[u] for u in val_uids]
    train_sets = [response_set(r) for r in train + val]
    real = {r.uid: response_set(r) for r in pool}
    atlas = {u: atlas_mean(train_sets, s) for u, s in real.items()}
    rows = []
    corr = lambda a, b: 1 - c_pattern(a, b)  # noqa: E731
    real_vs_atlas = [corr(real[u], atlas[u]) for u in real]
    print(f"single real worm vs atlas average: median r = {np.nanmedian(real_vs_atlas):.3f}", flush=True)
    rows.append({"system": "real worm (single)", "r_with_atlas_avg": float(np.nanmedian(real_vs_atlas))})
    for spec in args.models.split(","):
        m = make_model(spec).fit(train, val)
        r_single, r_avg = [], []
        for i, rec in enumerate(pool):
            sims = [response_set(m.simulate(rec, np.random.default_rng(10_000 * i + k))) for k in range(args.repeats)]
            r_single.append(corr(sims[0], atlas[rec.uid]))
            r_avg.append(corr(mean_set(sims, rec.uid), atlas[rec.uid]))
        row = {"system": spec, "r_single_with_atlas_avg": float(np.nanmedian(r_single)),
               "r_with_atlas_avg": float(np.nanmedian(r_avg))}
        rows.append(row)
        print(f"{spec:32s} averaged echo vs atlas average r = {row['r_with_atlas_avg']:.3f} "
              f"(single simulated worm {row['r_single_with_atlas_avg']:.3f})", flush=True)
    with (Path(args.out) / f"signal_noise_f{args.fold}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
