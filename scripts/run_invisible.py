"""Invisible machinery: the distant-past gain (pre-registered 8 Nov 2026, README section "Invisible
machinery"). Usage: python scripts/run_invisible.py calib|worms|spiking|all
Output: docs/figures/invisible.csv (one row per system)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "figures" / "invisible.csv"
KEEP_S, NPC = 960.0, 8
RECENT_S = [(0, 2), (2, 5), (5, 10)]
AHEAD_S = (20, 40)   # deviation 8 Nov: target is the mean 20 to 40 s ahead
BLOCKS_S = [(10, 30), (30, 90), (90, 270)]
LAMS = 10.0 ** np.arange(-2, 3.01, 0.5)


def prep(Y):
    """Y: units x T, NaN allowed. Drop units with > 20% missing, interpolate the rest, z-score."""
    keep = np.isfinite(Y).mean(1) > 0.8
    Y = Y[keep]
    t = np.arange(Y.shape[1])
    out = []
    for y in Y:
        ok = np.isfinite(y)
        y = np.interp(t, t[ok], y[ok])
        sd = y.std()
        if sd > 0:
            out.append((y - y.mean()) / sd)
    return np.array(out)


def ridge(X, Y, lam):
    p = X.shape[1]
    return np.linalg.solve(X.T @ X + lam * len(X) * np.eye(p), X.T @ Y)


def r2(Yh, Y):
    return 1 - ((Y - Yh) ** 2).sum() / ((Y - Y.mean(0)) ** 2).sum()


def dpg(Y, dt):
    Z = prep(Y[:, :int(round(KEEP_S / dt))])
    if Z.shape[0] < 10:
        return np.nan, np.nan, np.nan
    T = Z.shape[1]
    h = T // 2
    U, S, Vt = np.linalg.svd(Z[:, :h] - Z[:, :h].mean(1, keepdims=True), full_matrices=False)
    P = (U[:, :NPC].T @ Z).T                              # T x NPC
    fr = lambda sec: max(1, int(round(sec / dt)))  # noqa: E731
    blocks = [(fr(a), fr(b)) for a, b in BLOCKS_S]
    recent = [(fr(a) if a else 0, fr(b)) for a, b in RECENT_S]
    a1, a2 = fr(AHEAD_S[0]), fr(AHEAD_S[1])
    t0 = blocks[-1][1]
    ts = np.arange(t0, T - a2)
    cs = np.vstack([np.zeros((1, NPC)), np.cumsum(P, 0)])
    mean_back = lambda a, b: (cs[ts - a + 1] - cs[ts - b + 1]) / (b - a)  # noqa: E731  mean of P[t-b+1 .. t-a]
    rec = np.hstack([P[ts]] + [mean_back(a, b) for a, b in recent])
    far = np.hstack([mean_back(a, b) for a, b in blocks])
    Ytar = (cs[ts + a2 + 1] - cs[ts + a1 + 1]) / (a2 - a1)                      # mean of P[t+a1+1 .. t+a2]
    XR = np.hstack([rec, np.ones((len(ts), 1))])
    XD = np.hstack([rec, far, np.ones((len(ts), 1))])
    half = len(ts) // 2
    A, B = np.arange(half), np.arange(half, len(ts))
    res = {"R": [], "D": []}
    for tr, te in ((A, B), (B, A)):
        for name, X in (("R", XR), ("D", XD)):
            cut = int(len(tr) * 0.75)
            f, v = tr[:cut], tr[cut:]
            best = max(LAMS, key=lambda lam: r2(X[v] @ ridge(X[f], Ytar[f], lam), Ytar[v]))
            Wt = ridge(X[tr], Ytar[tr], best)
            res[name].append(r2(X[te] @ Wt, Ytar[te]))
    rR, rD = np.mean(res["R"]), np.mean(res["D"])
    return rD - rR, rR, rD


def summarise(name, vals, extra=""):
    v = np.array([x for x in vals if np.isfinite(x)])
    rng = np.random.default_rng(0)
    bs = np.array([np.median(v[rng.integers(0, len(v), len(v))]) for _ in range(2000)])
    lo, hi = np.percentile(bs, [5, 95])
    row = dict(system=name, n=len(v), dpg_median=round(float(np.median(v)), 4), lo=round(float(lo), 4),
               hi=round(float(hi), 4), note=extra)
    print(row, flush=True)
    rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
    rows = [r for r in rows if r["system"] != name] + [row]
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row))
        w.writeheader()
        w.writerows(rows)
    return v, bs


def lab(share, r=0.1, n_ind=30, frames=1920, all_seen=False, seed=1, ind0=5000):
    from nematica import annlab as L
    br0 = L.make_brain(rho=1.3, share=share, tau=90.0, seed=seed, q=0.2)
    br0.r = r
    hidden = L.design(br0.n, np.random.default_rng(200))
    rng = np.random.default_rng(7)
    out = []
    for i in range(n_ind):
        ind = L.individual(br0, 0.3, ind0 + i)
        ind.r = r
        obs = np.ones(br0.n, bool) if all_seen else (rng.random(br0.n) < 0.5) & ~hidden
        y = L.record(ind, rng, obs, None, frames=frames)
        out.append(dpg(y[:, obs].T, 0.5)[0])
    return out


def calib():
    vals = {}
    for r in (0.1, 0.3):
        for sh in (0.0, 0.1, 0.25, 0.4):
            v, bs = summarise(f"lab share {sh} r {r}", lab(sh, r))
            vals[(sh, r)] = v
    summarise("lab share 0.0 r 0.1 all units seen", lab(0.0, 0.1, all_seen=True))
    med = [np.median(vals[(sh, 0.1)]) for sh in (0.0, 0.1, 0.25, 0.4)]
    mono = all(b > a for a, b in zip(med, med[1:]))
    rng = np.random.default_rng(1)
    a, b = vals[(0.0, 0.1)], vals[(0.1, 0.1)]
    d = [np.median(b[rng.integers(0, len(b), len(b))]) - np.median(a[rng.integers(0, len(a), len(a))]) for _ in range(2000)]
    lo, hi = np.percentile(d, [5, 95])
    ok = mono and lo > 0
    line = (f"CALIBRATION: medians at r 0.1 {[round(m, 4) for m in med]}; monotone {mono}; share 0.1 - 0 "
            f"{np.median(b) - np.median(a):+.4f} [90%: {lo:+.4f}, {hi:+.4f}] -> {'PASS' if ok else 'FAIL'}")
    print(line)
    with (ROOT / "docs" / "figures" / "invisible.txt").open("a") as fh:
        fh.write(line + "\n")


def worms():
    from nematica.data import load_any_dir
    for name, d in (("worms Atanas 2023", "data/raw/atanas2023_wwweb"),
                    ("worms copper set", "data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415")):
        rs = load_any_dir(ROOT / d)
        vals = []
        for r in rs:
            Y = r.traces.copy()
            if r.valid is not None:
                Y[:, ~r.valid] = np.nan
            vals.append(dpg(Y, r.frame_interval)[0])
        summarise(name, vals)


def spiking():
    from nematica import spiking as S
    for v in ("S0", "S1"):
        recs = S.recordings(v, n_ind=30, poke=False, burn=400)
        summarise(f"spiking {v}", [dpg(r.x, 0.5)[0] for r in recs])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd in ("calib", "all"):
        calib()
    if cmd in ("worms", "all"):
        worms()
    if cmd in ("spiking", "all"):
        spiking()
