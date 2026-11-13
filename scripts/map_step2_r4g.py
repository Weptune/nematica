"""Step 2 for species 2 under amendment 17: calibration at R4's single-unit instrument numbers with units
pooled into groups of 8 (synthetic systems of 480 units, 60 groups). Writes docs/figures/map_step2_r4g.json;
the grouped mouse map uses the measurements that pass here."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_calibrate as cal  # noqa: E402

GROUP = 8
N_SYNTH = 480


def r4g_profile():
    m = json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"]["R4"]["median"]
    return {k: m[k] for k in ("bins_per_tau", "count_per_bin", "noise", "rate_log_sd")} | {"group": GROUP}


def main():
    out = ROOT / "docs/figures/map_step2_r4g.json"
    sweep = {m: (par, lv, sign, {**fx, "N": N_SYNTH}) for m, (par, lv, sign, fx) in cal.SWEEP.items()}
    cal.C4_BASE = {"N": N_SYNTH}
    c4 = {"samples_per_tau": cal.C4["samples_per_tau"], "population": [480, 960, 2400]}
    cal.main(profiles={"native": {"-": None}, "spikes": {"R4g": r4g_profile()}}, out_path=out,
             cache_tag="_r4g", c4=c4, sweep=sweep)
    d = json.loads(out.read_text())
    d["r4g_profile"] = r4g_profile()
    d["r4g_set"] = d["used"]["spikes/R4g"]
    out.write_text(json.dumps(d, indent=1))
    print("R4 grouped set", d["r4g_set"])


if __name__ == "__main__":
    main()
