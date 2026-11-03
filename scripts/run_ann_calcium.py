"""Artificial lab E: is the worm's resistance to watching a property of the measurement?

Lab D found that artificial brains, recorded and scored exactly like atlas worms, can be copied
by watching nearly as well as by poking (watching copies 62-82% of the individuals' agreement,
poke-trained 75-89%), while on real worms watching copies reach 4-22% (poke-trained 76-97%).
One difference between the two is how activity is seen. The lab reads each unit directly once
per 0.5 s step. Worms are seen through a calcium indicator that responds slowly, sampled twice
a second, while neurons act faster than that. A slow, smearing measurement could hide fast
cause and effect in ongoing activity while leaving the large, sustained response to a poke
visible.

Here the lab brains run their dynamics in SUBSTEPS per 0.5 s frame (the same equations,
integrated finely: leak and drive per substep divided by SUBSTEPS, noise by sqrt(SUBSTEPS), a
poke's input spread evenly over the substeps of its frames). What a recording sees each frame:
  direct     tanh(x) at the end of the frame, plus measurement noise (the lab so far)
  calcium    a calcium trace c, c <- c * e + (1 - e) * tanh(x) every substep with
             e = exp(-dt / TAU_CA), plus measurement noise
Everything else is lab D's decisive check (scripts/run_ann_ruler_stitch.py, atlas-matched:
113 individuals, sigma 0.3, about 2 minutes unpoked then a poke every 30 s, the unchanged
ruler). Only the ruler's verdicts and echo agreements are used; the true-K columns are not
computed here (they would need the same measurement model) and are left empty.

Lab F uses the same runner with SUBSTEPS=1 and no calcium (the original lab dynamics) to test
brains whose resting activity is as smooth and low-dimensional as a worm's (lag-1
autocorrelation 0.90, participation ratio 0.11 of the recorded units in the atlas's longest
unpoked stretches; the lab so far: 0.64 and 0.43), made in two ways: unrecorded slow drives at
75% of input (--share 0.75: 0.89 and 0.11), or the network's own rank-3 global modes
(NEMATICA_LOWRANK=1.7 with --share 0.05: about 0.9 and 0.11).

Usage:
  NEMATICA_LEAD=230 NEMATICA_SUBSTEPS=5 NEMATICA_CALCIUM=0   python scripts/run_ann_calcium.py --n 113 --out ...
  NEMATICA_LEAD=230 NEMATICA_SUBSTEPS=5 NEMATICA_CALCIUM=1.5 python scripts/run_ann_calcium.py --n 113 --out ...
"""
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_ann_ruler_stitch as RS  # noqa: E402  (patches make_model and atlas_recording)

L = RS.L
R = RS.R
SUB = int(os.environ.get("NEMATICA_SUBSTEPS", "5"))
TAU_CA = float(os.environ.get("NEMATICA_CALCIUM", "0"))      # seconds; 0 = direct readout
FRAME_S = 0.5


def record(br, rng, obs, kicks=None, frames=None, burn=400):
    frames = frames or L.FRAMES
    n = br.n
    k = 0 if br.D is None else br.D.shape[1]
    x, s, c = np.zeros(n), np.zeros(k), np.zeros(n)
    y = np.full((frames, n), np.nan)
    active = {f + d: j for f, j in (kicks or {}).items() for d in range(L.KICK_FRAMES)}
    a = L.LEAK / SUB
    qn = br.q / np.sqrt(SUB)
    sd = np.exp(-FRAME_S / SUB / br.tau)
    e = np.exp(-FRAME_S / SUB / TAU_CA) if TAU_CA > 0 else 0.0
    for t in range(-burn, frames):
        j = active.get(t)
        for _ in range(SUB):
            if k:
                s = sd * s + np.sqrt(1 - sd * sd) * rng.standard_normal(k)
            inp = br.W @ np.tanh(x) + br.b + (br.D @ s if k else 0.0)
            Wg = getattr(br, "Wg", None)
            if Wg is not None:       # lab G: links that carry signal only above GATE_TH
                inp = inp + Wg @ (np.maximum(np.tanh(x) - GATE_TH, 0.0) / (1 - GATE_TH))
            x = (1 - a) * x + a * inp + qn * rng.standard_normal(n)
            if j is not None:
                x[j] += L.KICK / SUB
            r = np.tanh(x)
            c = e * c + (1 - e) * r if TAU_CA > 0 else r
        if t >= 0:
            v = c + br.r * rng.standard_normal(n)
            y[t, obs] = v[obs]
    return y


L.record = record

# Lab F: worm-like resting activity from the network's own few global modes. NEMATICA_LOWRANK=g
# adds a symmetric rank-3 component with gain g on 3 random orthonormal directions to every
# brain's wiring (individuals then vary it like any other connection).
LOWRANK = float(os.environ.get("NEMATICA_LOWRANK", "0"))
_make_brain = L.make_brain


def make_brain(*a, **kw):
    br = _make_brain(*a, **kw)
    if LOWRANK:
        rng = np.random.default_rng(11)
        U = np.linalg.qr(rng.standard_normal((br.n, 3)))[0]
        br.W = br.W + LOWRANK * (U @ U.T)
    return br


L.make_brain = make_brain

# Lab G: links that are silent in ongoing activity. NEMATICA_GATED=g adds a second sparse set of
# connections (density 0.05, weights g * N(0, 1)) that carries a unit's signal only when that
# unit exceeds GATE_TH (0.98; resting activity crosses it in about 0.3% of frames, a held poke
# drives the unit to 0.99999). Individuals vary these links like any others.
GATED = float(os.environ.get("NEMATICA_GATED", "0"))
GATE_TH = float(os.environ.get("NEMATICA_GATE_TH", "0.98"))
_make_brain2 = L.make_brain
_individual = L.individual


def make_brain_g(*a, **kw):
    br = _make_brain2(*a, **kw)
    if GATED:
        rng = np.random.default_rng(12)
        Wg = GATED * rng.standard_normal((br.n, br.n)) * (rng.random((br.n, br.n)) < 0.05)
        np.fill_diagonal(Wg, 0.0)
        br.Wg = Wg
    return br


def individual_g(br0, sigma, seed):
    ind = _individual(br0, sigma, seed)
    if getattr(br0, "Wg", None) is not None:
        rng = np.random.default_rng(seed + 777)
        ind.Wg = br0.Wg * (1 + sigma * rng.standard_normal(br0.Wg.shape))
    return ind


L.make_brain = make_brain_g
L.individual = individual_g
# the true-K and noise-averaged-echo truth columns would need this measurement model too; they
# are not used here, so they are skipped (empty) to save hours of simulation
L.true_K = lambda br, rng, *a, **kw: np.full((br.n, br.n), np.nan)
R.mean_echo = lambda *a, **kw: np.full((120, 120), np.nan)

if __name__ == "__main__":
    if not any(a.startswith("--copies") for a in sys.argv):
        sys.argv += ["--copies", "another_individual,var3_spontaneous,stitch3_hp,hybrid_kernels"]
    raise SystemExit(R.main())
