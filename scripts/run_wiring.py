"""Arc 3, what the wiring buys: the per-worm calcium-drive VAR(10) with hysteresis
reversals, refitted with its neuron-to-neuron weights restricted to the connectome, to
shuffled wiring with the same number of inputs per class (3 seeds), or to no coupling.
Design and expectations: README, "Arc 3".

Writes wiring_combined.csv (pairwise levels on the rotating pools) and wiring_forecast.csv
(one-step and 30 s ahead R^2 of each pooled model on the held-out worms).

Usage:
  python scripts/run_wiring.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \\
      --folds configs/splits/copper2026_cv3.yaml [--out results/wiring]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import from_recording  # noqa: E402
from nematica.bench.cv import cv_score, print_table  # noqa: E402
from nematica.data import load_copper_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.forecasters import CalciumStateSpace, Debounced, LagFeatures  # noqa: E402
from nematica.systems.wiring import (MaskedForecaster, PriorForecaster, WiredVAR, class_wiring,  # noqa: E402
                                     diagonal_wiring, shuffled_wiring)

LAGS = 10
WIRINGS = {
    "full": lambda names: np.ones((len(names), len(names)), dtype=bool),
    "connectome": class_wiring,
    **{f"shuffled{s}": (lambda names, s=s: shuffled_wiring(class_wiring(names), 100 + s)) for s in range(3)},
    "diagonal": lambda names: diagonal_wiring(len(names)),
}


PRIOR = ("connectome", "shuffled0", "shuffled1", "shuffled2")   # wirings tried as priors
REALISM_RHOS = (1.0, 1.5, 2.0, 3.0, 5.0, 10.0)
REALISM_METRICS = ("L2.dimension", "L2.correlation", "L1.timescale")
_CACHE: dict = {}


class RealismRho:
    """Wiring prior whose rho is chosen by in-sample realism on the training worms (see
    README, arc 3): no reference worm is used."""

    def __init__(self, key):
        self.key = key
        self.m = None
        self.info: dict = {}

    @property
    def name(self) -> str:
        return f"realism_{self.key}"

    @property
    def names(self):
        return self.m.names if self.m else []

    def fit(self, train, val):
        from nematica.bench import build_reference, score_system
        ck = (self.key, tuple(s.origin for s in train))
        if ck in _CACHE:
            self.m, self.info = _CACHE[ck]
            return self
        ref = build_reference(train)
        best = None
        crit = {}
        for rho in REALISM_RHOS:
            cs = CalciumStateSpace.from_train(train, gamma=0.5)
            m = Debounced(WiredVAR(PriorForecaster(f"var{LAGS}", cs, LagFeatures(cs.k, LAGS, False), rhos=(rho,)),
                                   fixed_lam=300, wiring=WIRINGS[self.key], label=f"prior_{self.key}"))
            m.fit(train, val)
            own = [m.generate(s, np.random.default_rng(7 + i), which=i) for i, s in enumerate(train)]
            rows = {r["metric"]: r for r in score_system("insample", own, train, ref)}
            c = sum(abs(np.log(max(float(rows[k]["system_median"]) / float(rows[k]["bio_median"]), 1e-6)))
                    for k in REALISM_METRICS if k in rows and rows[k].get("bio_median"))
            crit[rho] = round(float(c), 4)
            if best is None or c < best[0]:
                best = (c, rho, m)
        self.m = best[2]
        self.info = {"rho": best[1], "realism_criterion": crit}
        _CACHE[ck] = (self.m, self.info)
        return self

    def generate(self, template, rng, which, **kw):
        return self.m.generate(template, rng, which=which, **kw)


def wired(label, train):
    """label: a WIRINGS key (hard mask) or "prior_" + key (wiring as a ridge prior)."""
    cs = CalciumStateSpace.from_train(train, gamma=0.5)
    key = label[6:] if label.startswith("prior_") else label
    cls = PriorForecaster if label.startswith("prior_") else MaskedForecaster
    return WiredVAR(cls(f"var{LAGS}", cs, LagFeatures(cs.k, LAGS, False)), fixed_lam=300,
                    wiring=WIRINGS[key], label=label)


LABELS = list(WIRINGS)


def build(train):
    if LABELS and LABELS[0].startswith("realism_"):
        return {"real_other_worms": None, **{k: RealismRho(k[8:]) for k in LABELS}}
    return {"real_other_worms": None, **{f"wired_{k}": Debounced(wired(k, train)) for k in LABELS}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="results/wiring")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--prior", action="store_true", help="wirings as ridge priors instead of hard masks")
    ap.add_argument("--prior-realism", action="store_true", help="priors with rho chosen by in-sample realism")
    args = ap.parse_args()
    global LABELS
    if args.prior:
        LABELS = [f"prior_{k}" for k in PRIOR]
        if args.out == "results/wiring":
            args.out = "results/wiring_prior"
    if args.prior_realism:
        LABELS = [f"realism_{k}" for k in PRIOR]
        if args.out == "results/wiring":
            args.out = "results/wiring_realism"
    recs = load_copper_dir(Path(args.data))
    by = {r.uid: r for r in recs}
    classes = tuple(canonical_classes(recs, 0.25))
    folds = load_folds(args.folds)["folds"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # forecasting on held-out worms (pooled model, which is what a new worm gets)
    rows = []
    for fi, pool_uids in enumerate(folds):
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        val_uids = [rest[len(rest) // 3], rest[2 * len(rest) // 3]]
        S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
        pool, train, val = S(pool_uids), S([u for u in rest if u not in val_uids]), S(val_uids)
        for label in LABELS:
            if label.startswith("realism_"):
                rr = RealismRho(label[8:]).fit(train, val)
                m = rr.m.model
                extra = {**m.fit_info(), "realism_criterion": rr.info["realism_criterion"]}
            else:
                m = wired(label, train).fit(train, val)
                extra = m.fit_info()
            rows.append({"wiring": label, "rotation": fi, **extra,
                         "one_step_r2": round(m.pooled.one_step_r2(pool), 4),
                         "r2_30s": round(m.pooled.multi_step_r2(pool, horizon=50, stride=25, context=50), 4)})
            print(rows[-1], flush=True)
    with (out / "wiring_forecast.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    combined, flat = cv_score(recs, classes, folds, build, args.seeds)
    for name, data in [("wiring_combined.csv", combined), ("wiring_per_fold.csv", flat)]:
        keys = list(dict.fromkeys(k for r in data for k in r))
        with (out / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(data)
    print()
    print_table(combined)
    print("\nForecasting on held-out worms (mean over rotations):")
    for label in LABELS:
        v = [r for r in rows if r["wiring"] == label]
        print(f"  {label:20s} rho {[r.get('rho', '-') for r in v]} one-step R2 {np.mean([r['one_step_r2'] for r in v]):.4f}   "
              f"30 s R2 {np.mean([r['r2_30s'] for r in v]):.4f}   inputs/class {v[0]['inputs_per_class_mean']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
