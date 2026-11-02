"""Copies learned from freely moving worms, given the poke test (pre-registered as model 2 of
the causal plan, never run until now).

A class-level VAR is fitted by watching freely moving worms (Atanas 2023, the copper-boundary
set, or both), resampled to the atlas frame interval (0.5 s). It is then poked like any copy,
on the held-out atlas worms of each fold, and scored on the echo levels. Comparison rows: the
watching copy fitted on the atlas's own unpoked frames, and the poke-trained copy.

Pre-registered expectation (README, causal plan (c)): copies fitted on behaving worms do worse
than copies fitted on atlas worms.

Usage:  python scripts/run_behaving_pokes.py [--split cv3]
"""

from __future__ import annotations

import argparse
import csv
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nematica.bench.scorecard import SPLITS, SPLITS_DIR, FoldRuler, fold_parts, set_norm  # noqa: E402
from nematica.data.copper import load_copper_dir  # noqa: E402
from nematica.data.pumpprobe import FRAME_S, PumpProbe, load_pumpprobe_dir, neuron_class  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.data.wormwideweb import load_wormwideweb_dir  # noqa: E402
from nematica.systems.causal_models import ClassVAR  # noqa: E402
from run_same_worms import make_model  # noqa: E402

SOURCES = {"atanas": "data/raw/atanas2023_wwweb", "copper": "data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415"}
OUT = Path("docs/figures/behaving_pokes.csv")


def as_pumpprobe(rec, dt=FRAME_S, min_conf=2.0) -> PumpProbe:
    """A freely moving recording as an unpoked atlas-style worm: labelled class traces on a
    0.5 s grid; frames outside valid ranges or within 30 s after a heat pulse become NaN."""
    names, tr = rec.class_traces(min_conf)
    t = rec.t
    grid = np.arange(0.0, t[-1], dt)
    bad = np.zeros(rec.n_frames, bool)
    if rec.valid is not None:
        bad |= ~rec.valid
    for f in rec.events.get("heat", []):
        bad[(t >= t[f]) & (t < t[f] + 30.0)] = True
    x = np.full((len(names), grid.size), np.nan)
    keep = ~bad
    for i in range(len(names)):
        x[i] = np.interp(grid, t[keep], tr[i, keep], left=np.nan, right=np.nan)
    gb = np.interp(grid, t, bad.astype(float)) > 0
    x[:, gb] = np.nan
    return PumpProbe(uid=f"{rec.dataset}:{rec.uid}", x=x, names=names, classes=[neuron_class(n) for n in names],
                     stims=[], dt=dt, all_stim_frames=[])


class BehavingVAR(ClassVAR):
    """ClassVAR whose classes come from the atlas training worms but whose weights are fitted
    on freely moving worms."""

    def __init__(self, behaving, lags=3):
        super().__init__(lags=lags, frames="all")
        self.behaving = behaving

    def fit(self, train, val):
        cnt = Counter(c for r in train for c in set(r.classes) if c)
        classes = sorted(c for c, n in cnt.items() if n >= self.min_fraction * len(train))
        b = self.behaving
        btrain, bval = [r for i, r in enumerate(b) if i % 5], [r for i, r in enumerate(b) if not i % 5]
        super().fit(btrain, bval)          # sets classes from the behaving worms ...
        if self.classes != classes:        # ... so refit on the atlas classes
            self.classes = classes
            self._fit_fixed_classes(btrain, bval)
        return self

    def _fit_fixed_classes(self, train, val):
        X, Y = self._design(train)
        Xv, Yv = self._design(val)
        best = None
        for lam in self.ridges:
            W = self._solve(X, Y, lam)
            P = Xv @ W
            m = np.isfinite(Yv)
            r2 = 1 - np.sum((Yv - P)[m] ** 2) / np.sum((Yv - np.nanmean(Yv, axis=0))[m] ** 2)
            if best is None or r2 > best[1]:
                best = (lam, r2)
        X, Y = np.vstack([X, Xv]), np.vstack([Y, Yv])
        self.W = self._solve(X, Y, best[0])
        R = Y - X @ self.W
        self.noise_sd = np.sqrt(np.nanmean(R ** 2, axis=0))
        self.noise_sd[~np.isfinite(self.noise_sd)] = 1.0
        self.nu = np.full(len(self.classes), 30.0)
        self.radius = self.spectral_radius()
        self.info = {"radius": round(self.radius, 4), "ridge": best[0], "val_r2": round(float(best[1]), 4),
                     "rows": int(X.shape[0])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=tuple(SPLITS), default="cv3")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    beh = {"atanas": [as_pumpprobe(r) for r in load_wormwideweb_dir(SOURCES["atanas"])],
           "copper": [as_pumpprobe(r) for r in load_copper_dir(SOURCES["copper"])]}
    beh["both"] = beh["atanas"] + beh["copper"]
    print({k: len(v) for k, v in beh.items()}, flush=True)
    recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
    folds = load_folds(SPLITS_DIR / SPLITS[args.split])["folds"]
    rows = []
    for fi in range(len(folds)):
        ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=False)
        copies = {f"behaving_{k}_var3": BehavingVAR(v) for k, v in beh.items()}
        copies.update({s: make_model(s) for s in ("var3_spontaneous", "hybrid_kernels")})
        for name, m in copies.items():
            res = ruler.score(name, m, seed_base=1000 * fi)
            info = getattr(m, "info", {}) or {}
            for r in res:
                if r["kind"] != "causal":
                    continue
                rows.append({"split": args.split, "fold": fi, "copy": name, "metric": r["metric"],
                             "copy_median": r["system_median"], "real_median": r["bio_median"],
                             "verdict": r["verdict"], "equivalence": r.get("equivalence", ""),
                             "shift_lo": r["shift_lo"], "shift_hi": r["shift_hi"],
                             "radius": info.get("radius", ""), "val_r2": info.get("val_r2", "")})
            c1 = next(r for r in res if r["metric"] == "C1.pattern")
            print(fi, name, "echo agreement", round(1 - c1["system_median"], 4), "real", round(1 - c1["bio_median"], 4),
                  c1["verdict"], info, flush=True)
            with OUT.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
