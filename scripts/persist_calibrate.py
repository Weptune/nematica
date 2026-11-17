"""Study 3 calibration (docs/PERSIST.md section 8). Synthetic systems through four real instruments (the
median, fastest, slowest and noisiest Study 2 mouse on NM1), recorded with Study 2's streaming recorder,
measured with the windowed measures. Resumable; shardable with PERSIST_SHARD="i/n".
Writes docs/figures/persist/calibration_runs.jsonl; `--summary` writes calibration.json."""
import json
import os
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.persist import measures as PM  # noqa: E402
from nematica.persist import synthetic as PS  # noqa: E402
from nematica.slow import stream as ST  # noqa: E402

OUT = ROOT / "docs/figures/persist"
RUNS = OUT / "calibration_runs.jsonl"
BINS = 6000
R = 10
N = 300
TAU_L = 10.0
SEEDS = (0, 1)
C_CLIP = 6.0                 # drive-time index c clipped to [-6, 6] per clip (an end/start ratio of 0.0025 to 400)


def instruments():
    mice = [json.loads(l) for l in open(ROOT / "docs/figures/slow_runs/mice.jsonl")]
    used = set(json.load(open(ROOT / "docs/figures/slow_runs/mice_table.json"))["rows"])
    mice = [m for m in mice if m["id"] in used]
    bpt = np.array([m["profile"]["bins_per_tau"] for m in mice])
    noise = np.array([m["profile"]["noise"] for m in mice])
    med = int(np.argsort(bpt)[len(bpt) // 2])
    pick = {"median": med, "fastest": int(np.argmin(bpt)), "slowest": int(np.argmax(bpt)),
            "noisiest": int(np.argmax(noise))}
    return {k: {"id": mice[i]["id"], "profile": mice[i]["profile"], "units": int(mice[i]["units"])}
            for k, i in pick.items()}


def grid():
    for inst in ("median", "fastest", "slowest", "noisiest"):
        for seed in SEEDS:
            for ti in (0.25, 0.5, 1.0, 2.5):
                yield inst, seed, "generated", {"tau_int": ti * TAU_L}, "normal"
            for tc in (0.1, 0.25, 0.5, 2.0):
                yield inst, seed, "carried", {"tau_c": tc}, "normal"
            yield inst, seed, "gain", {}, "normal"
            for env in ("flat", "reversed", "squared"):
                yield inst, seed, "generated", {"tau_int": TAU_L}, env
                yield inst, seed, "carried", {"tau_c": 0.5}, env


def key(inst, seed, kind, par, env):
    return f"{inst}|{seed}|{kind}|{json.dumps(par, sort_keys=True)}|{env}"


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    have = {json.loads(l)["key"] for l in open(RUNS)} if RUNS.exists() else set()
    shard = os.environ.get("PERSIST_SHARD")
    si, sn = (int(x) for x in shard.split("/")) if shard else (0, 1)
    ins = instruments()
    for inst, seed, kind, par, env in grid():
        k = key(inst, seed, kind, par, env)
        if k in have or zlib.crc32(k.encode()) % sn != si:
            continue
        prof = ins[inst]["profile"]
        T = int(np.clip(round(BINS * TAU_L / prof["bins_per_tau"]), 300, 40000))
        rng = np.random.default_rng([seed, zlib.crc32(f"{kind}{par}".encode())])   # same draws across envelopes
        A, starts = PS.system(rng, kind, T, R=R, N=N, env_kind=env, **par)
        out = ST.record_stream(A, starts, T, prof, nb_mouse=BINS, R_mouse=R,
                               n_units_mouse=min(ins[inst]["units"], 200), seed=seed + 11, halves=False,
                               extra=lambda rec, inc: PM.windowed_stream(rec, inc, W=8), max_bins=4 * BINS)
        row = {"key": k, "instrument": inst, "mouse": ins[inst]["id"], "seed": seed, "kind": kind, **par,
               "env": env, "T": T, **{x: out.get(x) for x in ("M1", "M2", "reached", "recorded_bins",
                                                          "units_used", "numbers_on_repeats", "error")},
               "windows": out.get("extra")}
        with open(RUNS, "a") as f:
            f.write(json.dumps(row, default=float) + "\n")
        w = out.get("extra") or {}
        print(k, out.get("reached"), out.get("recorded_bins"), w.get("P_share"), w.get("P_amp"), flush=True)


if __name__ == "__main__" and "--summary" not in sys.argv:
    run()


def summary():
    """C1 to C4 of docs/PERSIST.md section 8, per index; writes docs/figures/persist/calibration.json."""
    from nematica.persist.measures import drive_time_fit
    rows = [json.loads(l) for l in open(RUNS)]
    n_all = len(rows)
    rows = [r for r in rows if r.get("windows") and r.get("reached")]     # as in the data: reached only
    for r in rows:                                                        # recompute with the current fit
        w = r["windows"]
        I, S = np.array(w["int_amp_w"]), np.array(w["same_amp_w"])
        f = drive_time_fit(I, S - I)
        w["c_time"] = float(np.clip(f["c"], -C_CLIP, C_CLIP)) if np.isfinite(f["c"]) else np.nan
        w["c_log"] = float(np.clip(f.get("c_loglinear", np.nan), -C_CLIP, C_CLIP))
        w["b_drive"] = f["b"]
    out = {"n_runs": n_all, "n_reached": len(rows), "c_clip": C_CLIP, "indices": {}}
    insts = sorted({r["instrument"] for r in rows})
    for ix in ("P_share", "P_amp", "c_time", "c_log"):
        res = {"C1": {}, "C2": {}, "C3": {}, "C4": {}}
        v = lambda r: r["windows"][ix]
        med_gap = []
        for inst in insts:
            for seed in SEEDS:
                g = [v(r) for r in rows if r["instrument"] == inst and r["seed"] == seed and r["kind"] == "generated"
                     and r["env"] == "normal"]
                c = [v(r) for r in rows if r["instrument"] == inst and r["seed"] == seed and r["kind"] == "carried"
                     and r["env"] == "normal" and r["tau_c"] <= 0.5]
                c2 = [v(r) for r in rows if r["instrument"] == inst and r["seed"] == seed and r["kind"] == "carried"
                      and r["env"] == "normal" and r["tau_c"] == 2.0]
                if not g or not c:
                    continue
                res["C1"][f"{inst}|{seed}"] = {"generated_min": min(g), "generated_median": float(np.median(g)),
                                               "carried_max": max(c), "separated": bool(min(g) > max(c)),
                                               "carried_2clip": c2[0] if c2 else None,
                                               "carried_2clip_below_gen_median": bool(c2 and c2[0] < np.median(g))}
                med_gap.append(float(np.median(g)) - float(np.median(c)))
        gap = float(np.median(med_gap)) if med_gap else np.nan
        tol = abs(gap) / 4
        for inst in insts:
            for seed in SEEDS:
                for kind, par in (("generated", ("tau_int", TAU_L)), ("carried", ("tau_c", 0.5))):
                    base = [v(r) for r in rows if r["instrument"] == inst and r["seed"] == seed and r["kind"] == kind
                            and r.get(par[0]) == par[1] and r["env"] == "normal"]
                    for env in ("flat", "reversed", "squared"):
                        x = [v(r) for r in rows if r["instrument"] == inst and r["seed"] == seed and r["kind"] == kind
                             and r.get(par[0]) == par[1] and r["env"] == env]
                        if base and x:
                            res["C2"][f"{inst}|{seed}|{kind}|{env}"] = {"shift": x[0] - base[0],
                                                                        "within": bool(abs(x[0] - base[0]) <= tol)}
        for kind, par in (("generated", ("tau_int", TAU_L)), ("carried", ("tau_c", 0.5))):
            meds = {inst: float(np.median([v(r) for r in rows if r["instrument"] == inst and r["kind"] == kind
                                           and r.get(par[0]) == par[1] and r["env"] == "normal"] or [np.nan]))
                    for inst in insts}
            res["C3"][kind] = {"medians": meds, "range": float(np.nanmax(list(meds.values())) - np.nanmin(list(meds.values())))}
        for inst in insts:
            for seed in SEEDS:
                g = [v(r) for r in rows if r["instrument"] == inst and r["seed"] == seed and r["kind"] == "generated"
                     and r["env"] == "normal"]
                gn = [v(r) for r in rows if r["instrument"] == inst and r["seed"] == seed and r["kind"] == "gain"]
                if g and gn:
                    res["C4"][f"{inst}|{seed}"] = {"gain": gn[0], "within": bool(min(g) - tol <= gn[0] <= max(g) + tol)}
        res["gap_generated_minus_carried"] = gap
        res["C2_tolerance"] = tol
        res["passes"] = {k: bool(res[k]) and all(x.get("separated", x.get("within", True)) for x in res[k].values())
                         for k in ("C1", "C2", "C4")}
        out["indices"][ix] = res
    (OUT / "calibration.json").write_text(json.dumps(out, indent=1, default=float))
    b = {kind: [r["windows"]["b_drive"] for r in rows if r["kind"] == kind and r["env"] == "normal"]
         for kind in ("generated", "carried", "gain")}
    c5 = {}
    for inst in insts:
        for seed in SEEDS:
            g = [r["windows"]["b_drive"] for r in rows if r["instrument"] == inst and r["seed"] == seed
                 and r["kind"] == "generated" and r["env"] == "normal"]
            gn = [r["windows"]["b_drive"] for r in rows if r["instrument"] == inst and r["seed"] == seed
                  and r["kind"] == "gain"]
            if g and gn:
                c5[f"{inst}|{seed}"] = {"generated_max": max(g), "gain": gn[0], "separated": bool(max(g) < gn[0])}
    out["C5"] = {"cells": c5, "passes": bool(c5) and all(x["separated"] for x in c5.values())}
    out["b_drive"] = {k: {"median": float(np.nanmedian(v_)), "min": float(np.nanmin(v_)), "max": float(np.nanmax(v_))}
                      for k, v_ in b.items() if v_}
    (OUT / "calibration.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({ix: out["indices"][ix]["passes"] for ix in out["indices"]}), json.dumps(out["b_drive"]), "C5", out["C5"]["passes"])


if __name__ == "__main__" and "--summary" in sys.argv:
    summary()
