"""Why does echo complexity fail? (README hypothesis): median PCI of real and hybrid echoes, and
how similar repeated pokes of the same class are within a worm (correlation of their
class-level echo vectors, 0 to 15 s mean), real against simulated, on one pool.

Usage:
  python scripts/run_pci_why.py --data data/raw/randi2023_wt_npz --folds configs/splits/pumpprobe_cv3.yaml --fold 0
"""

from __future__ import annotations

import argparse
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import nematica.bench.causal as causal  # noqa: E402
from nematica.bench.perturbational import event_matrices  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from run_same_worms import make_model  # noqa: E402


def repeat_similarity(events) -> list[float]:
    by = {}
    for e in events:
        amp = dict(zip(e["classes"], np.nanmean(e["R"][:, :31], axis=1)))
        by.setdefault(e["stim_class"], []).append(amp)
    out = []
    for amps in by.values():
        for a, b in combinations(amps, 2):
            keys = sorted(set(a) & set(b))
            if len(keys) >= 10:
                x, y = np.array([a[k] for k in keys]), np.array([b[k] for k in keys])
                if x.std() > 0 and y.std() > 0:
                    out.append(float(np.corrcoef(x, y)[0, 1]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--model", default="hybrid_kernels_regimes_obsfit")
    args = ap.parse_args()
    causal.NORM = "fluct"
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    folds = load_folds(args.folds)["folds"]
    pool = [recs[u] for u in folds[args.fold]]
    rest = sorted(u for i, f in enumerate(folds) if i != args.fold for u in f)
    val_uids = rest[::5]
    m = make_model(args.model).fit([recs[u] for u in rest if u not in val_uids], [recs[u] for u in val_uids])
    real_pci, sim_pci, real_rep, sim_rep = [], [], [], []
    for i, r in enumerate(pool):
        er = event_matrices(r, keep=True)
        es = event_matrices(m.simulate(r, np.random.default_rng(i)), keep=True)
        real_pci += [e["pci"] for e in er]
        sim_pci += [e["pci"] for e in es]
        real_rep += repeat_similarity(er)
        sim_rep += repeat_similarity(es)
    print(f"PCI: real median {np.median(real_pci):.3f} (IQR {np.percentile(real_pci, 25):.3f} to {np.percentile(real_pci, 75):.3f}), "
          f"model median {np.median(sim_pci):.3f} (IQR {np.percentile(sim_pci, 25):.3f} to {np.percentile(sim_pci, 75):.3f}); "
          f"model lower: p = {mannwhitneyu(sim_pci, real_pci, alternative='less').pvalue:.2e}")
    print(f"repeat similarity: real median r {np.median(real_rep):.3f} ({len(real_rep)} pairs), model {np.median(sim_rep):.3f} "
          f"({len(sim_rep)} pairs); real lower: p = {mannwhitneyu(real_rep, sim_rep, alternative='less').pvalue:.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
