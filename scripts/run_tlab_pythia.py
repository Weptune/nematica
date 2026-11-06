"""Transformer phase 8: the depth test on real language models (Pythia; pre-registered, README
"Phase 8: real language models").

Usage: python scripts/run_tlab_pythia.py seeds|checkpoints|70m
Output: docs/figures/tlab_pythia.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures" / "tlab_pythia.csv"
TEXT = ROOT / "data" / "external" / "wikitext" / "test.parquet"
import os
N_WIN = int(os.environ.get("NEMATICA_PY_WIN", "48"))       # 24 for Pythia-70m (memory)
WIN, POS, N_ATTR = 256, 200, 256
torch.set_num_threads(1)


def windows(tok):
    import pandas as pd
    text = "\n".join(t for t in pd.read_parquet(TEXT)["text"].tolist() if t.strip())
    ids = tok(text[:400000], return_tensors="pt")["input_ids"][0]
    g = np.random.default_rng(0)
    starts = g.choice(len(ids) - WIN, N_WIN, replace=False)
    return torch.stack([ids[s:s + WIN] for s in starts])


class Patcher:
    """Forward hooks: record the residual after each layer and the MLP hidden units of each layer;
    optionally add a patch at layer 0 (residual or MLP hidden)."""

    def __init__(self, model, record_mlp=True):
        self.m, self.rec, self.patch, self.hooks = model, {}, None, []
        self.record_mlp = record_mlp
        layers = model.gpt_neox.layers
        for i, layer in enumerate(layers):
            self.hooks.append(layer.register_forward_hook(self._res_hook(i)))
            self.hooks.append(layer.mlp.act.register_forward_hook(self._mlp_hook(i)))

    def _res_hook(self, i):
        def f(mod, inp, out):
            h = out[0] if isinstance(out, tuple) else out
            if self.patch is not None and self.patch[0] == ("resid", i):
                h = h + self.patch[1]
            self.rec[("resid", i)] = h
            return ((h,) + tuple(out[1:])) if isinstance(out, tuple) else h
        return f

    def _mlp_hook(self, i):
        def f(mod, inp, out):
            if self.patch is not None and self.patch[0] == ("mlp", i):
                out = out + self.patch[1]
            if self.record_mlp:
                self.rec[("mlp", i)] = out
            return out
        return f

    def run(self, ids, patch=None, grad=False):
        self.patch, self.rec = patch, {}
        with torch.set_grad_enabled(grad):
            self.m.gpt_neox(ids)
        return dict(self.rec)


def analyse(model, ids, basis, attribution=True):
    P = Patcher(model, record_mlp=(basis == "mlp"))
    L = model.config.num_hidden_layers
    src, dst = (basis, 0), [(basis, l) for l in range(1, L)]
    rec = P.run(ids)
    X = rec[src].reshape(-1, rec[src].shape[-1]).numpy()
    Yfull = torch.cat([rec[d] for d in dst], -1)
    Y = Yfull.reshape(-1, Yfull.shape[-1]).numpy()
    sx, sy = X.std(0) + 1e-6, Y.std(0) + 1e-6
    J, I = X.shape[1], Y.shape[1]
    K = np.zeros((I, J))
    for j in range(J):
        z = torch.zeros(N_WIN, WIN, J)
        z[:, POS, j] = float(sx[j])
        r = P.run(ids, (src, z))
        K[:, j] = ((torch.cat([r[d] for d in dst], -1) - Yfull)[:, POS].mean(0).numpy()) / sy
    Xs, Ys = (X - X.mean(0)) / sx, (Y - Y.mean(0)) / sy
    B = np.linalg.solve(Xs.T @ Xs / len(Xs) + 1e-2 * np.eye(J), Xs.T @ Ys / len(Xs))
    corr = lambda a, b: float(np.corrcoef(a.ravel(), b.ravel())[0, 1])  # noqa: E731
    out = {"watch_all": corr(B.T, K)}
    halves = []
    for r_ in range(5):
        seen = np.random.default_rng(50 + r_).random(J) < 0.5
        Xo = Xs[:, seen]
        Bh = np.linalg.solve(Xo.T @ Xo / len(Xo) + 1e-2 * np.eye(seen.sum()), Xo.T @ Ys / len(Xo))
        halves.append(corr(Bh.T, K[:, seen]))
    out["watch_half"] = float(np.mean(halves))
    if attribution:
        sel = np.random.default_rng(7).choice(I, min(N_ATTR, I), replace=False)
        sub = ids[:12]
        z = torch.zeros(12, WIN, J, requires_grad=True)
        r = P.run(sub, (src, z), grad=True)
        o = torch.cat([r[d] for d in dst], -1)[:, POS]
        Ka = np.zeros((len(sel), J))
        for a, i in enumerate(sel):
            gi, = torch.autograd.grad(o[:, i].sum(), z, retain_graph=True)
            Ka[a] = gi[:, POS, :].mean(0).numpy() * sx / sy[i]
        out["attribution"] = corr(Ka, K[sel])
        out["watch_on_same_units"] = corr(B.T[sel], K[sel])
        # exploratory (added after seeing three seeds, before the rest): without the skip-connection
        # entries (same dimension in later layers, residual basis) and by rank correlation
        from scipy.stats import spearmanr
        out["attribution_spearman"] = float(spearmanr(Ka.ravel(), K[sel].ravel()).statistic)
        out["watch_spearman"] = float(spearmanr(B.T[sel].ravel(), K[sel].ravel()).statistic)
        if basis == "resid":
            D = J
            off = np.array([[(i % D) != j for j in range(J)] for i in sel])
            out["attribution_offdiag"] = float(np.corrcoef(Ka[off], K[sel][off])[0, 1])
            out["watch_offdiag"] = float(np.corrcoef(B.T[sel][off], K[sel][off])[0, 1])
        out["_K"], out["_Kw"], out["_Ka"], out["_sel"] = K, B.T, Ka, sel
    if basis == "resid":
        D = J
        offm = np.array([[(i % D) != j for j in range(J)] for i in range(I)])
        out["watch_all_offdiag"] = float(np.corrcoef(B.T[offm], K[offm])[0, 1])
    for h in P.hooks:
        h.remove()
    return out


def load(name, revision=None):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    kw = {"dtype": torch.float32}
    m = AutoModelForCausalLM.from_pretrained(name, revision=revision, **kw) if revision else AutoModelForCausalLM.from_pretrained(name, **kw)
    m.eval()
    return m, AutoTokenizer.from_pretrained("EleutherAI/pythia-14m")


def record(row):
    rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
    rows.append(row)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, restval="")
        w.writeheader()
        w.writerows(rows)
    print(row, flush=True)


def main():
    what = sys.argv[1]
    if what == "seeds":
        jobs = [("EleutherAI/pythia-14m", None)] + [(f"EleutherAI/pythia-14m-seed{k}", None) for k in range(1, 10)]
        bases = ("resid", "mlp")
    elif what == "checkpoints":
        jobs = [("EleutherAI/pythia-14m", f"step{s}") for s in (0, 1000, 8000, 33000)]
        bases = ("resid", "mlp")
    else:
        jobs = [("EleutherAI/pythia-70m", None)] + [(f"EleutherAI/pythia-70m-seed{k}", None) for k in (1, 2)]
        bases = ("resid",)
    ids = None
    for name, rev in jobs:
        m, tok = load(name, rev)
        if ids is None:
            ids = windows(tok)
        for basis in bases:
            res = analyse(m, ids, basis)
            mats = {k: res.pop(k) for k in [k for k in res if k.startswith("_")]}
            save = ROOT / "results" / "tlab" / "pythia"
            save.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(save / f"{name.split('/')[-1]}_{rev or 'final'}_{basis}.npz", **{k[1:]: v for k, v in mats.items()})
            record({"model": name, "revision": rev or "final", "basis": basis, **{k: round(v, 4) for k, v in res.items()}})


if __name__ == "__main__":
    main()
