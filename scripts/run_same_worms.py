"""Arc 4, the headline test: the same models on the same worms, scored on ordinary activity
statistics (the spontaneous ruler: distributions, timescales, correlations, dimensionality,
lead-lag, AVA bouts) and on the causal levels. Everything uses the original atlas archive
(randi2023_wt_npz) for real and simulated worms; models are fitted on the training worms;
real and model worms are stimulated on the same schedule.

Usage:
  python scripts/run_same_worms.py --data data/raw/randi2023_wt_npz --folds configs/splits/pumpprobe_cv3.yaml
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import build_reference, score_system  # noqa: E402
from nematica.bench.causal import response_set, score_sets  # noqa: E402
from nematica.bench.sample import BenchSample  # noqa: E402
from nematica.data.canonical import zscore_rows  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.causal_models import ClassVAR, CreamerCausal, class_matrix  # noqa: E402

ACTIVITY_LEVELS = ("L1.distribution", "L1.timescale", "L2.correlation", "L2.dimension", "L4.leadlag", "L4.dwell")


def bench_sample(rec, classes, name, origin, max_gap_frac: float = 0.05) -> BenchSample:
    """Class-level z-scored activity on a fixed class index; short gaps interpolated, classes
    missing more than 5% of frames left out."""
    x = class_matrix(rec, classes)
    t = np.arange(x.shape[1])
    for i in range(len(x)):
        ok = np.isfinite(x[i])
        if ok.mean() < 1 - max_gap_frac:
            x[i] = np.nan
        elif not ok.all():
            x[i] = np.interp(t, t[ok], x[i, ok])
    return BenchSample(name, tuple(classes), zscore_rows(x), rec.dt, origin=origin)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="docs/figures")
    ap.add_argument("--models", default="var3_all,var3_spontaneous,creamer2024_fully_connected,creamer2024_connectome_constrained")
    args = ap.parse_args()
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    folds = load_folds(args.folds)["folds"]
    rows = []
    for fi, pool_uids in enumerate(folds):
        t0 = time.time()
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        val_uids = rest[::5]
        train = [recs[u] for u in rest if u not in val_uids]
        val = [recs[u] for u in val_uids]
        pool = [recs[u] for u in pool_uids]
        classes = ClassVAR(3, "all").fit(train, val).classes          # one class index for the fold
        real_b = [bench_sample(r, classes, f"real:{r.uid}", r.uid) for r in pool]
        ref = build_reference(real_b, metrics=ACTIVITY_LEVELS)
        real_c = [response_set(r) for r in pool]
        for name in args.models.split(","):
            if name.startswith("creamer2024_"):
                m = CreamerCausal(name.replace("creamer2024_", ""))
            else:
                L, fr = name.replace("var", "").split("_")
                m = ClassVAR(lags=int(L), frames=fr).fit(train, val)
            sims = [m.simulate(r, np.random.default_rng(1000 * fi + i)) for i, r in enumerate(pool)]
            sim_b = [bench_sample(s, classes, f"{name}:{r.uid}", r.uid) for s, r in zip(sims, pool)]
            for b, r in zip(sim_b, pool):
                b.name = f"{name}:{r.uid}"
            for row in score_system(name, sim_b, real_b, ref):
                if row["metric"] in ACTIVITY_LEVELS:
                    rows.append({"fold": fi, "kind": "activity", **row})
            sim_c = []
            for s, r in zip(sims, pool):
                rs = response_set(s, f"{name}:{r.uid}")
                rs.group = r.uid
                sim_c.append(rs)
            for row in score_sets(name, sim_c, real_c):
                rows.append({"fold": fi, "kind": "causal", **row})
            mine = [r for r in rows if r["fold"] == fi and r["system"] == name]
            print(f"fold {fi} {name:36s} " + "  ".join(f"{r['metric']}={r['verdict']}" for r in mine), flush=True)
        print(f"fold {fi} done ({time.time() - t0:.0f} s)", flush=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (Path(args.out) / "same_worms.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
