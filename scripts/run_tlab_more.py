"""Transformer phases 5, 6 and 9 in depth (pre-registered; README "Phases 5, 6 and 9 in depth").

Usage: python scripts/run_tlab_more.py trained|untrained
Output: docs/figures/tlab_more.csv
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
import run_tlab_depth as TD  # noqa: E402

torch.set_num_threads(1)
OUT = ROOT / "docs" / "figures" / ("tlab_more_v2.csv" if "--v2" in sys.argv else "tlab_more.csv")
N_CTX, LENGTH, POS = 48, 300, [20, 90, 160, 230]


def analyse(net, basis, Tm, E, seed):
    L = net.cfg["L"]
    src, dst = (basis, 0), [(basis, l) for l in range(1, L)]
    g = np.random.default_rng(seed)
    pairs = [T.sample(Tm, E, LENGTH, g, return_states=True) for _ in range(N_CTX)]
    toks = torch.tensor(np.array([p[0] for p in pairs]))
    states = np.array([p[1] for p in pairs])[:, POS].reshape(-1)          # hidden state at each patched position
    with torch.no_grad():
        rec = net(toks)[1]
    X = rec[src].reshape(-1, rec[src].shape[-1]).numpy()
    Yfull = torch.cat([rec[d] for d in dst], -1)
    Y = Yfull.reshape(-1, Yfull.shape[-1]).numpy()
    sx, sy = X.std(0) + 1e-6, Y.std(0) + 1e-6
    J, I = X.shape[1], Y.shape[1]
    width = net.cfg["D"] if basis == "resid" else net.cfg["H"]
    dys = np.zeros((J, len(states), I))                                     # per-sample effects
    for j in range(J):
        z = torch.zeros(N_CTX, LENGTH, width)
        z[:, POS, j] = float(sx[j])
        with torch.no_grad():
            r = net(toks, {src: z})[1]
        dys[j] = ((torch.cat([r[d] for d in dst], -1) - Yfull)[:, POS].reshape(-1, I).numpy()) / sy
    K = dys.mean(1).T                                                        # (I, J)
    # phase 5: state dependence
    corr = lambda a, b: float(np.corrcoef(a.ravel(), b.ravel())[0, 1])  # noqa: E731
    Ks = [dys[:, states == s_].mean(1).T for s_ in np.unique(states) if (states == s_).sum() >= 10]
    st = [corr(Ks[a], Ks[b]) for a in range(len(Ks)) for b in range(a + 1, len(Ks))]
    floor = []
    for r_ in range(10):
        perm = np.random.default_rng(300 + r_).permutation(len(states))
        h1, h2 = perm[: len(perm) // 2], perm[len(perm) // 2:]
        floor.append(corr(dys[:, h1].mean(1).T, dys[:, h2].mean(1).T))
    state_dis, floor_dis = 1 - float(np.mean(st)), 1 - float(np.mean(floor))
    # review 3: floors with groups the same size as the state groups, (a) labels shuffled across
    # samples, (b) labels shuffled across whole contexts (keeps the within-context grouping, so it
    # also absorbs context differences that sticky states would otherwise be confused with)
    def grouped(lab):
        Kg = [dys[:, lab == s_].mean(1).T for s_ in np.unique(lab) if (lab == s_).sum() >= 10]
        return 1 - float(np.mean([corr(Kg[a], Kg[b]) for a in range(len(Kg)) for b in range(a + 1, len(Kg))]))
    lab2 = states.reshape(N_CTX, len(POS))
    floor_size = float(np.mean([grouped(np.random.default_rng(400 + r_).permutation(states)) for r_ in range(10)]))
    floor_ctx = float(np.mean([grouped(lab2[np.random.default_rng(500 + r_).permutation(N_CTX)].reshape(-1))
                               for r_ in range(10)]))
    # phase 6: silent links (effects in low-variance directions of later-layer natural activity)
    Ys = (Y - Y.mean(0)) / sy
    _, sv, Vt = np.linalg.svd(Ys, full_matrices=False)
    low = Vt[len(Vt) // 2:]
    nat_low = float((sv[len(sv) // 2:] ** 2).sum() / (sv ** 2).sum())
    eff_low = float(np.mean([(np.linalg.norm(low @ K[:, j]) ** 2) / (np.linalg.norm(K[:, j]) ** 2 + 1e-12) for j in range(J)]))
    # phase 9: attribution patching (Jacobian at natural activations) against the truth, beside watching
    Ka = np.zeros_like(K)
    sub = toks[:12]
    z = torch.zeros(12, LENGTH, width, requires_grad=True)
    r = net(sub, {src: z})[1]
    out = torch.cat([r[d] for d in dst], -1)[:, POS]                         # (12, 4, I)
    for i in range(I):
        gi, = torch.autograd.grad(out[..., i].sum(), z, retain_graph=True)
        Ka[i] = gi[:, POS, :].mean((0, 1)).numpy() * sx / sy[i]             # gradient for every j at once
    Xs, Ysn = (X - X.mean(0)) / sx, (Y - Y.mean(0)) / sy
    B = np.linalg.solve(Xs.T @ Xs / len(Xs) + 1e-2 * np.eye(J), Xs.T @ Ysn / len(Xs))
    return dict(state_dissimilarity=state_dis, floor_dissimilarity=floor_dis,
                floor_same_size=floor_size, floor_context_shuffle=floor_ctx, effect_low_share=eff_low,
                natural_low_share=nat_low, attribution=corr(Ka, K), watching=corr(B.T, K))


def main():
    cond = sys.argv[1]
    Tm, E = T.hmm()
    base, _ = T.base_model(steps=3000 if cond == "trained" else 0)
    rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
    for basis in ("resid", "mlp"):
        res = []
        for i in range(6):
            net = TD.individual(base, i, 50 if cond == "trained" else 0, Tm, E)
            res.append(analyse(net, basis, Tm, E, seed=i))
            print(cond, basis, i, {k: round(v, 3) for k, v in res[-1].items()}, flush=True)
        row = {"condition": cond, "basis": basis, **{k: round(float(np.median([r[k] for r in res])), 4) for k in res[0]}}
        rows.append(row)
        with OUT.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(row))
            w.writeheader()
            w.writerows(rows)
        print(row, flush=True)


if __name__ == "__main__":
    main()
