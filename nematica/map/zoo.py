"""The artificial networks of the map (docs/MAP.md, systems A1 to A5 and augmented candidate (a)).

Each function returns (activity: time x units float32, segments: list of start indices, meta). Native time
is each network's own step; the recording models handle time through the matching rule. Every family is
run as several *instances* (seeds), the units of the hierarchical bootstrap (amendment 10).
Language models (A6, A7) live in ai.py.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BOOKS = ROOT / "data/external/books"


# ---------------------------------------------------------------- A1 random rate RNN (and candidate (a))
def random_rnn(n=120, g=1.5, steps=60000, seed=0, alpha=0.2, noise=0.1, burn=2000):
    """x <- (1 - alpha) x + alpha tanh(g W x) + noise, W Gaussian with variance 1/n (chaotic for g > 1)."""
    rng = np.random.default_rng(seed)
    W = rng.normal(0, 1 / np.sqrt(n), (n, n))
    x = rng.normal(0, 1, n)
    out = np.empty((steps, n), np.float32)
    for t in range(steps + burn):
        x = (1 - alpha) * x + alpha * np.tanh(g * W @ x) + noise * rng.standard_normal(n)
        if t >= burn:
            out[t - burn] = x
    return out, [], {"family": "A1", "n": n, "g": g, "seed": seed}


def with_slow_drives(A, seed=0, share=0.4, tau_mult=50.0, k=10):
    """Augmented candidate (a), amendment 2: slow hidden drives carrying `share` of each unit's variance,
    time constant tau_mult x the network's native timescale; k Ornstein-Uhlenbeck processes through a fixed
    random projection, added to unit activity and scaled per unit."""
    from .measures import tau_med
    A = np.asarray(A, float)
    t0 = max(tau_med(A), 1.0)
    tau = tau_mult * t0 / np.log(2)                      # half-life -> 1/e time constant
    rng = np.random.default_rng(10_000 + seed)
    a = np.exp(-1 / tau)
    Z = np.zeros((len(A), k))
    z = rng.standard_normal(k)
    e = rng.standard_normal((len(A), k)) * np.sqrt(1 - a * a)
    for t in range(len(A)):
        z = a * z + e[t]
        Z[t] = z
    S = Z @ rng.normal(0, 1, (k, A.shape[1]))
    S = (S - S.mean(0)) / S.std(0)
    sd = A.std(0)
    scale = sd * np.sqrt(share / (1 - share))
    return (A + S * scale).astype(np.float32)


# ---------------------------------------------------------------- A2 task-trained RNN
def _train(model, batches, steps, lr=3e-3, seed=0):
    import torch
    torch.manual_seed(seed)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    for i in range(steps):
        loss = model.loss(*batches(i))
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
    return float(loss)


def decision_task(batch, T=60, rng=None, coh=(0.0, 0.05, 0.1, 0.2, 0.4)):
    """Perceptual decision: two noisy evidence channels for 40 steps after a 10-step fixation; the output
    (2 units) must report the larger mean during the last 10 steps."""
    rng = rng or np.random.default_rng(0)
    c = rng.choice(coh, batch) * rng.choice([-1, 1], batch)
    X = np.zeros((batch, T, 3), np.float32)
    X[:, :50, 2] = 1.0                                       # fixation cue
    ev = rng.normal(0, 1, (batch, 40, 2)) + np.stack([1 + c, 1 - c], -1)[:, None]
    X[:, 10:50, :2] = ev
    y = (c < 0).astype(np.int64)
    y[c == 0] = rng.integers(0, 2, (c == 0).sum())
    return X, y


def task_rnn(seed=0, n=128, train_steps=1500, trials=1500):
    import torch
    torch.set_num_threads(2)

    class Net(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.rnn = torch.nn.RNN(3, n, batch_first=True, nonlinearity="tanh")
            self.out = torch.nn.Linear(n, 2)

        def forward(self, x):
            h, _ = self.rnn(x)
            return h, self.out(h)

        def loss(self, X, y):
            _, o = self(X)
            return torch.nn.functional.cross_entropy(o[:, -10:].reshape(-1, 2), y.repeat_interleave(10))

    torch.manual_seed(seed)
    net = Net()
    rng = np.random.default_rng(seed)

    def batches(i):
        X, y = decision_task(64, rng=rng)
        return torch.tensor(X), torch.tensor(y)

    final = _train(net, batches, train_steps, seed=seed)
    X, y = decision_task(trials, rng=np.random.default_rng(seed + 777))
    with torch.no_grad():
        h0 = torch.zeros(1, 1, n)
        acts = []
        for i in range(trials):                          # one continuous session: trials back to back
            h, h0 = net.rnn(torch.tensor(X[i:i + 1]), h0)
            acts.append(h[0].numpy())
        _, o = net(torch.tensor(X))
        acc = float((o[:, -1].argmax(-1).numpy() == y).mean())
    return np.concatenate(acts).astype(np.float32), [], {"family": "A2", "seed": seed, "loss": final,
                                                          "accuracy": acc}


# ---------------------------------------------------------------- A3 GRU and A5 CfC on characters
def chars(n=None):
    text = "".join((BOOKS / f).read_text(errors="ignore") for f in sorted(p.name for p in BOOKS.glob("pg*.txt")))
    vocab = sorted(set(text))
    idx = np.array([vocab.index(c) for c in text[: n or len(text)]], np.int64) if n else None
    if idx is None:
        lut = {c: i for i, c in enumerate(vocab)}
        idx = np.fromiter((lut[c] for c in text), np.int64, len(text))
    return idx, len(vocab)


def _cfc_cell(torch, n_in, n):
    class CfC(torch.nn.Module):
        """Closed-form continuous-time cell (Hasani et al. 2022), unit time step:
        h' = sigmoid(-f t) * g + (1 - sigmoid(-f t)) * k, with f, g, k read from [x, h]."""
        def __init__(self):
            super().__init__()
            self.backbone = torch.nn.Sequential(torch.nn.Linear(n_in + n, n), torch.nn.Tanh())
            self.f, self.g, self.k = (torch.nn.Linear(n, n) for _ in range(3))

        def forward(self, x, h):
            z = self.backbone(torch.cat([x, h], -1))
            s = torch.sigmoid(-self.f(z))
            return s * torch.tanh(self.g(z)) + (1 - s) * torch.tanh(self.k(z))
    return CfC()


def char_net(kind="gru", seed=0, n=256, train_steps=1500, seq=128, batch=32, record_chars=200_000):
    """A3 (GRU) or A5 (CfC) trained on next-character prediction over the book sample; activity = hidden
    state over `record_chars` held-out characters, run continuously."""
    import torch
    torch.set_num_threads(2)
    data, V = chars()
    split = len(data) - record_chars
    torch.manual_seed(seed)
    emb = torch.nn.Embedding(V, 32)
    cell = torch.nn.GRUCell(32, n) if kind == "gru" else _cfc_cell(torch, 32, n)
    head = torch.nn.Linear(n, V)
    params = list(emb.parameters()) + list(cell.parameters()) + list(head.parameters())
    opt = torch.optim.Adam(params, lr=2e-3)
    rng = np.random.default_rng(seed)
    for i in range(train_steps):
        s = rng.integers(0, split - seq - 1, batch)
        xb = torch.tensor(np.stack([data[a:a + seq] for a in s]))
        yb = torch.tensor(np.stack([data[a + 1:a + seq + 1] for a in s]))
        h = torch.zeros(batch, n)
        e = emb(xb)
        loss = 0
        for t in range(seq):
            h = cell(e[:, t], h)
            loss = loss + torch.nn.functional.cross_entropy(head(h), yb[:, t])
        loss = loss / seq
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
    with torch.no_grad():
        x = torch.tensor(data[split:])
        e = emb(x)
        h = torch.zeros(1, n)
        out = np.empty((len(x), n), np.float32)
        for t in range(len(x)):
            h = cell(e[t:t + 1], h)
            out[t] = h[0].numpy()
    return out, [], {"family": "A3" if kind == "gru" else "A5", "seed": seed, "train_loss": float(loss)}


# ---------------------------------------------------------------- A4 spiking network
def lif_network(seed=0, n=1000, frac_e=0.8, p=0.1, seconds=300.0, dt=0.0005, step=0.005,
                adaptation=False):
    """Leaky integrate-and-fire network, excitatory and inhibitory (Brunel-style, inhibition-dominated),
    driven by external Poisson input; activity = spike counts per 5 ms native step."""
    rng = np.random.default_rng(seed)
    ne = int(n * frac_e)
    tau_m, v_th, v_r, t_ref = 0.02, 1.0, 0.0, 0.002
    J, g = 0.02, 5.0
    W = (rng.random((n, n)) < p).astype(np.float32)
    np.fill_diagonal(W, 0)
    W[:, :ne] *= J
    W[:, ne:] *= -g * J
    nu_ext = 1.1 * v_th / (J * p * ne * tau_m)               # suprathreshold drive (asynchronous state)
    lam = nu_ext * p * ne * dt
    v = rng.random(n) * v_th
    ref = np.zeros(n)
    a = np.zeros(n)
    per = int(round(step / dt))
    steps = int(seconds / step)
    out = np.zeros((steps, n), np.float32)
    for t in range(steps * per):
        I = J * rng.poisson(lam, n)
        v += dt / tau_m * (-v) + I - a
        v[ref > 0] = v_r
        ref -= dt
        s = np.flatnonzero(v >= v_th)
        if len(s):
            v[s] = v_r
            ref[s] = t_ref
            v += W[:, s].sum(1)
            out[t // per, s] += 1
            if adaptation:
                a[s] += 0.002
        if adaptation:
            a *= np.exp(-dt / 0.2)
    return out, [], {"family": "A4", "seed": seed, "adaptation": adaptation, "rate_hz": float(out.mean() / step)}
