"""Step 2 for the mouse (docs/MAP.md, amendments 15 and 16): calibration through the deconvolved instrument at
the mouse instrument numbers (median over the 7 mice of R5m), the frame fixed at 8.5 native timescales (frame
duration over R4's median native timescale), measured as the mice are: 3,000-frame crops, not detrended.
Writes docs/figures/map_step2_mouse.json; the mouse map uses the measurements that pass here."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_calibrate as cal  # noqa: E402

CROP_FRAMES = 3000             # amendment 16: 20 minutes at 2.5 Hz


def mouse_profile(taus_mult=1.0):
    P = json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"]
    m = P["R5m"]["median"]
    tau_r4 = float(np.median([r["tau_med_s"] for r in P["R4"]["individuals"] if "error" not in r]))
    return {"taus_per_frame": float(1.0 / m["fs"] / tau_r4) * taus_mult, "noise": m["noise"], "fs": m["fs"],
            "indicator_frames": m["indicator_frames"], "kernel_frames": m["kernel_frames"],
            "crop_len": CROP_FRAMES, "targets_reported": {k: m[k] for k in ("frames_per_tau", "zero_frac")},
            "r4_native_tau_s": tau_r4}


def main():
    prof = mouse_profile()
    out = ROOT / "docs/figures/map_step2_mouse.json"
    cal.MAX_T = 200000
    cal.BIG_TAU = 6
    c4 = {"samples_per_tau": [1.5, 3.0, 6.0], "population": [60, 300, 3000], "gain": [0.5, 1.0, 4.0]}
    cal.main(profiles={"native": {"-": None}, "deconv": {"R5m": prof}}, out_path=out, cache_tag="_mouse", c4=c4)
    d = json.loads(out.read_text())
    d["mouse_profile"] = prof
    d["mouse_set"] = d["used"]["deconv/R5m"]
    out.write_text(json.dumps(d, indent=1))
    print("mouse profile", prof, "set", d["mouse_set"])


if __name__ == "__main__":
    main()
