"""A transformer through the worm measurements (pre-registered 6 Nov 2026; README "A transformer
through the same test"). Units = MLP hidden units, one token = one frame, recorded and poked like
the artificial lab, then measured on the ingredient ladder's six axes by the same code.

Usage:  python scripts/run_transformer_test.py trained|untrained
Output: docs/figures/transformer_test.csv (one row per condition)
"""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica import annlab as L  # noqa: E402
import run_ladder as LD  # noqa: E402
import run_week1 as W1  # noqa: E402

OUT = ROOT / "docs" / "figures" / "transformer_test.csv"
V, S_HID, STAY = 32, 8, 0.98
LAYERS, D, HEADS, HID, BAND = 4, 64, 4, 128, 64
N_IND, FRAMES, LEAD, EVERY = 113, 4440, 230, 60
import os
KICK_SD = float(os.environ.get("NEMATICA_TF_KICK", "3.0"))      # amended run: 10
KICK_FR = int(os.environ.get("NEMATICA_TF_FRAMES", "4"))        # amended run: 30
torch.set_num_threads(1)


# ---------------------------------------------------------------- the synthetic language
def hmm(seed=0):
    g = np.random.default_rng(seed)
    E = g.dirichlet(np.full(V, 0.3), size=S_HID)
    Tm = np.full((S_HID, S_HID), (1 - STAY) / (S_HID - 1))
    np.fill_diagonal(Tm, STAY)
    return Tm, E


def sample(Tm, E, n, g):
    s = g.integers(S_HID)
    out = np.empty(n, int)
    for t in range(n):
        out[t] = g.choice(V, p=E[s])
        s = g.choice(S_HID, p=Tm[s])
    return out


# ---------------------------------------------------------------- the network
class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(D), nn.LayerNorm(D)
        self.qkv, self.o = nn.Linear(D, 3 * D), nn.Linear(D, D)
        self.fc, self.pr = nn.Linear(D, HID), nn.Linear(HID, D)

    def attend(self, x):
        B, T, _ = x.shape
        q, k, v = self.qkv(x).split(D, -1)
        sh = lambda a: a.view(B, T, HEADS, D // HEADS).transpose(1, 2)  # noqa: E731
        q, k, v = sh(q), sh(k), sh(v)
        out = torch.empty_like(q)
        for a in range(0, T, 256):             # banded causal attention, chunked over queries
            b = min(T, a + 256)
            lo = max(0, a - BAND + 1)
            sc = q[:, :, a:b] @ k[:, :, lo:b].transpose(-1, -2) / np.sqrt(D // HEADS)
            qi = torch.arange(a, b)[:, None]
            ki = torch.arange(lo, b)[None, :]
            sc = sc.masked_fill((ki > qi) | (ki <= qi - BAND), float("-inf"))
            out[:, :, a:b] = F.softmax(sc, -1) @ v[:, :, lo:b]
        return self.o(out.transpose(1, 2).reshape(B, T, D))

    def forward(self, x, patch=None):
        x = x + self.attend(self.ln1(x))
        h = F.gelu(self.fc(self.ln2(x)))
        if patch is not None:                   # (B, T, HID) additive patch on hidden units
            h = h + patch
        return x + self.pr(h), h


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.emb = nn.Embedding(V, D)
        self.blocks = nn.ModuleList([Block() for _ in range(LAYERS)])
        self.ln, self.head = nn.LayerNorm(D), nn.Linear(D, V)

    def forward(self, tok, patches=None):
        x = self.emb(tok)
        hs = []
        for i, b in enumerate(self.blocks):
            x, h = b(x, None if patches is None else patches[i])
            hs.append(h)
        return self.head(self.ln(x)), hs


def train(net, Tm, E, steps, seed, lr=1e-3):
    g = np.random.default_rng(seed)
    torch.manual_seed(seed)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    for _ in range(steps):
        tok = torch.tensor(np.array([sample(Tm, E, 257, g) for _ in range(16)]))
        logits, _ = net(tok[:, :-1])
        loss = F.cross_entropy(logits.reshape(-1, V), tok[:, 1:].reshape(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
    return float(loss)


# ---------------------------------------------------------------- recording like the lab
def record(net, Tm, E, rng, obs, sd):
    tok = torch.tensor(sample(Tm, E, FRAMES, rng))[None]
    n = LAYERS * HID
    targets = np.flatnonzero(obs)
    kicks = {f: int(rng.choice(targets)) for f in range(LEAD, FRAMES - L.WIN, EVERY)}
    patches = [torch.zeros(1, FRAMES, HID) for _ in range(LAYERS)]
    for f, j in kicks.items():
        layer, u = divmod(j, HID)
        patches[layer][0, f:f + KICK_FR, u] += KICK_SD * sd[j]
    with torch.no_grad():
        _, hs = net(tok, patches)
    y = torch.cat([h[0] for h in hs], -1).numpy()           # (FRAMES, n)
    y = y + 0.1 * sd[None, :] * rng.standard_normal(y.shape)
    out = np.full((FRAMES, n), np.nan)
    out[:, obs] = y[:, obs]
    return out, kicks


def unit_sd(net, Tm, E):
    with torch.no_grad():
        tok = torch.tensor(sample(Tm, E, 2000, np.random.default_rng(99)))[None]
        _, hs = net(tok)
    sd = torch.cat([h[0] for h in hs], -1).numpy().std(0)
    return np.where(sd > 1e-6, sd, 1e-6)


def main():
    cond = sys.argv[1]
    t0 = time.time()
    Tm, E = hmm(0)
    torch.manual_seed(0)
    base = Net()
    loss = float("nan")
    if cond == "trained":
        loss = train(base, Tm, E, 3000, seed=0)
        print(f"base trained, loss {loss:.3f} ({(time.time() - t0) / 60:.1f} min)", flush=True)
    n = LAYERS * HID
    hidden = L.design(n, np.random.default_rng(200))
    rng = np.random.default_rng(7)
    recs, losses = [], []
    for i in range(N_IND):
        net = Net()
        net.load_state_dict(base.state_dict())
        g = torch.Generator().manual_seed(1000 + i)
        with torch.no_grad():
            for p in net.parameters():
                p.mul_(1 + 0.1 * torch.randn(p.shape, generator=g))
        if cond == "trained":
            losses.append(train(net, Tm, E, 50, seed=1000 + i, lr=3e-4))   # amended from 200
        sd = unit_sd(net, Tm, E)
        obs = (rng.random(n) < 0.5) & ~hidden
        y, kicks = record(net, Tm, E, rng, obs, sd)
        recs.append(L.as_pumpprobe(y, obs, kicks, f"ind{i:03d}"))
        if i % 20 == 0:
            print(f"individual {i} ({(time.time() - t0) / 60:.1f} min)", flush=True)
    worms = [W1.Worm(r, valid_fn=lambda c: True) for r in recs]
    fp = LD.fingerprint(worms)
    if KICK_FR != 4:
        cond = f"{cond}_kick{KICK_SD:g}x{KICK_FR}"
    row = {"condition": cond, **{k: round(v, 4) for k, v in fp.items()},
           "base_loss": round(loss, 3), "individual_loss": round(float(np.mean(losses)), 3) if losses else "",
           "minutes": round((time.time() - t0) / 60, 1)}
    rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
    rows = [r for r in rows if r["condition"] != cond] + [row]
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row))
        w.writeheader()
        w.writerows(rows)
    print(row)


if __name__ == "__main__":
    main()
