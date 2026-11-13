"""AIs whose native timescale is undefined (activity decorrelates within one native step: A4, the
asynchronous spiking network, and A5, the CfC network) are held by 16 sub-steps before recording, the same
convention as for fast networks (recording.HOLD_TARGET x 2), and flagged as below the calibrated speed
(docs/MAP.md, amendment 13 note). Everything else is scripts/map_ais.py unchanged (same code hash).
"""
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_ais as AIS  # noqa: E402
from nematica.map import pipeline, recording  # noqa: E402

PRE_HOLD = 16
TRUNC = {"R4g": 25_000}       # amendment 17 (memory): native steps kept before the hold; a 5,000-timescale crop
                              # needs about 2,500 native steps at this hold


def run(aid, pids=("R2",)):
    import json
    d = json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"]
    built = {}
    for pid in pids:
        key, build = AIS.builder(aid, pid)              # amendment 17: R4g activity has 480 units
        if key not in built:
            built.clear()
            built[key] = [recording.hold(np.asarray(a, np.float32)[:TRUNC.get(pid)], PRE_HOLD) for a, _ in build()]
        acts = built[key]
        rt, prof = AIS.profile(pid, d)
        try:
            r = pipeline.ai_at_prep(acts, rt, prof, recs_per_instance=7 if aid in AIS.PAIRED else 2,
                                    budget=True, crop_len=AIS.CROP_LEN[pid], n_draws=AIS.N_DRAWS,
                                    max_crops=AIS.MAX_CROPS.get(pid, 4))
        except Exception as e:  # noqa: BLE001
            r = {"values": {}, "replicates": [], "reached": False, "error": f"{type(e).__name__}: {e}"}
        r["family"], r["role"] = AIS.SPECS[aid][0], AIS.SPECS[aid][1]
        r["code_sha256_16"] = AIS.code_hash()
        r["pre_hold"] = PRE_HOLD
        (AIS.CACHE / f"{aid}_{pid}.pkl").write_bytes(pickle.dumps(r))
        print(aid, pid, "reached", r["reached"], {k: round(v, 3) for k, v in r["values"].items() if v == v},
              flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    pids = tuple(args.pop(0).split("=")[1].split(",")) if args and args[0].startswith("--preps=") else ("R2",)
    for aid in args or ["A4", "A5"]:
        run(aid, pids)
