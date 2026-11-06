"""The transformer lab: small causal transformers trained on a synthetic language, with patching
anywhere (residual stream after any block, MLP hidden units, attention-head outputs).

Language: a hidden Markov chain with S sticky hidden states (stay probability 0.98) emitting V tokens
from Dirichlet(0.3) distributions, so predicting well needs a slow hidden state inferred from context.
Optional second task: modular addition (a + b = c mod P), used to study training far past fitting.

Patches are additive tensors keyed by site:
  ("resid", l)      (B, T, D)  added to the residual stream after block l
  ("mlp", l)        (B, T, H)  added to block l's MLP hidden units (after the GELU)
  ("head", l)       (B, T, NH) multiplicative gain on each head's output in block l (1 = unchanged)
The forward pass returns logits and a dict of recorded activations (residual after each block,
MLP hidden units of each block).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

CACHE = Path(__file__).resolve().parents[1] / "results" / "tlab"


def hmm(V=32, S=8, stay=0.98, seed=0):
    g = np.random.default_rng(seed)
    E = g.dirichlet(np.full(V, 0.3), size=S)
    Tm = np.full((S, S), (1 - stay) / (S - 1))
    np.fill_diagonal(Tm, stay)
    return Tm, E


def sample(Tm, E, n, g, return_states=False):
    S, V = E.shape
    s = g.integers(S)
    out = np.empty(n, int)
    st = np.empty(n, int)
    cumE, cumT = np.cumsum(E, 1), np.cumsum(Tm, 1)
    u1, u2 = g.random(n), g.random(n)
    for t in range(n):
        st[t] = s
        out[t] = min(int(np.searchsorted(cumE[s], u1[t])), V - 1)
        s = min(int(np.searchsorted(cumT[s], u2[t])), S - 1)
    return (out, st) if return_states else out


class Block(nn.Module):
    def __init__(self, D, NH, H, band):
        super().__init__()
        self.D, self.NH, self.band = D, NH, band
        self.ln1, self.ln2 = nn.LayerNorm(D), nn.LayerNorm(D)
        self.qkv, self.o = nn.Linear(D, 3 * D), nn.Linear(D, D)
        self.fc, self.pr = nn.Linear(D, H), nn.Linear(H, D)

    def attend(self, x, head_gain=None):
        B, T, D = x.shape
        q, k, v = self.qkv(x).split(D, -1)
        dh = D // self.NH
        sh = lambda a: a.view(B, T, self.NH, dh).transpose(1, 2)  # noqa: E731
        q, k, v = sh(q), sh(k), sh(v)
        out = torch.empty_like(q)
        for a in range(0, T, 256):
            b = min(T, a + 256)
            lo = max(0, a - self.band + 1)
            sc = q[:, :, a:b] @ k[:, :, lo:b].transpose(-1, -2) / np.sqrt(dh)
            qi = torch.arange(a, b)[:, None]
            ki = torch.arange(lo, b)[None, :]
            sc = sc.masked_fill((ki > qi) | (ki <= qi - self.band), float("-inf"))
            out[:, :, a:b] = F.softmax(sc, -1) @ v[:, :, lo:b]
        if head_gain is not None:                       # (B, T, NH)
            out = out * head_gain.transpose(1, 2)[..., None]
        return self.o(out.transpose(1, 2).reshape(B, T, D))

    def forward(self, x, mlp_patch=None, head_gain=None):
        x = x + self.attend(self.ln1(x), head_gain)
        h = F.gelu(self.fc(self.ln2(x)))
        if mlp_patch is not None:
            h = h + mlp_patch
        return x + self.pr(h), h


class Net(nn.Module):
    def __init__(self, V=32, D=64, NH=4, H=128, L=4, band=64):
        super().__init__()
        self.cfg = dict(V=V, D=D, NH=NH, H=H, L=L, band=band)
        self.emb = nn.Embedding(V, D)
        self.blocks = nn.ModuleList([Block(D, NH, H, band) for _ in range(L)])
        self.ln, self.head = nn.LayerNorm(D), nn.Linear(D, V)

    def forward(self, tok, patches=None):
        patches = patches or {}
        x = self.emb(tok)
        rec = {}
        for i, b in enumerate(self.blocks):
            x, h = b(x, patches.get(("mlp", i)), patches.get(("head", i)))
            if ("resid", i) in patches:
                x = x + patches[("resid", i)]
            rec[("resid", i)] = x
            rec[("mlp", i)] = h
        return self.head(self.ln(x)), rec


def train(net, Tm, E, steps, seed, lr=1e-3, batch=16, length=256):
    g = np.random.default_rng(seed)
    torch.manual_seed(seed)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    V = net.cfg["V"]
    loss = torch.tensor(float("nan"))
    for _ in range(steps):
        tok = torch.tensor(np.array([sample(Tm, E, length + 1, g) for _ in range(batch)]))
        logits, _ = net(tok[:, :-1])
        loss = F.cross_entropy(logits.reshape(-1, V), tok[:, 1:].reshape(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
    return float(loss)


def base_model(steps=3000, seed=0, **cfg):
    """A trained base model, cached on disk (results/tlab)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = "_".join(f"{k}{v}" for k, v in sorted(cfg.items())) or "default"
    path = CACHE / f"base_{key}_steps{steps}_seed{seed}.pt"
    torch.manual_seed(seed)
    net = Net(**cfg)
    if steps == 0:
        return net, float("nan")
    if path.exists():
        d = torch.load(path)
        net.load_state_dict(d["state"])
        return net, d["loss"]
    Tm, E = hmm()
    loss = train(net, Tm, E, steps, seed)
    torch.save({"state": net.state_dict(), "loss": loss}, path)
    return net, loss
