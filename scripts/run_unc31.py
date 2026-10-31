"""Arc 4: unc-31 (no neuropeptide release) against wild type, written up in the README before
running: (1) unc-31 response sets scored against each wild-type pool; (2) per worm, the
excess AUC of class wiring over shuffled wiring at separating response sizes.

Usage:
  python scripts/run_unc31.py --wt data/raw/2025_creamer_lds_npz --unc31 data/raw/randi2023_unc31_npz \
      --folds configs/splits/pumpprobe_cv3.yaml
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.causal import response_set, score_sets  # noqa: E402
from nematica.bench.discriminability import auc  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.wiring import class_wiring, shuffled_wiring  # noqa: E402


def wiring_excess(rs, classes, A, shuffles) -> dict | None:
    idx = {c: i for i, c in enumerate(classes)}
    keys = [k for k in rs.traces if k[0] in idx and k[1] in idx and k[0] != k[1]]
    if len(keys) < 30:
        return None
    size = np.array([abs(rs.amp(k)) for k in keys])
    ok = np.isfinite(size)
    keys = [k for k, o in zip(keys, ok) if o]
    size = size[ok]

    def a(W):
        y = np.array([W[idx[j], idx[i]] for i, j in keys], float)   # W[to, from]
        return auc(size, y) if 0 < y.sum() < len(y) else np.nan

    real = a(A)
    null = np.array([a(S) for S in shuffles])
    return {"auc": real, "null_mean": float(np.nanmean(null)), "excess": real - float(np.nanmean(null)),
            "n_pairs": len(keys), "frac_wired": float(np.mean([A[idx[j], idx[i]] for i, j in keys]))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wt", required=True)
    ap.add_argument("--unc31", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="docs/figures")
    args = ap.parse_args()
    wt = {r.uid: r for r in load_pumpprobe_dir(args.wt)}
    un = [r for r in load_pumpprobe_dir(args.unc31) if sum(1 for c in r.classes if c) > 0]
    wt_sets = {u: response_set(r) for u, r in wt.items()}
    un_sets = [response_set(r, f"unc31:{r.uid}") for r in un]
    print(f"wild type {len(wt_sets)} worms, unc-31 {len(un_sets)} worms with identities")
    folds = load_folds(args.folds)["folds"]
    rows = []
    for fi, pool in enumerate(folds):
        for row in score_sets("unc31", un_sets, [wt_sets[u] for u in pool]):
            rows.append({"fold": fi, **row})
            print(f"fold {fi} unc31 {row['metric']:13s} {row['verdict']:11s} median {row.get('system_median')} "
                  f"vs wild type {row.get('bio_median')} [{row.get('bio_p05')}, {row.get('bio_p95')}] "
                  f"pct {row.get('percentile_of_bio')}", flush=True)
    with (Path(args.out) / "unc31_vs_wt.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)
    # anatomy
    classes = sorted({c for s in list(wt_sets.values()) + un_sets for k in s.traces for c in k})
    A = class_wiring(classes)
    shuffles = [shuffled_wiring(A, s) for s in range(20)]
    wrows = []
    for kind, sets in (("wild type", list(wt_sets.values())), ("unc-31", un_sets)):
        for s in sets:
            r = wiring_excess(s, classes, A, shuffles)
            if r:
                wrows.append({"genotype": kind, "worm": s.group, **r})
    for kind in ("wild type", "unc-31"):
        e = np.array([r["excess"] for r in wrows if r["genotype"] == kind])
        au = np.array([r["auc"] for r in wrows if r["genotype"] == kind])
        print(f"{kind}: {len(e)} worms, wiring AUC median {np.nanmedian(au):.3f}, excess over shuffled "
              f"median {np.nanmedian(e):+.4f} (above zero in {int(np.sum(e > 0))} of {len(e)})")
    from scipy.stats import mannwhitneyu
    e_wt = [r["excess"] for r in wrows if r["genotype"] == "wild type" and np.isfinite(r["excess"])]
    e_un = [r["excess"] for r in wrows if r["genotype"] == "unc-31" and np.isfinite(r["excess"])]
    print(f"unc-31 > wild type: Mann-Whitney p = {mannwhitneyu(e_un, e_wt, alternative='greater').pvalue:.4f}")
    with (Path(args.out) / "wiring_predicts_responses.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(wrows[0]))
        w.writeheader()
        w.writerows(wrows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
