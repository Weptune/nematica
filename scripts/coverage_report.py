"""Per-worm coverage table and sanity checks for a folder of WormWideWeb JSON recordings.

Usage:  python scripts/coverage_report.py data/raw/atanas2023_wwweb [--out results/m1]

Writes coverage.csv (one row per worm), class_frequency.csv (how many worms label
each neuron class) and prints the AVA-reversal sanity check.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.data import load_wormwideweb_dir  # noqa: E402


def ava_reversal_check(rec) -> float | None:
    """Mean AVA activity during reversals minus outside, in units of AVA's SD."""
    ava = rec.find("AVA")
    if ava is None or not rec.reversals:
        return None
    during = np.zeros(rec.n_frames, dtype=bool)
    for a, b in rec.reversals:
        during[a: b + 1] = True
    during &= rec.valid
    outside = ~during & rec.valid
    sd = ava[rec.valid].std()
    if sd == 0 or during.sum() == 0 or outside.sum() == 0:
        return None
    return float((ava[during].mean() - ava[outside].mean()) / sd)


def velocity_reversal_check(rec) -> float | None:
    """Fraction of reversal frames with negative velocity."""
    v = rec.behaviour.get("velocity")
    if v is None or not rec.reversals:
        return None
    frames = np.concatenate([np.arange(a, b + 1) for a, b in rec.reversals])
    return float(np.mean(v[frames] < 0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out", default="results/m1")
    ap.add_argument("--min-confidence", type=float, default=2.0)
    args = ap.parse_args()

    recs = load_wormwideweb_dir(args.folder)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows, freq = [], Counter()
    for r in recs:
        s = r.summary(args.min_confidence)
        s["ava_reversal_z"] = ava_reversal_check(r)
        s["reversal_frames_backward"] = velocity_reversal_check(r)
        rows.append(s)
        freq.update(set(r.classes(args.min_confidence)))

    with (out / "coverage.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with (out / "class_frequency.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["neuron_class", "worms_labelled", "fraction"])
        for name, n in sorted(freq.items(), key=lambda x: (-x[1], x[0])):
            w.writerow([name, n, round(n / len(recs), 3)])

    lab = np.array([s["labelled"] for s in rows])
    print(f"{len(recs)} recordings; labelled ROIs per worm: median {np.median(lab):.0f} "
          f"(range {lab.min()} to {lab.max()})")
    print(f"Neuron classes labelled in at least half the worms: "
          f"{sum(n >= len(recs) / 2 for n in freq.values())}")
    z = [s["ava_reversal_z"] for s in rows if s["ava_reversal_z"] is not None]
    if z:
        print(f"AVA higher during reversals in {sum(x > 0 for x in z)} of {len(z)} worms "
              f"with AVA labelled (median effect {np.median(z):.2f} SD)")
    b = [s["reversal_frames_backward"] for s in rows if s["reversal_frames_backward"] is not None]
    if b:
        print(f"Velocity negative in a median {np.median(b):.0%} of reversal frames")
    print(f"Wrote {out / 'coverage.csv'} and {out / 'class_frequency.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
