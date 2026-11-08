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
        mask = next((p for p in parts if not p.startswith("bg") and p not in ("obs", "heavy", "regimes", "obsfit", "classquiet", "quietfit", "quietobsfit", "indiv", "indivshock", "hp", "mem", "ownrho", "nokernels", "diag", "drift", "driftpool") and not p.startswith("burst") and not p.startswith("driftpool") and not p.startswith("indivslow") and not p.startswith("lowrank") and not p.startswith("smooth")
                     and not p.startswith("gru") and not p.startswith("innov") and not p.startswith("slow")), None)
        hk = HybridKernel(mask=mask, background=bg, obs_noise="obs" in parts, heavy="heavy" in parts,
                            regimes="regimes" in parts, obs_fit="obsfit" in parts,
                            lowrank=next((int(p[7:]) for p in parts if p.startswith("lowrank")), 0),
                            obs_smooth=next((float(p[6:]) for p in parts if p.startswith("smooth")), 0.0),
                            class_quiet="classquiet" in parts, quiet_fit="quietfit" in parts,
                            quiet_obs_fit="quietobsfit" in parts, individual="indiv" in parts or "indivshock" in parts,
                            gru=next((int(p[3:].replace("ss", "")) for p in parts if p.startswith("gru")), 0),
                            gru_sampled=any(p.startswith("gru") and p.endswith("ss") for p in parts),
                            gru_steps=3000 if any(p.startswith("gru") and p.endswith("ss") for p in parts) else 1500,
                            innov=next((int(p[5:]) for p in parts if p.startswith("innov")), 0),
                            slow=next((int(p[4:].replace("d", "")) for p in parts if p.startswith("slow")), 0))
        hk.slow_dyn = any(p.startswith("slow") and p.endswith("d") for p in parts)
        if hk.slow_dyn:
            hk.name = hk.name.replace(f"_slow{hk.slow}", f"_slow{hk.slow}d")
        hk.indiv_shock = "indivshock" in parts
        hk.highpass = "hp" in parts
        hk.members = "mem" in parts
        hk.slow_own_rho = "ownrho" in parts
        hk.no_kernels = "nokernels" in parts
        hk.coupling = "diagonal" if "diag" in parts else "full"
        hk.slow_drift = "drift" in parts
        bu = next((p for p in parts if p.startswith("burst")), None)
        if bu:
            hk.burst_nu = float(bu[5:])
            hk.name += "_" + bu
        hk.slow_drift = "drift" in parts
        dp = next((p for p in parts if p.startswith("driftpool")), None)
        hk.slow_drift_pool = dp is not None
        if dp:
            hk.drift_gain = float(dp[9:]) if len(dp) > 9 else 1.0
            hk.name += "_" + dp
        for flag in ("nokernels", "diag", "drift"):
            if flag in parts:
                hk.name += "_" + flag
        if hk.slow_own_rho:
            hk.name += "_ownrho"
        if hk.members:
            hk.name += "_mem"
        if hk.highpass:
            hk.name += "_hp"
        isl = next((p for p in parts if p.startswith("indivslow")), None)
        hk.indiv_slow = isl is not None
        if hk.indiv_slow:
            hk.slow_w_own = float(isl[9:]) if len(isl) > 9 else 0.5
            hk.name += "_" + isl
        if hk.indiv_shock:
            hk.name = hk.name.replace("_indiv", "_indivshock")
        return hk
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
    ap.add_argument("--seed-offset", type=int, default=0, help="different simulation noise (cache names get _s<offset>)")
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
        sfx = f"_s{args.seed_offset}" if args.seed_offset else ""
        todo = [n for n in args.models.split(",") if not (cache / f"{args.norm}_f{fi}_{n}{sfx}.csv").exists()]
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
            sims = [m.simulate(r, np.random.default_rng(1000 * fi + i + 100000 * args.seed_offset)) for i, r in enumerate(pool)]
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
            for r in rows[n_before:]:
                r["system"] = name + sfx
            with (cache / f"{args.norm}_f{fi}_{name}{sfx}.csv").open("w", newline="", encoding="utf-8") as fh:
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
