"""Artificial lab D, decisive check: the stitched watching copy put through the exact worm
pipeline. Lab brains are recorded like atlas worms (annlab.atlas_recording: 37 min, half the
units seen, 30% never, a poke every 30 s), copies are fitted to the training individuals and
scored by the unchanged ruler (FoldRuler), as in scripts/run_ann_ruler.py, whose code is reused.
If the stitched copy passes here but fails on real worms, the worm result is not an artefact of
the pipeline's data format or metric.

Usage (atlas-matched: 113 individuals, about 2 minutes unpoked each):
  NEMATICA_LEAD=230 python scripts/run_ann_ruler_stitch.py --n 113 --share 0.05 --out docs/figures/ann_ruler_stitch_s0.05.csv
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_ann_ruler as R  # noqa: E402
from run_worm_stitch import StitchedVAR  # noqa: E402

_orig = R.make_model


def make_model(name):
    if name == "stitch3":
        return StitchedVAR(False, True)
    if name == "stitch3_hp":
        return StitchedVAR(True, True)
    return _orig(name)


R.make_model = make_model

# The atlas worms have a median of 232 usable unpoked frames (about 2 minutes) before and
# between pokes; annlab.atlas_recording pokes from frame 60, leaving about 57. With
# NEMATICA_LEAD=230 the first poke comes at frame 230, giving each simulated worm about as
# much unpoked activity as an atlas worm.
import os  # noqa: E402

from nematica import annlab as L  # noqa: E402

LEAD = int(os.environ.get("NEMATICA_LEAD", str(L.EVERY)))


def atlas_recording(br, rng, hidden, uid):
    obs = (rng.random(br.n) < 0.5) & ~hidden
    targets = np.flatnonzero(obs)
    kicks = {f: int(rng.choice(targets)) for f in range(LEAD, L.FRAMES - L.WIN, L.EVERY)}
    return L.as_pumpprobe(L.record(br, rng, obs, kicks), obs, kicks, uid)


L.atlas_recording = atlas_recording

if __name__ == "__main__":
    if not any(a.startswith("--copies") for a in sys.argv):
        sys.argv += ["--copies", "another_individual,var3_spontaneous,stitch3,stitch3_hp,hybrid_kernels"]
    raise SystemExit(R.main())
