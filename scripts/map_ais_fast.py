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


def run(aid):
    import json
    d = json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"]
    rt, prof = AIS.profile("R2", d)
    inst = AIS.SPECS[aid][2]()
    acts = [recording.hold(np.asarray(a, np.float32), PRE_HOLD) for a, _ in inst]
    r = pipeline.ai_at_prep(acts, rt, prof, recs_per_instance=7 if aid in AIS.PAIRED else 2,
                            budget=True, crop_len=AIS.CROP_LEN["R2"], n_draws=AIS.N_DRAWS)
    r["family"], r["role"] = AIS.SPECS[aid][0], AIS.SPECS[aid][1]
    r["code_sha256_16"] = AIS.code_hash()
    r["pre_hold"] = PRE_HOLD
    (AIS.CACHE / f"{aid}_R2.pkl").write_bytes(pickle.dumps(r))
    print(aid, "reached", r["reached"], {k: round(v, 3) for k, v in r["values"].items() if v == v}, flush=True)


if __name__ == "__main__":
    for aid in sys.argv[1:] or ["A4", "A5"]:
        run(aid)
