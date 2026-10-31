"""Nonlinear rung: a GRU over the calcium-aware state, with an optional identity per worm.

    state v_t       drive-space state (CalciumStateSpace: deconvolved drive in per-worm
                    normal scores, plus velocity and reversal), the space in which the
                    per-worm linear model passed all eight pairwise levels
    model           GRU(input v_t [+ worm identity], hidden H) -> mean and log-variance of
                    v_{t+1}; state-dependent noise is something linear models cannot do
    identity        `emb` learned numbers per TRAINING worm (0 = one shared model)
    loss            Gaussian negative log-likelihood on observed variables only, on random
                    200-frame chunks; Gaussian input noise during training keeps free-running
                    simulation stable [A]
    simulation      sample j uses training worm j's identity and drive quantiles

PyTorch is imported lazily, so the rest of NEMATICA does not depend on it.
"""

from __future__ import annotations

import time

import numpy as np

from ..bench.sample import BenchSample
from .forecasters import CalciumStateSpace


def _torch():
    import torch
    return torch


class GRUWorms:
    def __init__(self, gamma: float = 0.5, hidden: int = 128, emb: int = 8, steps: int = 2000,
                 chunk: int = 200, batch: int = 16, lr: float = 2e-3, input_noise: float = 0.1,
                 seed: int = 0, device: str | None = None, verbose: bool = False,
                 eval_every: int = 100, weight_decay: float = 1e-4, dropout: float = 0.0):
        self.gamma, self.hidden, self.emb, self.steps = gamma, hidden, emb, steps
        self.chunk, self.batch, self.lr, self.input_noise = chunk, batch, lr, input_noise
        self.seed, self.device, self.verbose = seed, device, verbose
        self.eval_every, self.weight_decay, self.dropout = eval_every, weight_decay, dropout
        self.names: list = []
        self.info: dict = {}

    @property
    def name(self) -> str:
        return f"gru{self.hidden}" + (f"_id{self.emb}" if self.emb else "_shared")

    # ---------------------------------------------------------------- network
    def _build(self, k: int, n_worms: int):
        torch = _torch()
        nn = torch.nn

        class Net(nn.Module):
            def __init__(s):
                super().__init__()
                s.emb = nn.Embedding(max(n_worms, 1), self.emb) if self.emb else None
                s.gru = nn.GRU(k + self.emb, self.hidden, batch_first=True)
                s.out = nn.Linear(self.hidden, 2 * k)

            def forward(s, x, wid, h=None):
                if s.emb is not None:
                    e = s.emb(wid)[:, None, :].expand(-1, x.shape[1], -1)
                    x = torch.cat([x, e], dim=-1)
                y, h = s.gru(x, h)
                mu, logvar = s.out(y).chunk(2, dim=-1)
                return mu, logvar.clamp(-8, 4), h

        return Net()

    # ---------------------------------------------------------------- fit
    def fit(self, train, val=None):
        torch = _torch()
        torch.manual_seed(self.seed)
        dev = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.device = dev
        self.space = CalciumStateSpace.from_train(train, gamma=self.gamma)
        enc = [self.space.encode(s) for s in train]
        self.names = [s.origin for s in train]
        k = self.space.k
        V = [torch.tensor(v.T, dtype=torch.float32) for v, _ in enc]          # (T, k)
        M = [torch.tensor(np.broadcast_to(m, (v.shape[1], k)).copy(), dtype=torch.float32) for v, m in enc]
        self.net = self._build(k, len(train)).to(dev)
        opt = torch.optim.AdamW(self.net.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        best = (np.inf, 0, None)                     # early stopping on VALIDATION worms only
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, self.steps)
        rng = np.random.default_rng(self.seed)
        t0 = time.time()
        losses = []
        for step in range(self.steps):
            wi = rng.integers(0, len(V), self.batch)
            xs, ys, ms = [], [], []
            for w in wi:
                T = V[w].shape[0]
                a = int(rng.integers(0, T - self.chunk - 1))
                xs.append(V[w][a:a + self.chunk])
                ys.append(V[w][a + 1:a + self.chunk + 1])
                ms.append(M[w][a + 1:a + self.chunk + 1])
            x, y, m = (torch.stack(z).to(dev) for z in (xs, ys, ms))
            x = x + self.input_noise * torch.randn_like(x)
            mu, logvar, _ = self.net(x, torch.tensor(wi, device=dev))
            nll = 0.5 * (logvar + (y - mu) ** 2 / logvar.exp())
            loss = (nll * m).sum() / m.sum()
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.0)
            opt.step()
            sched.step()
            losses.append(float(loss.detach()))
            if val and (step + 1) % self.eval_every == 0:
                vn = self.nll(val)
                if vn < best[0]:
                    import copy
                    best = (vn, step + 1, copy.deepcopy(self.net.state_dict()))
                if self.verbose:
                    print(f"  {self.name} step {step + 1}: train {np.mean(losses[-self.eval_every:]):.3f} val {vn:.3f}",
                          flush=True)
        if val and best[2] is None:                   # fewer steps than eval_every: score the end state
            best = (self.nll(val), self.steps, None)
        if best[2] is not None:
            self.net.load_state_dict(best[2])
        self.info = {"train_nll_final": round(float(np.mean(losses[-100:])), 4),
                     "train_seconds": round(time.time() - t0, 1), "device": dev,
                     "best_step": best[1], "val_nll": round(float(best[0]), 4) if val else None}
        return self

    # ---------------------------------------------------------------- evaluation
    def nll(self, samples) -> float:
        """Teacher-forced NLL on new worms, with the mean identity (they have none of their own)."""
        torch = _torch()
        self.net.eval()
        tot = cnt = 0.0
        with torch.no_grad():
            for s in samples:
                v, m = self.space.encode(s)
                x = torch.tensor(v.T[None, :-1], dtype=torch.float32, device=self.device)
                y = torch.tensor(v.T[None, 1:], dtype=torch.float32, device=self.device)
                mask = torch.tensor(np.broadcast_to(m, y.shape[1:]).copy()[None], dtype=torch.float32,
                                    device=self.device)
                mu, logvar = self._forward_mean_id(x)
                nll = 0.5 * (logvar + (y - mu) ** 2 / logvar.exp())
                tot += float((nll * mask).sum())
                cnt += float(mask.sum())
        self.net.train()
        return tot / cnt

    def _forward_mean_id(self, x, h=None):
        torch = _torch()
        net = self.net
        if net.emb is not None:
            e = net.emb.weight.mean(0)[None, None, :].expand(x.shape[0], x.shape[1], -1)
            x = torch.cat([x, e], dim=-1)
        y, _ = net.gru(x, h)
        mu, logvar = net.out(y).chunk(2, dim=-1)
        return mu, logvar.clamp(-8, 4)

    # ---------------------------------------------------------------- simulation
    def generate(self, template: BenchSample, rng: np.random.Generator, which: int = 0,
                 burn: int = 300, clip: float = 8.0) -> BenchSample:
        torch = _torch()
        self.net.eval()
        i = which % len(self.names)
        g = torch.Generator(device="cpu").manual_seed(int(rng.integers(0, 2**31 - 1)))
        k = self.space.k
        T = template.x.shape[1]
        out = np.empty((k, T + burn), dtype=np.float32)
        x = torch.zeros(1, 1, k, device=self.device)
        h = None
        wid = torch.tensor([i], device=self.device)
        with torch.no_grad():
            for t in range(T + burn):
                mu, logvar, h = self.net(x, wid, h)
                eps = torch.randn(mu.shape, generator=g).to(self.device)
                v = (mu + (0.5 * logvar).exp() * eps).clamp(-clip, clip)
                out[:, t] = v[0, 0].cpu().numpy()
                x = v
        self.net.train()
        s = self.space.decode(out[:, burn:].astype(float), template, self.name, source=self.names[i])
        s.name = f"{self.name}:{self.names[i]}"
        return s
