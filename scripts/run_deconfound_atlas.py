"""Does taking out slow shared patterns rescue the watching copy on real worms?

In the artificial lab, with every unit recorded and slow hidden drives at 25% of input, a
linear watcher given the 3 strongest slow patterns of activity as extra inputs rose from
0.61 to 0.77 (true drives: 0.86; poking 0.81). Here the same idea on the atlas: the watching
copy (VAR(3) on unpoked frames) gets, as extra inputs during fitting only, each worm's k
strongest slow patterns (class activity smoothed over 30 s, principal components of that
worm's own recording). The extra inputs are dropped when the copy is simulated, so they can
only change the copy by changing which influences it attributes to neurons. Scored on the
poke test exactly as every copy (split cv3, all 3 pools).

Usage:  python scripts/run_deconfound_atlas.py [--ks 3,6]
"""

from __future__ import annotations

import argparse
import csv
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.scorecard import SPLITS, SPLITS_DIR, FoldRuler, fold_parts, set_norm  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.causal_models import ClassVAR, class_matrix, spontaneous_mask  # noqa: E402

OUT = Path("docs/figures/deconfound_atlas.csv")


def slow_patterns(z, k, w=60):
    zf = np.nan_to_num(z - np.nanmean(z, axis=1, keepdims=True))
    ker = np.ones(w) / w
    sm = np.array([np.convolve(r, ker, mode="same") for r in zf])
    u, s, vt = np.linalg.svd(sm, full_matrices=False)
    sc = vt[:k].T * s[:k]
    return (sc - sc.mean(0)) / np.maximum(sc.std(0), 1e-9)


class DeconfVAR(ClassVAR):
    def __init__(self, k):
        super().__init__(lags=3, frames="spontaneous")
        self.k = k
        self.name = f"var3_spontaneous_slowpcs{k}"

    def _design(self, recs):
        p = self.lags
        Xs, Ys = [], []
        for r in recs:
            z = class_matrix(r, self.classes)
            spont = spontaneous_mask(r)
            zf = np.nan_to_num(z)
            T = z.shape[1]
            ok = np.array([spont[t - p:t + 1].all() for t in range(p, T)])
            ts = np.arange(p, T)[ok]
            if ts.size == 0:
                continue
            U = slow_patterns(z, self.k)
            blocks = [zf[:, ts - L].T for L in range(1, p + 1)] + [U[ts - 1]]
            Xs.append(np.hstack(blocks + [np.ones((ts.size, 1))]))
            Ys.append(z[:, ts].T)
        return np.vstack(Xs), np.vstack(Ys)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ks", default="3,6")
    ap.add_argument("--split", default="cv3")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
    folds = load_folds(SPLITS_DIR / SPLITS[args.split])["folds"]
    rows = []
    for fi in range(len(folds)):
        ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=False)
        copies = [ClassVAR(3, "spontaneous")] + [DeconfVAR(int(k)) for k in args.ks.split(",")]
        for m in copies:
            name = getattr(m, "name", "var3_spontaneous")
            res = ruler.score(name, m, seed_base=1000 * fi)
            c1 = next(r for r in res if r["metric"] == "C1.pattern")
            rows.append({"fold": fi, "copy": name, "echo_agreement": round(1 - c1["system_median"], 4),
                         "real_agreement": round(1 - c1["bio_median"], 4), "verdict": c1["verdict"],
                         "equivalence": c1.get("equivalence", ""), "radius": m.info.get("radius"),
                         "val_r2": m.info.get("val_r2")})
            print(rows[-1], flush=True)
            with OUT.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
