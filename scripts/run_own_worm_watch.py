"""Per-worm test of "record everything" (pre-registered in the README, 2 Nov 2026).

For each wild-type atlas worm: a linear model z(t+1) = A z(t) + B u(t) + c is fitted by
ridge to that worm's unpoked frames only (frames at least 30 s after any stimulation), in
three versions:
  A_named      named neurons only
  B_all        every tracked neuron
  C_all_slow   every tracked neuron, plus u = the worm's 3 strongest slow patterns
               (all its tracked activity smoothed over 30 s, principal components)
The ridge is chosen per worm on held-out stretches (every fifth unpoked stretch).
Each model is poked like the worm: for every stimulation of a named neuron, the target's
deviation is held to its own measured response for 15 s and the others evolve under A.
Echo amplitude: mean deviation over the first 15 s (measured: minus the 5 s before).
Score per worm: correlation of predicted and measured amplitudes over (named target, named
responder) pairs, the same pairs for every version. Reference: the leave-one-out average
of the other worms' measured amplitudes for the same pairs.

Output: docs/figures/own_worm_watch.csv

Usage:  python scripts/run_own_worm_watch.py
"""

from __future__ import annotations

import csv
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.systems.causal_models import spontaneous_mask  # noqa: E402

PRE, AMP = 10, 30            # 5 s before, 15 s after, at 0.5 s frames
RIDGES = (1.0, 10.0, 100.0, 1000.0, 10000.0)
OUT = Path("docs/figures/own_worm_watch.csv")


def zscore(x):
    out = np.empty_like(x)
    for i, row in enumerate(x):
        ok = np.isfinite(row)
        if ok.sum() < 10:
            out[i] = np.nan
            continue
        r = np.interp(np.arange(len(row)), np.flatnonzero(ok), row[ok])
        out[i] = (r - r.mean()) / (r.std() or 1.0)
    return out


def slow(z, k=3, w=60):
    ker = np.ones(w) / w
    sm = np.array([np.convolve(r, ker, mode="same") for r in z])
    u, s, vt = np.linalg.svd(sm, full_matrices=False)
    sc = vt[:k].T * s[:k]
    return (sc - sc.mean(0)) / np.maximum(sc.std(0), 1e-9)


def segments(mask):
    segs, start = [], None
    for t, m in enumerate(mask):
        if m and start is None:
            start = t
        if not m and start is not None:
            segs.append((start, t))
            start = None
    if start is not None:
        segs.append((start, len(mask)))
    return [s for s in segs if s[1] - s[0] >= 4]


def design(z, U, segs):
    X, Y = [], []
    for a, b in segs:
        ts = np.arange(a + 1, b)
        X.append(np.hstack([z[:, ts - 1].T, U[ts - 1], np.ones((ts.size, 1))]))
        Y.append(z[:, ts].T)
    return np.vstack(X), np.vstack(Y)


def fit(z, U, segs):
    val = segs[::5]
    tr = [s for i, s in enumerate(segs) if i % 5]
    Xt, Yt = design(z, U, tr)
    Xv, Yv = design(z, U, val)
    best = None
    for lam in RIDGES:
        P = np.eye(Xt.shape[1]) * lam
        P[-1, -1] = 0
        W = np.linalg.solve(Xt.T @ Xt + P, Xt.T @ Yt)
        err = np.mean((Xv @ W - Yv) ** 2)
        if best is None or err < best[0]:
            best = (err, lam)
    X, Y = design(z, U, segs)
    P = np.eye(X.shape[1]) * best[1]
    P[-1, -1] = 0
    W = np.linalg.solve(X.T @ X + P, X.T @ Y)
    n = z.shape[0]
    A = W[:n].T
    r = np.abs(np.linalg.eigvals(A)).max()
    if r > 0.99:
        A = A * 0.99 / r
    return A, best[1]


def predict(A, z, k, f):
    n = A.shape[0]
    tgt = z[k, f:f + AMP] - z[k, f - PRE:f].mean()
    d = np.zeros(n)
    acc = np.zeros(n)
    for t in range(AMP):
        d = A @ d
        d[k] = tgt[t]
        acc += d
    return acc / AMP


def measured(z, f):
    return z[:, f:f + AMP].mean(1) - z[:, f - PRE:f].mean(1)


def main() -> int:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    recs = load_pumpprobe_dir("data/raw/randi2023_wt_npz")
    # measured echoes of every worm, by (target class, responder class), for the reference
    meas = {}
    prepared = []
    for r in recs:
        z = zscore(r.x)
        keep = np.isfinite(z).all(1)
        named = np.array([bool(c) and c != "TARGET" for c in r.classes])
        T = z.shape[1]
        stims = [(k, f) for k, f in r.stims if named[k] and keep[k] and f - PRE >= 0 and f + AMP <= T]
        d = {}
        for k, f in stims:
            m = measured(z, f)
            for j in np.flatnonzero(named & keep):
                if j != k and r.classes[j] != r.classes[k]:
                    d.setdefault((r.classes[k], r.classes[j]), []).append(m[j])
        meas[r.uid] = {key: float(np.mean(v)) for key, v in d.items()}
        prepared.append((r, z, keep, named, stims))
    rows = []
    for r, z, keep, named, stims in prepared:
        mask = spontaneous_mask(r)
        segs = segments(mask)
        n_spont = sum(b - a for a, b in segs)
        if len(stims) < 10 or n_spont < 200 or len(segs) < 5:
            continue
        idx_all = np.flatnonzero(keep)
        idx_named = np.flatnonzero(keep & named)
        zall = z[idx_all]
        versions = {
            "A_named": (z[idx_named], np.zeros((z.shape[1], 0)), idx_named),
            "B_all": (zall, np.zeros((z.shape[1], 0)), idx_all),
            "C_all_slow": (zall, slow(zall), idx_all),
        }
        preds, lams = {}, {}
        for name, (zz, U, idx) in versions.items():
            A, lam = fit(zz, U, segs)
            lams[name] = lam
            pos = {g: i for i, g in enumerate(idx)}
            out = {}
            for k, f in stims:
                p = predict(A, zz, pos[k], f)
                for j in idx_named:
                    if j != k and r.classes[j] != r.classes[k]:
                        out.setdefault((r.classes[k], r.classes[j]), []).append(p[pos[j]])
            preds[name] = {key: float(np.mean(v)) for key, v in out.items()}
        keys = sorted(meas[r.uid])
        y = np.array([meas[r.uid][key] for key in keys])
        row = {"uid": r.uid, "tracked": int(keep.sum()), "named": int((keep & named).sum()),
               "unpoked_frames": int(n_spont), "stims": len(stims), "pairs": len(keys)}
        for name in versions:
            x = np.array([preds[name].get(key, np.nan) for key in keys])
            ok = np.isfinite(x)
            row[name] = round(float(np.corrcoef(x[ok], y[ok])[0, 1]), 4) if ok.sum() > 15 and x[ok].std() > 0 else ""
            row[f"ridge_{name}"] = lams[name]
        ref = np.array([np.nanmean([meas[u][key] for u in meas if u != r.uid and key in meas[u]]) if any(
            key in meas[u] for u in meas if u != r.uid) else np.nan for key in keys])
        ok = np.isfinite(ref)
        row["other_worms_average"] = round(float(np.corrcoef(ref[ok], y[ok])[0, 1]), 4) if ok.sum() > 15 else ""
        rows.append(row)
        print(row, flush=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from scipy.stats import wilcoxon
    get = lambda c: np.array([float(r[c]) if r[c] != "" else np.nan for r in rows])
    a, b, c, o = get("A_named"), get("B_all"), get("C_all_slow"), get("other_worms_average")
    print(f"{len(rows)} worms; median echo agreement: named {np.nanmedian(a):.3f}, all {np.nanmedian(b):.3f}, "
          f"all+slow {np.nanmedian(c):.3f}, other worms' average {np.nanmedian(o):.3f}")
    for lab, x, y in (("all - named", b, a), ("all+slow - all", c, b), ("all+slow - named", c, a)):
        ok = np.isfinite(x) & np.isfinite(y)
        print(f"  {lab}: median {np.median(x[ok] - y[ok]):+.3f}, better in {np.sum(x[ok] > y[ok])} of {ok.sum()}, "
              f"Wilcoxon p = {wilcoxon(x[ok], y[ok]).pvalue:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
