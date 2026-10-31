"""Automatic, dataset-agnostic settings for the per-worm calcium-drive VAR with hysteresis
reversals: memory length and shrinkage chosen per rotation by in-sample realism on the
training worms only. Design and expectations: README ("Automatic settings").

Usage:
  python scripts/run_auto.py --data DATA_DIR --folds FOLDS_YAML [--out results/auto_<name>]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import build_reference, score_system  # noqa: E402
from nematica.bench.cv import cv_score, print_table  # noqa: E402
from nematica.data import load_any_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.forecasters import CalciumStateSpace, Debounced, Forecaster, IndividualVAR, LagFeatures  # noqa: E402

LAG_GRID = (3, 6, 10)
LAM_GRID = (100, 300, 1000)
CHOICES: list = []


def realism_criterion(rows) -> float:
    c = 0.0
    for r in rows:
        if r.get("bio_median") and r.get("system_median") is not None:
            c += abs(np.log(max(float(r["system_median"]) / float(r["bio_median"]), 1e-6)))
            c += 1.0 if r.get("verdict") == "too typical" else 0.0
    return float(c)


class AutoSettings:
    """Chooses (lags, lambda) on the training worms, then behaves like the chosen model."""

    def __init__(self):
        self.m = None
        self.info: dict = {}

    @property
    def name(self) -> str:
        return "auto_calcium_hyst"

    @property
    def names(self):
        return self.m.names if self.m else []

    def fit(self, train, val):
        ref = build_reference(train)
        crit, best = {}, None
        for lags in LAG_GRID:
            for lam in LAM_GRID:
                cs = CalciumStateSpace.from_train(train, gamma=0.5)
                m = Debounced(IndividualVAR(Forecaster(f"var{lags}", cs, LagFeatures(cs.k, lags, False)), fixed_lam=lam))
                m.fit(train, val)
                own = [m.generate(s, np.random.default_rng(11 + i), which=i) for i, s in enumerate(train)]
                c = realism_criterion(score_system("insample", own, train, ref, n_boot=200))
                crit[f"{lags}/{lam}"] = round(c, 3)
                if best is None or c < best[0]:
                    best = (c, lags, lam, m)
        self.m = best[3]
        self.info = {"lags": best[1], "lam": best[2], "criterion": crit}
        CHOICES.append(self.info)
        print("chosen", {k: v for k, v in self.info.items() if k != "criterion"}, flush=True)
        return self

    def generate(self, template, rng, which, **kw):
        return self.m.generate(template, rng, which=which, **kw)


def build(train):
    return {"real_other_worms": None, "auto_calcium_hyst": AutoSettings()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()
    recs = load_any_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    folds = load_folds(args.folds)["folds"]
    out = Path(args.out or f"results/auto_{Path(args.folds).stem}")
    out.mkdir(parents=True, exist_ok=True)
    combined, flat = cv_score(recs, classes, folds, build, args.seeds)
    for name, data in [("auto_combined.csv", combined), ("auto_per_fold.csv", flat)]:
        keys = list(dict.fromkeys(k for r in data for k in r))
        with (out / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(data)
    with (out / "auto_choices.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["rotation", "lags", "lam", "criterion"])
        w.writeheader()
        for i, c in enumerate(CHOICES):
            w.writerow({"rotation": i + 1, **c})
    print()
    print_table(combined)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
