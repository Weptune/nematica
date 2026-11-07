"""Neuron or tool (pre-registered 8 Nov 2026, README "Neuron or tool: does a worm neuron's resting level drop
before its second poke?").

For each recording: repeat pairs (a target's first two pokes) and control pairs (first pokes of two
different neurons about the same time apart; up to 5 nearest in time, as run_week1.b1_pairs). Levels of
the target in units of its unpoked SD, relative to its unpoked mean: pre = mean over the 10 s before the
poke, post = mean over the 15 s after. Per recording: mean change (second minus first) over repeats
minus mean change over controls. 90% bootstrap over recordings.

Usage:  python scripts/run_neuron_or_tool.py
Output: docs/figures/neuron_or_tool.csv
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_week1 as W  # noqa: E402

OUT = ROOT / "docs" / "figures" / "neuron_or_tool.csv"


def levels(w, k, f):
    X = w.r.x
    with np.errstate(all="ignore"):
        pre = (np.nanmean(X[k, f - W.PRE:f]) - w.mu_u[k]) / w.sd[k]
        post = (np.nanmean(X[k, f:f + W.POST]) - w.mu_u[k]) / w.sd[k]
    return pre, post


def per_recording(w):
    by = defaultdict(list)
    for k, f, _ in w.stims:
        by[k].append(f)
    first = sorted((fs[0], k) for k, fs in ((k, sorted(v)) for k, v in by.items()))
    dr, dc = [], []
    for k, fs in by.items():
        if len(fs) < 2:
            continue
        f1, f2 = sorted(fs)[:2]
        p1, q1 = levels(w, k, f1)
        p2, q2 = levels(w, k, f2)
        gap = f2 - f1
        tol = max(0.2 * gap, 60)
        cand = []
        for a in range(len(first)):
            for b in range(a + 1, len(first)):
                fx, kx = first[a]
                fy, ky = first[b]
                if kx == ky or abs((fy - fx) - gap) > tol:
                    continue
                cand.append((abs(fx - f1), kx, fx, ky, fy))
        cand.sort(key=lambda t: t[0])
        cs = []
        for _, kx, fx, ky, fy in cand[:5]:
            px, qx = levels(w, kx, fx)
            py, qy = levels(w, ky, fy)
            cs.append((py - px, qy - qx))
        if not cs or not np.isfinite([p1, p2, q1, q2]).all():
            continue
        dr.append((p2 - p1, q2 - q1))
        dc += cs
    if not dr or not dc:
        return None
    dr, dc = np.array(dr), np.array(dc)
    return np.nanmean(dr, 0) - np.nanmean(dc, 0)


def summarise(name, worms):
    v = np.array([x for x in (per_recording(w) for w in worms) if x is not None])
    rng = np.random.default_rng(0)
    bs = np.array([np.nanmean(v[rng.integers(0, len(v), len(v))], 0) for _ in range(2000)])
    lo, hi = np.nanpercentile(bs, [5, 95], axis=0)
    m = np.nanmean(v, 0)
    row = {"system": name, "recordings": len(v), "pre_change": round(float(m[0]), 3), "pre_lo": round(float(lo[0]), 3),
           "pre_hi": round(float(hi[0]), 3), "post_change": round(float(m[1]), 3), "post_lo": round(float(lo[1]), 3),
           "post_hi": round(float(hi[1]), 3)}
    print(row, flush=True)
    return row


def main():
    rows = [summarise("worms", W.load_worms())]
    from nematica import spiking as S
    valid = lambda c: True  # noqa: E731
    for v in ("S0", "S5", "S6"):
        kf, kd = S.KF, S.KD
        if v == "S5":
            S.KF = 4 * kf
        try:
            recs = S.recordings(v, n_ind=40, n_targets=14)
        finally:
            S.KF, S.KD = kf, kd
        rows.append(summarise(f"spiking {v}@w", [W.Worm(r, valid_fn=valid) for r in recs]))
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
