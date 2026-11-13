"""Step 1 of the map (docs/MAP.md, amendments 4 to 6): instrument numbers only, from the real datasets.

Runs the frozen `instrument.instrument_numbers` on every individual of every preparation that can be loaded
and writes docs/figures/map_step1.json: per individual and per preparation the aggregates it returns
(timescale in seconds, samples per timescale, noise share, decay ratio at the indicator value and at twice
it, or count per bin; units; duration), never per-unit values or any measure; plus the code hash
(`instrument.code_hash` over instrument.py, measures.py, data.py and this script) and dataset identifiers.
Per-individual results are cached in data/cache/step1 (gitignored) so a restart resumes.

Usage: python scripts/map_step1.py [preparation ids, e.g. R2 R9]
"""
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.map import data, instrument  # noqa: E402

OUT = ROOT / "docs/figures/map_step1.json"
MAX_UNITS = 500          # amendment 9: instrument numbers from at most 500 randomly chosen units (memory)
CACHE = ROOT / "data/cache/step1"

PREPS = {
    "R2": {"group": "calcium", "type": "C. elegans, freely moving, in vivo", "rtype": "calcium",
           "source": "Atanas et al. 2023 (WormWideWeb release, local copy of 30 recordings)",
           "load": lambda skip: data.atanas_worms()},
    "R3": {"group": "calcium", "type": "zebrafish larva, in vivo", "rtype": "calcium",
           "source": "Chen et al. 2018, figshare 7272617 (streamed)", "load": lambda skip: data.chen_fish(skip)},
    "R4": {"group": "spikes", "type": "mouse, in vivo", "rtype": "spikes",
           "source": "Stringer et al. 2019, figshare 7739750", "load": lambda skip: data.stringer_neuropixels(skip)},
    "R6": {"group": "spikes", "type": "mouse, in vivo", "rtype": "spikes",
           "source": "Finkelstein et al., DANDI 000060", "load": lambda skip: data.finkelstein_alm(skip)},
    "R9": {"group": "spikes", "type": "rat cortical culture", "rtype": "spikes",
           "source": "DANDI 002020", "load": lambda skip: data.rat_cultures(skip)},
    "R10a": {"group": "spikes", "type": "human brain organoid", "rtype": "spikes", "source": "DANDI 001603",
             "load": lambda skip: data.organoid_sets("HO", "human organoid", skip)},
    "R10b": {"group": "spikes", "type": "mouse brain organoid", "rtype": "spikes", "source": "DANDI 001603",
             "load": lambda skip: data.organoid_sets("MO", "mouse organoid", skip)},
    "R10c": {"group": "spikes", "type": "mouse neonatal slice", "rtype": "spikes", "source": "DANDI 001603",
             "load": lambda skip: data.organoid_sets("slice", "mouse slice", skip)},
    "R10d": {"group": "spikes", "type": "rat cortical culture", "rtype": "spikes", "source": "DANDI 001603",
             "load": lambda skip: data.organoid_sets("PR", "rat planar culture", skip)},
}


def run_prep(pid, spec):
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = []
    done = {p.stem[len(pid) + 1:] for p in CACHE.glob(f"{pid}_*.pkl")}
    for ind in spec["load"](done):
        f = CACHE / f"{pid}_{ind['id']}.pkl"
        if f.exists():
            r = pickle.loads(f.read_bytes())
        elif ind.get("cached"):
            continue
        elif "error" in ind:
            r = {"id": ind["id"], "error": ind["error"]}
            f.write_bytes(pickle.dumps(r))
        else:
            X = np.asarray(ind["activity"])
            if X.shape[1] > MAX_UNITS:                   # amendment 9: a seeded random subset of units
                keep = np.sort(np.random.default_rng(0).choice(X.shape[1], MAX_UNITS, replace=False))
                ind = {**ind, "activity": X[:, keep], "units_total": int(X.shape[1])}
            r = instrument.instrument_numbers(ind, spec["rtype"])
            if "units_total" in ind:
                r["units_total"] = ind["units_total"]
            r = {"id": ind["id"], "kind": ind.get("kind", ""), **r}
            if "duration_total_s" in ind:
                r["duration_total_s"] = float(ind["duration_total_s"])
            f.write_bytes(pickle.dumps(r))
        del ind
        rows.append(r)
        print(pid, r["id"], {k: round(v, 3) if isinstance(v, float) else v for k, v in r.items() if k != "id"}, flush=True)
    return rows


def main(ids):
    t0 = time.time()
    res = json.loads(OUT.read_text()) if OUT.exists() else {"preparations": {}}
    for pid in ids or PREPS:
        spec = PREPS[pid]
        rows = run_prep(pid, spec)
        prep = instrument.preparation_numbers(rows, spec["rtype"])
        extra = {k: float(np.nanmedian([r.get(k, np.nan) for r in rows if "error" not in r]))
                 for k in ("tau_med_s", "duration_tau", "n_units", "decay_over_tau_x2") if any(k in r for r in rows)}
        res["preparations"][pid] = {k: v for k, v in spec.items() if k != "load"} | {
            "individuals": rows, "median": prep | extra}
    res["provenance"] = {"code_sha256_16": instrument.code_hash(["scripts/map_step1.py"]),
                         "seconds_last_run": round(time.time() - t0)}
    OUT.write_text(json.dumps(res, indent=1, default=float))
    for pid, p in res["preparations"].items():
        print(pid, p["median"])


if __name__ == "__main__":
    main(sys.argv[1:])
