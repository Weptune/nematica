"""Do human cortical responses tire? (pre-registered 6 Nov 2026; README section of the same name).

Reads the second extraction (data/derived/ccep_v2/*.npz, scripts/ccep_extract_v2.py).
Units: (recording, block, responding channel). A block is a run of consecutive pulses at the same
ordered stimulated pair with at least 4 valid pulses. Responding: not one of the pair, more than 10 mm
from both stimulated electrodes, block mean of log(response / pre-pulse) at least log 2.
Per unit: least-squares slope of log response on pulse number; the same for log pre-pulse strength;
log response of pulse 2 minus pulse 1. Control: slope of log response in non-responding channels
(more than 10 mm away, block-mean log ratio below log 1.2).
Per patient: medians over units; across patients: median, 95% interval by resampling patients
(2,000), sign test.

Usage: python scripts/run_ccep_tiring.py [--dry]     (--dry: counts only, no statistics)
Output: docs/figures/ccep_tiring.txt
"""
from __future__ import annotations

import glob
import re
import sys
from collections import defaultdict
from math import comb
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "derived" / "ccep_v2"
OUT = ROOT / "docs" / "figures" / "ccep_tiring.txt"
MIN_PULSES, NEAR_MM = 4, 10.0
RESP_LR, QUIET_LR = np.log(2.0), np.log(1.2)


def slope(y):
    x = np.arange(len(y), dtype=float)
    m = np.isfinite(y)
    if m.sum() < MIN_PULSES:
        return np.nan
    x, y = x[m], y[m]
    x = x - x.mean()
    return float((x * (y - y.mean())).sum() / (x * x).sum())


def blocks(site):
    """Runs of consecutive pulses at the same site: list of (site index, pulse indices)."""
    out, start = [], 0
    for k in range(1, len(site) + 1):
        if k == len(site) or site[k] != site[start]:
            out.append((int(site[start]), list(range(start, k))))
            start = k
    return out


def units_of(f):
    d = np.load(f, allow_pickle=False)
    names, xyz, sites = list(d["names"]), d["xyz"], list(d["sites"])
    ok, R, P = d["pulse_ok"], d["pulse_resp_rms"].astype(float), d["pulse_pre_rms"].astype(float)
    order = np.argsort(d["pulse_onset_s"])
    site = d["pulse_site"][order]
    ok, R, P = ok[order], R[order], P[order]
    resp, quiet = [], []
    for s, idx in blocks(site):
        valid = [k for k in idx if ok[k]]
        if len(valid) < MIN_PULSES:
            continue
        pair = [p.strip() for p in sites[s].split("-")]
        pidx = [names.index(p) for p in pair if p in names]
        pxyz = [xyz[i] for i in pidx if np.isfinite(xyz[i]).all()]
        if not pxyz:
            continue
        dist = np.min([np.linalg.norm(xyz - q, axis=1) for q in pxyz], axis=0)
        r, p = R[idx], P[idx]
        r[~ok[idx]] = np.nan
        p[~ok[idx]] = np.nan
        with np.errstate(all="ignore"):
            lr, lp = np.log(r), np.log(p)
            lratio = np.nanmean(lr - lp, axis=0)
        for c in range(len(names)):
            if c in pidx or not (dist[c] > NEAR_MM) or not np.isfinite(lratio[c]):
                continue
            if lratio[c] >= RESP_LR:
                sr, sp = slope(lr[:, c]), slope(lp[:, c])
                d21 = lr[1, c] - lr[0, c] if np.isfinite(lr[0, c]) and np.isfinite(lr[1, c]) else np.nan
                resp.append((sr, sp, sr - sp if np.isfinite(sr) and np.isfinite(sp) else np.nan, d21))
            elif lratio[c] < QUIET_LR:
                quiet.append(slope(lr[:, c]))
    return resp, quiet


def summarise(per, label, lines, seed=0):
    pats = sorted(k for k in per if np.isfinite(per[k]))
    v = np.array([per[k] for k in pats])
    rng = np.random.default_rng(seed)
    boot = [np.median(v[rng.integers(0, len(v), len(v))]) for _ in range(2000)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    neg = int((v < 0).sum())
    n = len(v)
    p = min(1.0, 2 * sum(comb(n, k) for k in range(0, min(neg, n - neg) + 1)) / 2 ** n) if n else np.nan
    lines.append(f"  {label}: median {np.median(v):+.4f} [95%: {lo:+.4f}, {hi:+.4f}], {neg} of {n} patients below 0, sign test p = {p:.3g}")
    return np.median(v), lo, hi


def main():
    dry = "--dry" in sys.argv
    files = sorted(glob.glob(str(SRC / "*.npz")))
    by = defaultdict(lambda: {"resp": [], "quiet": []})
    for f in files:
        pid = re.search(r"sub-(ccepAge\w+?)_", Path(f).name).group(1)
        r, q = units_of(f)
        by[pid]["resp"] += r
        by[pid]["quiet"] += q
    n_units = sum(len(v["resp"]) for v in by.values())
    lines = [f"{len(files)} recordings, {len(by)} patients, {n_units} responding units, "
             f"{sum(len(v['quiet']) for v in by.values())} non-responding units"]
    if dry:
        print("\n".join(lines))
        return
    med = lambda xs: float(np.nanmedian(xs)) if len(xs) and np.isfinite(xs).any() else np.nan  # noqa: E731
    per_slope = {k: med([u[0] for u in v["resp"]]) for k, v in by.items()}
    per_pre = {k: med([u[1] for u in v["resp"]]) for k, v in by.items()}
    per_diff = {k: med([u[2] for u in v["resp"]]) for k, v in by.items()}
    per_d21 = {k: med([u[3] for u in v["resp"]]) for k, v in by.items()}
    per_quiet = {k: med(v["quiet"]) for k, v in by.items()}
    m, lo, hi = summarise(per_slope, "slope of log response per pulse (primary)", lines)
    _, dlo, dhi = summarise(per_diff, "slope minus pre-pulse slope", lines, 1)
    summarise(per_pre, "pre-pulse slope (control)", lines, 2)
    summarise(per_quiet, "non-responding channels' slope (control)", lines, 3)
    summarise(per_d21, "pulse 2 minus pulse 1, log response", lines, 4)
    if hi < 0 and dhi < 0:
        verdict = "HUMAN RESPONSES TIRE (both intervals below 0)"
    elif lo <= 0 <= hi and lo > -0.01:
        verdict = "NO DETECTABLE TIRING (interval includes 0, lower end above -0.01 per pulse)"
    else:
        verdict = "INCONCLUSIVE by the pre-registered rule"
    lines.append(f"  verdict: {verdict}")
    text = "\n".join(lines)
    print(text)
    OUT.write_text(text + "\n")


if __name__ == "__main__":
    main()
