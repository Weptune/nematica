"""Watching limit, part D (pre-registered 7 Nov 2026): does watching a transformer improve with
more data? Small trained and untrained transformers of phase 2 (scripts/run_tlab_depth.py,
width 64, 4 layers, residual basis, 3 individuals each). Truth: exact paired runs over 96
contexts. Watching: the phase-2 ridge regression from the first m contexts, m = 6, 12, 24, 48, 96.
Score: correlation with the truth, off-diagonal (skip-connection entries excluded), as phase 2.

Usage:  python scripts/run_limit_tlab.py trained|untrained
Output: docs/figures/limit_tlab.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica import tlab as T  # noqa: E402
import run_tlab_depth as D  # noqa: E402

OUT = ROOT / "docs" / "figures" / "limit_tlab.csv"
MS = (6, 12, 24, 48, 96)


def main():
    cond = sys.argv[1]
    Tm, E = T.hmm()
    base, loss = T.base_model(steps=3000 if cond == "trained" else 0)
    ft = 50 if cond == "trained" else 0
    rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
    for i in range(3):
        net = D.individual(base, i, ft, Tm, E)
        K, _, J = D.matrices(net, "resid", Tm, E, n_ctx=96, seed=i)
        # the watching data: activations of the same 96 contexts, in order
        g = np.random.default_rng(i)
        toks = torch.tensor(np.array([T.sample(Tm, E, 300, g) for _ in range(96)]))
        with torch.no_grad():
            rec = net(toks)[1]
        L = net.cfg["L"]
        X = rec[("resid", 0)].numpy()                                          # (96, 300, J)
        Y = torch.cat([rec[("resid", l)] for l in range(1, L)], -1).numpy()    # (96, 300, I)
        mask = D.offdiag_mask(K, "resid", J)
        for m in MS:
            Xm = X[:m].reshape(-1, X.shape[-1])
            Ym = Y[:m].reshape(-1, Y.shape[-1])
            sx, sy = Xm.std(0) + 1e-6, Ym.std(0) + 1e-6
            Xs, Ys = (Xm - Xm.mean(0)) / sx, (Ym - Ym.mean(0)) / sy
            B = np.linalg.solve(Xs.T @ Xs / len(Xs) + 1e-2 * np.eye(J), Xs.T @ Ys / len(Xs))
            Kw = B.T
            row = dict(condition=cond, individual=i, contexts=m, tokens=m * 300,
                       watch_offdiag=round(D.corr(Kw, K, mask), 4), watch_all=round(D.corr(Kw, K), 4))
            print(row, flush=True)
            rows.append(row)
        with OUT.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
