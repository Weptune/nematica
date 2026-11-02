"""Artificial lab B: does the ruler's verdict match the truth?

On worms nobody knows the true cause and effect, so "inside the ruler" cannot be checked
against reality. Here it can. A species of nonlinear brains (nematica/annlab.py) with
individuals that differ (every connection scaled by 1 + sigma * N(0, 1)) and slow hidden
drives (5% of input, 90 s), kicks held for 4 s (calibrated so that single-poke echoes agree
between individuals about as well as between worms), 60 individuals, each recorded once like an atlas worm (37 min,
half the units seen, 30% of units never seen, a kick every 30 s). The atlas's 3-fold design
and the unchanged NEMATICA ruler (FoldRuler) score copies:

  species_mean        the brain the individuals vary around
  another_individual  one more individual of the species
  scrambled_F         the species brain with a fraction F of its connections moved
  var3_spontaneous    NEMATICA's watching copy, fitted to the training individuals
  hybrid_kernels      NEMATICA's poke-trained copy, fitted to the training individuals

Truth for brain copies: correlation of the copy's true K with each held-out individual's
true K (pairs of units ever seen), against individuals' true K with each other. A copy is
"truly as close as an individual" when its median is at least the individuals' median.

Output: docs/figures/ann_ruler.csv

Usage:  python scripts/run_ann_ruler.py [--sigma 0.3]
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
from nematica import annlab as L  # noqa: E402
from nematica.bench.scorecard import FoldRuler, fold_parts, set_norm  # noqa: E402
from run_same_worms import make_model  # noqa: E402


def kcorr(a, b, mask):
    ok = mask & np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def full_template(br0, hidden, reps_seed=0):
    """Every ever-seen unit recorded, kicked in a shuffled order, a kick every 30 s; recorded
    from the species brain so that copies which replay the target's own measured response
    (NEMATICA's clamp protocol) have one to replay."""
    obs = ~hidden
    units = np.flatnonzero(obs)
    rng = np.random.default_rng(reps_seed)
    order = rng.permutation(np.repeat(units, 2))
    kicks = {f: int(order[i % len(order)]) for i, f in enumerate(range(L.EVERY, L.FRAMES - L.WIN, L.EVERY))}
    return L.as_pumpprobe(L.record(br0, rng, obs, kicks), obs, kicks, "template")


def mean_echo(sim_fn, br0, hidden, reps=16, seed=0):
    """Noise-averaged echo of anything that can be poked: amplitude of every (target, responder)
    pair averaged over `reps` simulated full recordings, each with its own kick order."""
    from nematica.bench.causal import response_set
    n = br0.n
    tot, cnt = np.zeros((n, n)), np.zeros((n, n))
    rng = np.random.default_rng(seed)
    for k in range(reps):
        sim = sim_fn(full_template(br0, hidden, reps_seed=seed * 100 + k), rng)
        rs = response_set(sim)
        for (a, b) in rs.traces:
            v = rs.amp((a, b))
            if np.isfinite(v):
                i, j = int(b[1:]), int(a[1:])
                tot[i, j] += v
                cnt[i, j] += 1
    return np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sigma", type=float, default=0.3)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--share", type=float, default=0.05)
    ap.add_argument("--tau", type=float, default=90.0)
    ap.add_argument("--folds", default="0,1,2")
    ap.add_argument("--copies", default="species_mean,another_individual,scrambled_0.1,scrambled_0.25,scrambled_0.5,scrambled_1.0,var3_spontaneous,hybrid_kernels")
    ap.add_argument("--out", default="docs/figures/ann_ruler.csv")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    # calibrated so that single-poke echoes agree between individuals about as well as
    # between worms (about 0.09): kicks held for 4 s, as optogenetic pulses are
    L.KICK, L.KICK_FRAMES = 6.0, 8
    br0 = L.make_brain(rho=1.3, share=args.share, tau=args.tau, seed=0, q=0.2)
    hidden = L.design(br0.n, np.random.default_rng(200))
    mask = ~np.eye(br0.n, dtype=bool) & ~hidden[:, None] & ~hidden[None, :]
    inds = [L.individual(br0, args.sigma, 1000 + i) for i in range(args.n)]
    rng = np.random.default_rng(7)
    recs = {f"ind{i:02d}": L.atlas_recording(b, rng, hidden, f"ind{i:02d}") for i, b in enumerate(inds)}
    Ktrue = {u: L.true_K(b, np.random.default_rng(300 + i)) for i, (u, b) in enumerate(zip(recs, inds))}
    uids = sorted(recs)
    perm = np.random.default_rng(1).permutation(uids)
    folds = [sorted(perm[i::3]) for i in range(3)]
    brains = {"species_mean": br0, "another_individual": L.individual(br0, args.sigma, 999)}
    for c in args.copies.split(","):
        if c.startswith("scrambled_"):
            brains[c] = L.scrambled(br0, float(c.split("_")[1]), 5)
    Kb = {c: L.true_K(b, np.random.default_rng(400)) for c, b in brains.items()}
    rows = []
    out = Path(args.out)
    for fi in [int(f) for f in args.folds.split(",")]:
        ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=False)
        pool = [r.uid for r in ruler.pool]
        ii = [kcorr(Ktrue[a], Ktrue[b], mask) for k, a in enumerate(pool) for b in pool[k + 1:]]
        Epool = {u: mean_echo(L.BrainCopy(inds[uids.index(u)]).simulate, br0, hidden, seed=500 + uids.index(u)) for u in pool}
        ee = [kcorr(Epool[a], Epool[b], mask) for k, a in enumerate(pool) for b in pool[k + 1:]]
        for c in args.copies.split(","):
            copy = L.BrainCopy(brains[c]) if c in brains else make_model(c)
            res = ruler.score(c, copy, seed_base=1000 * fi)
            Ec = mean_echo(copy.simulate, br0, hidden, seed=900)
            echo_truth = [kcorr(Ec, Epool[u], mask) for u in pool]
            c1 = next(r for r in res if r["metric"] == "C1.pattern")
            acts = [r for r in res if r["kind"] == "activity" and r.get("primary")]
            truth = [kcorr(Kb[c], Ktrue[u], mask) for u in pool] if c in Kb else []
            row = {"sigma": args.sigma, "fold": fi, "copy": c,
                   "echo_agreement": round(1 - c1["system_median"], 4), "real_agreement": round(1 - c1["bio_median"], 4),
                   "verdict": c1["verdict"], "equivalence": c1.get("equivalence", ""),
                   "activity_inside": sum(r["verdict"] == "inside" for r in acts), "activity_levels": len(acts),
                   "true_copy_vs_individuals": round(float(np.median(truth)), 4) if truth else "",
                   "true_individuals_vs_each_other": round(float(np.median(ii)), 4),
                   "mean_echo_copy_vs_individuals": round(float(np.median(echo_truth)), 4),
                   "mean_echo_individuals_vs_each_other": round(float(np.median(ee)), 4),
                   "share": args.share, "tau": args.tau,
                   **{f"act_{r['metric']}": r["verdict"] for r in acts}}
            rows.append(row)
            print(row, flush=True)
            with out.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
