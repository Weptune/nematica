"""Transformer phase 0 (diagnostic, exploratory): which kind of poke gives a measurable echo?

For each poke type, on one trained base model: exact echoes from paired runs (with and without the
patch, same tokens), measured over the residual stream of the blocks after the poked one (in each
unit's natural SD), averaged over the 15-token window. Reported: echo size, consistency across
contexts (mean pairwise correlation of echo vectors), and the evoked share of the post-minus-pre
change (the worms' value is about 0.4).

Usage: python scripts/run_tlab_phase0.py  ->  docs/figures/tlab_phase0.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica import tlab as T  # noqa: E402

torch.set_num_threads(2)
POST, PRE, N_CTX, N_TGT, LEN = 30, 20, 20, 8, 600


def run():
    net, loss = T.base_model()
    cfg = net.cfg
    L, D, H, NH = cfg["L"], cfg["D"], cfg["H"], cfg["NH"]
    Tm, E = T.hmm()
    g = np.random.default_rng(5)
    toks = [torch.tensor(T.sample(Tm, E, LEN, g))[None] for _ in range(N_CTX)]
    with torch.no_grad():
        base = [net(t)[1] for t in toks]
    # natural SDs of every recorded site, over all contexts
    rec_sites = [("resid", l) for l in range(L)] + [("mlp", l) for l in range(L)]
    sd = {s: torch.cat([b[s][0] for b in base]).std(0) for s in rec_sites}
    # principal directions of the residual after block 0
    R0 = torch.cat([b[("resid", 0)][0] for b in base])
    R0c = R0 - R0.mean(0)
    _, sv, Vt = torch.linalg.svd(R0c, full_matrices=False)
    meas = [("resid", l) for l in range(1, L)]               # where echoes are measured

    def unitvec(b):
        return torch.cat([(b[s][0] / sd[s]) for s in meas], -1)   # (T, units)

    nat = []
    for b in base:
        u = unitvec(b)
        for t in range(PRE + 50, LEN - POST, 25):
            nat.append(((u[t:t + POST].mean(0) - u[t - PRE:t].mean(0)) ** 2).mean().item())
    nat_ms = float(np.mean(nat))

    def make_patch(kind, j, k, dur, t):
        p = {}
        if kind == "mlp-unit":
            z = torch.zeros(1, LEN, H)
            z[0, t:t + dur, j] = k * sd[("mlp", 0)][j]
            p[("mlp", 0)] = z
        elif kind == "resid-dim":
            z = torch.zeros(1, LEN, D)
            z[0, t:t + dur, j] = k * sd[("resid", 0)][j]
            p[("resid", 0)] = z
        elif kind in ("resid-random", "resid-pc"):
            if kind == "resid-random":
                v = torch.tensor(np.random.default_rng(100 + j).standard_normal(D), dtype=torch.float32)
                v = v / v.norm()
                s_ = (R0c @ v).std()
            else:
                v = Vt[j]
                s_ = sv[j] / np.sqrt(len(R0c))
            z = torch.zeros(1, LEN, D)
            z[0, t:t + dur] = k * s_ * v
            p[("resid", 0)] = z
        elif kind == "head":
            z = torch.ones(1, LEN, NH)
            z[0, t:t + dur, j % NH] = k                       # gain on one head's output
            p[("head", 0)] = z
        return p

    rows = []
    designs = [("mlp-unit", 3, 4), ("mlp-unit", 10, 30), ("resid-dim", 3, 4), ("resid-dim", 10, 30),
               ("resid-random", 3, 4), ("resid-random", 10, 30), ("resid-pc", 3, 4), ("resid-pc", 10, 30),
               ("head", 0.0, 30), ("head", 4.0, 30)]
    for kind, k, dur in designs:
        echoes, evoked = [], []
        for j in range(N_TGT):
            vecs = []
            for c in range(N_CTX // 2):
                t = int(np.random.default_rng(1000 * j + c).integers(PRE + 50, LEN - POST - 1))
                with torch.no_grad():
                    rec = net(toks[c], make_patch(kind, j, k, dur, t))[1]
                up, ub = unitvec(rec), unitvec(base[c])
                vecs.append((up[t:t + POST] - ub[t:t + POST]).mean(0).numpy())
                evoked.append(((up[t:t + POST].mean(0) - up[t - PRE:t].mean(0)) ** 2).mean().item())
            V_ = np.array(vecs)
            C = np.corrcoef(V_)
            echoes.append((np.abs(V_).mean(), np.nanmean(C[np.triu_indices(len(V_), 1)])))
        size = float(np.mean([e[0] for e in echoes]))
        cons = float(np.mean([e[1] for e in echoes]))
        ev = float(np.mean(evoked))
        rows.append(f"{kind:13s} strength {k:>4g} for {dur:>2d} tokens: mean |echo| {size:.3f} SD; "
                    f"consistency across contexts {cons:.2f}; evoked share {(ev - nat_ms) / ev:.2f}")
        print(rows[-1], flush=True)
    out = [f"base model loss {loss:.3f}; natural mean-square change {nat_ms:.3f}"] + rows
    (ROOT / "docs" / "figures" / "tlab_phase0.txt").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    run()
