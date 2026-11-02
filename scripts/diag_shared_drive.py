"""Model-free look at slow shared drives, wild type vs unc-31.

Pokes come every ~30 s, so there is little untouched activity. What there is: the few seconds
just before each poke. Each pre-poke window gives every neuron a baseline level. If slow drives
push many neurons together, those baselines rise and fall together from one window to the next.

Per worm, on z-scored activity:
  baseline_corr   mean |correlation| between neurons of their pre-poke baselines
  top1, top3      share of baseline variance in the first 1 and 3 principal components,
                  on random 40-neuron subsets (so worms with more neurons are not favoured)
  slow_share      median over neurons of baseline variance / total variance

Usage:  python scripts/diag_shared_drive.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402

PRE_S, CLEAR_S, SUBSET, N_SUB = 5.0, 20.0, 40, 50
OUT = Path("docs/figures/shared_drive.csv")
WINDOW_T: dict = {}


def baselines(r):
    pre, clear = int(PRE_S / r.dt), int(CLEAR_S / r.dt)
    x = r.x
    mu, sd = np.nanmean(x, 1, keepdims=True), np.nanstd(x, 1, keepdims=True)
    z = (x - mu) / np.where(sd > 0, sd, np.nan)
    frames = sorted(set(r.all_stim_frames))
    rows, last, ts = [], -10 ** 9, []
    for f in frames:
        if f - last >= clear and f - pre >= 0:
            rows.append(np.nanmean(z[:, f - pre:f], 1))
            ts.append(f * r.dt)
        last = f
    WINDOW_T[r.uid] = np.array(ts)
    return (np.array(rows).T if rows else np.empty((x.shape[0], 0))), z


def measures(r, rng):
    b, z = baselines(r)
    good = np.isfinite(b).all(1) & (np.nanstd(b, 1) > 0)
    b = b[good]
    if b.shape[0] < SUBSET or b.shape[1] < 15:
        return None
    c = np.corrcoef(b)
    iu = np.triu_indices_from(c, 1)
    top1, top3 = [], []
    for _ in range(N_SUB):
        s = b[rng.choice(b.shape[0], SUBSET, replace=False)]
        s = (s - s.mean(1, keepdims=True)) / s.std(1, keepdims=True)
        ev = np.linalg.svd(s, compute_uv=False) ** 2
        top1.append(ev[0] / ev.sum())
        top3.append(ev[:3].sum() / ev.sum())
    slow = np.nanvar(b, 1) / np.nanvar(z[good], 1)
    # how many shared components stand above a null with each neuron's windows shuffled
    bz = (b - b.mean(1, keepdims=True)) / b.std(1, keepdims=True)
    ev = np.linalg.svd(bz, compute_uv=False) ** 2
    null = np.array([np.linalg.svd(np.array([rng.permutation(row) for row in bz]), compute_uv=False) ** 2
                     for _ in range(30)])
    n_shared = int(np.sum(ev > np.percentile(null, 95, axis=0)))
    # timescale of the main shared component: correlation of its score between consecutive windows
    u, sv, vt = np.linalg.svd(bz, full_matrices=False)
    score = vt[0] * sv[0]
    gaps = np.diff(WINDOW_T[r.uid])
    ok = (gaps > 25) & (gaps < 40)
    ac1 = float(np.corrcoef(score[:-1][ok], score[1:][ok])[0, 1]) if ok.sum() > 8 else np.nan
    tau = float(-np.median(gaps[ok]) / np.log(ac1)) if np.isfinite(ac1) and 0 < ac1 < 1 else np.nan
    return {"n_shared": n_shared, "pc1_ac_31s": ac1, "pc1_tau_s": tau, "neurons": b.shape[0], "windows": b.shape[1], "baseline_corr": float(np.nanmean(np.abs(c[iu]))),
            "top1": float(np.mean(top1)), "top3": float(np.mean(top3)), "slow_share": float(np.nanmedian(slow))}


def main() -> int:
    rng = np.random.default_rng(0)
    rows = []
    for cond, d in (("wt", "data/raw/randi2023_wt_npz"), ("unc31", "data/raw/randi2023_unc31_npz")):
        for r in load_pumpprobe_dir(d):
            m = measures(r, rng)
            if m:
                rows.append({"condition": cond, "uid": r.uid, **{k: round(v, 4) if isinstance(v, float) else v for k, v in m.items()}})
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for key in ("baseline_corr", "top1", "top3", "slow_share", "n_shared", "pc1_ac_31s", "pc1_tau_s"):
        a = np.array([r[key] for r in rows if r["condition"] == "wt"], float)
        u = np.array([r[key] for r in rows if r["condition"] == "unc31"], float)
        a, u = a[np.isfinite(a)], u[np.isfinite(u)]
        boot = [np.median(rng.choice(u, len(u))) - np.median(rng.choice(a, len(a))) for _ in range(5000)]
        perm = []
        allv = np.concatenate([a, u])
        obs = np.median(u) - np.median(a)
        for _ in range(5000):
            p = rng.permutation(allv)
            perm.append(np.median(p[len(a):]) - np.median(p[:len(a)]))
        pval = float(np.mean(np.abs(perm) >= abs(obs)))
        print(f"{key:14s} wt {np.median(a):.3f} (n={len(a)})  unc31 {np.median(u):.3f} (n={len(u)})  "
              f"diff {obs:+.3f} [{np.percentile(boot, 5):+.3f}, {np.percentile(boot, 95):+.3f}]  p={pval:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
