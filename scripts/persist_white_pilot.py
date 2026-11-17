"""Study 3 v0.3 design probe (before the v0.3 criteria): which white share lets the synthetic systems reach
the mice's instruments? Gain-type and additive systems at the median and noisiest instruments, seed 5
(not a calibration seed). Prints reach, recorded white share and b."""
import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("cal", ROOT / "scripts/persist_calibrate.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
from nematica.persist import measures as PM, synthetic as PS  # noqa: E402
from nematica.slow import stream as ST  # noqa: E402

ins = C.instruments()
for inst in ("median", "noisiest"):
    prof = ins[inst]["profile"]
    T = int(np.clip(round(C.BINS * C.TAU_L / prof["bins_per_tau"]), 300, 40000))
    for kind, par in (("gain", {"gain_sd": 0.3}), ("generated", {"tau_int": 10.0})):
        for white in (0.0, 0.3, 0.6):
            A, st = PS.system(np.random.default_rng(5), kind, T, white=white, **par)
            out = ST.record_stream(A, st, T, prof, 6000, 10, 200, seed=16, halves=False, max_bins=4 * C.BINS,
                                   extra=lambda rec, inc: PM.windowed_stream(rec, inc, W=8))
            w = out.get("extra") or {}
            print(inst, kind, white, out.get("reached"), round(out["numbers_on_repeats"]["noise"], 3),
                  "target", round(prof["noise"], 3), "b", round(w.get("b_drive", np.nan), 2), flush=True)
