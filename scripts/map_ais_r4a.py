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
_h = hashlib.sha256()                                  # review 16, item 4: every file that shapes an R4a result
for _f in ("scripts/map_ais_r4a.py", "scripts/map_ais_big.py", "scripts/map_ais_fast_lowmem.py",
           "scripts/map_step2_r4g.py"):
    _h.update((ROOT / _f).read_bytes())
WRAPPER = _h.hexdigest()[:16]
A1_STEPS = 260_000          # review 16, item 8: two non-overlapping stretches per instance at R4a


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
    specs = dict(AIS.R4G_SPECS)
    specs["A1"] = lambda: [AIS.zoo.random_rnn(n=480, seed=s, steps=A1_STEPS)[:2] for s in range(3)]
    AIS.builder = lambda aid, pid: (("shared", specs[aid]) if aid in specs else None) \
        if pid == PID else old_builder(aid, pid)


def stamp(aid, t0):
    """Only a result written by this run is stamped (review 16, item 4), with the profile it was matched to."""
    f = AIS.CACHE / f"{aid}_{PID}.pkl"
    if f.exists() and f.stat().st_mtime >= t0:
        r = pickle.loads(f.read_bytes())
        r["r4a_wrapper_sha256_16"] = WRAPPER
        r["r4a_profile"] = r4a_profile(True)
        f.write_bytes(pickle.dumps(r))


def transfer(ids, recs=2):
    """Amendment 25 (review 16, item 3): A1 recorded (no budget) at single mice's own instrument numbers.
    Results: data/cache/map_ais/A1_R4a_at_<mouse>.pkl."""
    from nematica.map import pipeline
    d = json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"][PID]["individuals"]
    rows = {r["id"]: r for r in d}
    acts = None
    for mid in ids:
        f = AIS.CACHE / f"A1_{PID}_at_{mid}.pkl"
        if f.exists() and pickle.loads(f.read_bytes()).get("r4a_wrapper_sha256_16") == WRAPPER:
            continue
        if acts is None:
            inst = AIS.builder("A1", PID)[1]()
            acts, segs = [a for a, _ in inst], [g for _, g in inst]
        m = rows[mid]
        prof = {k: m[k] for k in ("bins_per_tau", "count_per_bin", "noise", "rate_log_sd")} | {"group": S2.GROUP}
        crop = int(round(S2.CROP_TAU * m["bins_per_tau"]))
        try:
            r = pipeline.ai_at_prep(acts, "spikes", prof, segments=segs[0] or None, recs_per_instance=recs,
                                    budget=False, crop_len=crop, n_draws=AIS.N_DRAWS, max_crops=1,
                                    cross_segments=True)
        except Exception as e:  # noqa: BLE001
            r = {"values": {}, "replicates": [], "reached": False, "error": f"{type(e).__name__}: {e}"}
        r.update(code_sha256_16=AIS.code_hash(), r4a_wrapper_sha256_16=WRAPPER, mouse=mid, profile=prof,
                 crop_len=crop)
        f.write_bytes(pickle.dumps(r))
        print("A1 at", mid, r.get("reached"), {k: round(v, 3) for k, v in r.get("values", {}).items() if v == v},
              flush=True)


if __name__ == "__main__":
    setup()
    args = sys.argv[1:]
    mode = args.pop(0) if args and args[0].startswith("--") else ""
    if mode == "--big":
        import map_ais_big as B
        AIS.ai.record = B.record_lowmem
    import time
    t0 = time.time()
    if mode == "--transfer":
        transfer(args)
    elif mode == "--fast":
        import map_ais_fast as F
        import map_ais_fast_lowmem as FL
        for aid in args:
            F.TRUNC = {PID: FL.LEN[aid]}
            F.run(aid, (PID,))
            stamp(aid, t0)
    else:
        d = json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"]
        for aid in args:
            f = AIS.CACHE / f"{aid}_{PID}.pkl"
            if f.exists() and pickle.loads(f.read_bytes()).get("r4a_wrapper_sha256_16") == WRAPPER:
                continue                                 # only results stamped by this exact wrapper count
            b = AIS.builder(aid, PID)
            if b is not None:
                AIS._record(aid, "", b[1], [PID], d, "")
            stamp(aid, t0)
