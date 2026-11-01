"""Do real worms have stable individual echoes? Each worm's stimulations are split in two
(alternate pulses); the echo pattern from one half is compared with the other half of the
same worm, and with halves of other worms. If the same worm's halves agree more than
different worms' halves do, worms differ from each other beyond noise: each has a stable
echo of its own, which a copy that only reproduces the average echo cannot have.

Usage:  python scripts/analyse_individuality.py [--data data/raw/randi2023_wt_npz]
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import causal  # noqa: E402
from nematica.bench.causal import c_pattern, response_set  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw/randi2023_wt_npz")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--split", choices=("alternate", "time"), default="alternate",
                    help="alternate pulses, or first half of the recording against the second")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    causal.NORM = "fluct"
    recs = [r for r in load_pumpprobe_dir(args.data) if len(r.stims) >= 20]
    if args.split == "alternate":
        A = [response_set(r, stims=r.stims[0::2]) for r in recs]
        B = [response_set(r, stims=r.stims[1::2]) for r in recs]
    else:
        A = [response_set(r, stims=r.stims[:len(r.stims) // 2]) for r in recs]
        B = [response_set(r, stims=r.stims[len(r.stims) // 2:]) for r in recs]
    n = len(recs)
    S = np.full((n, n), np.nan)                     # agreement: half A of i with half B of j
    for i in range(n):
        for j in range(n):
            d = c_pattern(A[i], B[j])
            S[i, j] = 1 - d if np.isfinite(d) else np.nan
    same = np.diag(S)
    other = S[~np.eye(n, dtype=bool)]
    ok = np.isfinite(same)
    # per worm: own other half minus the mean of its halves with other worms
    excess = np.array([S[i, i] - np.nanmean(np.r_[np.delete(S[i], i), np.delete(S[:, i], i)]) for i in range(n)])
    excess = excess[np.isfinite(excess)]
    rng = np.random.default_rng(0)
    boot = [np.mean(rng.choice(excess, excess.size)) for _ in range(args.boot)]
    print(f"{n} worms with at least 20 pulses ({ok.sum()} with a scorable same-worm comparison)")
    print(f"same worm, two halves:      median agreement {np.nanmedian(same):.3f}")
    print(f"different worms, halves:    median agreement {np.nanmedian(other):.3f}")
    print(f"per-worm excess (own half minus other worms): mean {np.mean(excess):.3f}, "
          f"95% interval [{np.percentile(boot, 2.5):.3f}, {np.percentile(boot, 97.5):.3f}], "
          f"positive in {np.mean(excess > 0):.0%} of worms")
    # a copy of one worm: predict its second half from a blend of its own first half and the
    # average of the other worms (w = weight on the worm's own data)
    full = [response_set(r) for r in recs]
    keys_all = set().union(*[set(f.traces) for f in full])
    tot = {k: [f.amp(k) for f in full if k in f.traces] for k in keys_all}
    print("predicting each worm's second half (agreement with it, median over worms):")
    for w in (0.0, 0.25, 0.5, 0.75, 1.0):
        scores = []
        for i in range(n):
            mine = full[i]
            xs, ys = [], []
            for k in B[i].traces:
                b = B[i].amp(k)
                others = [v for v in tot.get(k, []) if np.isfinite(v)]
                own_in = k in mine.traces and np.isfinite(mine.amp(k))
                if own_in and k in full[i].traces:
                    others = [v for f, v in ((f, f.amp(k)) for j, f in enumerate(full) if j != i and k in f.traces) if np.isfinite(v)]
                if not np.isfinite(b) or len(others) < 3:
                    continue
                pop = float(np.mean(others))
                a = A[i].amp(k) if k in A[i].traces else np.nan
                xs.append(pop if not np.isfinite(a) else w * a + (1 - w) * pop)
                ys.append(b)
            if len(xs) >= 15 and np.std(xs) > 0 and np.std(ys) > 0:
                scores.append(np.corrcoef(xs, ys)[0, 1])
        print(f"  weight on own first half {w:.2f}: {np.median(scores):.3f}  ({len(scores)} worms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
