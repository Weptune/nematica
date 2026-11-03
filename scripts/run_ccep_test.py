"""Human test, step 2: score watching copies of human brains against their own pokes.

Runs on the per-recording summaries written by ccep_extract.py (data/derived/ccep/*.npz).
Everything here was fixed in the README ("Analysis details, fixed 3 Nov 2026") before any
reduced human recording was looked at.

Per recording, for every (stimulated pair, electrode) with the pair's own electrodes left out:
  measured     RMS of the average response, 10 to 100 ms
  ceiling      Spearman, odd-pulse against even-pulse response strength
  watching     a VAR(5) fitted to the between-pulse activity, pulsed (+1, -1) at the pair
  distance     1 / distance to the nearer stimulated electrode
  others       other patients' mean z-scored log response for the same Destrieux region pair
Scores are Spearman correlations with the measured strengths, over all electrodes and over
electrodes more than 20 mm from both stimulated electrodes; recordings are averaged per
patient (weighted by pairs scored).

Output: docs/figures/ccep_recordings.csv, ccep_patients.csv, ccep_summary.txt

Usage:  python scripts/run_ccep_test.py [--data data/derived/ccep]
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

FS_OUT, WIN0 = 256, -0.05            # stored responses: 256 Hz from -50 ms
FS, LAGS = 512, 5
FAR_MM = 20.0
RIDGE = 1e-3
MIN_SITES, MIN_CEILING, MIN_OTHERS = 10, 0.2, 3


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 10:
        return np.nan
    ra = np.argsort(np.argsort(a[ok])).astype(float)
    rb = np.argsort(np.argsort(b[ok])).astype(float)
    if ra.std() == 0 or rb.std() == 0:
        return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])


def rms_window(w, fs, t0, lo=0.010, hi=0.100):
    i0, i1 = int(round((lo - t0) * fs)), int(round((hi - t0) * fs))
    with np.errstate(invalid="ignore"):
        return np.sqrt(np.nanmean(w[..., i0:i1] ** 2, axis=-1))


def watching_response(z, idx_pos, idx_neg):
    """Pulse a VAR(5) fitted from stored statistics; returns RMS 10-100 ms per channel."""
    XtX, XtY = z["XtX"], z["XtY"]
    C = XtY.shape[1]
    d = XtX.shape[0]
    pen = RIDGE * np.mean(np.diag(XtX)[:-1]) * np.ones(d)
    pen[-1] = 0.0
    B = np.linalg.solve(XtX + np.diag(pen), XtY)
    A = [B[L * C:(L + 1) * C].T for L in range(LAGS)]            # x(t) = sum_L A[L] x(t-L-1)
    comp = np.zeros((LAGS * C, LAGS * C))
    comp[:C] = np.hstack(A)
    comp[C:, :-C] = np.eye((LAGS - 1) * C)
    rad = np.abs(np.linalg.eigvals(comp)).max()
    if rad > 0.999:
        g = 0.999 / rad
        A = [a * g ** (L + 1) for L, a in enumerate(A)]
    T = int(0.100 * FS) + 1
    x = np.zeros((T + LAGS, C))
    x[LAGS, idx_pos] = 1.0
    x[LAGS, idx_neg] = -1.0
    for t in range(LAGS + 1, T + LAGS):
        x[t] = sum(A[L] @ x[t - L - 1] for L in range(LAGS))
    w = x[LAGS:].T                                                   # (C, T) from t = 0
    return rms_window(w, FS, 0.0)


def load_recording(path):
    z = np.load(path, allow_pickle=False)
    names = [str(n) for n in z["names"]]
    sites = [str(s) for s in z["sites"]]
    no, ne = z["n_odd"].astype(float), z["n_even"].astype(float)
    odd, even = z["ccep_odd"].astype(float), z["ccep_even"].astype(float)
    tot = (no + ne)[:, None, None]
    with np.errstate(invalid="ignore", divide="ignore"):
        avg = (odd * no[:, None, None] + even * ne[:, None, None]) / np.where(tot > 0, tot, np.nan)
    return {"z": z, "names": names, "sites": sites, "xyz": z["xyz"].astype(float), "label": [str(l) for l in z["label"]],
            "amp": rms_window(avg, FS_OUT, WIN0), "amp_odd": rms_window(odd, FS_OUT, WIN0),
            "amp_even": rms_window(even, FS_OUT, WIN0), "n": no + ne}


def pair_index(rec, site):
    parts = [p.strip() for p in site.split("-")]
    return [rec["names"].index(p) if p in rec["names"] else None for p in parts]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/derived/ccep")
    ap.add_argument("--out", default="docs/figures")
    ap.add_argument("--min-sites", type=int, default=MIN_SITES)
    ap.add_argument("--min-ceiling", type=float, default=MIN_CEILING)
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(args.data, "*.npz")))
    files = [f for f in files if not f.endswith(".part.npz")]
    print(f"{len(files)} reduced recordings in {args.data}", flush=True)
    recs = {}
    for f in files:
        stem = Path(f).stem
        recs[stem] = load_recording(f)
        recs[stem]["patient"] = re.match(r"(sub-[^_]+)", stem).group(1)

    # region-pair table per patient: z-scored log response strength
    region = defaultdict(lambda: defaultdict(list))          # patient -> (stim region, resp region) -> values
    for stem, r in recs.items():
        a = np.log(r["amp"])
        fin = np.isfinite(a)
        if fin.sum() < 10:
            continue
        zs = (a - a[fin].mean()) / (a[fin].std() or 1.0)
        for s, site in enumerate(r["sites"]):
            i0 = pair_index(r, site)[0]
            if i0 is None:
                continue
            for c in range(len(r["names"])):
                if np.isfinite(zs[s, c]):
                    region[r["patient"]][(r["label"][i0], r["label"][c])].append(zs[s, c])
    region_mean = {p: {k: float(np.mean(v)) for k, v in d.items()} for p, d in region.items()}

    rows = []
    for stem, r in sorted(recs.items()):
        S, C = r["amp"].shape
        meas, odd, even, w_pm, w_pp, dist, oth, far = [], [], [], [], [], [], [], []
        for s, site in enumerate(r["sites"]):
            idx = pair_index(r, site)
            stim = [i for i in idx if i is not None]
            if not stim or r["n"][s] < 4:
                continue
            pos = [idx[0]] if idx[0] is not None else []
            neg = [idx[1]] if len(idx) > 1 and idx[1] is not None else []
            wpm = watching_response(r["z"], pos, neg)
            wpp = watching_response(r["z"], pos + neg, [])
            sx = r["xyz"][stim]
            for c in range(C):
                if c in stim or not np.isfinite(r["amp"][s, c]):
                    continue
                d = np.nanmin(np.linalg.norm(sx - r["xyz"][c], axis=1)) if np.isfinite(r["xyz"][c]).all() else np.nan
                key = (r["label"][idx[0]] if idx[0] is not None else "n/a", r["label"][c])
                vals = [region_mean[p][key] for p in region_mean if p != r["patient"] and key in region_mean[p]]
                meas.append(r["amp"][s, c]); odd.append(r["amp_odd"][s, c]); even.append(r["amp_even"][s, c])
                w_pm.append(wpm[c]); w_pp.append(wpp[c])
                dist.append(1.0 / d if d and np.isfinite(d) and d > 0 else np.nan)
                oth.append(np.mean(vals) if len(vals) >= MIN_OTHERS else np.nan)
                far.append(bool(np.isfinite(d) and d > FAR_MM))
        meas, far = np.array(meas), np.array(far, bool)
        row = {"recording": stem, "patient": r["patient"], "sites": S, "channels": C, "pairs": int(len(meas)),
               "far_pairs": int(far.sum()), "seconds_between_pulses": round(float(r["z"]["seg_seconds"]), 1),
               "ceiling": spearman(odd, even), "watching": spearman(w_pm, meas), "watching_same_sign": spearman(w_pp, meas),
               "distance": spearman(dist, meas), "others": spearman(oth, meas),
               "others_coverage": float(np.mean(np.isfinite(oth))) if len(oth) else np.nan,
               "watching_far": spearman(np.array(w_pm)[far], meas[far]) if far.any() else np.nan,
               "distance_far": spearman(np.array(dist)[far], meas[far]) if far.any() else np.nan,
               "others_far": spearman(np.array(oth)[far], meas[far]) if far.any() else np.nan}
        rows.append(row)
        print(f"  {stem}: pairs {row['pairs']}, ceiling {row['ceiling']:.2f}, watching {row['watching']:.2f}, "
              f"distance {row['distance']:.2f}, others {row['others']:.2f}", flush=True)
    os.makedirs(args.out, exist_ok=True)
    keys = list(rows[0])
    with open(os.path.join(args.out, "ccep_recordings.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows([{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rows])

    # patients: weighted means over recordings
    score_keys = ["ceiling", "watching", "watching_same_sign", "distance", "others", "watching_far", "distance_far", "others_far"]
    pats = []
    for p in sorted({r["patient"] for r in rows}):
        rr = [r for r in rows if r["patient"] == p]
        out = {"patient": p, "recordings": len(rr), "sites": int(sum(r["sites"] for r in rr)), "pairs": int(sum(r["pairs"] for r in rr))}
        for k in score_keys:
            wts = [(r["far_pairs"] if k.endswith("_far") else r["pairs"], r[k]) for r in rr if np.isfinite(r[k])]
            out[k] = float(np.average([v for _, v in wts], weights=[w_ for w_, _ in wts])) if wts and sum(w_ for w_, _ in wts) > 0 else np.nan
        out["included"] = bool(out["sites"] >= args.min_sites and np.isfinite(out["ceiling"]) and out["ceiling"] >= args.min_ceiling)
        pats.append(out)
    with open(os.path.join(args.out, "ccep_patients.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(pats[0]))
        w.writeheader()
        w.writerows([{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in pats])

    inc = [p for p in pats if p["included"]]
    rng = np.random.default_rng(0)
    lines = [f"{len(files)} recordings, {len(pats)} patients, {len(inc)} included "
             f"(at least {args.min_sites} stimulated pairs and ceiling >= {args.min_ceiling})"]
    for k in score_keys:
        v = np.array([p[k] for p in inc], float)
        v = v[np.isfinite(v)]
        if v.size:
            lines.append(f"  {k:20s} median {np.median(v):+.3f}   (n={v.size})")

    def diff(a, b, label):
        x = np.array([p[a] - p[b] for p in inc], float)
        x = x[np.isfinite(x)]
        if x.size < 3:
            lines.append(f"  {label}: too few patients")
            return
        boots = [rng.choice(x, x.size).mean() for _ in range(10000)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        lines.append(f"  {label}: mean {x.mean():+.3f}, 95% interval {lo:+.3f} to {hi:+.3f}, "
                     f"positive in {int((x > 0).sum())} of {x.size} patients")
    lines.append("Pre-registered comparisons (patient level):")
    diff("watching", "distance", "(1) watching minus distance, all electrodes")
    diff("watching_far", "distance_far", "(1) watching minus distance, beyond 20 mm")
    diff("others", "watching", "(2) other patients minus watching")
    txt = "\n".join(lines)
    print(txt)
    Path(args.out, "ccep_summary.txt").write_text(txt + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
