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


G_UNITS, GROUP = 2400, 8                # amendment 17: R4 pooled ("R4g")


def prepare_r4g(ind, cols=None):
    """Amendment 17: every included unit (at most 2,400, seeded subset), pooled in seeded groups of 8.
    `cols` (amendment 25): a boolean unit mask applied first (Allen QC sensitivity)."""
    from nematica.map import recording
    if cols is not None:
        ind = {**ind, "activity": np.asarray(ind["activity"])[:, cols]}
    if not ind.get("rest"):                              # memory only: the same selection on float32 counts
        X, seg = np.asarray(ind["activity"], np.float32), list(ind.get("segments") or [])
        n, dt = X.sum(0, dtype=np.float64), float(ind["dt"])
        keep = (X.std(0) > 1e-9) & (n >= instrument.MIN_SPIKES) & (n / (len(X) * dt) >= instrument.MIN_RATE_HZ)
        X = X[:, keep]
        if X.shape[1] > G_UNITS:
            X = X[:, np.sort(np.random.default_rng(0).choice(X.shape[1], G_UNITS, replace=False))]
        return recording.pool(X, GROUP, seed=0).astype(float), seg
    X, seg = instrument._rest(ind)
    X = instrument.include_units(X, "spikes", float(ind["dt"]))
    if X.shape[1] > G_UNITS:
        X = X[:, np.sort(np.random.default_rng(0).choice(X.shape[1], G_UNITS, replace=False))]
    return recording.pool(X, GROUP, seed=0), seg


CROP_TAU = 5000


def measure_r4g(ind, step1_pid="R4", cols=None):
    """Amendment 19 (review 15, item 3), primary: each mouse's pooled recording is cut into non-overlapping
    crops of 5,000 of its own timescales (timescale from the whole 20 minutes), each crop measured exactly as
    an AI crop is; the mouse's value is the mean over crops and its SE the RMS crop split-half SE over the
    square root of the number of crops. Sensitivity: the whole 20 minutes as one recording."""
    X, seg = prepare_r4g(ind, cols)
    t = measures.tau_med(X, segments=seg)
    s1r = [r for r in json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"][step1_pid]
           ["individuals"] if r["id"] == ind["id"]][0]
    L = int(round(CROP_TAU * s1r["bins_per_tau"]))          # amendment 21: as the AIs, single-unit step-1 numbers
    if step1_pid == "R4":
        cs = [(X[a:a + L], []) for a in range(0, len(X) - L + 1, L)]
    else:                                                # amendment 24: crops may span blocks (as AI crops)
        from nematica.map.pipeline import crops_across
        cs = crops_across(X, seg, L, 10 ** 6)
    vals, ses = [], []
    for j, (c, sc) in enumerate(cs):
        v = measures.measure_matched(c, seed=j, segments=sc)
        vals.append({m: v.get(m, np.nan) for m in measures.MEASURES} | {     # review 16, item 3
            "tau_used": v.get("tau_used", np.nan), "resolution_limited": v.get("resolution_limited")})
        ses.append(measures.split_half_se(c, seed=j, n_splits=5, segments=sc) if "error" not in v else {})
    k = len(cs)
    def fin(v):                                          # amendment 21: the AIs' 80%-finite rule
        v = np.array(v, float)
        return float(np.nanmean(v)) if k and np.isfinite(v).sum() >= 0.8 * k else np.nan
    mean = {m: fin([x[m] for x in vals]) for m in measures.MEASURES}
    se = {m: float(np.sqrt(np.nanmean([x.get(m, np.nan) ** 2 for x in ses]))) if k else np.nan
          for m in measures.MEASURES}                   # amendment 21: no division by sqrt(k) (groups shared)
    w = measures.measure_matched(X, seed=0, segments=seg)
    if not k and step1_pid == "R4a":                     # amendment 25 (review 16, item 6): no crop: slow memory
        ws = measures.measure_matched(X, seed=0, segments=seg, only=["slow_fraction"], window_tau=1.0)
        w = {**w, "slow_fraction_whole": ws.get("slow_fraction", np.nan)}       # over the whole recording
    return {"id": ind["id"], "values": mean, "se": se, "crops": vals, "crop_se": ses, "n_crops": k,
            "crop_len_bins": L, "tau_med_pooled": float(t), "n_groups": int(X.shape[1]),
            "whole": {m: w.get(m, np.nan) for m in measures.MEASURES} | {
                "slow_fraction_whole": w.get("slow_fraction_whole", np.nan)},
            "error": None if k else "no crop"}


def run_prep(pid):
    spec = s1.PREPS["R4" if pid == "R4g" else pid]
    CACHE.mkdir(parents=True, exist_ok=True)
    done = {p.stem[len(pid) + 1:] for p in CACHE.glob(f"{pid}_*.pkl")}
    def stale_se(f):                                    # amendment 13: SEs computed before the C3 fix are redone
        r = pickle.loads(f.read_bytes())
        return not r.get("error") and not any(np.isfinite(v) for v in r.get("se", {}).values())
    done = {d for d in done if not stale_se(CACHE / f"{pid}_{d}.pkl")}
    for ind in spec["load"](done):
        f = CACHE / f"{pid}_{ind['id']}.pkl"
        if ind.get("cached") or (f.exists() and not stale_se(f)):
            continue
        if pid == "R2" and ind.get("kind") != "baseline":   # amendment 13: the 14 baseline worms only
            continue
        if "error" in ind:
            r = {"id": ind["id"], "error": ind["error"]}
        elif pid == "R4g":
            r = measure_r4g(ind)
        elif pid == "R4a":                               # amendment 24
            r = measure_r4g(ind, "R4a")
            qc = data.allen_qc()[ind["id"]]               # amendment 25: Allen's default QC, sensitivity
            assert len(qc) == np.asarray(ind["activity"]).shape[1]
            q = measure_r4g(ind, "R4a", qc)
            r["qc"] = {"values": q["values"], "se": q["se"], "n_crops": q["n_crops"], "n_qc_units": int(qc.sum())}
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
    for pid in [p for p in s1.PREPS if p != "R4a"] + ["R4g", "R4a"]:
        rows = [pickle.loads(f.read_bytes()) for f in sorted(CACHE.glob(f"{pid}_*.pkl"))]
        if rows:
            sp = s1.PREPS["R4" if pid == "R4g" else pid]
            res[pid] = {"type": sp["type"] + (" (units pooled in groups of 8)" if pid in ("R4g", "R4a") else ""),
                        "group": sp["group"], "individuals": rows}
    OUT.write_text(json.dumps({"preparations": res, "provenance": {
        "code_sha256_16": instrument.code_hash(["scripts/map_step1.py", "scripts/map_brains.py"]),
        "seconds_last_run": round(time.time() - t0)}}, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1:] or ["R2"])                    # amendment 13: the worm map only
