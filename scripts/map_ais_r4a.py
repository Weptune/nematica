"""AIs at the Allen Neuropixels instrument (preparation "R4a", amendment 24), without touching any file in
scripts/map_ais.py's code hash (so the worm and pooled-Stringer results stay current). This wrapper sets the
R4a profile, crop length, crop rules and the shared activity builders on map_ais at run time, then runs the
registered recording code. Results carry the hash of this wrapper too (`r4a_wrapper_sha256_16`).

Usage: python scripts/map_ais_r4a.py [AI ids]            (standard path)
       python scripts/map_ais_r4a.py --big A6-1b          (low-memory Pythia-1B path)
       python scripts/map_ais_r4a.py --fast A4 A5         (pre-held fast AIs, low-memory truncation)
"""
import hashlib
import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_ais as AIS  # noqa: E402
import map_step2_r4g as S2  # noqa: E402

PID = "R4a"
WRAPPER = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]


def r4a_profile(with_crop=False):
    m = json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"][PID]["median"]
    p = {k: m[k] for k in ("bins_per_tau", "count_per_bin", "noise", "rate_log_sd")} | {"group": S2.GROUP}
    if with_crop:
        p["crop_len"] = int(round(S2.CROP_TAU * m["bins_per_tau"]))
    return p


def setup():
    AIS.GROUPS = {"spikes": [PID]}
    AIS.CROP_LEN[PID] = r4a_profile(True)["crop_len"]
    AIS.MAX_CROPS[PID] = 1
    AIS.CROSS = set(AIS.CROSS) | {PID}
    old_profile, old_builder = AIS.profile, AIS.builder
    AIS.profile = lambda pid, d: ("spikes", r4a_profile()) if pid == PID else old_profile(pid, d)
    AIS.builder = lambda aid, pid: (("shared", AIS.R4G_SPECS[aid]) if aid in AIS.R4G_SPECS else None) \
        if pid == PID else old_builder(aid, pid)


def stamp(aid):
    f = AIS.CACHE / f"{aid}_{PID}.pkl"
    if f.exists():
        r = pickle.loads(f.read_bytes())
        r["r4a_wrapper_sha256_16"] = WRAPPER
        f.write_bytes(pickle.dumps(r))


if __name__ == "__main__":
    setup()
    args = sys.argv[1:]
    mode = args.pop(0) if args and args[0].startswith("--") else ""
    if mode == "--big":
        import map_ais_big as B
        AIS.ai.record = B.record_lowmem
    if mode == "--fast":
        import map_ais_fast as F
        import map_ais_fast_lowmem as FL
        for aid in args:
            F.TRUNC = {PID: FL.LEN[aid]}
            F.run(aid, (PID,))
            stamp(aid)
    else:
        for aid in args:
            AIS.run(aid)
            stamp(aid)
