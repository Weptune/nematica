"""Lab I amendment (5 Nov 2026): how strong is off-target activation in lab brains, measured the
way it was measured in worms (scripts/diag_offtarget_crosstalk.py)? For each poke whose target's
early change (frames 0-3 after onset minus the 20 before, resting-SD units) is between 1 and 4:
the two fixed neighbours' mean early change minus the mean over all other seen units, divided by
the target's early change. Worms: nearest neighbour 0.31, 2nd and 3rd 0.21 (stimulation), 0.06
and 0.04 after spontaneous rises. Usage: NEMATICA_OFFTARGET=a python scripts/calib_offtarget_lab.py
"""
import os
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.argv = [sys.argv[0]]
import run_ann_imperfect as I  # noqa: E402  (reads NEMATICA_OFFTARGET)
L = I.L
L.KICK = 6.0
L.KICK_FRAMES = 8
br0 = L.make_brain(rho=1.3, share=0.05, tau=90.0, seed=0, q=0.2)
hidden = L.design(br0.n, np.random.default_rng(200))
rng = np.random.default_rng(7)
num, den, n = 0.0, 0.0, 0
for i in range(30):
    ind = L.individual(br0, 0.3, 1000 + i)
    rec = L.atlas_recording(ind, rng, hidden, f"ind{i:02d}")
    X, T = rec.x, rec.n_frames
    units = [int(nm[1:]) for nm in rec.names]
    pos = {u: j for j, u in enumerate(units)}
    m = np.ones(T, bool)
    for f in rec.all_stim_frames:
        m[f:f + 60] = False
    sd = np.nanstd(np.where(m, X, np.nan), axis=1)
    for k, f in rec.stims:
        if f < 20:
            continue
        e = (X[:, f:f + 4].mean(axis=1) - X[:, f - 20:f].mean(axis=1)) / sd
        if not (1 < e[k] < 4):
            continue
        nb = [pos[u] for u in I.NEIGH[units[k]] if u in pos]
        if not nb:
            continue
        rest = [j for j in range(len(units)) if j != k and j not in nb]
        num += np.mean(e[nb]) - np.mean(e[rest]); den += e[k]; n += 1
print(f"off-target {os.environ.get('NEMATICA_OFFTARGET')}: pokes {n}; neighbour excess / target {num / den:+.3f}")
