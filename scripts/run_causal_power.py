"""Arc 4: power of the poke-pattern level (C1). Synthetic brains blend the true average echo
(atlas average of the training worms) with the same echoes reassigned to random pairs:

    trace(pair) = f * atlas(pair) + sqrt(1 - f^2) * atlas(random other pair)

so f is the brain's correlation with the true average and every echo keeps its real size and
shape. Each f is scored with the ruler's verdict rules on the frozen pools (README, "What does
inside mean on the poke pattern?").

Usage:
  python scripts/run_causal_power.py --data data/raw/randi2023_wt_npz --folds configs/splits/pumpprobe_cv3.yaml
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.causal import ResponseSet, atlas_mean, c_pattern, response_set, score_sets  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402


def blend(atlas: ResponseSet, f: float, rng: np.random.Generator) -> ResponseSet:
    keys = list(atlas.traces)
    perm = rng.permutation(len(keys))
    g = np.sqrt(max(0.0, 1.0 - f * f))
    out = ResponseSet(f"blend{f:.2f}:{atlas.group}", atlas.group, dt=atlas.dt)
    for k, p in zip(keys, perm):
        out.traces[k] = f * atlas.traces[k] + g * atlas.traces[keys[p]]
        out.counts[k] = atlas.counts.get(k, 1)
    return out


def corr_with(a: ResponseSet, b: ResponseSet) -> float:
    d = c_pattern(a, b)
    return float("nan") if not np.isfinite(d) else 1.0 - d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="docs/figures")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--step", type=float, default=0.05)
    ap.add_argument("--norm", default="recording", choices=("recording", "fluct"))
    args = ap.parse_args()
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    folds = load_folds(args.folds)["folds"]
    sets = {u: response_set(recs[u], norm=args.norm) for f in folds for u in f if u in recs}
    fs = np.round(np.arange(0.0, 1.0 + 1e-9, args.step), 3)
    rows = []
    for fi, pool_uids in enumerate(folds):
        real = [sets[u] for u in pool_uids if u in sets]
        train = [sets[u] for f in folds if f is not pool_uids for u in f if u in sets]
        atl = [atlas_mean(train, s) for s in real]
        own = np.nanmedian([corr_with(a, s) for a, s in zip(atl, real)])
        print(f"pool {fi}: {len(real)} worms; one real worm vs atlas average r = {own:.3f}", flush=True)
        for f in fs:
            for rep in range(args.reps):
                rng = np.random.default_rng(1000 * fi + 17 * rep + int(round(f * 100)))
                syn = [blend(a, float(f), rng) for a in atl]
                r_atl = np.nanmedian([corr_with(b, a) for b, a in zip(syn, atl)])
                row = score_sets(f"blend{f:.2f}", syn, real, levels={"C1.pattern": c_pattern})[0]
                rows.append({"fold": fi, "f": float(f), "rep": rep, "r_with_atlas": round(float(r_atl), 3),
                             "real_r_with_atlas": round(float(own), 3), **row})
            got = [r["verdict"] for r in rows if r["fold"] == fi and r["f"] == float(f)]
            med = np.median([r["system_median"] for r in rows if r["fold"] == fi and r["f"] == float(f)])
            print(f"  f={f:.2f}  distance {med:.3f} (real {row['bio_median']}, 5-95% [{row['bio_p05']}, "
                  f"{row['bio_p95']}])  {', '.join(got)}", flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (out / "causal_power.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
