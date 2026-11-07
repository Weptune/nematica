"""Exploratory (written 7 Nov 2026 after the first worm folds of part C were read): how much of the
seen units' rest variance does the best watcher attribute to its hidden units?

Part A found that when hidden drives supply most of the seen units' variance (93 to 96%), even
the best possible watcher has little to go on at realistic recording lengths. This refits the best
watcher exactly as part C did (train plus validation worms of a fold, the k part C chose) and
reports the hidden share (1 minus the seen variance left when hidden-to-seen links are cut, from
the stationary covariance), the scale of seen-to-seen links, and the slowest timescales.

Usage:  python scripts/explore_latent_hidden_share.py --data worms --fold 0 --k 4
Output: appends to docs/figures/latent_hidden_share.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
import warnings
from pathlib import Path

import numpy as np
import scipy.linalg as sl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from run_latent_watch import load  # noqa: E402
from nematica.bench.scorecard import fold_parts  # noqa: E402
from nematica.systems.latent import LatentCopy  # noqa: E402

OUT = ROOT / "docs" / "figures" / "latent_hidden_share.csv"


def shares(F, q, C):
    """Hidden share = the part of the seen units' stationary variance that originates in the hidden
    units' own noise (network intact, hidden noise switched off). A first version cut the
    hidden-to-seen links instead; with hidden units wired both ways that also removes feedback
    loops and can give negative 'shares' (it did, -0.94, worm fold 1), so it was replaced."""
    Q = np.diag(q)
    S = sl.solve_discrete_lyapunov(F, Q)
    q0 = q.copy()
    q0[C:] = 0
    S0 = sl.solve_discrete_lyapunov(F, np.diag(q0))
    hidden = 1 - np.trace(S0[:C, :C]) / np.trace(S[:C, :C])
    ev = np.sort(np.abs(np.linalg.eigvals(F)))[::-1]
    tau = -0.5 / np.log(np.clip(ev[:3], 1e-9, 0.999999))       # seconds, 0.5 s frames
    off = F[:C, :C][~np.eye(C, dtype=bool)]
    return float(hidden), float(np.sqrt(np.mean(off ** 2))), tau


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--fold", type=int, required=True)
    ap.add_argument("--k", type=int, required=True)
    a = ap.parse_args()
    warnings.filterwarnings("ignore")
    recs, folds = load(a.data)
    train, val, _ = fold_parts(recs, folds, a.fold)
    m = LatentCopy(steps=400, polish=150, fixed_k=a.k).fit(train, val)
    C = len(m.classes) - m.k
    F = m.W[:-1].T
    q = m.noise_sd ** 2
    h, off, tau = shares(F, q, C)
    mdir = ROOT / "results" / "limits" / "models"
    mdir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(mdir / f"explore_{a.data.replace(':', '_')}_fold{a.fold}_k{a.k}.npz", W=m.W,
                        noise_sd=m.noise_sd, lr=m.lr_, k=m.k, classes=np.array(m.classes))
    row = dict(data=a.data, fold=a.fold, k=a.k, hidden_share=round(h, 4), seen_link_rms=round(off, 4),
               slowest_s="/".join(f"{t:.0f}" for t in tau), radius=m.info["radius"])
    print(row, flush=True)
    rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
    rows.append(row)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
