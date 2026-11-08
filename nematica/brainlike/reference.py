"""The real-worm reference: each signature measured on many random groups of 30 atlas worms (the same
number of runs the test records from a system), giving the range real worm groups span.

Built once from the local copy of the atlas (`python -m nematica.brainlike.reference`) and stored as
summary numbers only (median and percentiles per signature) in reference.json, which the test and the
website ship. No recording is included. Data: Randi et al. 2023, CC BY 4.0.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np

from .signatures import SIGNATURES, measure

REF_PATH = Path(__file__).with_name("reference.json")
GROUPS, GROUP_SIZE = 60, 30


def build(data="data/raw/randi2023_wt_npz", groups: int = GROUPS, size: int = GROUP_SIZE, seed: int = 7) -> dict:
    from ..data.pumpprobe import load_pumpprobe_dir
    from ..roles import role
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    recs = sorted(load_pumpprobe_dir(data), key=lambda r: r.uid)
    rng = np.random.default_rng(seed)
    vals = {k: [] for k in SIGNATURES + ("poked_response", "units_per_run")}
    for g in range(groups):
        pick = [recs[i] for i in sorted(rng.choice(len(recs), size=size, replace=False))]
        m = measure(pick, valid_fn=lambda c: role(c) is not None)
        for k in vals:
            vals[k].append(m[k])
        print(f"group {g + 1}/{groups}", {k: round(m[k], 3) for k in SIGNATURES}, flush=True)
    full = measure(recs, valid_fn=lambda c: role(c) is not None)
    ref = {"source": "Randi et al. 2023 signal propagation atlas (CC BY 4.0), 113 wild-type worms",
           "groups": groups, "group_size": size, "seed": seed, "all_worms": {k: full[k] for k in vals},
           "signatures": {}}
    for k, v in vals.items():
        v = np.asarray(v, float)
        v = v[np.isfinite(v)]
        ref["signatures"][k] = {"median": float(np.median(v)), "p2_5": float(np.percentile(v, 2.5)),
                                "p97_5": float(np.percentile(v, 97.5)), "p25": float(np.percentile(v, 25)),
                                "p75": float(np.percentile(v, 75)), "n": int(v.size)}
    return ref


def load() -> dict:
    return json.loads(REF_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    ref = build(*sys.argv[1:2])
    REF_PATH.write_text(json.dumps(ref, indent=1), encoding="utf-8")
    print(REF_PATH)
