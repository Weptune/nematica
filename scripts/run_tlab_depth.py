"""Transformer phase 2: the watching-versus-poking test in depth, with known truth (pre-registered;
README "Transformers, phase 2").

For a network, the true effect matrix K[i, j]: the change in later-layer unit i when unit j of the
first block is pushed by 1 natural SD, averaged over contexts and positions (paired runs, exact).
Watching: a ridge regression of later-layer units on first-block units across natural activations
(tokens of many contexts), the observational estimate of the same matrix. Score: correlation of the
watching estimate with the truth over all (i, j) pairs, with every first-block unit seen, or with a
random half seen (the atlas's situation; unseen units are then unknown confounders). Reference: two
individuals' true matrices against each other (how much individuals differ).

Bases: "resid" (residual-stream dimensions after block 0, measured on the residual after blocks
1..L-1) and "mlp" (MLP hidden units of block 0, measured on the MLP hidden units of blocks 1..L-1).

Usage: python scripts/run_tlab_depth.py [trained|untrained] [--width 64 --layers 4 --steps 3000]
Output: docs/figures/tlab_depth.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica import tlab as T  # noqa: E402

torch.set_num_threads(2)
OUT = ROOT / "docs" / "figures" / "tlab_depth.csv"


def individual(base, i, steps, Tm, E):
    net = T.Net(**base.cfg)
    net.load_state_dict(base.state_dict())
    g = torch.Generator().manual_seed(1000 + i)
    with torch.no_grad():
        for p in net.parameters():
            p.mul_(1 + 0.1 * torch.randn(p.shape, generator=g))
    if steps:
        T.train(net, Tm, E, steps, seed=1000 + i, lr=3e-4)
    return net


def matrices(net, basis, Tm, E, n_ctx=24, length=300, ridge=1e-2, seed=0):
    """Truth from batched paired runs: in every context, unit j is pushed by 1 SD at positions 20, 90,
    160, 230 (spaced beyond the 64-token attention span, so patches cannot affect each other), and the
    effect is read at the same positions in later blocks."""
    L = net.cfg["L"]
    src = (basis, 0)
    dst = [(basis, l) for l in range(1, L)]
    g = np.random.default_rng(seed)
    toks = torch.tensor(np.array([T.sample(Tm, E, length, g) for _ in range(n_ctx)]))
    with torch.no_grad():
        rec = net(toks)[1]
    X = rec[src].reshape(-1, rec[src].shape[-1]).numpy()                                   # (N, J)
    Yfull = torch.cat([rec[d] for d in dst], -1)                                           # (B, T, I)
    Y = Yfull.reshape(-1, Yfull.shape[-1]).numpy()
    sx, sy = X.std(0) + 1e-6, Y.std(0) + 1e-6
    J = X.shape[1]
    pos = [20, 90, 160, 230]
    width = net.cfg["D"] if basis == "resid" else net.cfg["H"]
    K = np.zeros((Y.shape[1], J))
    for j in range(J):
        z = torch.zeros(n_ctx, length, width)
        z[:, pos, j] = float(sx[j])
        with torch.no_grad():
            r = net(toks, {src: z})[1]
        dy = (torch.cat([r[d] for d in dst], -1) - Yfull)[:, pos].reshape(-1, Y.shape[1]).numpy()
        K[:, j] = dy.mean(0) / sy
    Xs, Ys = (X - X.mean(0)) / sx, (Y - Y.mean(0)) / sy

    def watch(seen):
        Xo = Xs[:, seen]
        B = np.linalg.solve(Xo.T @ Xo / len(Xo) + ridge * np.eye(seen.sum()), Xo.T @ Ys / len(Xo))
        Kw = np.full_like(K, np.nan)
        Kw[:, seen] = B.T
        return Kw
    return K, watch, J


def corr(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[m], b[m])[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cond", choices=["trained", "untrained"])
    ap.add_argument("--width", type=int, default=64)
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--n_ind", type=int, default=6)
    a = ap.parse_args()
    Tm, E = T.hmm()
    cfg = dict(D=a.width, H=2 * a.width, L=a.layers)
    if (a.width, a.layers) == (64, 4):
        cfg = {}
    base, loss = T.base_model(steps=a.steps if a.cond == "trained" else 0, **cfg)
    ft = 50 if a.cond == "trained" else 0
    rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
    for basis in ("resid", "mlp"):
        Ks, scores = [], {"all": [], "half": []}
        for i in range(a.n_ind):
            net = individual(base, i, ft, Tm, E)
            K, watch, J = matrices(net, basis, Tm, E, seed=i)
            Ks.append(K)
            scores["all"].append(corr(watch(np.ones(J, bool)), K))
            halves = [corr(watch(np.random.default_rng(50 + r).random(J) < 0.5), K) for r in range(5)]
            scores["half"].append(float(np.mean(halves)))
        ind = [corr(Ks[p], Ks[q]) for p in range(len(Ks)) for q in range(p + 1, len(Ks))]
        row = {"condition": a.cond, "width": a.width, "layers": a.layers, "basis": basis,
               "base_loss": round(loss, 3) if loss == loss else "",
               "watch_all": round(float(np.median(scores["all"])), 3),
               "watch_half": round(float(np.median(scores["half"])), 3),
               "individuals": round(float(np.median(ind)), 3), "n_ind": a.n_ind}
        rows.append(row)
        print(row, flush=True)
        with OUT.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(row))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
