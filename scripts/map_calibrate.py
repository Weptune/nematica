"""Calibration gate for the map (docs/MAP.md, amendment 4), synthetic systems only, through the registered
matching call (recording.match) against two synthetic instrument profiles per recording type: a moderate one
(A) and a realistic noisy one (R; amendment 4, F7: real white-noise shares are 0.6 for calcium and 0.95 to
0.99 for sparse spikes).

C1  each measurement recovers the ordering of its target property (Spearman >= 0.9; 5 levels x 2 seeds).
C4  knobs the matching rule does not set: native timescale (samples per tau 1.5 to 30), population (60 to
    3,000), and for calcium the rectification gain (0.5 to 4, applied to matching and recording alike).
    Each must move a measurement by < 0.5 of its C1 range.
X   cross-talk ratios (reported).
TAU timescale recovery (F7): the recorded timescale converted to native steps, over the true population
    timescale of the native activity, across the samples-per-tau sweep (reported).
A synthetic system whose matched recording would be shorter than 240 recorded timescales is regenerated
longer (same seed and parameters). Writes docs/figures/map_calibration.json with a hash of the code.
"""
import hashlib
import json
import pickle
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.map import measures, recording, synthetic  # noqa: E402

M = measures.MEASURES
PROFILES = {"native": {"-": None},
            "calcium": {"A": dict(decay_over_tau=0.3, frames_per_tau=4.0, noise=0.2),
                        "R": dict(decay_over_tau=0.5, frames_per_tau=3.0, noise=0.6)},
            "spikes": {"A": dict(bins_per_tau=3.0, count_per_bin=0.5, noise=0.6),
                       "R": dict(bins_per_tau=10.0, count_per_bin=0.1, noise=0.97)}}
KEYS = [(rt, pn) for rt, ps in PROFILES.items() for pn in ps]
SWEEP = {"spectrum_steepness": ("alpha", [0.6, 0.8, 1.0, 1.4, 1.8], +1, {}),
         "shared_fraction": ("private", [4.0, 2.0, 1.0, 0.5, 0.25], -1, {}),
         "slow_fraction": ("slow", [0.0, 0.1, 0.2, 0.3, 0.4], +1, {}),
         "timescale_spread": ("tau_spread", [0.0, 0.1, 0.2, 0.4, 0.6], +1, {"private": 2.0}),
         "coupling_spread": ("coupling", [0.0, 0.25, 0.5, 0.75, 1.0], +1, {}),
         "drift": ("drift", [0.0, 1.0, 2.0, 4.0, 8.0], +1, {"T": 4000}),
         "sparsity": ("power", [1.0, 1.3, 1.6, 2.0, 2.5], +1, {})}
C4 = {"samples_per_tau": [1.5, 4.0, 12.0, 30.0], "population": [60, 300, 3000], "gain": [0.5, 1.0, 4.0]}
DRAWS = 20
SEEDS = (0, 1)
MIN_REC_TAU = 240
MAX_T = 80000
CODE = ["nematica/map/measures.py", "nematica/map/recording.py", "nematica/map/synthetic.py",
        "nematica/map/analysis.py", "nematica/map/instrument.py", "scripts/map_calibrate.py"]


def code_hash():
    h = hashlib.sha256()
    for f in CODE:
        h.update((ROOT / f).read_bytes())
    return h.hexdigest()[:16]


def meas(Y, seed):
    r = measures.measure_matched(Y, seed=seed, n_draws=DRAWS)
    return {m: r.get(m, np.nan) for m in M}


def system(job):
    """job: (params, rng seed, measurement seed, gain). Returns {key: (values, reached, tau_ratio)}."""
    params, gseed, s, gain = job
    out = {}
    A = synthetic.population(np.random.default_rng(gseed), **params)
    t_true = measures.tau_med(A[:, :recording.MATCH_MIN_UNITS])
    out[("native", "-")] = (meas(A, s), True, 1.0)
    recording.GAIN = gain
    try:
        for rt, profs in PROFILES.items():
            if rt == "native":
                continue
            for pn, prof in profs.items():
                k = recording.match(A, rt, prof, seed=s)
                B = A
                need = int(k["needs_steps"] * MIN_REC_TAU / recording.MATCH_MIN_TAU) if np.isfinite(k["needs_steps"]) else 0
                if need > len(A):                        # memory: at most 60 million unit-samples
                    tmax = min(MAX_T, int(6e7 / params.get("N", 300)))
                    B = synthetic.population(np.random.default_rng(gseed), **{**params, "T": min(need, tmax)})
                per_sample = (k["frame"] if rt == "calcium" else k["bin_steps"]) / k["hold"]
                if B.shape[1] >= 3000 and len(B) / per_sample * B.shape[1] > 1e8:   # memory (8 GB): not measured;
                    out[(rt, pn)] = ({m: np.nan for m in M}, bool(k["reached"]), np.nan)   # reported as nan
                    continue
                Y, seg = recording.record_matched(B, rt, k, rng=np.random.default_rng(s + 7))
                per = (k["frame"] if rt == "calcium" else k["bin_steps"]) / k["hold"]
                tr = k["achieved"]["frames_per_tau" if rt == "calcium" else "bins_per_tau"] * per / t_true
                out[(rt, pn)] = (meas(Y, s), bool(k["reached"]), float(tr))
    finally:
        recording.GAIN = 1.0
    return out


CACHE = ROOT / "data/cache/map_calibration"


def _cached(args):
    i, job, tag = args
    f = CACHE / f"{tag}_{i}.pkl"
    if f.exists():
        return pickle.loads(f.read_bytes())
    r = system(job)
    f.write_bytes(pickle.dumps(r))
    return r


def run_cached(jobs, t0, cache_tag=""):
    """Each job's result is cached under the code hash (a rerun after a crash skips finished jobs). Large
    systems (3,000 units, or 30 samples per tau) run one at a time to bound memory."""
    CACHE.mkdir(parents=True, exist_ok=True)
    tag = code_hash() + cache_tag
    big = [i for i, j in enumerate(jobs) if j[0].get("N", 0) >= 3000 or j[0].get("tau_fast", 0) >= 30]
    small = [i for i in range(len(jobs)) if i not in big]
    out = {}
    with Pool(2) as pool:
        for n, (i, r) in enumerate(zip(small, pool.imap(_cached, [(i, jobs[i], tag) for i in small]))):
            out[i] = r
            if n % 10 == 9:
                print(f"{n + 1}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    for i in big:
        out[i] = _cached((i, jobs[i], tag))
        print(f"big job {i} {time.time() - t0:.0f}s", flush=True)
    return [out[i] for i in range(len(jobs))]


def main(profiles=None, out_path=None, cache_tag="", c4=None, sweep=None):
    """Run C1, C4, X and TAU for the given profiles (default: the synthetic A and R profiles) and write the
    JSON (default docs/figures/map_calibration.json). Step 2 (scripts/map_step2.py) calls this with each
    preparation's own instrument numbers."""
    global PROFILES, KEYS
    if profiles is not None:
        PROFILES = profiles
        KEYS = [(rt, pn) for rt, ps in PROFILES.items() for pn in ps]
    C4_ = c4 if c4 is not None else C4
    SWEEP_ = sweep if sweep is not None else SWEEP
    t0 = time.time()
    jobs, tags = [], []
    for prop, (par, levels, sign, fixed) in SWEEP_.items():
        for lv in levels:
            for s in SEEDS:
                jobs.append(({**fixed, par: lv}, 1000 * s + 17, s, 1.0)); tags.append(("C1", prop, lv))
    for knob, vals in C4_.items():
        for v in vals:
            for s in SEEDS:
                if knob == "samples_per_tau":
                    p = dict(tau_fast=v, tau_slow=15 * v, T=int(2000 * max(v, 4)))
                elif knob == "population":
                    p = dict(N=v, K=min(100, v))
                else:
                    p = {}
                jobs.append((p, 300 + s, s, v if knob == "gain" else 1.0)); tags.append(("C4", knob, v))
    results = run_cached(jobs, t0, cache_tag)
    res = {p: [] for p in SWEEP_}
    c4 = {k: {key: {v: [] for v in vals} for key in KEYS} for k, vals in C4_.items()}
    taur = {key: {v: [] for v in C4_.get("samples_per_tau", [])} for key in KEYS}
    unreached = 0
    for (kind, name, lv), r in zip(tags, results):
        unreached += sum(not ok for _, ok, _ in r.values())
        if kind == "C1":
            res[name].append((lv, {k: v for k, (v, ok, tr) in r.items()}))
        else:
            for key in KEYS:
                c4[name][key][lv].append(r[key][0])
                if name == "samples_per_tau":
                    pass
                if name == "samples_per_tau":
                    taur[key][lv].append(r[key][2])
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    out = {"provenance": {"code_sha256_16": code_hash(), "git_head_at_run": head, "files": CODE,
                          "seconds": round(time.time() - t0)},
           "protocol": {"draws": DRAWS, "seeds": len(SEEDS), "profiles": PROFILES, "min_recorded_tau": MIN_REC_TAU},
           "unreached_matches": unreached, "jobs": len(jobs), "C1": {}, "X": {}, "C4": {}, "TAU": {}, "used": {}}
    for key in KEYS:
        kk = "/".join(key)
        out["C1"][kk], out["X"][kk], out["C4"][kk] = {}, {}, {}
        out["TAU"][kk] = {str(v): float(np.mean(t)) for v, t in taur[key].items()}
        for m in M:
            if m not in SWEEP_:
                out["C1"][kk][m] = {"rho": float("nan"), "range": float("nan"), "finite": 0}
                out["X"][kk][m] = {}
                continue
            par, levels, sign, _ = SWEEP_[m]
            x = np.array([lv for lv, v in res[m]]); y = np.array([v[key][m] for lv, v in res[m]])
            ok = np.isfinite(y)
            rho = float(spearmanr(x[ok], y[ok])[0] * sign) if ok.sum() >= 6 else float("nan")
            means = [np.nanmean(y[x == lv]) if np.isfinite(y[x == lv]).any() else np.nan for lv in levels]
            rngc = float(np.nanmax(means) - np.nanmin(means)) if np.isfinite(means).sum() > 1 else float("nan")
            out["C1"][kk][m] = {"rho": rho, "range": rngc, "finite": int(ok.sum())}
            out["X"][kk][m] = {}
            for prop in SWEEP_:
                lv_ = sorted(set(lv for lv, _ in res[prop]))
                mm = [np.nanmean([v[key][m] for lv, v in res[prop] if lv == l]) for l in lv_]
                ch = float(np.nanmax(mm) - np.nanmin(mm)) if np.isfinite(mm).sum() > 1 else float("nan")
                out["X"][kk][m][prop] = ch / rngc if rngc == rngc and rngc > 0 else None
        for knob, vals in C4_.items():
            if knob == "gain" and key[0] != "calcium":
                continue
            out["C4"][kk][knob] = {}
            for m in M:
                means = [np.nanmean([d[m] for d in c4[knob][key][v]]) for v in vals]
                ch = float(np.nanmax(means) - np.nanmin(means)) if np.isfinite(means).sum() > 1 else float("nan")
                rngc = out["C1"][kk][m]["range"]
                out["C4"][kk][knob][m] = ch / rngc if rngc == rngc and rngc > 0 else None
        out["used"][kk] = [m for m in M if out["C1"][kk][m]["rho"] >= 0.9 and all(
            v[m] is not None and v[m] == v[m] and v[m] < 0.5 for v in out["C4"][kk].values())]
    (out_path or ROOT / "docs/figures/map_calibration.json").write_text(json.dumps(out, indent=1))
    print("unreached matches:", unreached, "of", len(jobs) * 4)
    for key in KEYS:
        kk = "/".join(key)
        print(f"\n[{kk}] used {out['used'][kk]}  tau recovery {out['TAU'][kk]}")
        for m in M:
            c4s = " ".join(f"{k}={v[m]:.2f}" if v[m] is not None and v[m] == v[m] else f"{k}=nan" for k, v in out["C4"][kk].items())
            print(f"  {m:18s} {out['C1'][kk][m]['rho']:.2f} | {c4s}")


if __name__ == "__main__":
    main()
