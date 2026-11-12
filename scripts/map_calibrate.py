"""Calibration gate for the map (docs/MAP.md, amendment 3), synthetic systems only, through the
registered matching rule (recording.match_calcium / match_spikes) against two synthetic instrument profiles
per recording type that span plausible preparations.

C1  each measurement recovers the ordering of its target property (Spearman >= 0.9; 5 levels x 2 seeds)
    under every profile of a recording type (native: as is).
C4  knobs the matching rule does not set: the network's native timescale (samples per tau, 1.5 to 30),
    population size (60 to 3,000), and, for calcium, the rectification gain (0.5 to 4). Each must move a
    measurement by < 0.5 of its C1 range (mean over profiles).
X   cross-talk: for each measurement and each other property's sweep, the change it causes as a ratio to
    the measurement's own C1 range (reported; a ratio >= 0.5 marks the pair as confounded).
Knobs are matched on 60 units and the first 3,000 samples (population-level settings), then applied to all.
Writes docs/figures/map_calibration.json.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.map import measures, recording, synthetic  # noqa: E402

M = measures.MEASURES
PROFILES = {"native": {"-": None},
            "calcium": {"A": dict(decay_over_tau=0.3, frames_per_tau=4.0, noise=0.2),
                        "B": dict(decay_over_tau=0.8, frames_per_tau=7.0, noise=0.4)},
            "spikes": {"A": dict(bins_per_tau=3.0, count_per_bin=0.5, noise=0.6),
                       "B": dict(bins_per_tau=6.0, count_per_bin=0.2, noise=0.8)}}
SWEEP = {"spectrum_steepness": ("alpha", [0.6, 0.8, 1.0, 1.4, 1.8], +1, {}),
         "shared_fraction": ("private", [4.0, 2.0, 1.0, 0.5, 0.25], -1, {}),
         "slow_fraction": ("slow", [0.0, 0.1, 0.2, 0.3, 0.4], +1, {}),
         "timescale_spread": ("tau_spread", [0.0, 0.1, 0.2, 0.4, 0.6], +1, {"private": 2.0}),
         "coupling_spread": ("coupling", [0.0, 0.25, 0.5, 0.75, 1.0], +1, {}),
         "drift": ("drift", [0.0, 1.0, 2.0, 4.0, 8.0], +1, {"T": 4000}),
         "sparsity": ("power", [1.0, 1.3, 1.6, 2.0, 2.5], +1, {})}
DRAWS = 20
SEEDS = (0, 1)


def record(A, rt, prof, seed, gain=None):
    r = np.random.default_rng(seed + 7)
    if rt == "native":
        return A
    sub = A[:3000, :60]
    k = recording.match_calcium(sub, prof, rng=r) if rt == "calcium" else recording.match_spikes(sub, prof, rng=r)
    if gain is not None:
        recording.GAIN = gain
    try:
        Y = recording.record_matched(A, rt, k, rng=r)
    finally:
        recording.GAIN = 1.0
    return Y, k["reached"]


def meas(Y, seed):
    r = measures.measure_matched(Y, seed=seed, n_draws=DRAWS)
    return {m: r.get(m, np.nan) for m in M}


def run(A, seed, gain=None):
    out = {}
    for rt, profs in PROFILES.items():
        for pn, prof in profs.items():
            if rt == "native":
                out[(rt, pn)] = (meas(A, seed), True)
            else:
                Y, ok = record(A, rt, prof, seed, gain)
                out[(rt, pn)] = (meas(Y, seed), ok)
    return out


def main():
    t0 = time.time()
    keys = [(rt, pn) for rt, ps in PROFILES.items() for pn in ps]
    res = {}
    unreached = 0
    for prop, (par, levels, sign, fixed) in SWEEP.items():
        rows = []
        for lv in levels:
            for s in SEEDS:
                A = synthetic.population(np.random.default_rng(1000 * s + 17), **{**fixed, par: lv})
                o = run(A, s)
                unreached += sum(not ok for _, ok in o.values())
                rows.append((lv, {k: v for k, (v, ok) in o.items()}))
        res[prop] = rows
        print(f"sweep {prop} {time.time()-t0:.0f}s", flush=True)
    out = {"protocol": {"draws": DRAWS, "seeds": len(SEEDS), "profiles": {rt: PROFILES[rt] for rt in PROFILES}},
           "unreached_matches": unreached, "C1": {}, "X": {}, "C4": {}}
    for key in keys:
        kk = "/".join(key)
        out["C1"][kk], out["X"][kk] = {}, {}
        for m in M:
            par, levels, sign, _ = SWEEP[m]
            x = np.array([lv for lv, v in res[m]]); y = np.array([v[key][m] for lv, v in res[m]])
            ok = np.isfinite(y)
            rho = float(spearmanr(x[ok], y[ok])[0] * sign) if ok.sum() >= 6 else float("nan")
            means = [np.nanmean(y[x == lv]) if np.isfinite(y[x == lv]).any() else np.nan for lv in levels]
            rngc = float(np.nanmax(means) - np.nanmin(means)) if np.isfinite(means).sum() > 1 else float("nan")
            out["C1"][kk][m] = {"rho": rho, "range": rngc, "finite": int(ok.sum())}
            out["X"][kk][m] = {}
            for prop in SWEEP:
                lv_ = sorted(set(lv for lv, _ in res[prop]))
                mm = [np.nanmean([v[key][m] for lv, v in res[prop] if lv == l]) for l in lv_]
                ch = float(np.nanmax(mm) - np.nanmin(mm)) if np.isfinite(mm).sum() > 1 else float("nan")
                out["X"][kk][m][prop] = ch / rngc if rngc and rngc == rngc and rngc > 0 else None
    # C4
    for key in keys:
        out["C4"]["/".join(key)] = {}
    knobs = {"samples_per_tau": [1.5, 4.0, 12.0, 30.0], "population": [60, 300, 3000], "gain": [0.5, 1.0, 4.0]}
    for knob, vals in knobs.items():
        per = {key: {v: [] for v in vals} for key in keys}
        for s in SEEDS:
            for v in vals:
                if knob == "samples_per_tau":
                    A = synthetic.population(np.random.default_rng(300 + s), tau_fast=v, tau_slow=15 * v, T=int(2000 * max(v, 4)))
                    o = run(A, s)
                elif knob == "population":
                    A = synthetic.population(np.random.default_rng(300 + s), N=v, K=min(100, v))
                    o = run(A, s)
                else:
                    A = synthetic.population(np.random.default_rng(300 + s))
                    o = run(A, s, gain=v)
                for key in keys:
                    per[key][v].append(o[key][0])
        for key in keys:
            kk = "/".join(key)
            if knob == "gain" and key[0] != "calcium":
                continue
            out["C4"][kk][knob] = {}
            for m in M:
                means = [np.nanmean([d[m] for d in per[key][v]]) for v in vals]
                ch = float(np.nanmax(means) - np.nanmin(means)) if np.isfinite(means).sum() > 1 else float("nan")
                rngc = out["C1"][kk][m]["range"]
                out["C4"][kk][knob][m] = ch / rngc if rngc and rngc == rngc and rngc > 0 else None
        print(f"C4 {knob} {time.time()-t0:.0f}s", flush=True)
    Path("docs/figures/map_calibration.json").write_text(json.dumps(out, indent=1))
    print("unreached matches:", unreached)
    for key in keys:
        kk = "/".join(key)
        print(f"\n[{kk}] measure: C1 rho | C4 ratios")
        for m in M:
            c4 = " ".join(f"{k}={v[m]:.2f}" if v[m] is not None and v[m] == v[m] else f"{k}=nan" for k, v in out["C4"][kk].items())
            print(f"  {m:18s} {out['C1'][kk][m]['rho']:.2f} | {c4}")


if __name__ == "__main__":
    main()
