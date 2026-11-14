"""Step 2 for the Allen Neuropixels mice (amendment 24): exactly scripts/map_step2_r4g.py (groups of 8,
480-unit synthetic systems, 5,000-timescale crops), at R4a's median single-unit instrument numbers.
Writes docs/figures/map_step2_r4a.json."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_calibrate as cal  # noqa: E402
import map_step2_r4g as S2  # noqa: E402
from map_ais_r4a import r4a_profile  # noqa: E402


def main():
    out = ROOT / "docs/figures/map_step2_r4a.json"
    prof = r4a_profile(with_crop=True)
    sweep = {m: (par, lv, sign, {**fx, "N": S2.N_SYNTH}) for m, (par, lv, sign, fx) in cal.SWEEP.items()}
    cal.C4_BASE = {"N": S2.N_SYNTH}
    cal.MAX_T, cal.UNIT_SAMPLES, cal.BIG_TAU = 330000, 1.6e8, 12
    c4 = {"samples_per_tau": cal.C4["samples_per_tau"], "population": [480, 960, 2400]}
    cal.main(profiles={"native": {"-": None}, "spikes": {"R4a": prof}}, out_path=out, cache_tag="_r4a",
             c4=c4, sweep=sweep)
    d = json.loads(out.read_text())
    d["r4a_profile"] = prof
    d["r4a_set"] = d["used"]["spikes/R4a"]
    out.write_text(json.dumps(d, indent=1))
    print("R4a set", d["r4a_set"])


if __name__ == "__main__":
    main()
