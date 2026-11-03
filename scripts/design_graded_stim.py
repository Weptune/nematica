"""Design for the decisive experiment (3 Nov 2026, exploratory): stimulate the same neuron at
several strengths in the same animal. Does a lab detect links that are silent at rest?

Simulated in lab brains calibrated as in lab G (scripts/run_ann_calcium.py): the baseline brain
(ordinary links only) and the silent-link brain (GATED=1.5, threshold 0.98), both with 2 s
pokes, measurement noise as in the lab. In one individual, each of 6 stimulated units is poked
at 5 strengths (kick per frame 0.25, 0.5, 1, 2, 6), many trials each, 30 s apart.
Downstream response: mean over 15 s after onset minus the 5 s before, averaged over the 10
units responding most strongly at full strength.

Signature: with silent links, responses should rise steeply only at the top strengths
(convex); with ordinary links they rise and saturate (concave). Statistic: curvature
c = R(6) - 2 R(1) + R(0.25), divided by R(6). For N trials per strength, 2000 resampled
experiments estimate how often c > 0 is significant (one-sided, bootstrap over trials, p < 0.05)
in each brain: power in the silent-link brain, false alarms in the baseline brain.
Usage: python scripts/design_graded_stim.py
"""
import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("NEMATICA_SUBSTEPS", "1")
os.environ.setdefault("NEMATICA_CALCIUM", "0")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

STRENGTHS = (0.25, 0.5, 1.0, 2.0, 6.0)
HOLD, EVERY, POST, PRE = 4, 60, 30, 10
TRIALS = 60


def simulate(gated, seed=0):
    os.environ["NEMATICA_GATED"] = str(gated)
    for m in [k for k in list(sys.modules) if k in ("run_ann_calcium", "run_ann_ruler_stitch", "run_ann_ruler",
                                                    "nematica.annlab")]:
        del sys.modules[m]
    import run_ann_calcium as C
    L = C.L
    L.KICK_FRAMES = HOLD
    br = L.make_brain(rho=1.3, share=0.05, tau=90, seed=0, q=0.2)
    ind = L.individual(br, 0.3, 1000 + seed)
    rng = np.random.default_rng(seed)
    obs = np.ones(ind.n, bool)
    units = rng.choice(ind.n, 6, replace=False)
    out = {}
    for u in units:
        sched = [(s, t) for s in STRENGTHS for t in range(TRIALS)]
        rng.shuffle(sched)
        frames = EVERY * (len(sched) + 1)
        kicks = {EVERY * (i + 1): int(u) for i in range(len(sched))}
        # per-trial strength: record() reads L.KICK, so run the recording in chunks of one trial
        y_all, strength = [], []
        x_state = None
        resp = {s: [] for s in STRENGTHS}
        for i, (s, _) in enumerate(sched):
            L.KICK = s
            y = L.record(ind, rng, obs, {PRE + 20: int(u)}, frames=PRE + 20 + POST + 5, burn=60 if i else 400)
            f = PRE + 20
            resp[s].append(y[f:f + POST].mean(0) - y[f - PRE:f].mean(0))
        R = {s: np.array(v) for s, v in resp.items()}          # trials x units
        top = np.argsort(-np.abs(R[6.0].mean(0)))
        top = [j for j in top if j != u][:10]
        sign = np.sign(R[6.0].mean(0)[top])
        out[int(u)] = {s: (R[s][:, top] * sign).mean(1) for s in STRENGTHS}   # per-trial response
    return out


def curvature(r):
    return (r[6.0] - 2 * r[1.0] + r[0.25]) / r[6.0]


def power(per_trial, n, reps=2000, rng=None):
    rng = rng or np.random.default_rng(1)
    hits = 0
    for _ in range(reps):
        sample = {s: rng.choice(v, n) for s, v in per_trial.items()}
        boot = []
        for _ in range(200):
            b = {s: rng.choice(v, n).mean() for s, v in sample.items()}
            boot.append(curvature(b))
        hits += np.mean(np.array(boot) <= 0) < 0.05
    return hits / reps


def main():
    for label, g in (("baseline brain", 0.0), ("silent-link brain", 1.5)):
        sims = simulate(g)
        print(f"{label}:")
        for u, r in sims.items():
            means = [r[s].mean() for s in STRENGTHS]
            c = curvature({s: r[s].mean() for s in STRENGTHS})
            pw = {n: power(r, n, reps=300) for n in (5, 10, 20)}
            print(f"  unit {u:3d}: response by strength " + " / ".join(f"{m:+.3f}" for m in means)
                  + f"; curvature {c:+.2f}; detected (p<0.05) with 5/10/20 trials per strength: "
                  + " / ".join(f"{pw[n]:.2f}" for n in (5, 10, 20)))


if __name__ == "__main__":
    main()
