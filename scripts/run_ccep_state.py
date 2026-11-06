"""Does the brain's state change where a pulse spreads in human cortex? (pre-registered 6 Nov 2026;
README section of the same name). Reads the third extraction (data/derived/ccep_v3/*.npz).

Usage: python scripts/run_ccep_state.py [--dry]
Output: docs/figures/ccep_state.txt
"""
from __future__ import annotations

import glob
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "derived" / "ccep_v3"
OUT = ROOT / "docs" / "figures" / "ccep_state.txt"
MIN_PULSES, NEAR_MM, N_NULL = 8, 10.0, 200


def blocks(site):
    out, start = [], 0
    for k in range(1, len(site) + 1):
        if k == len(site) or site[k] != site[start]:
            out.append((int(site[start]), list(range(start, k))))
            start = k
    return out


def pattern(W, idx):
    """log RMS over time of the averaged waveform of pulses idx, per channel."""
    m = np.nanmean(W[idx], axis=0)
    return np.log(np.sqrt(np.nanmean(m ** 2, axis=1)) + 1e-9)


def corr(a, b):
    k = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[k], b[k])[0, 1]) if k.sum() >= 10 else np.nan


def block_scores(f, rng):
    d = np.load(f)
    names, xyz, sites = list(d["names"]), d["xyz"], list(d["sites"])
    order = np.argsort(d["pulse_onset_s"])
    ok = d["pulse_ok"][order]
    W = d["pulse_wave"][order].astype(np.float64)
    S = d["pulse_state"][order].astype(np.float64)
    site = d["pulse_site"][order]
    out = []
    for s, idx in blocks(site):
        idx = [k for k in idx if ok[k] and np.isfinite(S[k]).sum() > 10]
        if len(idx) < MIN_PULSES:
            continue
        pair = [p.strip() for p in sites[s].split("-")]
        pidx = [names.index(p) for p in pair if p in names]
        pxyz = [xyz[i] for i in pidx if np.isfinite(xyz[i]).all()]
        if not pxyz:
            continue
        dist = np.min([np.linalg.norm(xyz - q, axis=1) for q in pxyz], axis=0)
        far = np.where((dist > NEAR_MM) & np.isfinite(dist))[0]
        far = np.array([c for c in far if c not in pidx])
        if len(far) < 10:
            continue
        St = S[np.ix_(idx, far)]
        St = St[:, np.isfinite(St).all(0)]
        if St.shape[1] < 5:
            continue
        St = St - St.mean(0)
        u, sv, vt = np.linalg.svd(St, full_matrices=False)
        load = vt[0]
        if load.mean() < 0:
            load = -load
        state = St @ load
        rank = np.argsort(np.argsort(state))
        n = len(idx)
        hi = [idx[k] for k in range(n) if rank[k] >= n - n // 2]
        lo = [idx[k] for k in range(n) if rank[k] < n // 2]
        Wf = W[:, far]
        s_state = corr(pattern(Wf, hi), pattern(Wf, lo))
        first, second = idx[: n // 2], idx[n - n // 2:]
        s_order = corr(pattern(Wf, first), pattern(Wf, second))
        null = []
        for _ in range(N_NULL):
            p = rng.permutation(idx)
            null.append(corr(pattern(Wf, list(p[: n // 2])), pattern(Wf, list(p[n - n // 2:]))))
        mnull = np.nanmean(null)
        out.append((s_state - mnull, s_order - mnull, mnull, (s_state - mnull) / max(1e-6, 1 - mnull)))
    return out


def summarise(per, label, lines, seed):
    v = np.array([per[k] for k in sorted(per) if np.isfinite(per[k])])
    rng = np.random.default_rng(seed)
    boot = [np.median(v[rng.integers(0, len(v), len(v))]) for _ in range(2000)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    flips = np.array([np.median(v * rng.choice([-1, 1], len(v))) for _ in range(10000)])
    p = (np.sum(flips <= np.median(v)) + 1) / 10001
    lines.append(f"  {label}: median {np.median(v):+.4f} [95%: {lo:+.4f}, {hi:+.4f}], {int((v < 0).sum())} of {len(v)} patients below 0, sign-flip p (below) = {p:.4f}")
    return np.median(v), lo, hi, p


def main():
    dry = "--dry" in sys.argv
    files = sorted(glob.glob(str(SRC / "*.npz")))
    rng = np.random.default_rng(0)
    by = defaultdict(list)
    for f in files:
        pid = re.search(r"sub-(ccepAge\w+?)_", Path(f).name).group(1)
        if dry:
            d = np.load(f)
            by[pid].append(len(blocks(d["pulse_site"][np.argsort(d["pulse_onset_s"])])))
            continue
        by[pid] += block_scores(f, rng)
    lines = [f"{len(files)} recordings, {len(by)} patients, {sum(len(v) for v in by.values())} blocks"]
    if dry:
        print("\n".join(lines))
        return
    per_state = {k: float(np.nanmedian([b[0] for b in v])) for k, v in by.items() if v}
    per_order = {k: float(np.nanmedian([b[1] for b in v])) for k, v in by.items() if v}
    m, lo, hi, p = summarise(per_state, "S, state split minus random splits (primary)", lines, 1)
    mo, _, _, _ = summarise(per_order, "positive control: order split (first half against second) minus random splits", lines, 2)
    if m < 0 and p < 0.05:
        v = "STATE DEPENDENCE"
    elif lo <= 0 <= hi and lo > -0.02:
        v = "NONE DETECTED"
    else:
        v = "INCONCLUSIVE"
    if "--scale" in sys.argv:   # review 5: the level of the random-split correlation, and S relative to its distance from 1
        per_null = {k: float(np.nanmedian([b[2] for b in v])) for k, v in by.items() if v}
        per_rel = {k: float(np.nanmedian([b[3] for b in v])) for k, v in by.items() if v}
        nv = np.array(list(per_null.values()))
        lines.append(f"  EXPLORATORY (review 5): random-split correlation, median over patients {np.median(nv):.4f}")
        summarise(per_rel, "S relative to (1 - random-split correlation)", lines, 3)
    lines.append(f"  verdict: {v}; control check: order split {'differs less' if abs(mo) <= abs(m) else 'differs MORE'} from random splits than the state split does")
    text = "\n".join(lines)
    print(text)
    if "--scale" in sys.argv:
        with OUT.open("a") as fh:
            fh.write("\n".join(l for l in lines if "EXPLORATORY" in l or "relative" in l) + "\n")
    else:
        OUT.write_text(text + "\n")


if __name__ == "__main__":
    main()
