"""Brain measurements for the map (docs/MAP.md). RUN ONLY AFTER step 2 and an independent review clear it.

For every individual of every loadable preparation (the step-1 loaders, the same rest stretches, at most
the first 20 minutes and at most 500 seeded random units, as for the instrument numbers), the registered
measurements (`measures.measure_matched`, 40 draws of 50 units, 150-timescale windows) and the pooled
split-half SE (5 splits; C3). Calcium recordings are detrended per segment first (amendment 5). Only
summary values are kept: data/cache/map_brains/<prep>_<id>.pkl and docs/figures/map_brains.json.

Usage: python scripts/map_brains.py [prep ids]
"""
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_step1 as s1  # noqa: E402
from nematica.map import data, instrument, measures  # noqa: E402

CACHE = ROOT / "data/cache/map_brains"
OUT = ROOT / "docs/figures/map_brains.json"


def prepare(ind, rtype):
    """The same activity instrument_numbers saw: rest stretches, unit inclusion, unit cap, detrending."""
    X, seg = instrument._rest(ind)
    if X.shape[1] > s1.MAX_UNITS:
        keep = np.sort(np.random.default_rng(0).choice(X.shape[1], s1.MAX_UNITS, replace=False))
        X = X[:, keep]
    if rtype == "calcium":
        X = measures.detrend(X, seg)
    X = instrument.include_units(X, rtype, float(ind["dt"]))
    return X, seg


def run_prep(pid):
    spec = s1.PREPS[pid]
    CACHE.mkdir(parents=True, exist_ok=True)
    done = {p.stem[len(pid) + 1:] for p in CACHE.glob(f"{pid}_*.pkl")}
    for ind in spec["load"](done):
        f = CACHE / f"{pid}_{ind['id']}.pkl"
        if ind.get("cached") or f.exists():
            continue
        if pid == "R2" and ind.get("kind") != "baseline":   # amendment 13: the 14 baseline worms only
            continue
        if "error" in ind:
            r = {"id": ind["id"], "error": ind["error"]}
        else:
            X, seg = prepare(ind, spec["rtype"])
            v = measures.measure_matched(X, seed=0, segments=seg)
            se = measures.split_half_se(X, seed=0, n_splits=5, segments=seg) if "error" not in v else {}
            r = {"id": ind["id"], "values": {m: v.get(m, np.nan) for m in measures.MEASURES},
                 "sd": {m: v.get(m + "_sd", np.nan) for m in measures.MEASURES}, "se": se,
                 "tau_med": v.get("tau_med"), "error": v.get("error"), "n_units": int(X.shape[1])}
        f.write_bytes(pickle.dumps(r))
        print(pid, r["id"], r.get("error") or {k: round(x, 3) for k, x in r["values"].items() if x == x}, flush=True)
        del ind


def main(ids):
    t0 = time.time()
    for pid in ids:
        run_prep(pid)
    res = {}
    for pid in s1.PREPS:
        rows = [pickle.loads(f.read_bytes()) for f in sorted(CACHE.glob(f"{pid}_*.pkl"))]
        if rows:
            res[pid] = {"type": s1.PREPS[pid]["type"], "group": s1.PREPS[pid]["group"], "individuals": rows}
    OUT.write_text(json.dumps({"preparations": res, "provenance": {
        "code_sha256_16": instrument.code_hash(["scripts/map_step1.py", "scripts/map_brains.py"]),
        "seconds_last_run": round(time.time() - t0)}}, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1:] or ["R2"])                    # amendment 13: the worm map only
