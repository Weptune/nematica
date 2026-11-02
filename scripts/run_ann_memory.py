"""Artificial lab A, follow-up: is the watching cap our watchers' fault?

Two objections to lab A, tested here on one brain (seed 0), 40 hours:
  1. The kick. Lab A kicks the watchers in recorded-activity space (adds 3 to the unit's
     recorded value for 4 s), while the truth kicks the hidden state. Here every watcher is
     instead clamped: the kicked unit's recorded value is held at 0.95 (near saturation,
     as a strongly driven tanh unit is) for 4 s, the way NEMATICA clamps a stimulated
     neuron to its measured response.
  2. Memory. Lab A's recurrent watcher was trained for a fixed, small budget. Here: a
     next-frame network given the last 5 s (10 frames) of recorded activity, and the
     recurrent network trained four times longer with a larger memory.

Settings: every unit seen, hidden drives 25% (90 s); atlas-like recording with no drives;
atlas-like with drives 5% (90 s). Output: docs/figures/ann_memory.csv

Usage:  python scripts/run_ann_memory.py
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica import annlab as L  # noqa: E402

OUT = Path("docs/figures/ann_memory.csv")
CLAMP = 0.95
SETTINGS = [("every unit", 0.0, 1.0, 0.25, 90.0), ("atlas-like", 0.3, 0.5, 0.0, 10.0), ("atlas-like", 0.3, 0.5, 0.05, 90.0)]


def K_linear_clamp(recs, n, ridge=1.0):
    XtX = np.zeros((n, n, n))
    XtY = np.zeros((n, n))
    mu_s, mu_n = np.zeros(n), np.zeros(n)
    for y, obs, _ in recs:
        X = np.nan_to_num(y[:-1])
        Y = y[1:]
        G = X.T @ X
        for i in np.flatnonzero(obs):
            XtX[i] += G
            XtY[i] += X.T @ Y[:, i]
        mu_s[obs] += np.nanmean(y[:, obs], 0)
        mu_n[obs] += 1
    W = np.zeros((n, n))
    for i in range(n):
        if XtX[i].any():
            W[i] = np.linalg.solve(XtX[i] + ridge * np.eye(n), XtY[i])
    r = np.abs(np.linalg.eigvals(W)).max()
    if r > 0.999:
        W *= 0.999 / r
    mu = mu_s / np.maximum(mu_n, 1)
    K = np.zeros((n, n))
    for j in range(n):
        z = np.zeros(n)
        acc = np.zeros(n)
        for t in range(L.WIN):
            if t < L.KICK_FRAMES:
                z[j] = CLAMP - mu[j]
            acc += z
            z = W @ z
        K[:, j] = acc
    return K


def frames_from(recs, starts, hist, rng):
    out = []
    per = max(1, starts // len(recs) + 1)
    for y, obs, _ in recs:
        for t in rng.integers(hist, len(y) - 1, per):
            out.append((np.nan_to_num(y[t - hist + 1:t + 1]).astype(np.float32), obs.astype(np.float32)))
    return out[:starts]


def fit_mlp_hist(recs, n, H=10, hidden=256, steps=6000, seed=0):
    torch = L._torch()
    torch.manual_seed(seed)
    ys, ms = L._nn_data(recs, n)
    Xs, Ys, Ms = [], [], []
    for y, m in zip(ys, ms):
        T = len(y)
        idx = np.arange(H - 1, T - 1)
        lag = np.stack([y[idx - h] * m[idx - h] for h in range(H)], 1).reshape(len(idx), -1)
        Xs.append(np.concatenate([lag, m[idx]], 1))
        Ys.append(y[idx + 1])
        Ms.append(m[idx + 1])
    X, Y, M = (torch.from_numpy(np.concatenate(a)) for a in (Xs, Ys, Ms))
    net = torch.nn.Sequential(torch.nn.Linear(H * n + n, hidden), torch.nn.Tanh(), torch.nn.Linear(hidden, hidden),
                              torch.nn.Tanh(), torch.nn.Linear(hidden, n))
    opt = torch.optim.Adam(net.parameters(), 1e-3)
    g = torch.Generator().manual_seed(seed)
    for _ in range(steps):
        i = torch.randint(0, len(X), (512,), generator=g)
        pred = X[i, :n] + net(X[i])
        loss = (((pred - Y[i]) ** 2) * M[i]).sum() / M[i].sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
    net.eval()
    return net


def K_mlp_hist(net, recs, n, H=10, starts=60, rng=None):
    torch = L._torch()
    rng = rng or np.random.default_rng(0)
    K = np.zeros((n, n))
    picks = frames_from(recs, starts, H, rng)
    ar = torch.arange(n)
    with torch.no_grad():
        for seg, m in picks:
            hist = torch.from_numpy(seg[::-1].copy())[None].repeat(n + 1, 1, 1)    # newest first
            mask = torch.from_numpy(m)[None].repeat(n + 1, 1)
            hist[:, :, :] *= mask[:, None, :]
            acc = torch.zeros(n + 1, n)
            for t in range(L.WIN):
                cur = hist[:, 0]
                if t < L.KICK_FRAMES:
                    cur[ar, ar] = CLAMP
                acc += cur - cur[-1]
                nxt = cur + net(torch.cat([hist.reshape(n + 1, -1), mask], 1))
                hist = torch.cat([nxt[:, None], hist[:, :-1]], 1)
                mask = torch.ones_like(mask)
            K += acc[:n].numpy().T
    return K / len(picks)


def K_gru_clamp(net, recs, n, starts=60, warm=60, rng=None):
    torch = L._torch()
    rng = rng or np.random.default_rng(0)
    K = np.zeros((n, n))
    picks = frames_from(recs, starts, warm + 1, rng)
    ar = torch.arange(n)
    with torch.no_grad():
        for seg, m in picks:
            yseg = torch.from_numpy(seg)[None]
            mseg = torch.from_numpy(np.broadcast_to(m, seg.shape).copy())[None]
            _, h = net(yseg[:, :-1], mseg[:, :-1])
            h = h.repeat(1, n + 1, 1)
            cur = (yseg[:, -1] * mseg[:, -1]).repeat(n + 1, 1)
            mask = mseg[:, -1].repeat(n + 1, 1)
            acc = torch.zeros(n + 1, n)
            for t in range(L.WIN):
                if t < L.KICK_FRAMES:
                    cur[ar, ar] = CLAMP
                    mask[ar, ar] = 1.0
                acc += cur - cur[-1]
                nxt, h = net(cur[:, None], mask[:, None], h)
                cur = nxt[:, 0]
                mask = torch.ones_like(mask)
            K += acc[:n].numpy().T
    return K / len(picks)


def K_mlp_clamp(net, recs, n, starts=60, rng=None):
    torch = L._torch()
    rng = rng or np.random.default_rng(0)
    K = np.zeros((n, n))
    picks = frames_from(recs, starts, 1, rng)
    ar = torch.arange(n)
    with torch.no_grad():
        for seg, m in picks:
            cur = torch.from_numpy(seg[-1] * m)[None].repeat(n + 1, 1)
            mask = torch.from_numpy(m)[None].repeat(n + 1, 1)
            acc = torch.zeros(n + 1, n)
            for t in range(L.WIN):
                if t < L.KICK_FRAMES:
                    cur[ar, ar] = CLAMP
                    mask[ar, ar] = 1.0
                acc += cur - cur[-1]
                cur = cur + net(torch.cat([cur * mask, mask], 1))
                mask = torch.ones_like(mask)
            K += acc[:n].numpy().T
    return K / len(picks)


def main() -> int:
    L.KICK, L.KICK_FRAMES = 6.0, 8
    rows = []
    for label, hfrac, seen, share, tau in SETTINGS:
        t0 = time.time()
        br = L.make_brain(rho=1.3, share=share, tau=tau, seed=0, q=0.2)
        K = L.true_K(br, np.random.default_rng(100))
        hidden = L.design(br.n, np.random.default_rng(200), hfrac)
        mask = ~np.eye(br.n, dtype=bool) & ~hidden[:, None] & ~hidden[None, :]
        rng = np.random.default_rng(400)
        W = L.recordings(br, 40.0, rng, hidden, seen=seen)
        res = {"linear_add": L.score(L.K_linear(W, br.n), K, mask),
               "linear_clamp": L.score(K_linear_clamp(W, br.n), K, mask)}
        net = L.fit_mlp(W, br.n, steps=6000)
        res["mlp_add"] = L.score(L.K_mlp(net, W, br.n), K, mask)
        res["mlp_clamp"] = L.score(K_mlp_clamp(net, W, br.n), K, mask)
        nh = fit_mlp_hist(W, br.n)
        res["mlp_5s_history_clamp"] = L.score(K_mlp_hist(nh, W, br.n), K, mask)
        g = L.fit_gru(W, br.n, hidden=256, steps=6000)
        res["gru_long_clamp"] = L.score(K_gru_clamp(g, W, br.n), K, mask)
        res["gru_long_add"] = L.score(L.K_gru(g, W, br.n), K, mask)
        row = {"recording": label, "share": share, "tau": tau, "hours": 40.0, **{k: round(v, 4) for k, v in res.items()}}
        rows.append(row)
        print(row, f"({time.time() - t0:.0f} s)", flush=True)
        with OUT.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
