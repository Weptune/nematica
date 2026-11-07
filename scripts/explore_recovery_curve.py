"""Exploratory (8 Nov 2026): model-free recovery curve of the repeat decline. For every consecutive pair of
pokes of the same neuron (not only the first two), log(second / first own response) minus the same for
control pairs (first pokes of two different neurons about the same time apart, as test B1), binned by gap.
Per worm means, then 90% bootstrap over worms. Output appended to docs/figures/light_or_activity.txt and
docs/figures/recovery_curve.csv.
Corrected after review 7 (8 Nov): the first bin starts at 0.6 min; the first version (0 to 2 min, -0.92) is kept in
light_or_activity.txt and superseded."""
import csv
import sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
import run_light_or_activity as R  # noqa: E402
import run_week1 as W  # noqa: E402

BINS = [(0.6, 2), (2, 5), (5, 10), (10, 20), (20, 40)]   # review 7: repeats under 36 s start from a still-raised baseline (the 10 s before falls inside the first response) and are excluded; first version used (0, 2)


def per_worm(w):
    by = defaultdict(list)
    for k, f, v in w.stims:
        by[k].append((f, v[k]))
    first = sorted((s[0][0], k, s[0][1]) for k, s in ((k, sorted(s)) for k, s in by.items()))
    out = defaultdict(list)
    for k, s in by.items():
        s = sorted(s)
        for (f1, a1), (f2, a2) in zip(s, s[1:]):
            if not (a1 > 0 and a2 > 0):
                continue
            gap = f2 - f1
            gm = gap / 120
            b = next((i for i, (lo, hi) in enumerate(BINS) if lo <= gm < hi), None)
            if b is None:
                continue
            tol = max(0.2 * gap, 30)
            cand = []
            for i in range(len(first)):
                for j in range(i + 1, len(first)):
                    fx, kx, ax = first[i]
                    fy, ky, ay = first[j]
                    if kx != ky and abs((fy - fx) - gap) <= tol and ax > 0 and ay > 0:
                        cand.append((abs(fx - f1), np.log(ay / ax)))
            cand.sort()
            if not cand:
                continue
            out[b].append(np.log(a2 / a1) - np.mean([c for _, c in cand[:5]]))
    return {b: np.mean(v) for b, v in out.items()}, {b: len(v) for b, v in out.items()}


def main():
    worms = W.load_worms()
    res = [per_worm(w) for w in worms]
    rng = np.random.default_rng(5)
    rows = []
    for b, (lo, hi) in enumerate(BINS):
        vals = np.array([r[0][b] for r in res if b in r[0]])
        npairs = sum(r[1].get(b, 0) for r in res)
        bs = [np.mean(vals[rng.integers(0, len(vals), len(vals))]) for _ in range(2000)]
        l, h = np.percentile(bs, [5, 95])
        rows.append(dict(gap_min=f"{lo}-{hi}", worms=len(vals), pairs=npairs, decline=round(float(vals.mean()), 3),
                         lo=round(float(l), 3), hi=round(float(h), 3)))
        R.log(f"EXPLORATORY recovery curve, gap {lo}-{hi} min: {vals.mean():+.3f} [90%: {l:+.3f}, {h:+.3f}], worms {len(vals)}, pairs {npairs}")
    with (ROOT / "docs" / "figures" / "recovery_curve.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)


if __name__ == "__main__":
    main()
