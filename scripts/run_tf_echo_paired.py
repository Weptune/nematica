"""Amendment 1 of "Does a transformer have the worm's narrow, lasting echo?" (README; written after the
registered test proved uninformative and before any number below was computed).

Echo = exact paired difference between a poked run and the same run unpoked, in units of each unit's
pre-poke fluctuation (deviation from its own 10-step mean, pooled over the unpoked runs); significant
above 3. Sparseness = median over pokes of the share of (non-poked) units ever significant in the 31
steps from the poke; persistence = mean run length of significance. Applied to the phase 2 small
transformers (residual and MLP readouts of the last block; s = 1, 3, 10 natural SDs) and, as a method
control, to the base recurrent lab brain of run_ladder.py (twin runs from visited states; the ladder's
kick, 6 per frame held 4 frames, times s = 1 and 3), 3 individuals each.

Usage:  python scripts/run_tf_echo_paired.py
Output: docs/figures/tf_echo_paired.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica import tlab as T  # noqa: E402
from nematica import annlab as LA  # noqa: E402
import run_tlab_depth as D  # noqa: E402
import run_ladder as LD  # noqa: E402

OUT = ROOT / "docs" / "figures" / "tf_echo_paired.csv"
POKES, F, PRE, POST, LEN = 256, 100, 10, 31, 160
torch.set_num_threads(2)


def echo_measures(poked, unpoked, exclude):
    """poked, unpoked: (pokes, PRE + POST, units); exclude: unit index per poke or None."""
    pre = unpoked[:, :PRE, :]
    dev = pre - pre.mean(axis=1, keepdims=True)
    noise = dev.reshape(-1, dev.shape[-1]).std(axis=0)
    ok = noise > 1e-12
    R = (poked[:, PRE:, :] - unpoked[:, PRE:, :]) / np.where(ok, noise, 1.0)
    ever, runs = [], []
    for p in range(len(R)):
        keep = ok.copy()
        if exclude is not None and exclude[p] is not None:
            keep[exclude[p]] = False
        B = np.abs(R[p][:, keep]) > 3                          # (steps, units)
        ever.append(B.any(axis=0).mean())
        for col in B.T:
            n = 0
            for v in col:
                if v:
                    n += 1
                elif n:
                    runs.append(n)
                    n = 0
            if n:
                runs.append(n)
    return float(np.median(ever)), float(np.mean(runs)) if runs else 0.0, float(np.median(runs)) if runs else 0.0


def transformer_runs(net, Tm, E, s, readout, seed):
    g = np.random.default_rng(seed)
    L, Dm = net.cfg["L"], net.cfg["D"]
    toks = torch.tensor(np.array([T.sample(Tm, E, LEN, g) for _ in range(POKES)]))
    with torch.no_grad():
        rec0 = net(toks)[1]
    sd = rec0[("resid", 0)].reshape(-1, Dm).std(0)
    dims = g.integers(Dm, size=POKES)
    z = torch.zeros(POKES, LEN, Dm)
    z[torch.arange(POKES), F, torch.tensor(dims)] = s * sd[torch.tensor(dims)]
    with torch.no_grad():
        rec = net(toks, {("resid", 0): z})[1]
    key = (readout, L - 1)
    a = rec[key][:, F - PRE:F + POST, :].numpy()
    b = rec0[key][:, F - PRE:F + POST, :].numpy()
    excl = [int(d) for d in dims] if readout == "resid" else None
    return a, b, excl


def rnn_runs(br, s, seed):
    """Twin runs of a lab brain from visited states; shared noise, the ladder's held kick."""
    rng = np.random.default_rng(seed)
    n = br.n
    x = np.zeros(n)
    states = []
    for t in range(400 + POKES * 25):
        x = br.step(x, None, rng.standard_normal(n))
        if t >= 400 and (t - 400) % 25 == 0:
            states.append(x.copy())
    a = np.empty((POKES, PRE + POST, n))
    b = np.empty_like(a)
    excl = []
    for p, x0 in enumerate(states[:POKES]):
        j = int(rng.integers(n))
        excl.append(j)
        eps = rng.standard_normal((PRE + POST, n))
        meas = br.r * rng.standard_normal((PRE + POST, n))
        xa, xb = x0.copy(), x0.copy()
        for t in range(PRE + POST):
            xa = br.step(xa, None, eps[t])
            xb = br.step(xb, None, eps[t])
            if PRE <= t < PRE + LD.KICK_FRAMES:
                xa[j] += LD.KICK * s
            a[p, t] = np.tanh(xa) + meas[t]
            b[p, t] = np.tanh(xb) + meas[t]
    return a, b, excl


def main():
    rows = []

    def add(**kw):
        rows.append(kw)
        print(kw, flush=True)

    br0 = LA.make_brain(rho=1.3, share=0.0, tau=90.0, seed=0, q=0.2)
    for i in range(3):
        br = LA.individual(br0, 0.3, 1000 + i)
        for s in (1.0, 3.0):
            sp, mr, md = echo_measures(*rnn_runs(br, s, seed=50 + i))
            add(system="recurrent (base lab brain)", individual=i, readout="units", strength=s,
                sparseness=round(sp, 4), persistence=round(mr, 3), median_run=md)
    Tm, E = T.hmm()
    for cond in ("untrained", "trained"):
        base, _ = T.base_model(steps=3000 if cond == "trained" else 0)
        ft = 50 if cond == "trained" else 0
        for i in range(3):
            net = D.individual(base, i, ft, Tm, E)
            for readout in ("resid", "mlp"):
                for s in (1.0, 3.0, 10.0):
                    sp, mr, md = echo_measures(*transformer_runs(net, Tm, E, s, readout, seed=1000 * i + 7))
                    add(system=f"transformer, {cond}", individual=i, readout=readout, strength=s,
                        sparseness=round(sp, 4), persistence=round(mr, 3), median_run=md)
    for r in rows:
        r["worm_like"] = bool(0.55 <= r["sparseness"] <= 0.75 and r["persistence"] >= 5.5)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
