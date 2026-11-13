"""Step 2 of the map (docs/MAP.md): the calibration gate rerun at each mapped preparation's own instrument
numbers from step 1 (docs/figures/map_step1.json), through the registered matching call. Profiles: the
spike preparations that can be mapped (R4, R9, R10b, R10d: at least 3 individuals with at least 50
units; amendment 11) and the baseline worms (R2, calcium arm, descriptive). A measurement is used in a group only if it
passes (C1 >= 0.9 and every C4 ratio < 0.5) at **every** preparation's profile of that group.
Writes docs/figures/map_step2.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_calibrate as cal  # noqa: E402

SPIKE_PREPS = ["R4", "R9", "R10b", "R10d"]          # amendment 11: R10c has 2 individuals with 50+ units
CALCIUM_PREPS = ["R2"]


def profiles():
    d = json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"]
    sp = {p: {k: d[p]["median"][k] for k in ("bins_per_tau", "count_per_bin", "noise", "rate_log_sd")}
          for p in SPIKE_PREPS}
    ca = {p: {k: d[p]["median"][k] for k in ("decay_over_tau", "frames_per_tau", "noise")} for p in CALCIUM_PREPS}
    return {"native": {"-": None}, "calcium": ca, "spikes": sp}


def main():
    out = ROOT / "docs/figures/map_step2.json"
    cal.main(profiles=profiles(), out_path=out, cache_tag="_step2")
    d = json.loads(out.read_text())
    groups = {"spikes": [f"spikes/{p}" for p in SPIKE_PREPS], "calcium": [f"calcium/{p}" for p in CALCIUM_PREPS]}
    d["group_sets"] = {g: [m for m in cal.M if all(m in d["used"][k] for k in ks)] for g, ks in groups.items()}
    out.write_text(json.dumps(d, indent=1))
    print("group measurement sets:", d["group_sets"])


if __name__ == "__main__":
    main()
