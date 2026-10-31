"""Is the wiring diagram enough? Descriptive part: which poked pairs carry a reliable echo
across real worms, and whether those pairs are wired (class-level synapse or gap junction,
Kunert et al. 2014) or reachable in two wired steps.

Usage:
  python scripts/analyse_wiring_echo.py --data data/raw/randi2023_wt_npz
Writes docs/figures/wiring_echo.csv (one row per pair) and prints the summary in the README.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.causal import response_set  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.systems.wiring import class_members_known, class_wiring  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw/randi2023_wt_npz")
    ap.add_argument("--min-worms", type=int, default=3)
    ap.add_argument("--out", default="docs/figures/wiring_echo.csv")
    args = ap.parse_args()
    acc: dict = {}
    recs = load_pumpprobe_dir(args.data)
    for r in recs:
        rs = response_set(r)
        for k in rs.traces:
            if k[0] == k[1]:
                continue
            a = rs.amp(k)
            if np.isfinite(a):
                acc.setdefault(k, []).append(a)
    keys = [k for k, v in acc.items() if len(v) >= args.min_worms]
    cls = sorted({c for k in keys for c in k})
    A = class_wiring(cls)
    known = class_members_known(cls)
    idx = {c: i for i, c in enumerate(cls)}
    keys = [k for k in keys if known[idx[k[0]]] and known[idx[k[1]]]]
    A2 = (A.astype(int) @ A.astype(int)) > 0
    rows = []
    for k in keys:
        v = np.asarray(acc[k])
        se = v.std(ddof=1) / np.sqrt(len(v))
        rows.append({"stim": k[0], "resp": k[1], "n_worms": len(v), "mean": round(float(v.mean()), 4),
                     "t": round(float(v.mean() / se), 3) if se > 0 else 0.0,
                     "wired": bool(A[idx[k[1]], idx[k[0]]]), "two_step": bool(A2[idx[k[1]], idx[k[0]]])})
    with Path(args.out).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    t = np.array([r["t"] for r in rows]); m = np.array([r["mean"] for r in rows])
    wired = np.array([r["wired"] for r in rows]); two = np.array([r["two_step"] for r in rows])
    print(f"{len(rows)} pairs in {len(recs)} worms; wired {wired.mean():.3f}")
    for thr in (2, 3, 4):
        sel = np.abs(t) > thr
        print(f"|t| > {thr}: {sel.sum()} pairs, wired {wired[sel].mean():.3f}")
    sel = np.abs(t) > 3
    print(f"share of reliable echo size on unwired pairs: {(np.abs(m[sel]) * ~wired[sel]).sum() / np.abs(m[sel]).sum():.3f}")
    print(f"reliable unwired pairs two wired steps apart: {two[sel & ~wired].mean():.3f} (all unwired {two[~wired].mean():.3f})")
    # what predicts where a poke's echo goes in worms not used to make the prediction?
    from sklearn.metrics import roc_auc_score
    import ast
    from nematica.systems.wiring import KUNERT, _members
    names = [str(n) for n in ast.literal_eval((KUNERT / "neuron_names.txt").read_text())]
    Gs, Gg = np.load(KUNERT / "Gs.npy"), np.load(KUNERT / "Gg.npy")
    mem = {c: _members(names, c) for c in cls}
    syn = {k: float(Gs[np.ix_(mem[k[1]], mem[k[0]])].sum() + Gg[np.ix_(mem[k[1]], mem[k[0]])].sum()
                    + Gg[np.ix_(mem[k[0]], mem[k[1]])].sum()) for k in keys}
    per = {}
    for r_i, r in enumerate(recs):
        rs = response_set(r)
        for k in rs.traces:
            if k in syn:
                a = rs.amp(k)
                if np.isfinite(a):
                    per.setdefault(k, []).append((r_i, a))
    tstat = lambda v: (np.mean(v) / (np.std(v, ddof=1) / np.sqrt(len(v)))) if len(v) > 2 and np.std(v) > 0 else 0.0
    aucs = {"wired": [], "two wired steps": [], "synapse count": [], "other worms' echoes": []}
    for seed in range(20):
        half = set(np.random.default_rng(seed).permutation(len(recs))[: len(recs) // 2])
        ks, y, preds = [], [], {n: [] for n in aucs}
        for k, v in per.items():
            a = [x for i, x in v if i in half]; b = [x for i, x in v if i not in half]
            if len(b) < 3 or len(a) < 2:
                continue
            y.append(abs(tstat(b)) > 2)
            preds["wired"].append(float(A[idx[k[1]], idx[k[0]]])); preds["two wired steps"].append(float(A2[idx[k[1]], idx[k[0]]]))
            preds["synapse count"].append(syn[k]); preds["other worms' echoes"].append(abs(tstat(a)))
        for n in aucs:
            aucs[n].append(roc_auc_score(y, preds[n]))
    print("AUC for a reliable echo in held-out worms (20 random halves): " +
          "; ".join(f"{n} {np.mean(v):.3f} [{np.min(v):.3f}, {np.max(v):.3f}]" for n, v in aucs.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
