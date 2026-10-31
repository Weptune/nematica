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
import nematica.bench.causal as causal  # noqa: E402
from nematica.bench.causal import response_set, score_sets  # noqa: E402
from nematica.bench.perturbational import PCI_LEVELS, pci_set  # noqa: E402
from nematica.bench.sample import BenchSample  # noqa: E402
from nematica.data.canonical import zscore_rows  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.causal_models import ClassVAR, CreamerCausal, HybridKernel, class_matrix  # noqa: E402

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


def make_model(spec: str):
    base, _, protocol = spec.partition("@")
    protocol = protocol or "clamp"
    if base.startswith("hybrid_kernels"):
        parts = [p for p in base.replace("hybrid_kernels", "").split("_") if p]
        bg = next((p[2:] for p in parts if p.startswith("bg")), "spontaneous")
        mask = next((p for p in parts if not p.startswith("bg") and p not in ("obs", "heavy", "regimes", "obsfit") and not p.startswith("lowrank") and not p.startswith("smooth")), None)
        return HybridKernel(mask=mask, background=bg, obs_noise="obs" in parts, heavy="heavy" in parts,
                            regimes="regimes" in parts, obs_fit="obsfit" in parts,
                            lowrank=next((int(p[7:]) for p in parts if p.startswith("lowrank")), 0),
                            obs_smooth=next((float(p[6:]) for p in parts if p.startswith("smooth")), 0.0))
    if base.startswith("creamer2024_"):
        return CreamerCausal(base.replace("creamer2024_", ""), protocol=protocol)
    parts = base[3:].split("_")
    extra = parts[2:]
    return ClassVAR(lags=int(parts[0]), frames=parts[1], protocol=protocol,
                    coupling="diagonal" if "diagonal" in extra else "full",
                    features="relu" if "relu" in extra else "linear",
                    penalty="lasso" if "lasso" in extra else "ridge")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="docs/figures")
    ap.add_argument("--models", default="var3_all,var3_spontaneous,creamer2024_fully_connected,creamer2024_connectome_constrained")
    ap.add_argument("--norm", default="recording", choices=("recording", "fluct"))
    ap.add_argument("--cache", default="results/same_worms")
    ap.add_argument("--tag", default="")
    ap.add_argument("--fold", type=int, default=None)
    ap.add_argument("--pci", action="store_true", help="also score perturbational complexity (P1, P2)")
    args = ap.parse_args()
    causal.NORM = args.norm
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    folds = load_folds(args.folds)["folds"]
    rows = []
    for fi, pool_uids in enumerate(folds):
        if args.fold is not None and fi != args.fold:
            continue
        todo = [n for n in args.models.split(",") if not (cache / f"{args.norm}_f{fi}_{n}.csv").exists()]
        if not todo:
            continue
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
        real_p = [pci_set(r) for r in pool] if args.pci else None
        for name in todo:
            m = make_model(name).fit(train, val)
            n_before = len(rows)
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
            if args.pci:
                sim_p = []
                for s, r in zip(sims, pool):
                    ps = pci_set(s, f"{name}:{r.uid}")
                    ps.group = r.uid
                    sim_p.append(ps)
                for row in score_sets(name, sim_p, real_p, levels=PCI_LEVELS):
                    med = np.concatenate([q.spread for q in sim_p if len(q.spread)])
                    rows.append({"fold": fi, "kind": "complexity", **row,
                                 "median_spread": round(float(np.median(med)), 4) if med.size else None})
            mine = [r for r in rows if r["fold"] == fi and r["system"] == name]
            for r in mine:
                r["system"] = name
            with (cache / f"{args.norm}_f{fi}_{name}.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows[n_before:] for k in r)))
                w.writeheader()
                w.writerows(rows[n_before:])
            print(f"fold {fi} {name:36s} " + "  ".join(f"{r['metric']}={r['verdict']}" for r in mine), flush=True)
        print(f"fold {fi} done ({time.time() - t0:.0f} s)", flush=True)
    rows = []
    for f in sorted(cache.glob(f"{args.norm}_f*_*.csv")):
        with f.open(encoding="utf-8") as fh:
            rows += [dict(r, norm=args.norm) for r in csv.DictReader(fh)]
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (Path(args.out) / f"same_worms_{args.norm}{args.tag}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
