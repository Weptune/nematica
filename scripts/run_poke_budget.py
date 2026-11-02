"""How many pokes does a lab need, and which neurons pay off first?

For every stimulated neuron class (target) poked in enough worms, its echo is a vector: the
response amplitude of each other class. Two independent groups of worms that poked the same
target give two estimates of that vector; their correlation is the echo's reliability.

  r1      reliability of a single worm's echo (median over random pairs of worms)
  r(k)    reliability of the average of k worms vs another k (random disjoint halves)
  k80     worms (poke sessions) needed for reliability 0.8, from Spearman-Brown on r1
  k80_half  the same formula applied to the largest measured split, r(k_half): k_half worms
          per group. Measured r(k) grows more slowly than Spearman-Brown predicts from r1, and
          the curves keep flattening, so even k80_half is likely an underestimate

Output: docs/figures/poke_budget.csv (one row per target) and poke_budget_curve.csv.

Usage:  python scripts/run_poke_budget.py
"""

from __future__ import annotations

import csv
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.causal import response_set  # noqa: E402
from nematica.bench.scorecard import set_norm  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402

MIN_WORMS, MIN_SHARED, N_SPLITS = 6, 15, 200
PLACEHOLDER = "TARGET"   # atlas name 'target' = a stimulated neuron left unidentified; not a class


def echoes(recs):
    """target -> list of {responder: amplitude}, one dict per worm that poked it."""
    out: dict = {}
    for r in recs:
        rs = response_set(r)
        per: dict = {}
        for (ti, rj), _ in rs.traces.items():
            if ti == rj or PLACEHOLDER in (ti, rj):
                continue
            v = rs.amp((ti, rj))
            if np.isfinite(v):
                per.setdefault(ti, {})[rj] = v
        for t, d in per.items():
            out.setdefault(t, []).append(d)
    return out


def corr_of_means(group_a, group_b):
    keys = sorted(set().union(*group_a) & set().union(*group_b))
    if len(keys) < MIN_SHARED:
        return np.nan
    ma = np.array([np.nanmean([d.get(k, np.nan) for d in group_a]) for k in keys])
    mb = np.array([np.nanmean([d.get(k, np.nan) for d in group_b]) for k in keys])
    ok = np.isfinite(ma) & np.isfinite(mb)
    if ok.sum() < MIN_SHARED or ma[ok].std() == 0 or mb[ok].std() == 0:
        return np.nan
    return float(np.corrcoef(ma[ok], mb[ok])[0, 1])


def main() -> int:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    rng = np.random.default_rng(0)
    recs = load_pumpprobe_dir("data/raw/randi2023_wt_npz")
    ech = echoes(recs)
    rows, curve = [], []
    for t, worms in sorted(ech.items()):
        n = len(worms)
        if n < MIN_WORMS:
            continue
        pairs = [corr_of_means([worms[i]], [worms[j]]) for i in range(n) for j in range(i + 1, n)]
        r1 = float(np.nanmedian(pairs)) if np.isfinite(pairs).any() else np.nan
        for k in range(1, n // 2 + 1):
            vals = []
            for _ in range(N_SPLITS):
                p = rng.permutation(n)
                vals.append(corr_of_means([worms[i] for i in p[:k]], [worms[i] for i in p[k:2 * k]]))
            curve.append({"target": t, "k": k, "r_k": round(float(np.nanmedian(vals)), 4),
                          "spearman_brown": round(k * r1 / (1 + (k - 1) * r1), 4) if np.isfinite(r1) else ""})
        k80 = 0.8 * (1 - r1) / (r1 * 0.2) if np.isfinite(r1) and r1 > 0 else np.inf
        half = [c for c in curve if c["target"] == t]
        rh, kh = max(half[-1]["r_k"], 1e-3), half[-1]["k"]
        rows.append({"target": t, "worms": n, "r1": round(r1, 4), "k80": round(k80, 1) if np.isfinite(k80) else "never",
                     "r_half": half[-1]["r_k"], "k_half": kh, "k80_half": round(kh * 0.8 * (1 - rh) / (rh * 0.2), 1),
                     "responders": int(np.median([len(d) for d in worms]))})
    rows.sort(key=lambda r: -r["r1"] if np.isfinite(r["r1"]) else 9)
    for name, data in (("poke_budget.csv", rows), ("poke_budget_curve.csv", curve)):
        with (Path("docs/figures") / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    r1s = np.array([r["r1"] for r in rows], float)
    k80 = np.array([r["k80"] if r["k80"] != "never" else np.inf for r in rows], float)
    print(f"{len(rows)} targets poked in >= {MIN_WORMS} worms")
    print(f"single-worm reliability r1: median {np.nanmedian(r1s):.3f}, IQR {np.nanpercentile(r1s, 25):.3f} to {np.nanpercentile(r1s, 75):.3f}")
    kh = np.array([r["k80_half"] for r in rows], float)
    print(f"from the largest measured split: median {np.median(kh):.0f} worms, IQR {np.percentile(kh, 25):.0f} to {np.percentile(kh, 75):.0f}, within 20 for {np.mean(kh <= 20):.0%}")
    print(f"worms needed for 0.8 (from r1): median {np.median(k80):.1f}; reachable within 10 worms for {np.mean(k80 <= 10):.0%} of targets, never (r1<=0) for {np.mean(~np.isfinite(k80)):.0%}")
    for r in rows[:8]:
        print("  top", r)
    for r in rows[-5:]:
        print("  bottom", r)
    # check Spearman-Brown against measured at the largest k with many targets
    ks = [c for c in curve if c["k"] == 4 and c["spearman_brown"] != ""]
    if ks:
        a = np.array([c["r_k"] for c in ks], float)
        b = np.array([c["spearman_brown"] for c in ks], float)
        ok = np.isfinite(a) & np.isfinite(b)
        print(f"k=4: measured median {np.median(a[ok]):.3f} vs Spearman-Brown {np.median(b[ok]):.3f} (n={ok.sum()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
