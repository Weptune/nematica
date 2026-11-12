"""Calibration gate for the map (docs/MAP.md, C1 to C3, as amended 12 Nov), synthetic systems only.

All values use the matched protocol (measures.measure_matched: 50 units x 20 draws, windows of 80 tau_med).
C1: each measurement recovers the ordering of the property it targets (Spearman >= 0.9, 5 levels x 3
seeds) under every recording model. C2: calcium vs spikes differ by < 0.5 between-individual SD (if not,
the measurement is compared only within a recording type). C3 (amended): two independent sets of draws
agree to within 0.25 between-individual SD (mean |a - b| / sqrt 2).
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

REC = {"native": lambda A, r: recording.native(A),
       "calcium": lambda A, r: recording.calcium(A, decay=8.0, frame=2, snr=4.0, rng=r),
       "spikes": lambda A, r: recording.spikes(A, mean_count=0.5, bin_steps=4, rng=r)}
C1 = {"spectrum_exponent": ("alpha", [0.6, 0.8, 1.0, 1.4, 1.8], +1, {}),
      "shared_dim": ("K", [5, 10, 20, 50, 100], +1, {"alpha": 0.3}),
      "shared_fraction": ("private", [4.0, 2.0, 1.0, 0.5, 0.25], -1, {}),
      "slow_fraction": ("slow", [0.0, 0.15, 0.3, 0.5, 0.7], +1, {}),
      "timescale_spread": ("tau_spread", [0.0, 0.1, 0.2, 0.4, 0.6], +1, {"private": 2.0}),
      "coupling_spread": ("coupling", [0.0, 0.25, 0.5, 0.75, 1.0], +1, {}),
      "drift": ("drift", [0.0, 0.3, 0.6, 1.0, 1.5], +1, {}),
      "sparsity": ("power", [1.0, 1.3, 1.6, 2.0, 2.5], +1, {})}
SEEDS = (0, 1, 2)
T = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


def run(A, rec, seed, only):
    Y = REC[rec](A, np.random.default_rng(seed + 7))
    return measures.measure_matched(Y, seed=seed, only=only)


def main():
    out = {"protocol": {"n_units": measures.N_UNITS, "n_draws": measures.N_DRAWS, "window_tau": measures.WINDOW_TAU, "T": T},
           "C1": {}, "C2": {}, "C3": {}}
    t0 = time.time()
    for m, (par, levels, sign, fixed) in C1.items():
        res = {r: [] for r in REC}
        for lv in levels:
            for s in SEEDS:
                A = synthetic.population(np.random.default_rng(1000 * s + 17), T=T, **{**fixed, par: lv})
                for r in REC:
                    res[r].append((lv, run(A, r, s, [m]).get(m, np.nan)))
        out["C1"][m] = {}
        for r in REC:
            x, y = np.array(res[r], float).T
            ok = np.isfinite(y)
            rho = spearmanr(x[ok], y[ok])[0] * sign if ok.sum() > 4 else np.nan
            out["C1"][m][r] = {"rho": float(rho), "pass": bool(rho >= 0.9), "values": [float(v) for v in y]}
        print(f"C1 {m:18s}", {r: round(out['C1'][m][r]['rho'], 2) for r in REC}, f"{time.time()-t0:.0f}s", flush=True)
    jit = lambda rng: ({k: synthetic.DEFAULT[k] * (1 + 0.1 * rng.uniform(-1, 1)) for k in ("alpha", "slow", "coupling", "private", "tau_spread")}
                       | {"drift": 0.6 * (1 + 0.1 * rng.uniform(-1, 1))})
    a = {r: {m: [] for m in C1} for r in REC}
    b = {r: {m: [] for m in C1} for r in REC}
    for i in range(6):
        rng = np.random.default_rng(500 + i)
        A = synthetic.population(rng, T=T, **jit(rng))
        for r in REC:
            ra, rb = run(A, r, 10 + i, None), run(A, r, 50 + i, None)
            for m in C1:
                a[r][m].append(ra.get(m, np.nan)); b[r][m].append(rb.get(m, np.nan))
        print(f"individual {i} {time.time()-t0:.0f}s", flush=True)
    for m in C1:
        sd = float(np.nanmean([np.nanstd(a[r][m], ddof=1) for r in REC]))
        d = abs(np.nanmean(a["calcium"][m]) - np.nanmean(a["spikes"][m]))
        out["C2"][m] = {"diff": float(d), "between_sd": sd, "ratio": float(d / sd) if sd > 0 else None, "pass": bool(sd > 0 and d < 0.5 * sd)}
        out["C3"][m] = {}
        for r in REC:
            sdr = float(np.nanstd(a[r][m], ddof=1))
            st = float(np.nanmean(np.abs(np.array(a[r][m]) - np.array(b[r][m]))) / np.sqrt(2))
            out["C3"][m][r] = {"draw_sd": st, "between_sd": sdr, "ratio": st / sdr if sdr > 0 else None,
                               "pass": bool(sdr > 0 and st < 0.25 * sdr)}
    Path("docs/figures/map_calibration.json").write_text(json.dumps(out, indent=1))
    print("\nmeasure            C1 native/calcium/spikes  C2 ratio  C3 ratio native/calcium/spikes")
    for m in C1:
        c1 = "/".join(f"{out['C1'][m][r]['rho']:.2f}" for r in REC)
        c3 = "/".join(f"{out['C3'][m][r]['ratio']:.2f}" if out['C3'][m][r]['ratio'] is not None else "nan" for r in REC)
        c2 = out['C2'][m]['ratio']
        print(f"{m:18s} {c1:25s} {('%.2f' % c2) if c2 is not None else 'nan':9s} {c3}")


if __name__ == "__main__":
    main()
