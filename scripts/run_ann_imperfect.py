"""Artificial lab I: can the worm experiment's own imperfections make an artificial brain look
like a worm? (pre-registered 5 Nov 2026; README, "Lab I: the worm experiment's imperfections").

Lab D's decisive check (scripts/run_ann_ruler_stitch.py: 113 individuals, sigma 0.3, drives 5%,
atlas-format recordings, first poke at frame 230, kick 6 held 8 frames, the unchanged ruler),
with imperfections of the real experiment added one at a time and all together:

  NEMATICA_POOL=1       class pooling: units 2k and 2k+1 form one class (like left/right
                        neurons pooled in the atlas); copies and scoring see classes only
  NEMATICA_MISID=f      misidentification: in every recording, a random fraction f of the seen
                        units have their class labels shuffled among themselves (a stimulated
                        unit can be among them)
  NEMATICA_OFFTARGET=a  off-target stimulation: every unit has two fixed neighbours (the same in
                        every individual, like anatomy); a poke also kicks them at a times the
                        kick; copies are told only the intended target

Usage:
  NEMATICA_LEAD=230 NEMATICA_OFFTARGET=0.5 python scripts/run_ann_imperfect.py --n 113 --folds 0 --out ...
"""
from __future__ import annotations

import os
import sys
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_ann_ruler_stitch as RS  # noqa: E402  (patches make_model and atlas_recording)

L = RS.L
R = RS.R
POOL = os.environ.get("NEMATICA_POOL", "0") == "1"
MISID = float(os.environ.get("NEMATICA_MISID", "0"))
OFF = float(os.environ.get("NEMATICA_OFFTARGET", "0"))
NEIGH = np.random.default_rng(4242).integers(0, 120, size=(120, 2))   # fixed "anatomy"
for i in range(120):
    while i in NEIGH[i]:
        NEIGH[i] = np.random.default_rng(4242 + i).integers(0, 120, size=2)

_record = L.record


def record(br, rng, obs, kicks=None, frames=L.FRAMES, burn=400):
    if not OFF or not kicks:
        return _record(br, rng, obs, kicks, frames=frames, burn=burn)
    n = br.n
    k = 0 if br.D is None else br.D.shape[1]
    x, s = np.zeros(n), np.zeros(k)
    y = np.full((frames, n), np.nan)
    active = {f + d: j for f, j in kicks.items() for d in range(L.KICK_FRAMES)}
    for t in range(-burn, frames):
        s = br.drive_step(s, rng)
        x = br.step(x, s, rng.standard_normal(n))
        if t in active:
            j = active[t]
            x[j] += L.KICK
            x[NEIGH[j]] += OFF * L.KICK
        if t >= 0:
            v = np.tanh(x) + br.r * rng.standard_normal(n)
            y[t, obs] = v[obs]
    return y


L.record = record
_as_pp = L.as_pumpprobe
_counter = [0]


def as_pumpprobe(y, obs, kicks, uid):
    out = _as_pp(y, obs, kicks, uid)
    units = [int(nm[1:]) for nm in out.names]
    cls = [f"C{u // 2:03d}" if POOL else f"U{u:03d}" for u in units]
    if MISID > 0 and len(cls) > 1:
        _counter[0] += 1
        rng = np.random.default_rng(zlib.crc32(uid.encode()) + 7919 * _counter[0])
        pick = np.flatnonzero(rng.random(len(cls)) < MISID)
        if len(pick) > 1:
            perm = rng.permutation(pick)
            cls = list(cls)
            orig = [cls[i] for i in pick]
            for i, p in zip(perm, orig):
                cls[i] = p
    out.classes = cls
    return out


L.as_pumpprobe = as_pumpprobe
L.true_K = lambda br, rng, *a, **kw: np.full((br.n, br.n), np.nan)
R.mean_echo = lambda *a, **kw: np.full((120, 120), np.nan)

if __name__ == "__main__":
    if not any(a.startswith("--copies") for a in sys.argv):
        sys.argv += ["--copies", "another_individual,var3_spontaneous,stitch3_hp,hybrid_kernels"]
    raise SystemExit(R.main())
