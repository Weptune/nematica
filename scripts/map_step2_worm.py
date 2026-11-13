"""Step 2 for the worm map (docs/MAP.md, amendment 13): calibration at the baseline worms' instrument
numbers (median over the 14 baseline worms of R2), measured as the worms are: 1,600-frame crops, detrended.
Writes docs/figures/map_step2_worm.json; the worm map uses the measurements that pass here."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_calibrate as cal  # noqa: E402


def worm_profile():
    d = json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"]["R2"]["individuals"]
    rows = [r for r in d if r.get("kind") == "baseline" and "error" not in r]
    p = {k: float(np.median([r[k] for r in rows])) for k in ("decay_over_tau", "frames_per_tau", "noise")}
    return p | {"crop_len": 1600, "n_worms": len(rows)}


def main():
    prof = worm_profile()
    out = ROOT / "docs/figures/map_step2_worm.json"
    cal.main(profiles={"native": {"-": None}, "calcium": {"R2": prof}}, out_path=out, cache_tag="_worm")
    d = json.loads(out.read_text())
    d["worm_profile"] = prof
    d["worm_set"] = d["used"]["calcium/R2"]
    out.write_text(json.dumps(d, indent=1))
    print("worm profile", prof, "set", d["worm_set"])


if __name__ == "__main__":
    main()
