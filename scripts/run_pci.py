"""Perturbational complexity on the optogenetic atlas (README, "Signatures of a mind"):
calibrations with designed outcomes, then models under the same stimulation protocol.

Usage:
  python scripts/run_pci.py --data data/raw/2025_creamer_lds_npz --folds configs/splits/pumpprobe_cv3.yaml
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.causal import score_sets  # noqa: E402
from nematica.bench.perturbational import PCI_LEVELS, desynchronised, pci_set  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.causal_models import ClassVAR, CreamerCausal  # noqa: E402

EXPECTED = {
    "real": {"P1.complexity": "inside", "P2.spread": "inside"},
    "scaled_x3": {"P1.complexity": "either", "P2.spread": "outside"},
    "desynchronised": {"P1.complexity": "outside", "P2.spread": "inside"},
    "time_reversed": {"P1.complexity": "inside", "P2.spread": "inside"},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="docs/figures")
    ap.add_argument("--models", default="var3_all,creamer2024_connectome_constrained,creamer2024_fully_connected,creamer2024_shuffled_constrained")
    args = ap.parse_args()
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    folds = load_folds(args.folds)["folds"]
    real_sets = {u: pci_set(r) for u, r in recs.items()}
    allp = np.concatenate([s.pci for s in real_sets.values()])
    alls = np.concatenate([s.spread for s in real_sets.values()])
    print(f"real events {allp.size}: PCI median {np.median(allp):.3f} (IQR {np.percentile(allp, 25):.3f} to "
          f"{np.percentile(allp, 75):.3f}), spread median {np.median(alls):.4f}, no response in {np.mean(alls == 0):.2f}")
    rows, hits, total = [], 0, 0
    for fi, pool_uids in enumerate(folds):
        t0 = time.time()
        pool = [recs[u] for u in pool_uids]
        real = [real_sets[u] for u in pool_uids]
        calib = {
            "real": real,
            "scaled_x3": [pci_set(r, f"scaled:{r.uid}", transform=lambda R: 3 * R) for r in pool],
            "desynchronised": [pci_set(r, f"desync:{r.uid}", transform=lambda R, g=np.random.default_rng(fi): desynchronised(R, g))
                               for r in pool],
            "time_reversed": [pci_set(r, f"reversed:{r.uid}", transform=lambda R: R[:, ::-1]) for r in pool],
        }
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        val_uids = rest[::5]
        train = [recs[u] for u in rest if u not in val_uids]
        val = [recs[u] for u in val_uids]
        systems = {}
        for name in args.models.split(","):
            if name.startswith("creamer2024_"):
                m = CreamerCausal(name.replace("creamer2024_", ""))
            else:
                L, fr = name.replace("var", "").split("_")
                m = ClassVAR(lags=int(L), frames=fr).fit(train, val)
            sims = []
            for i, r in enumerate(pool):
                s = pci_set(m.simulate(r, np.random.default_rng(1000 * fi + i)), f"{name}:{r.uid}")
                s.group = r.uid
                sims.append(s)
            systems[name] = sims
        for kind, sets in {**calib, **systems}.items():
            for row in score_sets(kind, sets, real, levels=PCI_LEVELS):
                exp = EXPECTED.get(kind, {}).get(row["metric"], "model")
                ok = exp in ("either", "model") or exp == row["verdict"]
                if exp not in ("either", "model"):
                    total += 1
                    hits += ok
                med_pci = float(np.median(np.concatenate([s.pci for s in sets if len(s.pci)])))
                med_sp = float(np.median(np.concatenate([s.spread for s in sets if len(s.spread)])))
                rows.append({"fold": fi, **row, "expected": exp, "median_pci": round(med_pci, 4),
                             "median_spread": round(med_sp, 4)})
                print(f"fold {fi} {kind:36s} {row['metric']:14s} {row['verdict']:11s} (expected {exp:7s}) "
                      f"KS {row.get('system_median')} vs real {row.get('bio_median')}  "
                      f"PCI {med_pci:.3f} spread {med_sp:.4f}", flush=True)
        print(f"fold {fi} done ({time.time() - t0:.0f} s)", flush=True)
    print(f"\ndesigned calibration outcomes hit: {hits} / {total}")
    with (Path(args.out) / "pci.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
