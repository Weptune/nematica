"""Task-trained networks: artificial neural networks trained to do a worm's job, never shown
a neural recording. One unit per neuron of the 279-neuron somatic nervous system, named as
in the Kunert et al. 2014 connectome, so they can be poked and read like a worm.

The task (all choices [A]; a stylised version of well-known worm behaviour):
  inputs  ASH (noxious), ALM/AVM (head touch), PLM (tail touch), AWC and ASE (smell and
          taste; the input is the change in attractant concentration)
  outputs locomotion read out from the command interneurons only (AVA, AVB, AVD, AVE, PVC,
          RIM, AIB, AIY, AIZ, RIA, SMD, RIV, RMD classes): velocity (forward +, reverse -)
          and turning
  rules   noxious or head touch: reverse for about 4 s, then a turn, then forward;
          tail touch: speed up forward; attractant falling: more turning and short
          reversals; rising: steady forward; otherwise slow forward with small wandering

Two variants: "dense" (all-to-all) and "wired" (connections only where the connectome has a
chemical or electrical synapse, plus self-connections). Dynamics, per 0.5 s frame:
    x <- (1 - a) x + a (W tanh(x) + B u + b) + noise,   a = 0.5
Activity shown to the ruler: tanh(x), filtered by a GCaMP decay of 1.5 s, plus measurement
noise [A]. Training: backpropagation through time on random episodes; weights are cached
under results/gallery_models/ and are the same for every fold (the task uses no worm data).
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np

from .score import BrainCopy

SENSORS = {"ASH": "noxious", "ALM": "head", "AVM": "head", "PLM": "tail", "AWC": "smell", "ASE": "smell"}
COMMAND = ("AVA", "AVB", "AVD", "AVE", "PVC", "RIM", "AIB", "AIY", "AIZ", "RIA", "SMD", "RIV", "RMD")
CHANNELS = ("noxious", "head", "tail", "smell")
CACHE = Path(__file__).resolve().parents[1] / "results" / "gallery_models"


def episodes(n: int, T: int, rng: np.random.Generator):
    """Random sensory episodes and the target behaviour (velocity, turning)."""
    u = np.zeros((n, T, len(CHANNELS)), np.float32)
    y = np.zeros((n, T, 2), np.float32)
    for e in range(n):
        conc = np.cumsum(rng.standard_normal(T)) * 0.05
        dc = np.diff(conc, prepend=conc[0])
        u[e, :, 3] = dc * 5
        y[e, :, 0] = 0.3 + 0.4 * np.clip(dc * 5, 0, 1)        # forward, faster up the gradient
        y[e, :, 1] = 0.1 * np.sin(np.arange(T) / 7.0 + e) + 0.6 * np.clip(-dc * 5, 0, 1)
        t = int(rng.integers(5, 25))
        while t < T - 20:
            kind = rng.choice(["noxious", "head", "tail"])
            ch = CHANNELS.index(kind)
            u[e, t:t + 2, ch] = 1.0
            if kind == "tail":
                y[e, t:t + 8, 0] = 1.0
            else:
                y[e, t:t + 8, 0] = -0.8                     # reverse about 4 s
                y[e, t + 8:t + 12, 1] = 1.0                 # then turn
            t += int(rng.integers(25, 60))
    return u, y


def connectome():
    from .systems.kunert import DATA
    from .data.pumpprobe import neuron_class
    names = ast.literal_eval((DATA / "neuron_names.txt").read_text())
    Gg = np.load(DATA / "Gg.npy")
    Gs = np.load(DATA / "Gs.npy")
    mask = ((Gg + Gs + Gg.T) > 0) | np.eye(len(names), dtype=bool)
    return names, [neuron_class(n) for n in names], mask


def train(variant: str, steps: int = 2000, seed: int = 0, log=print):
    import torch
    torch.set_num_threads(1)
    names, classes, mask = connectome()
    n = len(names)
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    M = torch.tensor(mask if variant == "wired" else np.ones((n, n), bool), dtype=torch.float32)
    # weights scaled by fan-in so one Adam step moves every unit's input by the same amount
    # in both variants (without it the dense network saturates within 50 steps)
    scale = 1.0 / np.sqrt(M.sum(1).mean().item())
    W = torch.nn.Parameter(torch.randn(n, n) * 0.9)                # effective gain 0.9: stable start
    sens = np.zeros((n, len(CHANNELS)), np.float32)
    for i, c in enumerate(classes):
        if c in SENSORS:
            sens[i, CHANNELS.index(SENSORS[c])] = 1.0
    Bmask = torch.tensor(sens)
    B = torch.nn.Parameter(torch.randn(n, len(CHANNELS)) * 0.5)
    b = torch.nn.Parameter(torch.zeros(n))
    readable = torch.tensor([c in COMMAND for c in classes], dtype=torch.float32)
    R = torch.nn.Parameter(torch.zeros(2, n))
    opt = torch.optim.Adam([W, B, b, R], lr=3e-3)
    a = 0.5
    for step in range(steps):
        u, y = episodes(16, 100, rng)
        u, y = torch.tensor(u), torch.tensor(y)
        x = torch.zeros(16, n)
        loss = 0.0
        for t in range(u.shape[1]):
            r = torch.tanh(x)
            x = (1 - a) * x + a * (r @ (W * M * scale).T + u[:, t] @ (B * Bmask).T + b) + 0.05 * torch.randn_like(x)
            out = torch.tanh(x) @ (R * readable).T
            loss = loss + ((out - y[:, t]) ** 2).mean()
        loss = loss / u.shape[1] + 1e-4 * (W * M * scale).pow(2).sum() / n
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_([W, B, b, R], 1.0)
        opt.step()
        if step % 100 == 0 or step == steps - 1:
            log(f"{variant} step {step} loss {loss.item():.4f}")
    return {"names": names, "W": (W * M * scale).detach().numpy(), "B": (B * Bmask).detach().numpy(),
            "b": b.detach().numpy(), "R": (R * readable).detach().numpy(), "final_loss": float(loss.item())}


def load_or_train(variant: str, steps: int = 2000, seed: int = 0, log=print) -> dict:
    path = CACHE / f"taskworm_{variant}_s{seed}_n{steps}_fanin.npz"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        p = train(variant, steps, seed, log)
        np.savez(path, **{k: v for k, v in p.items()})
    z = np.load(path, allow_pickle=False)
    return {k: z[k] for k in z.files}


class TaskNet(BrainCopy):
    """A task-trained network as a copy. Ongoing activity: weak random sensory input plus
    intrinsic noise (immobilised, unstimulated worms) [A]. A poke: the poked neuron held to
    its drive, scaled to its own spread [A]."""

    def __init__(self, variant: str = "wired", steps: int = 2000, seed: int = 0, noise: float = 0.05,
                 tau_ca: float = 1.5, meas: float = 0.2):
        from .data.pumpprobe import neuron_class
        self.variant, self.steps, self.seed = variant, steps, seed
        self.noise, self.tau_ca, self.meas = noise, tau_ca, meas
        self.name = f"task-{variant}"
        names, classes, _ = connectome()
        self.cell = {n.upper(): i for i, n in enumerate(names)}
        self.members = {}
        for i, c in enumerate(classes):
            self.members.setdefault(c, []).append(i)
        self._cls = neuron_class

    def fit(self, worms):
        self.p = load_or_train(self.variant, self.steps, self.seed)

    def _rows(self, name: str) -> list[int]:
        if not name:
            return []
        if name.upper() in self.cell:
            return [self.cell[name.upper()]]
        return self.members.get(self._cls(name), [])

    def run(self, worm, rng):
        if not hasattr(self, "p"):
            self.fit([])
        W, B, b = self.p["W"], self.p["B"], self.p["b"]
        n, T, burn, a = len(W), worm.n_frames, 200, 0.5
        clamp = {}
        for pk in worm.pokes:
            for i in self._rows(pk.neuron):
                for t, v in enumerate(pk.drive):
                    if np.isfinite(v):
                        clamp.setdefault(pk.frame + t, []).append((i, pk.frame, float(v)))
        x = np.zeros(n)
        hist = []
        for t in range(2 * burn):                               # settle, then measure each unit's spread
            u = 0.1 * rng.standard_normal(B.shape[1])
            x = (1 - a) * x + a * (W @ np.tanh(x) + B @ u + b) + self.noise * rng.standard_normal(n)
            if t >= burn:
                hist.append(np.tanh(x))
        spread = np.maximum(np.std(hist, axis=0), 1e-3)
        R = np.empty((n, T))
        base = {}
        for t in range(T):
            u = 0.1 * rng.standard_normal(B.shape[1])
            x = (1 - a) * x + a * (W @ np.tanh(x) + B @ u + b) + self.noise * rng.standard_normal(n)
            r = np.tanh(x)
            for i, f0, v in clamp.get(t, []):
                if (i, f0) not in base:
                    base[(i, f0)] = R[i, t - 1] if t > 0 else r[i]
                r[i] = np.clip(base[(i, f0)] + v * spread[i], -0.999, 0.999)
                x[i] = np.arctanh(r[i])
            R[:, t] = r
        k = np.exp(-worm.dt / self.tau_ca)
        ca = np.empty_like(R)
        ca[:, 0] = R[:, 0]
        for t in range(1, T):
            ca[:, t] = k * ca[:, t - 1] + (1 - k) * R[:, t]
        ca += self.meas * ca.std(axis=1, keepdims=True) * rng.standard_normal(ca.shape)
        out = np.full((len(worm.names), T), np.nan)
        for j, nm in enumerate(worm.names):
            idx = self._rows(nm)
            if idx:
                out[j] = ca[idx].mean(axis=0)
        return out
