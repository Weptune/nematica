"""The reverse question (pre-registered 7 Nov 2026, README "The reverse question: do artificial networks
keep the same rules while brains drift?").

Drift = similarity(lag-1 cross-correlations, quarters 1+3 vs 2+4) minus similarity(quarters 1+2 vs
3+4), off-diagonal entries; similarity = correlation of entries. Median over recordings, 90% bootstrap.

Usage:  python scripts/run_drift.py [system ...]   systems: worms human lab_base lab_D spk_S0 spk_S1 spk_S2 spk_S3
Output: docs/figures/drift.csv (resumable)
"""
from __future__ import annotations

import csv
import glob
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_week1 as W1  # noqa: E402

OUT = ROOT / "docs" / "figures" / "drift.csv"


def lag1_corr(Z, pairs):
    """Z: (units, T) with NaN; pairs: indices t (uses t-1 and t). Returns (units, units) correlations
    corr(z_i(t), z_j(t-1)) over valid pairs, NaN where fewer than 50."""
    X1, X0 = Z[:, pairs], Z[:, pairs - 1]
    v1, v0 = np.isfinite(X1), np.isfinite(X0)

    def std(X, v):
        with np.errstate(all="ignore"):
            m = np.nansum(X, 1, keepdims=True) / v.sum(1, keepdims=True)
            sd = np.sqrt(np.nansum((X - m) ** 2, 1, keepdims=True) / v.sum(1, keepdims=True))
            return np.where(v, (X - m) / sd, 0.0)
    A, B = std(X1, v1), std(X0, v0)
    n = v1.astype(float) @ v0.T.astype(float)
    with np.errstate(all="ignore"):
        C = (A @ B.T) / n
    C[n < 50] = np.nan
    return C


def similarity(C1, C2):
    m = ~np.eye(len(C1), dtype=bool) & np.isfinite(C1) & np.isfinite(C2)
    if m.sum() < 50:
        return np.nan
    return float(np.corrcoef(C1[m], C2[m])[0, 1])


RULE = {"excl": None}


def drift_from_rec(w):
    """w: run_week1.Worm. Unpoked frames (30 s rule, or RULE['excl'] frames after each stimulation),
    class means of z-scored neurons."""
    act = w.class_activity()
    if len(act) < 10:
        return np.nan
    Z = np.array(list(act.values()))
    T = Z.shape[1]
    unp = w.unpoked
    if RULE["excl"] is not None:
        unp = np.ones(T, bool)
        for f in w.r.all_stim_frames:
            unp[max(f, 0):f + RULE["excl"]] = False
    ok = np.zeros(T, bool)
    ok[1:] = unp[1:] & unp[:-1]
    t = np.arange(T)
    q = np.minimum(3, 4 * t // T)
    sel = lambda qs: t[ok & np.isin(q, qs)]  # noqa: E731
    C = {k: lag1_corr(Z, sel(v)) for k, v in {"E": [0, 1], "L": [2, 3], "A": [0, 2], "B": [1, 3]}.items()}
    return similarity(C["A"], C["B"]) - similarity(C["E"], C["L"])


def drift_human(path):
    z = np.load(path)
    if "XtX_q" not in z.files:
        return np.nan
    Xq, n = z["XtX_q"], z["n_rows_q"]
    C = z["XtY_q"].shape[2]

    def corr(qs):
        S = Xq[qs].sum(0)
        N = n[qs].sum()
        if N < 1000:
            return None
        s1, s2 = S[-1, 0:C], S[-1, C:2 * C]                      # sums of x(t-1) and x(t-2)
        cov = (S[0:C, C:2 * C] - np.outer(s1, s2) / N) / N
        v1 = (np.diag(S[0:C, 0:C]) - s1 ** 2 / N) / N
        v2 = (np.diag(S[C:2 * C, C:2 * C]) - s2 ** 2 / N) / N
        with np.errstate(all="ignore"):
            return cov / np.sqrt(np.outer(v1, v2))
    E, L, A, B = corr([0, 1]), corr([2, 3]), corr([0, 2]), corr([1, 3])
    if any(x is None for x in (E, L, A, B)):
        return np.nan
    return similarity(A, B) - similarity(E, L)


def lab_rest(LD, code, n_ind):
    """The same lab individuals recorded without pokes: the poke schedule starts after the recording."""
    lead = LD.LEAD
    LD.LEAD = 10 ** 9
    try:
        return LD.variant_recs("" if code == "base" else code, 0, n_ind=n_ind)
    finally:
        LD.LEAD = lead


def summarise(name, vals):
    v = np.array([x for x in vals if np.isfinite(x)])
    rng = np.random.default_rng(0)
    bs = [np.median(v[rng.integers(0, len(v), len(v))]) for _ in range(2000)]
    lo, hi = np.percentile(bs, [5, 95])
    row = {"system": name, "recordings": len(v), "drift_median": round(float(np.median(v)), 4),
           "lo": round(float(lo), 4), "hi": round(float(hi), 4), "positive": int((v > 0).sum())}
    print(row, flush=True)
    rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
    rows = [r for r in rows if r["system"] != name] + [row]
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row))
        w.writeheader()
        w.writerows(rows)


def main():
    systems = sys.argv[1:] or ["worms", "human", "lab_base", "lab_D", "spk_S0", "spk_S1", "spk_S2", "spk_S3"]
    valid = lambda c: True  # noqa: E731
    for s in systems:
        warm = s.endswith("+warm")
        if warm:
            s = s[:-5]
        if s.endswith("@15s"):
            RULE["excl"] = 30
            s = s[:-4]
            suffix = "@15s"
        else:
            RULE["excl"] = None
            suffix = ""
        nopoke = s.endswith("@nopoke")
        if nopoke:
            s = s[:-7]
            suffix = "@nopoke"
        name = s + suffix + ("+warm" if warm else "")
        if s == "worms":
            summarise(name, [drift_from_rec(w) for w in W1.load_worms()])
        elif s == "human":
            files = [f for f in sorted(glob.glob(str(ROOT / "data/derived/ccep_q/*.npz"))) if not f.endswith(".part.npz")]
            summarise(s, [drift_human(f) for f in files])
        elif s.startswith("lab_"):
            import run_ladder as LD
            code = s.split("_")[1]
            recs = lab_rest(LD, code, 40) if nopoke else LD.variant_recs("" if code == "base" else code, 0, n_ind=40)
            summarise(name, [drift_from_rec(W1.Worm(r, valid_fn=valid)) for r in recs])
        elif s.startswith("spk_"):
            from nematica import spiking as S
            recs = S.recordings(s.split("_")[1], n_ind=40, poke=not nopoke, burn=3600 if warm else 400)
            summarise(name, [drift_from_rec(W1.Worm(r, valid_fn=valid)) for r in recs])


if __name__ == "__main__":
    main()
