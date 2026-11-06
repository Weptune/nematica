"""Human tiring test, sensitivity analyses asked for by review 4 (exploratory; README "Do human cortical
responses tire?"). (a) blocks by unordered electrode pair, split at gaps over 6 s; (b) response strength
from the saved waveforms with the window starting at about 18 ms instead of 10 (third extraction), to keep
clear of the blanked artefact. Everything else as run_ccep_tiring.py. Output appended to
docs/figures/ccep_tiring.txt."""
from __future__ import annotations

import glob
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_ccep_tiring as T  # noqa: E402


def blocks_unordered(sites, site, onset):
    key = [frozenset(p.strip() for p in sites[s].split("-")) for s in site]
    out, start = [], 0
    for k in range(1, len(site) + 1):
        if k == len(site) or key[k] != key[start] or onset[k] - onset[k - 1] > 6.0:
            out.append((int(site[start]), list(range(start, k))))
            start = k
    return out


def units(f, from_wave):
    d = np.load(f)
    names, xyz, sites = list(d["names"]), d["xyz"], list(d["sites"])
    order = np.argsort(d["pulse_onset_s"])
    ok, site, onset = d["pulse_ok"][order], d["pulse_site"][order], d["pulse_onset_s"][order]
    P = d["pulse_pre_rms"].astype(float)[order]
    if from_wave:
        W = d["pulse_wave"].astype(float)[order]           # 10 to 100 ms at 256 Hz; drop the first two bins
        R = np.sqrt(np.nanmean(W[:, :, 2:] ** 2, axis=2))     # bins of 3.9 ms: from about 18 ms
    else:
        R = d["pulse_resp_rms"].astype(float)[order]
    resp = []
    for s, idx in blocks_unordered(sites, site, onset):
        valid = [k for k in idx if ok[k]]
        if len(valid) < T.MIN_PULSES:
            continue
        pair = [p.strip() for p in sites[s].split("-")]
        pidx = [names.index(p) for p in pair if p in names]
        pxyz = [xyz[i] for i in pidx if np.isfinite(xyz[i]).all()]
        if not pxyz:
            continue
        dist = np.min([np.linalg.norm(xyz - q, axis=1) for q in pxyz], axis=0)
        r, p = R[idx].copy(), P[idx].copy()
        r[~ok[idx]] = np.nan
        p[~ok[idx]] = np.nan
        with np.errstate(all="ignore"):
            lr, lp = np.log(r), np.log(p)
            lratio = np.nanmean(lr - lp, axis=0)
        for c in range(len(names)):
            if c in pidx or not (dist[c] > T.NEAR_MM) or not np.isfinite(lratio[c]) or lratio[c] < T.RESP_LR:
                continue
            resp.append(T.slope(lr[:, c]))
    return resp


def run(src, from_wave, label):
    by = defaultdict(list)
    for f in sorted(glob.glob(str(src / "*.npz"))):
        pid = re.search(r"sub-(ccepAge\w+?)_", Path(f).name).group(1)
        by[pid] += units(f, from_wave)
    per = {k: float(np.nanmedian(v)) for k, v in by.items() if v}
    lines = [f"EXPLORATORY sensitivity (review 4), {label}: {len(per)} patients"]
    T.summarise(per, "slope of log response per pulse", lines, 11)
    return lines


def main():
    lines = run(ROOT / "data" / "derived" / "ccep_v2", False, "blocks by unordered pair split at gaps over 6 s")
    if (ROOT / "data" / "derived" / "ccep_v3").exists():
        lines += run(ROOT / "data" / "derived" / "ccep_v3", True, "same blocks, window from about 18 ms (third extraction)")
    print("\n".join(lines))
    with (ROOT / "docs" / "figures" / "ccep_tiring.txt").open("a") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
