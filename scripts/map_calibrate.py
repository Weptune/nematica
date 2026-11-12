"""Calibration gate for the map (docs/MAP.md, amendment 2), synthetic systems only.

Every value uses the matched protocol (measures.measure_matched; 10 draws here for speed).
C1  each measurement recovers the ordering of its target property (Spearman >= 0.9; 5 levels x 3 seeds)
    under each recording type at its reference settings. A measurement is used within a type where it passes.
C4  nuisance invariance: at the default system, sweeping a nuisance knob (samples per tau, unit scale,
    population size, and each recording type's knobs) must move the measurement by less than half its C1
    range in that type. A measurement failing C4 for a knob that real preparations vary is not used for
    brain vs AI comparisons in that type.
X   cross-talk: Spearman of every measurement with every property sweep (reported).
Writes docs/figures/map_calibration.json (amendment-1 results are kept in git history).
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
REF = {"native": {}, "calcium": dict(decay=4.0, frame=1.5, snr=2.0), "spikes": dict(mean_count=0.2, bin_steps=1.5, gain=3.0)}
SWEEP = {"spectrum_steepness": ("alpha", [0.6, 0.8, 1.0, 1.4, 1.8], +1, {}),
         "shared_dim": ("K", [3, 6, 12, 25, 50], +1, {"alpha": 0.3}),
         "shared_fraction": ("private", [4.0, 2.0, 1.0, 0.5, 0.25], -1, {}),
         "slow_fraction": ("slow", [0.0, 0.15, 0.3, 0.5, 0.7], +1, {}),
         "timescale_spread": ("tau_spread", [0.0, 0.1, 0.2, 0.4, 0.6], +1, {"private": 2.0}),
         "coupling_spread": ("coupling", [0.0, 0.25, 0.5, 0.75, 1.0], +1, {}),
         "drift": ("drift", [0.0, 1.0, 2.0, 4.0, 8.0], +1, {"T": 4000}),
         "sparsity": ("power", [1.0, 1.3, 1.6, 2.0, 2.5], +1, {})}
DRAWS = 10


def rec(A, rtype, seed, **kw):
    f = recording.RECORDINGS[rtype]
    return f(A, rng=np.random.default_rng(seed + 7), **{**REF[rtype], **kw})


def meas(Y, seed):
    r = measures.measure_matched(Y, seed=seed, n_draws=DRAWS)
    return {m: r.get(m, np.nan) for m in M}


def main():
    t0 = time.time()
    out = {"protocol": {"n_units": measures.N_UNITS, "draws": DRAWS, "window_tau": measures.WINDOW_TAU, "ref": REF},
           "C1": {}, "X": {}, "C4": {}}
    allv = {}
    for prop, (par, levels, sign, fixed) in SWEEP.items():
        rows = []
        for lv in levels:
            for s in (0, 1, 2):
                A = synthetic.population(np.random.default_rng(1000 * s + 17), **{**fixed, par: lv})
                for rt in REF:
                    rows.append((rt, lv, meas(rec(A, rt, s), s)))
        allv[prop] = rows
        print(f"sweep {prop} done {time.time()-t0:.0f}s", flush=True)
    for rt in REF:
        out["C1"][rt], out["X"][rt] = {}, {}
        for m in M:
            par, levels, sign, _ = SWEEP[m]
            x = np.array([lv for r, lv, v in allv[m] if r == rt]); y = np.array([v[m] for r, lv, v in allv[m] if r == rt])
            ok = np.isfinite(y)
            rho = float(spearmanr(x[ok], y[ok])[0] * sign) if ok.sum() > 6 else float("nan")
            means = [np.nanmean(y[x == lv]) for lv in levels]
            out["C1"][rt][m] = {"rho": rho, "pass": bool(rho >= 0.9), "range": float(np.nanmax(means) - np.nanmin(means)),
                                "n_finite": int(ok.sum())}
            out["X"][rt][m] = {}
            for prop in SWEEP:
                xx = np.array([lv for r, lv, v in allv[prop] if r == rt]); yy = np.array([v[m] for r, lv, v in allv[prop] if r == rt])
                okk = np.isfinite(yy)
                out["X"][rt][m][prop] = float(spearmanr(xx[okk], yy[okk])[0]) if okk.sum() > 6 and np.nanstd(yy) > 0 else None
    # C4: nuisance sweeps at the default system
    nuis = {"native": {"samples_per_tau": None, "unit_scale": None, "population": None},
            "calcium": {"decay": [1.0, 4.0, 16.0], "frame": [1.0, 1.5, 3.0], "snr": [1.0, 2.0, 6.0],
                        "samples_per_tau": None, "population": None},
            "spikes": {"mean_count": [0.05, 0.2, 1.0], "bin_steps": [1.0, 1.5, 3.0], "gain": [1.0, 3.0, 10.0],
                       "samples_per_tau": None, "population": None}}
    for rt, knobs in nuis.items():
        out["C4"][rt] = {}
        for knob, vals in knobs.items():
            res = []
            for s in (0, 1, 2):
                if knob == "samples_per_tau":
                    for tf in (1.5, 4.0, 12.0, 30.0):
                        A = synthetic.population(np.random.default_rng(300 + s), tau_fast=tf, tau_slow=15 * tf, T=int(2000 * tf))
                        res.append((tf, meas(rec(A, rt, s), s)))
                elif knob == "population":
                    for n in (60, 300, 3000):
                        A = synthetic.population(np.random.default_rng(300 + s), N=n, K=min(100, n))
                        res.append((n, meas(rec(A, rt, s), s)))
                elif knob == "unit_scale":
                    A = synthetic.population(np.random.default_rng(300 + s))
                    for sc in (0.01, 1.0, 100.0):
                        res.append((sc, meas(rec(A * sc, rt, s), s)))
                else:
                    A = synthetic.population(np.random.default_rng(300 + s))
                    for v in vals:
                        res.append((v, meas(rec(A, rt, s, **{knob: v}), s)))
            out["C4"][rt][knob] = {}
            for m in M:
                levels = sorted(set(k for k, _ in res))
                means = [np.nanmean([v[m] for k, v in res if k == lv]) for lv in levels]
                change = float(np.nanmax(means) - np.nanmin(means)) if np.isfinite(means).any() else float("nan")
                rng_c1 = out["C1"][rt][m]["range"]
                out["C4"][rt][knob][m] = {"change": change, "ratio": change / rng_c1 if rng_c1 > 0 else None,
                                          "pass": bool(rng_c1 > 0 and change < 0.5 * rng_c1)}
            print(f"C4 {rt} {knob} done {time.time()-t0:.0f}s", flush=True)
    Path("docs/figures/map_calibration.json").write_text(json.dumps(out, indent=1))
    for rt in REF:
        print(f"\n[{rt}] measure: C1 rho | C4 ratios (pass < 0.5)")
        for m in M:
            c4 = " ".join(f"{k}={out['C4'][rt][k][m]['ratio']:.2f}" if out['C4'][rt][k][m]['ratio'] is not None else f"{k}=nan" for k in out["C4"][rt])
            print(f"  {m:18s} {out['C1'][rt][m]['rho']:.2f} | {c4}")


if __name__ == "__main__":
    main()
