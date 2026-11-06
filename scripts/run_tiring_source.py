"""Is it the neuron or the tool that tires? (pre-registered; README section of the same name).

Every direct stimulation of a valid neuron k: log own response regressed on whether k was itself
stimulated in the previous 5 min (positive control, the B1 effect) and whether it was strongly driven
by another neuron's stimulation without light on it (the test), with order, pre level and a class
fixed effect.

Usage: python scripts/run_tiring_source.py [--window 600]
Output: docs/figures/tiring_source.txt
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_week1 as W  # noqa: E402

POS = ROOT / "data" / "derived" / "positions"
FIG = ROOT / "docs" / "figures"
S_Z = 4.0


def nearest3(pos):
    """For each neuron, the set of its three nearest positioned neurons (or None if unpositioned)."""
    P = pos * np.array([S_Z, 1.0, 1.0])
    ok = np.isfinite(P).all(1)
    out = [None] * len(P)
    for k in np.where(ok)[0]:
        d = np.linalg.norm(P - P[k], axis=1)
        d[~ok] = np.inf
        d[k] = np.inf
        out[k] = set(np.argsort(d)[:3].tolist())
    return out


def rows_for(w, pos, window, lo=0.5, hi=1.0):
    near = nearest3(pos)
    cl = w.r.classes
    X = w.r.x
    stims = sorted(w.stims, key=lambda t: t[1])
    out = []
    for k, f, v in stims:
        a = v[k]
        if not (np.isfinite(a) and a > 0) or near[k] is None:
            continue
        before = [(j, g, u) for j, g, u in stims if f - window <= g and g + W.POST <= f]
        direct = int(any(j == k for j, _, _ in before))
        other = [(j, u) for j, g, u in before if j != k and cl[j] != cl[k] and near[j] is not None
                 and j not in near[k] and k not in near[j]]
        if not other:
            continue
        drive = max((u[k] for _, u in other if np.isfinite(u[k])), default=np.nan)
        if not np.isfinite(drive):
            continue
        with np.errstate(all="ignore"):
            pre = (np.nanmean(X[k, f - W.PRE:f]) - w.mu_u[k]) / w.sd[k]
        if not np.isfinite(pre):
            continue
        after = [(j, u) for j, g, u in stims if f + W.POST <= g <= f + W.POST + window and j != k
                 and cl[j] != cl[k] and near[j] is not None and j not in near[k] and k not in near[j]]
        drive_after = max((u[k] for _, u in after if np.isfinite(u[k])), default=np.nan)
        out.append(dict(cls=cl[k], loga=np.log(a), direct=direct, drive=drive, drive_after=drive_after,
                        driven=1 if drive >= hi else (0 if drive < lo else -1),
                        order=f / w.T, pre=pre))
    return out


def fit(rows, cont=False, extra=()):
    """OLS with class fixed effects (within-class demeaning). Returns coefficients dict."""
    cols = ["direct", "drive" if cont else "driven", "order", "pre", *extra]
    rs = [r for r in rows if (cont or r["driven"] >= 0) and all(np.isfinite(r[x]) for x in extra)]
    by = defaultdict(list)
    for r in rs:
        by[r["cls"]].append(r)
    Xs, ys = [], []
    for c, g in by.items():
        if len(g) < 2:
            continue
        M = np.array([[r[x] for x in cols] for r in g], float)
        y = np.array([r["loga"] for r in g])
        Xs.append(M - M.mean(0))
        ys.append(y - y.mean())
    Xa, ya = np.vstack(Xs), np.concatenate(ys)
    b = np.linalg.lstsq(Xa, ya, rcond=None)[0]
    return dict(zip(cols, b)), len(ya)


def analyse(per_worm, cont=False, seed=0, extra=()):
    allr = [r for rs in per_worm for r in rs]
    est, n = fit(allr, cont, extra)
    rng = np.random.default_rng(seed)
    boots = defaultdict(list)
    for _ in range(W.BOOT):
        idx = rng.integers(0, len(per_worm), len(per_worm))
        try:
            b, _ = fit([r for i in idx for r in per_worm[i]], cont, extra)
        except Exception:
            continue
        for k_, v_ in b.items():
            boots[k_].append(v_)
    ci = {k_: (np.percentile(v_, 5), np.percentile(v_, 95)) for k_, v_ in boots.items()}
    return est, ci, n


def perm_p(per_worm, n_perm=5000, seed=1):
    allr = [dict(r) for rs in per_worm for r in rs if r["driven"] >= 0]
    obs = fit(allr)[0]["driven"]
    by = defaultdict(list)
    for i, r in enumerate(allr):
        by[r["cls"]].append(i)
    rng = np.random.default_rng(seed)
    lab = np.array([r["driven"] for r in allr])
    cnt = 0
    for _ in range(n_perm):
        new = lab.copy()
        for idx in by.values():
            new[idx] = rng.permutation(lab[idx])
        for r, d in zip(allr, new):
            r["driven"] = int(d)
        if fit(allr)[0]["driven"] <= obs:
            cnt += 1
    return (cnt + 1) / (n_perm + 1), obs


def main():
    window = 600
    if "--window" in sys.argv:
        window = int(sys.argv[sys.argv.index("--window") + 1])
    worms = W.load_worms()
    per = []
    for w in worms:
        fp = POS / f"{w.r.uid}.npz"
        if not fp.exists():
            continue
        pos = np.load(fp)["pos"]
        if pos.shape[0] != w.N:
            continue
        rs = rows_for(w, pos, window)
        if rs:
            per.append(rs)
    allr = [r for rs in per for r in rs]
    nd = sum(r["driven"] == 1 for r in allr)
    nn = sum(r["driven"] == 0 for r in allr)
    lines = [f"window {window} frames; {len(per)} worms; {len(allr)} direct stimulations; "
             f"driven {nd}, not driven {nn}, middle {len(allr) - nd - nn}; direct before {sum(r['direct'] for r in allr)}"]
    if "--responsiveness" in sys.argv:
        est = ci = None
    else:
        est, ci, n = analyse(per)
        p, _ = perm_p(per)
    for k_ in (est or {}):
        lines.append(f"  {k_:7s} {est[k_]:+.3f} [90%: {ci[k_][0]:+.3f}, {ci[k_][1]:+.3f}]")
    if est is not None:
        lines.append(f"  driven: within-class shuffle p (one-sided, below) = {p:.4f}; n = {n}")
    if est is not None:
        est2, ci2, n2 = analyse(per, cont=True)
        lines.append(f"  sensitivity, continuous drive: {est2['drive']:+.3f} [90%: {ci2['drive'][0]:+.3f}, {ci2['drive'][1]:+.3f}]"
                 f"; direct {est2['direct']:+.3f} [{ci2['direct'][0]:+.3f}, {ci2['direct'][1]:+.3f}]; n = {n2}")
    if "--responsiveness" in sys.argv:
        lines = [f"EXPLORATORY (after the pre-registered run): responsiveness control, window {window}; "
                 "drive_after = k's largest response to other neurons' pokes in the same-length window after its own"]
        for cont in (False, True):
            e, c, n = analyse(per, cont=cont, extra=("drive_after",))
            lines.append("  " + ("continuous" if cont else "groups    ") + "; ".join(
                f" {k_} {e[k_]:+.3f} [{c[k_][0]:+.3f}, {c[k_][1]:+.3f}]" for k_ in e) + f"; n = {n}")
        print("\n".join(lines), flush=True)
        with (FIG / "tiring_source.txt").open("a") as fh:
            fh.write("\n".join(lines) + "\n")
        return
    text = "\n".join(lines)
    print(text, flush=True)
    out = FIG / "tiring_source.txt"
    mode = "a" if window != 600 else "w"
    with out.open(mode) as fh:
        fh.write(text + "\n")


if __name__ == "__main__":
    main()
