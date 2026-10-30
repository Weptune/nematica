"""Redraw the fidelity figure from saved results, adding Level 8 if l8_<dataset>.csv exists.

Usage:
  python scripts/plot_profile.py --dataset copper [--out results/bench]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import LEVELS  # noqa: E402
from nematica.bench.report import plot_profile  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", default="results/bench")
    args = ap.parse_args()
    out = Path(args.out)
    rows = list(csv.DictReader((out / f"fidelity_{args.dataset}.csv").open(encoding="utf-8")))
    l8_path = out / f"l8_{args.dataset}.csv"
    l8 = list(csv.DictReader(l8_path.open(encoding="utf-8"))) if l8_path.exists() else None
    subtitle = ""
    if l8:
        cal = next((r for r in l8 if r["system"].startswith("_calibration")), None)
        ctrl = next((r for r in l8 if r["system"] == "real_other_worms"), None)
        if cal and ctrl:
            subtitle = (f"L8 control: other real worms AUC {float(ctrl['auc']):.2f}; random real-vs-real "
                        f"splits AUC median {float(cal['auc']):.2f}, false-alarm rate {float(cal['p']):.3f}")
    systems = list(dict.fromkeys(r["system"] for r in rows))
    path = out / f"fidelity_{args.dataset}.png"
    plot_profile(rows, list(LEVELS), systems, path, l8=l8, subtitle=subtitle)
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
