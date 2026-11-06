"""The within-neuron refit of the tiring-source test (exploratory, after review 4; code committed after
review 5). Each worm's neuron is its own fixed effect (neurons stimulated at least twice); covariates:
direct poke before, largest drive by other neurons' pokes (no light on the neuron), number of such
pokes, order, pre level (the pre-registered covariate the first refit left out). Intervals by
resampling worms; p for drive by shuffling drive values within each neuron (2,000).
Output: appended to docs/figures/tiring_source.txt"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_tiring_source as T  # noqa: E402
import run_week1 as W  # noqa: E402

COLS = ["direct", "drive", "nother", "order", "pre"]


def rows_of(w, pos):
    near, cl, X = T.nearest3(pos), w.r.classes, w.r.x
    stims = sorted(w.stims, key=lambda t: t[1])
    out = []
    for k, f, v in stims:
        a = v[k]
        if not (np.isfinite(a) and a > 0) or near[k] is None:
            continue
        before = [(j, g, u) for j, g, u in stims if f - 600 <= g and g + W.POST <= f]
        direct = int(any(j == k for j, _, _ in before))
        other = [u for j, g, u in before if j != k and cl[j] != cl[k] and near[j] is not None and j not in near[k] and k not in near[j]]
        dr = [u[k] for u in other if np.isfinite(u[k])]
        if not dr:
            continue
        with np.errstate(all="ignore"):
            pre = (np.nanmean(X[k, f - W.PRE:f]) - w.mu_u[k]) / w.sd[k]
        if not np.isfinite(pre):
            continue
        out.append(dict(unit=k, loga=np.log(a), direct=direct, drive=max(dr), nother=len(dr), order=f / w.T, pre=pre))
    return out


def design(rows):
    by = defaultdict(list)
    for r in rows:
        by[r["key"]].append(r)
    Xs, ys, groups = [], [], []
    for g in by.values():
        if len(g) < 2:
            continue
        M = np.array([[r[c] for c in COLS] for r in g], float)
        Xs.append(M - M.mean(0)); ys.append(np.array([r["loga"] for r in g]) - np.mean([r["loga"] for r in g])); groups.append(len(g))
    return np.vstack(Xs), np.concatenate(ys), groups


def fit(rows):
    X, y, _ = design(rows)
    return np.linalg.lstsq(X, y, rcond=None)[0], len(y)


def main():
    per = []
    for wi, w in enumerate(W.load_worms()):
        fp = T.POS / f"{w.r.uid}.npz"
        if not fp.exists():
            continue
        pos = np.load(fp)["pos"]
        if pos.shape[0] != w.N:
            continue
        rs = rows_of(w, pos)
        for r in rs:
            r["key"] = f"{wi}_{r['unit']}"
        if rs:
            per.append(rs)
    allr = [r for p in per for r in p]
    b, n = fit(allr)
    rng = np.random.default_rng(21)
    bs = np.array([fit([r for i in rng.integers(0, len(per), len(per)) for r in per[i]])[0] for _ in range(1000)])
    lo, hi = np.percentile(bs, [5, 95], axis=0)
    X, y, groups = design(allr)
    j = COLS.index("drive")
    cnt = 0
    for _ in range(2000):
        Xp = X.copy()
        start = 0
        for g in groups:
            Xp[start:start + g, j] = rng.permutation(Xp[start:start + g, j])
            start += g
        if np.linalg.lstsq(Xp, y, rcond=None)[0][j] <= b[j]:
            cnt += 1
    p = (cnt + 1) / 2001
    line = ("EXPLORATORY within-neuron refit with pre level (review 5), n = %d: " % n
            + "; ".join(f"{c} {b[i]:+.3f} [90%: {lo[i]:+.3f}, {hi[i]:+.3f}]" for i, c in enumerate(COLS))
            + f"; drive within-neuron shuffle p (below) = {p:.4f}")
    print(line)
    with (ROOT / "docs" / "figures" / "tiring_source.txt").open("a") as fh:
        fh.write(line + "\n")


if __name__ == "__main__":
    main()
