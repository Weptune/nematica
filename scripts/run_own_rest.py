"""Experiment C (README, "Can you verify a brain copy by watching it?"):

1. Own rest -> own poke. For each worm, a VAR(2) fitted only on its own stimulation-free
   frames, simulated under its own stimulations; compared with the same worm simulated by
   five other worms' own models. Is a worm's own model closer to its real echoes?
2. Causal fingerprint. Each worm's stimulations split into odd and even events: is the
   odd-half echo pattern closer to the worm's own even half than to other worms' even
   halves, and can a worm be identified from its echoes?

Usage:
  python scripts/run_own_rest.py --data data/raw/randi2023_wt_npz
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nematica.bench.causal as causal  # noqa: E402
from nematica.bench.causal import c_pattern, response_set  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.systems.causal_models import ClassVAR, spontaneous_mask  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="docs/figures")
    ap.add_argument("--others", type=int, default=5)
    ap.add_argument("--ridge", type=float, default=300.0)
    ap.add_argument("--norm", default="fluct")
    args = ap.parse_args()
    causal.NORM = args.norm
    recs = [r for r in load_pumpprobe_dir(args.data)
            if sum(1 for c in r.classes if c) >= 20 and len(r.stims) >= 20 and spontaneous_mask(r).sum() >= 300]
    print(f"{len(recs)} worms with >= 20 named neurons, >= 20 stimulations and >= 300 free frames", flush=True)
    rng = np.random.default_rng(0)
    t0 = time.time()
    models = {}
    for r in recs:
        try:
            models[r.uid] = ClassVAR(lags=2, frames="spontaneous", min_fraction=1.0, fixed_ridge=args.ridge).fit([r], None)
        except Exception as e:  # noqa: BLE001 (a worm whose free frames cannot support a fit is skipped)
            print(f"  skip {r.uid}: {e}")
    print(f"fitted {len(models)} own models ({time.time() - t0:.0f} s)", flush=True)
    real = {r.uid: response_set(r) for r in recs}
    rows = []
    uids = [r.uid for r in recs if r.uid in models]
    by = {r.uid: r for r in recs}
    for k, u in enumerate(uids):
        r = by[u]
        own = response_set(models[u].simulate(r, np.random.default_rng(k)))
        others = rng.choice([v for v in uids if v != u], size=args.others, replace=False)
        d_others = []
        for j, v in enumerate(others):
            sim = response_set(models[v].simulate(r, np.random.default_rng(1000 * k + j)))
            d_others.append(c_pattern(real[u], sim))
        rows.append({"worm": u, "d_own_model": c_pattern(real[u], own), "d_other_models": float(np.nanmean(d_others)),
                     "own_model_radius": models[u].info.get("radius")})
        if k % 20 == 0:
            print(f"  {k}/{len(uids)} ({time.time() - t0:.0f} s)", flush=True)
    d_own = np.array([r["d_own_model"] for r in rows])
    d_oth = np.array([r["d_other_models"] for r in rows])
    ok = np.isfinite(d_own) & np.isfinite(d_oth)
    diff = d_own[ok] - d_oth[ok]
    print(f"\n1. own rest -> own poke ({ok.sum()} worms): pattern distance own model {np.median(d_own[ok]):.4f}, "
          f"other worms' models {np.median(d_oth[ok]):.4f}, median paired difference {np.median(diff):+.4f}, "
          f"own closer in {int(np.sum(diff < 0))}, Wilcoxon p = {wilcoxon(diff).pvalue:.4f}")
    # causal fingerprint
    odd = {u: response_set(by[u], stims=by[u].stims[0::2]) for u in uids}
    even = {u: response_set(by[u], stims=by[u].stims[1::2]) for u in uids}
    D = np.array([[c_pattern(odd[a], even[b]) for b in uids] for a in uids])
    within = np.diag(D)
    between = np.array([np.nanmean(np.delete(D[i], i)) for i in range(len(uids))])
    okf = np.isfinite(within) & np.isfinite(between)
    rank = []
    for i in range(len(uids)):
        row = D[i]
        if np.isfinite(row[i]):
            fin = row[np.isfinite(row)]
            rank.append(int(np.sum(fin < row[i])) + 1)
    rank = np.array(rank)
    n_cand = np.isfinite(D).sum(axis=1).mean()
    print(f"2. fingerprint ({okf.sum()} worms): odd-to-own-even {np.median(within[okf]):.4f}, odd-to-other-even "
          f"{np.median(between[okf]):.4f}, own closer in {int(np.sum(within[okf] < between[okf]))} of {okf.sum()}, "
          f"Wilcoxon p = {wilcoxon(within[okf] - between[okf]).pvalue:.2e}; own half ranked first in "
          f"{int(np.sum(rank == 1))} of {len(rank)} (chance about {len(rank) / n_cand:.1f}), median rank {np.median(rank):.0f} "
          f"of about {n_cand:.0f}")
    for r, w, b in zip(rows, within, between):
        r.update({"fp_within": w, "fp_between": b})
    with (Path(args.out) / f"own_rest_fingerprint_{args.norm}.csv").open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    np.save(Path(args.out) / f"fingerprint_matrix_{args.norm}.npy", D)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
