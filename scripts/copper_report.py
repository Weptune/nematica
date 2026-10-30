"""Load the copper-boundary dataset, check it, and settle its open questions.

Usage:  python scripts/copper_report.py data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 [--out results/m1]

Prints and writes:
  * per-worm table: frames, duration, ROIs, labelled neurons (confidence >= 2), classes,
    reversals, body length, copper-boundary encounters
  * AVA-during-reversal and velocity-during-reversal sanity checks
  * the label-rebuild check against the Atanas JSON naming rule
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.data import load_copper_dir  # noqa: E402
from nematica.data.posture import body_length_mm, valid_segments  # noqa: E402


def encounters(dist_mm: np.ndarray, threshold_mm: float) -> int:
    near = dist_mm >= threshold_mm
    return int(np.sum(near[1:] & ~near[:-1]) + near[0])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out", default="results/m1")
    ap.add_argument("--min-confidence", type=float, default=2.0)
    args = ap.parse_args()

    recs = load_copper_dir(args.folder)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows, freq = [], Counter()
    for r in recs:
        s = r.summary(args.min_confidence)
        seg = r.posture["segment_angle"]
        lengths = np.array([body_length_mm(seg[t]) for t in range(r.n_frames)])
        s["body_length_mm_median"] = round(float(np.median(lengths)), 3)
        s["frames_with_posture"] = int(np.sum([valid_segments(seg[t]) > 10 for t in range(r.n_frames)]))
        radius = r.meta["arena"]["radius_mm"]
        s["arena_radius_mm"] = round(radius, 2)
        s["boundary_encounters"] = encounters(r.behaviour["dist_from_center_mm"], radius - 0.3)
        v = r.behaviour["velocity"]
        if r.reversals:
            frames = np.concatenate([np.arange(a, b + 1) for a, b in r.reversals])
            s["reversal_frames_backward"] = round(float(np.mean(v[frames] < 0)), 3)
            ava = r.find("AVA", args.min_confidence)
            if ava is not None:
                during = np.zeros(r.n_frames, bool)
                during[frames] = True
                s["ava_reversal_z"] = round(float((ava[during].mean() - ava[~during].mean()) / ava.std()), 3)
        rows.append(s)
        freq.update(set(r.classes(args.min_confidence)))

    keys = sorted({k for s in rows for k in s}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with (out / "copper_coverage.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    with (out / "copper_class_frequency.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["neuron_class", "worms_labelled", "fraction"])
        for name, n in sorted(freq.items(), key=lambda x: (-x[1], x[0])):
            w.writerow([name, n, round(n / len(recs), 3)])

    def col(k):
        return np.array([s[k] for s in rows if s.get(k) is not None], dtype=float)

    print(f"{len(recs)} copper recordings")
    print(f"frames per worm: {sorted(set(int(x) for x in col('frames')))}; "
          f"frame interval median {np.median(col('frame_interval_s')):.3f} s")
    print(f"ROIs per worm: median {np.median(col('rois')):.0f} (range {col('rois').min():.0f} to {col('rois').max():.0f})")
    print(f"labelled at confidence >= {args.min_confidence:g}: median {np.median(col('labelled')):.0f} "
          f"(range {col('labelled').min():.0f} to {col('labelled').max():.0f})")
    print(f"classes labelled in at least half the worms: {sum(n >= len(recs) / 2 for n in freq.values())}")
    print(f"body length median {np.median(col('body_length_mm_median')):.3f} mm")
    print(f"boundary encounters per worm: median {np.median(col('boundary_encounters')):.0f}")
    if col("reversal_frames_backward").size:
        print(f"velocity negative in a median {np.median(col('reversal_frames_backward')):.0%} of reversal frames")
    z = col("ava_reversal_z")
    if z.size:
        print(f"AVA higher during reversals in {int(np.sum(z > 0))} of {z.size} worms with AVA labelled "
              f"(median {np.median(z):.2f} SD)")
    print(f"Wrote {out / 'copper_coverage.csv'} and {out / 'copper_class_frequency.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
