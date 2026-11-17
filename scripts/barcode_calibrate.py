"""Study 4 calibration v4 (docs/BARCODE.md): synthetic systems at 90 repeats of a ~400-bin clip through four
Study 2 instruments; M1, M2 and the drive exponent b (20 windows). Resumable. `--summary` writes
docs/figures/barcode/calibration.json."""
import importlib.util
import json
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("pcal", ROOT / "scripts/persist_calibrate.py")
PC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PC)
from nematica.persist import measures as PM, synthetic as PS  # noqa: E402
from nematica.slow import stream as ST  # noqa: E402

OUT = ROOT / "docs/figures/barcode"
RUNS = OUT / "calibration_runs.jsonl"
BINS = 400
R = 90
N = 300
TAU_L = 10.0
W = 20
SEEDS = (0, 1)


def grid():
    for inst in ("median", "fastest", "slowest", "noisiest"):
        for seed in SEEDS:
            for share in (0.1, 0.25, 0.4, 0.6):
                for ti in (1.0, 4.0):
                    yield inst, seed, "generated", {"share": share, "tau_int": ti * TAU_L}
            for sd in (0.15, 0.3, 0.6):
                yield inst, seed, "gain", {"gain_sd": sd}
            yield inst, seed, "gain", {"gain_sd": 0.3, "gain_tau": TAU_L}


def key(inst, seed, kind, par):
    return f"{inst}|{seed}|{kind}|{json.dumps(par, sort_keys=True)}"


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    have = {json.loads(l)["key"] for l in open(RUNS)} if RUNS.exists() else set()
    ins = PC.instruments()
    for inst, seed, kind, par in grid():
        k = key(inst, seed, kind, par)
        if k in have:
            continue
        prof = ins[inst]["profile"]
        T = int(np.clip(round(BINS * TAU_L / prof["bins_per_tau"]), 60, 20000))
        rng = np.random.default_rng([seed, zlib.crc32(f"{kind}{par}".encode())])
        A, starts = PS.system(rng, kind, T, R=R, N=N, env_kind="flat", **par)
        out = ST.record_stream(A, starts, T, prof, nb_mouse=BINS, R_mouse=R,
                               n_units_mouse=min(ins[inst]["units"], 200), seed=seed + 11, halves=False,
                               extra=lambda rec, inc: PM.windowed_stream(rec, inc, W=W), max_bins=4 * BINS)
        w = out.get("extra") or {}
        row = {"key": k, "instrument": inst, "seed": seed, "kind": kind, **par, "T": T,
               **{x: out.get(x) for x in ("M1", "M2", "reached", "recorded_bins", "units_used", "numbers_on_repeats",
                                          "error")},
               "b": w.get("b_drive"), "fit": w.get("fit")}
        with open(RUNS, "a") as f:
            f.write(json.dumps(row, default=float) + "\n")
        print(k, out.get("reached"), out.get("recorded_bins"), out.get("M1"), out.get("M2"), w.get("b_drive"), flush=True)


def summary():
    from scipy.stats import spearmanr
    rows = [json.loads(l) for l in open(RUNS)]
    insts = sorted({r["instrument"] for r in rows})
    out = {"n_runs": len(rows), "n_reached": sum(bool(r.get("reached")) for r in rows), "K1": {}, "K2": {}, "K3": {},
           "K4": {}}
    for inst in insts:
        g = [r for r in rows if r["instrument"] == inst and r["kind"] == "generated" and np.isfinite(r.get("M1") or np.nan)]
        rho = float(spearmanr([r["share"] for r in g], [r["M1"] for r in g])[0]) if len(g) > 3 else np.nan
        out["K1"][inst] = {"rho": rho, "n": len(g), "passes": bool(rho >= 0.9)}
        pairs = 0
        ok = 0
        for seed in SEEDS:
            for share in (0.1, 0.25, 0.4, 0.6):
                a = [r["M2"] for r in g if r["seed"] == seed and r["share"] == share and r["tau_int"] == TAU_L]
                b = [r["M2"] for r in g if r["seed"] == seed and r["share"] == share and r["tau_int"] == 4 * TAU_L]
                if a and b and np.isfinite(a[0]) and np.isfinite(b[0]):
                    pairs += 1
                    ok += int(b[0] > a[0])
        out["K2"][inst] = {"pairs": pairs, "higher": ok, "passes": bool(pairs == 8 and ok >= 7)}
        for seed in SEEDS:
            add = [r["b"] for r in rows if r["instrument"] == inst and r["seed"] == seed and r["kind"] == "generated"
                   and r.get("b") is not None and np.isfinite(r["b"])]
            gn = [r["b"] for r in rows if r["instrument"] == inst and r["seed"] == seed and r["kind"] == "gain"
                  and r.get("gain_sd", 0) >= 0.3 and r.get("b") is not None and np.isfinite(r["b"])]
            if add and gn:
                out["K3"][f"{inst}|{seed}"] = {"additive_max": max(add), "gain_min": min(gn),
                                               "passes": bool(max(add) < min(gn))}
        xs, ys = [], []
        for r in rows:
            if r["instrument"] != inst or r.get("b") is None or not np.isfinite(r["b"]):
                continue
            if r["kind"] == "generated" and r["share"] == 0.4 and r["tau_int"] == TAU_L:
                xs.append(0.0); ys.append(r["b"])
            elif r["kind"] == "gain" and "gain_tau" not in r:
                xs.append(r["gain_sd"]); ys.append(r["b"])
        rho = float(spearmanr(xs, ys)[0]) if len(set(xs)) >= 3 else np.nan
        out["K4"][inst] = {"rho": rho, "n": len(xs), "passes": bool(rho >= 0.8)}
    p = {k: bool(out[k]) and all(v["passes"] for v in out[k].values()) for k in ("K1", "K2", "K3", "K4")}
    out["passes"] = p
    out["eligible"] = {"M1": p["K1"], "M2": p["K1"] and p["K2"], "b": p["K3"] and p["K4"]}
    (OUT / "calibration.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({"passes": p, "eligible": out["eligible"]}))


if __name__ == "__main__":
    summary() if "--summary" in sys.argv else run()
