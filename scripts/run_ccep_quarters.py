"""Watching limit, part E (pre-registered 7 Nov 2026): does watching human cortex improve with
more rest data? Recordings re-extracted with NEMATICA_CCEP_QUARTERS=1 store the between-pulse
statistics per quarter of the recording. The human test's own watching copy
(scripts/run_ccep_test.py: VAR(5), same ridge, same pulse) is fitted from a quarter (each of the
four, averaged), a half (first and second halves, averaged) and all of the data, and scored the
same way: Spearman correlation with the measured response strength (RMS 10 to 100 ms) over
(stimulated pair, electrode).

Usage:  python scripts/run_ccep_quarters.py [--data data/derived/ccep_q]
Output: docs/figures/ccep_quarters.csv and ccep_quarters.txt
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_ccep_test as R  # noqa: E402


def score(r, XtX, XtY):
    z = {"XtX": XtX, "XtY": XtY}
    meas, w = [], []
    for s, site in enumerate(r["sites"]):
        idx = R.pair_index(r, site)
        stim = [i for i in idx if i is not None]
        if not stim or r["n"][s] < 4:
            continue
        pos = [idx[0]] if idx[0] is not None else []
        neg = [idx[1]] if len(idx) > 1 and idx[1] is not None else []
        wpm = R.watching_response(z, pos, neg)
        for c in range(len(r["names"])):
            if c in stim or not np.isfinite(r["amp"][s, c]):
                continue
            meas.append(r["amp"][s, c])
            w.append(wpm[c])
    return R.spearman(w, meas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/derived/ccep_q")
    a = ap.parse_args()
    rows = []
    for f in sorted(glob.glob(os.path.join(a.data, "*.npz"))):
        if f.endswith(".part.npz"):
            continue
        r = R.load_recording(f)
        z = r["z"]
        if "XtX_q" not in z.files:
            continue
        Xq, Yq, nq = z["XtX_q"], z["XtY_q"], z["n_rows_q"]
        quarter = [score(r, Xq[i], Yq[i]) for i in range(4) if nq[i] > 0]
        half = [score(r, Xq[0] + Xq[1], Yq[0] + Yq[1]), score(r, Xq[2] + Xq[3], Yq[2] + Yq[3])]
        full = score(r, Xq.sum(0), Yq.sum(0))
        row = {"recording": Path(f).stem, "rows_per_quarter": "/".join(str(int(x)) for x in nq),
               "quarter": round(float(np.nanmean(quarter)), 4), "half": round(float(np.nanmean(half)), 4),
               "all": round(float(full), 4)}
        rows.append(row)
        print(row, flush=True)
    out = Path("docs/figures")
    with (out / "ccep_quarters.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    gain_q = [r["half"] - r["quarter"] for r in rows]
    gain_h = [r["all"] - r["half"] for r in rows]
    txt = [f"{len(rows)} recordings",
           f"median watching: quarter {np.median([r['quarter'] for r in rows]):.3f}, half "
           f"{np.median([r['half'] for r in rows]):.3f}, all {np.median([r['all'] for r in rows]):.3f}",
           f"median gain quarter->half {np.median(gain_q):+.3f}; half->all {np.median(gain_h):+.3f}",
           f"prediction (plateau, median gain half->all below 0.02): {'holds' if np.median(gain_h) < 0.02 else 'refuted'}"]
    (out / "ccep_quarters.txt").write_text("\n".join(txt) + "\n")
    print("\n".join(txt))


if __name__ == "__main__":
    main()
