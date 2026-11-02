"""The artificial lab: nonlinear networks whose cause and effect is known exactly.

A ground-truth brain is a rate network of tanh units, per 0.5 s frame:
    x <- (1 - a) x + a (W tanh(x) + b + D s) + q * noise,      a = 0.5
    y  = tanh(x) + r * noise                                   (what a recording sees)
W is sparse and random with spectral radius `rho` (above 1 the units saturate and the
network is genuinely nonlinear). s is k slow shared drives (AR(1), timescale `tau`) that no
recording sees; their loadings D carry a fraction `share` of each unit's input variance.

True cause and effect K[i, j]: unit i's response, summed over 15 s, to a kick of unit j,
averaged over the states the brain actually visits. Measured by twin runs: from a visited
state, run the brain twice with identical noise and drives, once with x_j kicked, and take
the difference. Nothing about K is approximated.

Recorded like the atlas: 37-minute recordings, half the units seen in each, 30% never
seen, measurement noise. Watching recordings have no kicks; poking recordings kick a random
seen unit every 30 s.

Estimators of K:
  poke     mean summed response after kicks of j (no model)
  linear   VAR(1) fitted to watching recordings, kicked in silico (NEMATICA's watching copy)
  mlp      a neural network predicting the next frame from the current one, fitted to
           watching recordings, kicked in silico
  gru      a recurrent neural network (memory, so in principle able to infer slow hidden
           drives from history), fitted to watching recordings, kicked in silico
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FRAMES = 4440       # 37 min at 2 Hz
WIN = 30            # 15 s response window
EVERY = 60          # a kick every 30 s
LEAK = 0.5
KICK = 1.5
KICK_FRAMES = 1     # a kick is added to the state on this many consecutive frames


@dataclass
class Brain:
    W: np.ndarray
    b: np.ndarray
    D: np.ndarray | None
    q: float = 0.3
    r: float = 0.1
    tau: float = 10.0

    @property
    def n(self):
        return len(self.b)

    def drive_step(self, s, rng):
        if self.D is None:
            return s
        a = np.exp(-0.5 / self.tau)
        return a * s + np.sqrt(1 - a * a) * rng.standard_normal(s.shape)

    def step(self, x, s, eps):
        inp = self.W @ np.tanh(x) if x.ndim == 1 else np.tanh(x) @ self.W.T
        inp = inp + self.b
        if self.D is not None:
            inp = inp + (self.D @ s if s.ndim == 1 else s @ self.D.T)
        return (1 - LEAK) * x + LEAK * inp + self.q * eps


def make_brain(n=120, rho=1.3, density=0.1, share=0.0, k=3, tau=10.0, seed=0, W=None, b=None, q=0.3) -> Brain:
    rng = np.random.default_rng(seed)
    if W is None:
        W = rng.standard_normal((n, n)) * (rng.random((n, n)) < density)
        np.fill_diagonal(W, 0.0)
        W *= rho / np.abs(np.linalg.eigvals(W)).max()
    if b is None:
        b = 0.3 * rng.standard_normal(n)
    D = None
    if share > 0:
        # input variance per unit from the recurrent part and noise, measured on a short run
        br0 = Brain(W, b, None, q=q)
        x = np.zeros(n)
        acc = []
        for t in range(3000):
            x = br0.step(x, None, rng.standard_normal(n))
            if t > 500:
                acc.append(W @ np.tanh(x))
        base = np.var(np.array(acc), axis=0).mean() + (br0.q / LEAK) ** 2
        D = rng.standard_normal((n, k))
        D *= np.sqrt(share / (1 - share) * base / k)
    return Brain(W, b, D, q=q, tau=tau)


def record(br: Brain, rng, obs: np.ndarray, kicks: dict | None = None, frames=FRAMES, burn=400):
    n = br.n
    k = 0 if br.D is None else br.D.shape[1]
    x, s = np.zeros(n), np.zeros(k)
    y = np.full((frames, n), np.nan)
    active = {f + d: j for f, j in (kicks or {}).items() for d in range(KICK_FRAMES)}
    for t in range(-burn, frames):
        s = br.drive_step(s, rng)
        x = br.step(x, s, rng.standard_normal(n))
        if t in active:
            x[active[t]] += KICK
        if t >= 0:
            v = np.tanh(x) + br.r * rng.standard_normal(n)
            y[t, obs] = v[obs]
    return y


def true_K(br: Brain, rng, branches=40, spacing=25, burn=400) -> np.ndarray:
    """Twin runs from visited states: K[i, j] = mean over states of sum_t tanh(x_kick) - tanh(x)."""
    n = br.n
    k = 0 if br.D is None else br.D.shape[1]
    x, s = np.zeros(n), np.zeros(k)
    states, drives = [], []
    for t in range(burn + branches * spacing):
        s = br.drive_step(s, rng)
        x = br.step(x, s, rng.standard_normal(n))
        if t >= burn and (t - burn) % spacing == 0:
            states.append(x.copy())
            drives.append(s.copy())
    X0 = np.repeat(np.array(states), n, axis=0)                       # (branches*n, n)
    S = np.repeat(np.array(drives), n, axis=0) if k else np.zeros((len(X0), 0))
    J = np.tile(np.arange(n), branches)
    Xk = X0.copy()
    Xk[np.arange(len(J)), J] += KICK
    Xb = X0.copy()
    acc = np.tanh(Xk) - np.tanh(Xb)
    for t in range(1, WIN):
        eps = rng.standard_normal(X0.shape)
        S = br.drive_step(S, rng) if k else S
        Xk = br.step(Xk, S, eps)
        Xb = br.step(Xb, S, eps)
        if t < KICK_FRAMES:
            Xk[np.arange(len(J)), J] += KICK
        acc += np.tanh(Xk) - np.tanh(Xb)
    K = np.zeros((n, n))
    for j in range(n):
        K[:, j] = acc[J == j].mean(axis=0)
    return K


def design(n, rng, hidden_frac=0.3):
    return rng.random(n) < hidden_frac


def recordings(br, hours, rng, hidden, poke=False, seen=0.5):
    n_rec = max(1, int(round(hours * 3600 / (FRAMES / 2))))
    out = []
    for _ in range(n_rec):
        obs = (rng.random(br.n) < seen) & ~hidden
        kicks = None
        if poke:
            targets = np.flatnonzero(obs)
            kicks = {f: int(rng.choice(targets)) for f in range(EVERY, FRAMES - WIN, EVERY)}
        out.append((record(br, rng, obs, kicks), obs, kicks))
    return out


def K_poke(recs, n):
    tot, cnt = np.zeros((n, n)), np.zeros((n, n))
    for y, obs, kicks in recs:
        for f, j in kicks.items():
            base = y[f - 10:f].mean(axis=0)
            resp = (y[f:f + WIN] - base).sum(axis=0)
            tot[obs, j] += resp[obs]
            cnt[obs, j] += 1
    return np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)


def K_linear(recs, n, ridge=1.0):
    XtX = np.zeros((n, n, n))
    XtY = np.zeros((n, n))
    for y, obs, _ in recs:
        X = np.nan_to_num(y[:-1])
        Y = y[1:]
        G = X.T @ X
        for i in np.flatnonzero(obs):
            XtX[i] += G
            XtY[i] += X.T @ Y[:, i]
    W = np.zeros((n, n))
    for i in range(n):
        if XtX[i].any():
            W[i] = np.linalg.solve(XtX[i] + ridge * np.eye(n), XtY[i])
    r = np.abs(np.linalg.eigvals(W)).max()
    if r > 0.999:
        W *= 0.999 / r
    # response to a kick held for KICK_FRAMES frames: impulse responses summed over the hold
    K, P = np.zeros((n, n)), np.eye(n)
    for t in range(WIN):
        K += P * min(KICK_FRAMES, WIN - t)
        P = W @ P
    return K


# ------------------------------------------------------------------ neural-network watchers
def _torch():
    import torch
    import os
    torch.set_num_threads(int(os.environ.get("NEMATICA_TORCH_THREADS", "2")))
    return torch


def _nn_data(recs, n):
    ys, ms = [], []
    for y, obs, _ in recs:
        ys.append(np.nan_to_num(y).astype(np.float32))
        ms.append(np.broadcast_to(obs, y.shape).astype(np.float32))
    return ys, ms


def fit_mlp(recs, n, hidden=256, steps=3000, seed=0):
    torch = _torch()
    torch.manual_seed(seed)
    ys, ms = _nn_data(recs, n)
    X = np.concatenate([np.concatenate([y[:-1] * m[:-1], m[:-1]], 1) for y, m in zip(ys, ms)])
    Y = np.concatenate([y[1:] for y in ys])
    M = np.concatenate([m[1:] for m in ms])
    net = torch.nn.Sequential(torch.nn.Linear(2 * n, hidden), torch.nn.Tanh(), torch.nn.Linear(hidden, hidden),
                              torch.nn.Tanh(), torch.nn.Linear(hidden, n))
    opt = torch.optim.Adam(net.parameters(), 1e-3)
    Xt, Yt, Mt = map(torch.from_numpy, (X, Y, M))
    g = torch.Generator().manual_seed(seed)
    for _ in range(steps):
        idx = torch.randint(0, len(Xt), (512,), generator=g)
        if True:
            pred = Xt[idx, :n] + net(Xt[idx])
            loss = (((pred - Yt[idx]) ** 2) * Mt[idx]).sum() / Mt[idx].sum()
            opt.zero_grad()
            loss.backward()
            opt.step()
    net.eval()
    return net


def K_mlp(net, recs, n, starts=40, rng=None):
    """In-silico kicks from real recorded frames; after the first step the network's own full
    prediction is fed back as if every unit were seen."""
    torch = _torch()
    rng = rng or np.random.default_rng(0)
    ones = torch.ones(n)
    K = np.zeros((n, n))
    frames = []
    for y, obs, _ in recs:
        for t in rng.integers(0, len(y) - 1, max(1, starts // len(recs) + 1)):
            frames.append((np.nan_to_num(y[t]).astype(np.float32), obs.astype(np.float32)))
    frames = frames[:max(starts, 1)]
    with torch.no_grad():
        for y0, m0 in frames:
            base = torch.from_numpy(y0 * m0).repeat(n + 1, 1)
            mask = torch.from_numpy(m0).repeat(n + 1, 1)
            base[torch.arange(n), torch.arange(n)] += KICK * 0.5     # kick in recorded units
            mask[torch.arange(n), torch.arange(n)] = 1.0
            cur, acc = base, torch.zeros(n + 1, n)
            acc += cur - cur[-1]
            for t in range(1, WIN):
                cur = cur + net(torch.cat([cur * mask, mask], 1))
                if t < KICK_FRAMES:
                    cur[torch.arange(n), torch.arange(n)] += KICK * 0.5
                mask = ones.repeat(n + 1, 1)
                acc += cur - cur[-1]
            K += acc[:n].numpy().T
    return K / len(frames)


def fit_gru(recs, n, hidden=128, steps=1500, chunk=120, seed=0):
    torch = _torch()
    torch.manual_seed(seed)
    ys, ms = _nn_data(recs, n)

    class Net(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.gru = torch.nn.GRU(2 * n, hidden, batch_first=True)
            self.out = torch.nn.Linear(hidden, n)

        def forward(self, y, m, h=None):
            z, h = self.gru(torch.cat([y * m, m], -1), h)
            return y + self.out(z), h

    net = Net()
    opt = torch.optim.Adam(net.parameters(), 2e-3)
    chunks = []
    for y, m in zip(ys, ms):
        for s in range(0, len(y) - chunk - 1, chunk):
            chunks.append((y[s:s + chunk + 1], m[s:s + chunk + 1]))
    Yc = torch.from_numpy(np.stack([c[0] for c in chunks]))
    Mc = torch.from_numpy(np.stack([c[1] for c in chunks]))
    g = torch.Generator().manual_seed(seed)
    for _ in range(steps):
        idx = torch.randint(0, len(Yc), (32,), generator=g)
        if True:
            y, m = Yc[idx], Mc[idx]
            pred, _ = net(y[:, :-1], m[:, :-1])
            w = m[:, 1:]
            loss = (((pred - y[:, 1:]) ** 2) * w)[:, 20:].sum() / w[:, 20:].sum()   # 10 s warm-up
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
    net.eval()
    return net


def K_gru(net, recs, n, starts=40, warm=60, rng=None):
    """Warm the memory up on 30 s of real recording, then kick and roll out on its own."""
    torch = _torch()
    rng = rng or np.random.default_rng(0)
    K = np.zeros((n, n))
    picks = []
    for y, obs, _ in recs:
        for t in rng.integers(warm, len(y) - 1, max(1, starts // len(recs) + 1)):
            picks.append((np.nan_to_num(y[t - warm:t + 1]).astype(np.float32), obs.astype(np.float32)))
    picks = picks[:max(starts, 1)]
    with torch.no_grad():
        for seg, m in picks:
            yseg = torch.from_numpy(seg)[None]
            mseg = torch.from_numpy(np.broadcast_to(m, seg.shape).copy())[None]
            _, h = net(yseg[:, :-1], mseg[:, :-1])
            h = h.repeat(1, n + 1, 1)
            cur = yseg[:, -1].repeat(n + 1, 1) * mseg[:, -1].repeat(n + 1, 1)
            mask = mseg[:, -1].repeat(n + 1, 1)
            cur[torch.arange(n), torch.arange(n)] += KICK * 0.5
            mask[torch.arange(n), torch.arange(n)] = 1.0
            acc = cur - cur[-1]
            for t in range(1, WIN):
                nxt, h = net(cur[:, None], mask[:, None], h)
                cur = nxt[:, 0]
                if t < KICK_FRAMES:
                    cur[torch.arange(n), torch.arange(n)] += KICK * 0.5
                mask = torch.ones_like(mask)
                acc = acc + (cur - cur[-1])
            K += acc[:n].numpy().T
    return K / len(picks)


def score(K_hat, K, mask):
    a, b = K_hat[mask], K[mask]
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 20 or np.std(a[ok]) == 0:
        return np.nan
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


# ------------------------------------------------------------------ individuals and the ruler
def individual(br0: Brain, sigma: float, seed: int) -> Brain:
    """One individual of a species: every existing connection scaled by (1 + sigma * N(0, 1))."""
    rng = np.random.default_rng(seed)
    W = br0.W * (1 + sigma * rng.standard_normal(br0.W.shape))
    return Brain(W, br0.b.copy(), br0.D, q=br0.q, r=br0.r, tau=br0.tau)


def scrambled(br0: Brain, frac: float, seed: int) -> Brain:
    """A wrong copy: a fraction `frac` of the connections moved to other connections' places."""
    rng = np.random.default_rng(seed)
    W = br0.W.copy()
    nz = np.flatnonzero(W)
    pick = rng.choice(nz, int(round(frac * nz.size)), replace=False)
    W.flat[pick] = W.flat[rng.permutation(pick)]
    return Brain(W, br0.b.copy(), br0.D, q=br0.q, r=br0.r, tau=br0.tau)


NAMES = None


def unit_names(n):
    return [f"U{i:03d}" for i in range(n)]


def as_pumpprobe(y, obs, kicks, uid):
    """A simulated recording in the atlas's format: one row per seen unit."""
    from .data.pumpprobe import PumpProbe
    rows = np.flatnonzero(obs)
    pos = {u: i for i, u in enumerate(rows)}
    names = [f"U{u:03d}" for u in rows]
    stims = [(pos[j], f) for f, j in sorted((kicks or {}).items()) if j in pos]
    return PumpProbe(uid=uid, x=y[:, rows].T.copy(), names=names, classes=list(names), stims=stims,
                     dt=0.5, all_stim_frames=sorted((kicks or {}).keys()))


def atlas_recording(br: Brain, rng, hidden, uid):
    obs = (rng.random(br.n) < 0.5) & ~hidden
    targets = np.flatnonzero(obs)
    kicks = {f: int(rng.choice(targets)) for f in range(EVERY, FRAMES - WIN, EVERY)}
    return as_pumpprobe(record(br, rng, obs, kicks), obs, kicks, uid)


class BrainCopy:
    """A ground-truth-style brain used as a copy: poked exactly where the template was."""

    def __init__(self, br: Brain):
        self.br = br

    def fit(self, train=None, val=None):
        return self

    def simulate(self, rec, rng):
        n = self.br.n
        units = [int(nm[1:]) for nm in rec.names]
        obs = np.zeros(n, bool)
        obs[units] = True
        kicks = {f: units[k] for k, f in rec.stims}
        for f in rec.all_stim_frames:
            if f not in kicks:
                kicks[f] = units[0]
        y = record(self.br, rng, obs, kicks, frames=rec.n_frames)
        out = as_pumpprobe(y, obs, kicks, rec.uid)
        out.stims = list(rec.stims)
        out.all_stim_frames = list(rec.all_stim_frames)
        return out
