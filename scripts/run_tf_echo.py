"""Does a transformer have the worm's narrow, lasting echo? (pre-registered 7 Nov 2026; README section of
the same name). The worm's echo measure (`event_matrices`, threshold 3, 10 positions before, 31 after)
applied to pokes of the residual stream after the first block of the phase 2 small transformers.

Usage:  python scripts/run_tf_echo.py
Output: docs/figures/tf_echo.csv
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
from nematica.bench.perturbational import event_matrices  # noqa: E402
from nematica.data.pumpprobe import PumpProbe  # noqa: E402
import run_tlab_depth as D  # noqa: E402
from run_echo_sparse import measures  # noqa: E402

OUT = ROOT / "docs" / "figures" / "tf_echo.csv"
POKES, F, PRE, POST, LEN = 256, 100, 10, 31, 160
torch.set_num_threads(2)


def recording(net, Tm, E, s, readout, seed):
    """One individual's pokes as one atlas-style recording (units x positions)."""
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
    act = rec[key][:, F - PRE:F + POST, :].numpy()               # (pokes, 41, units)
    U = act.shape[-1]
    x = np.concatenate(list(act), axis=0).T                      # (units, pokes * 41)
    names = [f"u{u}" for u in range(U)]
    if readout == "resid":
        stims = [(int(d), i * (PRE + POST) + PRE) for i, d in enumerate(dims)]
    else:
        # MLP readout: no unit shares the poked dimension's identity; mark the stimulus on a dummy row
        x = np.vstack([x, np.zeros((1, x.shape[1]))])
        names = names + [""]
        stims = [(U, i * (PRE + POST) + PRE) for i in range(POKES)]
    return PumpProbe(uid=f"tf{seed}", x=x, names=names, classes=names, stims=stims, dt=0.5,
                     all_stim_frames=[f for _, f in stims])


def main():
    Tm, E = T.hmm()
    rows = []
    for cond in ("untrained", "trained"):
        base, _ = T.base_model(steps=3000 if cond == "trained" else 0)
        ft = 50 if cond == "trained" else 0
        for i in range(3):
            net = D.individual(base, i, ft, Tm, E)
            for readout in ("resid", "mlp"):
                for s in (1.0, 3.0):
                    rec = recording(net, Tm, E, s, readout, seed=1000 * i + 7)
                    m = measures([rec])
                    row = {"condition": cond, "individual": i, "readout": readout, "strength": s,
                           "sparseness": round(m["ever_respond"], 4), "persistence": round(m["mean_run"], 3),
                           "median_run": m["median_run"], "pokes": m["pokes"],
                           "worm_like": bool(0.55 <= m["ever_respond"] <= 0.75 and m["mean_run"] >= 5.5)}
                    rows.append(row)
                    print(row, flush=True)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
