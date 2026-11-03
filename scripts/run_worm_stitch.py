"""Does stitching rescue the watching copy on real worms?

Artificial lab D found the watching copy's failure under atlas-like recording was mostly the
method, not the data: the copy fills each recording's unrecorded units with zeros. A copy
that learns each pair of units only from recordings where both were seen (stitching), with
slow drift removed, matched poking there. The real watching copy (var3_spontaneous) zero-fills
the same way. This tries the stitched version on the atlas, scored on the poke test exactly
as every copy (split cv3, all 3 pools, fluctuation norm), against the same ruler.

Copies (all VAR(3) on unpoked frames, kicked by the same clamp protocol):
  var3_spontaneous      the existing watching copy (zero-filled), for reference
  stitch3               lagged covariances pooled pairwise across worms where both classes
                        were recorded; unrecorded classes keep running in the simulation
  stitch3_hp            the same after removing each class's 30 s moving average
  stitch3_hp_zero       stitch3_hp but unrecorded classes held at zero in simulation, as the
                        existing copy does (separates fitting from simulation)
Ridge for the stitched copies is chosen on the fold's validation worms by how well the
fitted dynamics predict their lag covariances (no poke data used).

Output: docs/figures/worm_stitch.csv
Usage:  python scripts/run_worm_stitch.py
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
from nematica.bench.scorecard import SPLITS, SPLITS_DIR, FoldRuler, fold_parts, set_norm  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.causal_models import ClassVAR, class_matrix, spontaneous_mask  # noqa: E402

OUT = Path("docs/figures/worm_stitch.csv")
RIDGES = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)


def nan_moving_average(z, w):
    ker = np.ones(w)
    f = np.isfinite(z)
    s = np.array([np.convolve(r, ker, mode="same") for r in np.where(f, z, 0.0)])
    c = np.array([np.convolve(r, ker, mode="same") for r in f.astype(float)])
    with np.errstate(invalid="ignore", divide="ignore"):
        return s / c


class StitchedVAR(ClassVAR):
    def __init__(self, highpass=False, run_unseen=True, lags=3):
        super().__init__(lags=lags, frames="spontaneous")
        self.highpass, self.run_unseen = highpass, run_unseen
        self.name = f"stitch{lags}" + ("_hp" if highpass else "") + ("" if run_unseen else "_zero")

    def _stats(self, recs):
        """Sums and counts of z_t,i * z_{t-L},j over unpoked frames, L = 0..p, per pair of
        classes, only where both were recorded."""
        p, C = self.lags, len(self.classes)
        G = np.zeros((p + 1, C, C))
        N = np.zeros((p + 1, C, C))
        for r in recs:
            z = class_matrix(r, self.classes)
            spont = spontaneous_mask(r)
            if self.highpass:      # drift estimated from unpoked frames only, so no evoked activity leaks in
                w = max(3, int(round(30.0 / r.dt)))
                z = z - nan_moving_average(np.where(spont[None, :], z, np.nan), w)
            T = z.shape[1]
            ok = np.array([spont[t - p:t + 1].all() for t in range(p, T)])
            ts = np.arange(p, T)[ok]
            if ts.size == 0:
                continue
            f = np.isfinite(z)
            zf = np.where(f, z, 0.0)
            M = f.astype(float)
            for L in range(p + 1):
                G[L] += zf[:, ts] @ zf[:, ts - L].T
                N[L] += M[:, ts] @ M[:, ts - L].T
        return G, N

    def _normal(self, G, N):
        p, C = self.lags, len(self.classes)
        with np.errstate(invalid="ignore", divide="ignore"):
            Cl = np.where(N > 0, G / np.maximum(N, 1), 0.0)       # Cl[L][i, j] = E z_t,i z_{t-L},j
        XtX = np.zeros((p * C, p * C))
        for a in range(1, p + 1):
            for b in range(1, p + 1):
                blk = Cl[b - a] if b >= a else Cl[a - b].T
                XtX[(a - 1) * C:a * C, (b - 1) * C:b * C] = blk
        XtX = (XtX + XtX.T) / 2
        XtY = np.vstack([Cl[a].T for a in range(1, p + 1)])
        okY = np.vstack([(N[a] > 0).T for a in range(1, p + 1)])
        return XtX, XtY, okY, Cl[0]

    def _solve_cov(self, XtX, XtY, ridge):
        w, V = np.linalg.eigh(XtX)
        Xp = (V * np.maximum(w, 1e-3 * w.max())) @ V.T
        lam = ridge * np.trace(Xp) / len(Xp)
        return np.linalg.solve(Xp + lam * np.eye(len(Xp)), XtY)

    def fit(self, train, val):
        cnt = Counter(c for r in train for c in set(r.classes) if c)
        self.classes = sorted(c for c, n in cnt.items() if n >= self.min_fraction * len(train))
        C, p = len(self.classes), self.lags
        Gt, Nt = self._stats(train)
        Gv, Nv = self._stats(val)
        XtX, XtY, _, _ = self._normal(Gt, Nt)
        XtXv, XtYv, okv, _ = self._normal(Gv, Nv)
        losses = []
        for r in RIDGES:
            Wl = self._solve_cov(XtX, XtY, r)
            losses.append(float(np.sum(((XtYv - XtXv @ Wl) ** 2)[okv])))
        best = RIDGES[int(np.argmin(losses))]
        XtX, XtY, _, C0 = self._normal(Gt + Gv, Nt + Nv)
        Wl = self._solve_cov(XtX, XtY, best)
        self.W = np.vstack([Wl, np.zeros((1, C))])
        resid = np.diag(C0) - np.sum(Wl * XtY, axis=0)
        self.noise_sd = np.sqrt(np.clip(resid, 0.05, None))
        self.nu = np.full(C, 30.0)
        self.radius = self.spectral_radius()
        self.info = {"radius": round(self.radius, 4), "ridge": best, "classes": C,
                     "pairs_never_together": int((Nt[0] + Nv[0] == 0).sum())}
        return self


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="cv3")
    ap.add_argument("--copies", default="var3_spontaneous,stitch3,stitch3_hp,stitch3_hp_zero")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
    folds = load_folds(SPLITS_DIR / SPLITS[args.split])["folds"]
    make = {"var3_spontaneous": lambda: ClassVAR(3, "spontaneous"),
            "stitch3": lambda: StitchedVAR(False, True),
            "stitch3_hp": lambda: StitchedVAR(True, True),
            "stitch3_hp_zero": lambda: StitchedVAR(True, False)}
    out = Path(args.out)
    rows = list(csv.DictReader(out.open(encoding="utf-8"))) if out.exists() else []
    done = {(r["fold"], r["copy"]) for r in rows}
    for fi in range(len(folds)):
        todo = [c for c in args.copies.split(",") if (str(fi), c) not in done]
        if not todo:
            continue
        ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=False)
        for name in todo:
            m = make[name]()
            res = ruler.score(name, m, seed_base=1000 * fi)
            c1 = next(r for r in res if r["metric"] == "C1.pattern")
            rows.append({"fold": fi, "copy": name, "echo_agreement": round(1 - c1["system_median"], 4),
                         "real_agreement": round(1 - c1["bio_median"], 4), "verdict": c1["verdict"],
                         "equivalence": c1.get("equivalence", ""), "radius": m.info.get("radius"),
                         "ridge": m.info.get("ridge", ""), "pairs_never_together": m.info.get("pairs_never_together", "")})
            print(rows[-1], flush=True)
            with out.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
                w.writeheader()
                w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
