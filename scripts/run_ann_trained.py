"""Artificial lab H: do TRAINED networks hide their cause and effect at rest, like worms?
(pre-registered 5 Nov 2026; README, "Trained networks through the worm pipeline").

So far every artificial brain was an untrained random network, and those reveal their cause and
effect in ongoing activity well enough to be copied by watching (lab D), unlike worms. Here the
same kind of network (annlab dynamics: x <- 0.5 x + 0.5 (W tanh x + b + B u) + q noise, 120
units, the lab's sparse random wiring with 10% of connections, q = 0.2) is trained on one of two
classic tasks for trained recurrent networks, keeping the wiring mask:

  flipflop  3-bit flip-flop (Sussillo and Barak 2013): three input lines carry brief +1 / -1
            pulses; three outputs must hold the sign of the last pulse on each line (memory,
            fixed-point attractors)
  cdi       context-dependent integration (Mante et al. 2013): two noisy evidence lines and two
            context lines; the output reports the sign of the evidence named by the context,
            integrated over a 2 s window (integration, line attractors)

During recordings the network performs its task without pause: the task inputs are its
unrecorded drives (B u). The control is the identical network before training (same wiring
mask, initial weights, input weights and task inputs). Individuals scale every connection and
input weight by (1 + sigma N(0, 1)). Everything else is lab D's decisive check
(scripts/run_ann_ruler_stitch.py: 113 individuals, atlas-format recordings, first poke at frame
230, the unchanged ruler).

Usage:
  python scripts/run_ann_trained.py train --task flipflop          # trains, saves, reports accuracy
  python scripts/run_ann_trained.py sigma --task flipflop          # chooses sigma by the pre-registered rule
  NEMATICA_TASK=flipflop NEMATICA_TRAINED=1 NEMATICA_SIGMA=s NEMATICA_LEAD=230 \\
      python scripts/run_ann_trained.py ruler --n 113 --folds 0 --out docs/figures/ann_trained_flipflop_fold0.csv
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nematica import annlab as L  # noqa: E402

OUT = ROOT / "data" / "derived" / "trained"
N, Q, SEED = 120, 0.2, 0
TRIAL = 60            # cdi: 30 s per trial
EVID = (10, 50)       # cdi: evidence on from frame 10 to 50 of a trial
REPORT = (50, 60)     # cdi: report window


# ------------------------------------------------------------------ task inputs
class Task:
    def __init__(self, name, rng):
        self.name, self.rng, self.t = name, rng, 0
        self.k = 3 if name == "flipflop" else 4
        self.state = np.zeros(3)
        self._new_trial()

    def _new_trial(self):
        r = self.rng
        self.ctx = int(r.integers(2))
        self.coh = r.choice([-0.4, -0.2, -0.1, 0.1, 0.2, 0.4], size=2)

    def step(self):
        """Next input vector and target (target NaN where not scored)."""
        r = self.rng
        if self.name == "flipflop":
            u = np.zeros(3)
            hit = r.random(3) < 0.03
            u[hit] = r.choice([-1.0, 1.0], size=hit.sum())
            self.state = np.where(hit, u, self.state)
            tgt = np.where(self.state != 0, self.state, np.nan)
            return u, tgt
        ph = self.t % TRIAL
        if ph == 0:
            self._new_trial()
        u = np.zeros(4)
        u[2 + self.ctx] = 1.0
        if EVID[0] <= ph < EVID[1]:
            u[:2] = self.coh + 1.0 * r.standard_normal(2)
        tgt = np.array([np.sign(self.coh[self.ctx])]) if REPORT[0] <= ph < REPORT[1] else np.array([np.nan])
        self.t += 1
        return u, tgt


def task_batch(name, B, T, seed):
    rng = np.random.default_rng(seed)
    us, ts = [], []
    for b in range(B):
        tk = Task(name, np.random.default_rng(rng.integers(1 << 30)))
        tk.t = int(rng.integers(TRIAL)) if name == "cdi" else 0
        u, t = zip(*[tk.step() for _ in range(T)])
        us.append(np.array(u))
        ts.append(np.array(t))
    return np.array(us), np.array(ts)


# ------------------------------------------------------------------ brains
class TaskBrain(L.Brain):
    """An annlab brain whose drives are its task's inputs (D = input weights, s = task inputs)."""

    task: str = "flipflop"

    def drive_step(self, s, rng):
        if not hasattr(self, "_task") or self._task is None:
            self._task = Task(self.task, np.random.default_rng(int(rng.integers(1 << 30))))
        return self._task.step()[0]


def init_params(task):
    br = L.make_brain(n=N, rho=1.3, seed=SEED, q=Q)
    rng = np.random.default_rng(100 + SEED)
    k = 3 if task == "flipflop" else 4
    Bin = rng.standard_normal((N, k)) * (1.0 if task == "flipflop" else 0.5)
    C = rng.standard_normal((3 if task == "flipflop" else 1, N)) / np.sqrt(N)
    return dict(W=br.W, b=br.b, B=Bin, C=C, mask=(br.W != 0).astype(float))


def load_params(task, trained):
    f = OUT / f"{task}_{'trained' if trained else 'init'}.npz"
    return dict(np.load(f))


def make_task_brain(task, trained):
    p = load_params(task, trained)
    br = TaskBrain(p["W"], p["b"], p["B"], q=Q)
    br.task = task
    br._task = None
    br.C = p["C"]
    return br


def individual(br0, sigma, seed):
    rng = np.random.default_rng(seed)
    W = br0.W * (1 + sigma * rng.standard_normal(br0.W.shape))
    B = br0.D * (1 + sigma * rng.standard_normal(br0.D.shape))
    ind = TaskBrain(W, br0.b.copy(), B, q=br0.q, r=br0.r, tau=br0.tau)
    ind.task, ind._task, ind.C = br0.task, None, br0.C
    return ind


def accuracy(br, seed=0, frames=6000):
    """Task accuracy with the trained readout, noise on, as recorded."""
    rng = np.random.default_rng(seed)
    tk = Task(br.task, np.random.default_rng(seed + 1))
    x = np.zeros(br.n)
    ok, tot = 0, 0
    trial_out, trial_tgt = [], None
    for t in range(frames):
        u, tgt = tk.step()
        x = 0.5 * x + 0.5 * (br.W @ np.tanh(x) + br.b + br.D @ u) + br.q * rng.standard_normal(br.n)
        y = br.C @ np.tanh(x)
        if br.task == "flipflop":
            m = np.isfinite(tgt)
            ok += int((np.sign(y[m]) == tgt[m]).sum())
            tot += int(m.sum())
        else:
            if np.isfinite(tgt[0]):
                trial_out.append(y[0])
                trial_tgt = tgt[0]
            elif trial_out:
                ok += int(np.sign(np.mean(trial_out)) == trial_tgt)
                tot += 1
                trial_out = []
    return ok / max(tot, 1)


# ------------------------------------------------------------------ training
def train(task, iters=3000, batch=64, T=200, lr=3e-3):
    import torch
    torch.manual_seed(SEED)
    p0 = init_params(task)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez(OUT / f"{task}_init.npz", **p0)
    W = torch.tensor(p0["W"], requires_grad=True)
    b = torch.tensor(p0["b"], requires_grad=True)
    Bm = torch.tensor(p0["B"], requires_grad=True)
    C = torch.tensor(p0["C"], requires_grad=True)
    mask = torch.tensor(p0["mask"])
    opt = torch.optim.Adam([W, b, Bm, C], lr=lr)
    for it in range(iters):
        u, tg = task_batch(task, batch, T, seed=it)
        u, tg = torch.tensor(u), torch.tensor(tg)
        x = torch.zeros(batch, N, dtype=torch.float64)
        loss, cnt = 0.0, 0
        Wm = W * mask
        for t in range(T):
            x = 0.5 * x + 0.5 * (torch.tanh(x) @ Wm.T + b + u[:, t] @ Bm.T) + Q * torch.randn(batch, N, dtype=torch.float64)
            y = torch.tanh(x) @ C.T
            m = torch.isfinite(tg[:, t])
            if m.any():
                loss = loss + ((y[m] - tg[:, t][m]) ** 2).sum()
                cnt += int(m.sum())
        loss = loss / max(cnt, 1)
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_([W, b, Bm, C], 1.0)
        opt.step()
        if it % 250 == 0 or it == iters - 1:
            print(f"{task} iter {it} loss {loss.item():.4f}", flush=True)
    p = dict(W=(W * mask).detach().numpy(), b=b.detach().numpy(), B=Bm.detach().numpy(),
             C=C.detach().numpy(), mask=p0["mask"])
    np.savez(OUT / f"{task}_trained.npz", **p)
    for tr in (False, True):
        br = make_task_brain(task, tr)
        rad = np.abs(np.linalg.eigvals(br.W)).max()
        print(f"{task} {'trained' if tr else 'init'}: accuracy {accuracy(br):.3f}; spectral radius {rad:.2f}")


def choose_sigma(task):
    br0 = make_task_brain(task, True)
    sp = accuracy(br0)
    lines = [f"{task} species accuracy {sp:.3f} (chance 0.5)"]
    chosen = None
    for s in (0.3, 0.2, 0.1):
        acc = [accuracy(individual(br0, s, 1000 + i), seed=i) for i in range(10)]
        lines.append(f"sigma {s}: individuals' accuracy mean {np.mean(acc):.3f} (min {np.min(acc):.3f})")
        if chosen is None and np.mean(acc) - 0.5 >= 0.8 * (sp - 0.5):
            chosen = s
    lines.append(f"chosen sigma: {chosen}")
    print("\n".join(lines))
    (ROOT / "docs" / "figures" / f"ann_trained_{task}_sigma.txt").write_text("\n".join(lines) + "\n")


# ------------------------------------------------------------------ ruler run
def ruler():
    import run_ann_ruler_stitch as RS  # patches make_model and atlas_recording (LEAD)
    R = RS.R
    task = os.environ["NEMATICA_TASK"]
    trained = os.environ.get("NEMATICA_TRAINED", "1") == "1"
    sigma = os.environ["NEMATICA_SIGMA"]
    L.make_brain = lambda *a, **kw: make_task_brain(task, trained)
    L.individual = individual
    L.true_K = lambda br, rng, *a, **kw: np.full((br.n, br.n), np.nan)
    R.mean_echo = lambda *a, **kw: np.full((N, N), np.nan)
    sys.argv = [sys.argv[0]] + [a for a in sys.argv[2:]] + ["--sigma", sigma]
    if not any(a.startswith("--copies") for a in sys.argv):
        sys.argv += ["--copies", "another_individual,var3_spontaneous,stitch3_hp,hybrid_kernels"]
    return R.main()


if __name__ == "__main__":
    import argparse
    cmd = sys.argv[1]
    if cmd == "ruler":
        raise SystemExit(ruler())
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--task", required=True)
    ap.add_argument("--iters", type=int, default=3000)
    a = ap.parse_args()
    if cmd == "train":
        train(a.task, iters=a.iters)
    else:
        choose_sigma(a.task)
