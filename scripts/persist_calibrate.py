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
                               extra=lambda rec, inc: PM.windowed_stream(rec, inc, W=8))
        row = {"key": k, "instrument": inst, "mouse": ins[inst]["id"], "seed": seed, "kind": kind, **par,
               "env": env, "T": T, **{x: out.get(x) for x in ("M1", "M2", "reached", "recorded_bins",
                                                          "units_used", "numbers_on_repeats", "error")},
               "windows": out.get("extra")}
        with open(RUNS, "a") as f:
            f.write(json.dumps(row, default=float) + "\n")
        w = out.get("extra") or {}
        print(k, out.get("reached"), out.get("recorded_bins"), w.get("P_share"), w.get("P_amp"), flush=True)


if __name__ == "__main__":
    run()
