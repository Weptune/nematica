"""Light or activity: the estimator and the semi-synthetic atlases that check it
(pre-registered 8 Nov 2026, README "Light or activity: what tires a worm neuron?").

A worm is a dict: stims [(k, f, v)] sorted by f (v = response of every neuron, SD units), pre(k, f) ->
pre level, near (list of sets of three nearest neurons or None), classes, T (frames).
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

POST = 30                     # 15 s at 0.5 s per frame (as run_week1)
WINDOW = 600                  # 5 min
BINS = [(0, 240), (240, 600), (600, 1200), (1200, 2400)]   # 0-2, 2-5, 5-10, 10-20 min


def _drive_ok(w, j, k):
    near, cl = w["near"], w["classes"]
    return (cl[j] != cl[k] and near[j] is not None and near[k] is not None
            and j not in near[k] and k not in near[j])


def rows(w, window=WINDOW, bins=None):
    """One row per direct stimulation of a neuron poked at least twice (T1; T3 if bins)."""
    stims = w["stims"]
    count = defaultdict(int)
    for k, _, _ in stims:
        count[k] += 1
    span = bins[-1][1] if bins else window
    out = []
    for i, (k, f, v) in enumerate(stims):
        a = v[k]
        if count[k] < 2 or not (np.isfinite(a) and a > 0) or w["near"][k] is None:
            continue
        pre = w["pre"](k, f)
        if not np.isfinite(pre):
            continue
        before = [(j, g, u) for j, g, u in stims if f - span <= g and g + POST <= f]
        r = dict(unit=k, loga=float(np.log(a)), order=f / w["T"], pre=float(pre),
                 nother=sum(1 for j, g, _ in before if j != k and g >= f - window))
        ranges = bins if bins else [(0, window)]
        for b, (lo, hi) in enumerate(ranges):
            ev = [(j, u) for j, g, u in before if lo <= f - g < hi]
            L = int(any(j == k for j, _ in ev))
            acts = [max(u[k], 0.0) for j, u in ev if j == k and np.isfinite(u[k])]
            acts += [max(u[k], 0.0) for j, u in ev if j != k and np.isfinite(u[k]) and _drive_ok(w, j, k)]
            A = max(acts) if acts else 0.0
            sfx = f"_{b}" if bins else ""
            r["L" + sfx], r["A" + sfx] = L, float(A)
        out.append(r)
    return out


def cols(bins=None):
    if bins:
        return [f"L_{b}" for b in range(len(bins))] + [f"A_{b}" for b in range(len(bins))] + ["nother", "order", "pre"]
    return ["L", "A", "nother", "order", "pre"]


def design(rs, C):
    by = defaultdict(list)
    for r in rs:
        by[r["key"]].append(r)
    Xs, ys, groups, Ldir = [], [], [], []
    for g in by.values():
        if len(g) < 2:
            continue
        M = np.array([[r[c] for c in C] for r in g], float)
        y = np.array([r["loga"] for r in g])
        Xs.append(M - M.mean(0))
        ys.append(y - y.mean())
        groups.append(len(g))
    if not Xs:
        return None
    return np.vstack(Xs), np.concatenate(ys), groups


def fit(rs, C):
    d = design(rs, C)
    if d is None:
        return None
    X, y, _ = d
    return np.linalg.lstsq(X, y, rcond=None)[0]


def light_share(b, rs, C):
    iL, iA = C.index("L"), C.index("A")
    adir = np.mean([r["A"] for r in rs if r["L"] == 1]) if any(r["L"] == 1 for r in rs) else np.nan
    tot = b[iL] + b[iA] * adir
    return b[iL] / tot if tot != 0 else np.nan, tot, adir


def t1(worm_rows, n_boot=2000, n_shuf=2000, seed=0, share=None):
    """worm_rows: list (per worm) of row lists (keys set). Returns point estimates, intervals, p."""
    C = cols()
    share = share or light_share
    allr = [r for p in worm_rows for r in p]
    b = fit(allr, C)
    S, tot, adir = share(b, allr, C)
    rng = np.random.default_rng(seed)
    n = len(worm_rows)
    bs, Ss = [], []
    for _ in range(n_boot):
        sub = [r for i in rng.integers(0, n, n) for r in worm_rows[i]]
        bb = fit(sub, C)
        if bb is None:
            continue
        bs.append(bb)
        Ss.append(share(bb, sub, C)[0])
    bs, Ss = np.array(bs), np.array(Ss)
    p = np.nan
    if n_shuf:
        X, y, groups = design(allr, C)
        iL = C.index("L")
        cnt = 0
        for _ in range(n_shuf):
            Xp = X.copy()
            s0 = 0
            for g in groups:
                Xp[s0:s0 + g, iL] = rng.permutation(Xp[s0:s0 + g, iL])
                s0 += g
            if np.linalg.lstsq(Xp, y, rcond=None)[0][iL] <= b[iL]:
                cnt += 1
        p = (cnt + 1) / (n_shuf + 1)
    lo, hi = np.nanpercentile(bs, [5, 95], axis=0)
    Slo, Shi = np.nanpercentile(Ss, [5, 95])
    return dict(C=C, b=b, lo=lo, hi=hi, S=S, S_lo=Slo, S_hi=Shi, total=tot, A_dir=adir, p_L=p,
                n=len(allr), n_L=int(sum(r["L"] > 0 for r in allr)))


TAU0 = 600                    # amendment 1: 5 min decay weight
SPAN1 = 2400                  # amendment 1: 20 min window


def rows_amended(w, span=SPAN1, tau0=TAU0):
    """Amendment 1: decay-weighted light and log-activity covariates over the previous 20 min."""
    stims = w["stims"]
    count = defaultdict(int)
    for k, _, _ in stims:
        count[k] += 1
    out = []
    for k, f, v in stims:
        a = v[k]
        if count[k] < 2 or not (np.isfinite(a) and a > 0) or w["near"][k] is None:
            continue
        pre = w["pre"](k, f)
        if not np.isfinite(pre):
            continue
        before = [(j, g, u) for j, g, u in stims if f - span <= g and g + POST <= f]
        L, acts = 0.0, [0.0]
        for j, g, u in before:
            wt = np.exp(-(f - g) / tau0)
            if j == k:
                L += wt
                if np.isfinite(u[k]):
                    acts.append(np.log1p(max(u[k], 0.0)) * wt)
            elif np.isfinite(u[k]) and _drive_ok(w, j, k):
                acts.append(np.log1p(max(u[k], 0.0)) * wt)
        out.append(dict(unit=k, loga=float(np.log(a)), order=f / w["T"], pre=float(pre),
                        nother=sum(1 for j, _, _ in before if j != k), L=float(L), A=float(max(acts))))
    return out


def light_share_amended(b, rs, C):
    iL, iA = C.index("L"), C.index("A")
    sel = [r for r in rs if r["L"] > 0]
    if not sel:
        return np.nan, np.nan, np.nan
    mL, mA = np.mean([r["L"] for r in sel]), np.mean([r["A"] for r in sel])
    tot = b[iL] * mL + b[iA] * mA
    return (b[iL] * mL / tot if tot != 0 else np.nan), tot, mA


# ---------------------------------------------------------------- semi-synthetic atlases
def synth_worm(sched, N, classes, T, truth, rng, h=0.5, kappa=0.25, tau=1200, drift_sd=0.3,
               drift_tau=1200, noise=0.6):
    """sched: [(k, f)] real poke schedule. truth 'tool' or 'neuron'."""
    r0 = np.exp(rng.normal(np.log(2.0), 0.5, N))
    grid = np.arange(0, T + 60, 60)
    z = np.zeros((N, len(grid)))
    phi = np.exp(-60 / drift_tau)
    for t in range(1, len(grid)):
        z[:, t] = phi * z[:, t - 1] + np.sqrt(1 - phi ** 2) * drift_sd * rng.standard_normal(N)
    mask = rng.random((N, N)) < 0.08
    Wt = np.where(mask, np.exp(rng.normal(np.log(0.5), 0.5, (N, N))) * np.where(rng.random((N, N)) < 0.75, 1, -1), 0.0)
    np.fill_diagonal(Wt, 0)
    dc, dg = np.zeros(N), np.zeros(N)
    last = 0
    stims = []
    pre_noise = {}
    for k, f in sorted(sched, key=lambda t: t[1]):
        decay = np.exp(-(f - last) / tau)
        dc *= decay
        dg *= decay
        last = f
        resp = r0 * np.exp(z[:, min(f // 60, len(grid) - 1)])
        eff = 0.05 if rng.random() < 0.12 else float(np.exp(rng.normal(0, 0.4)))
        act_k = resp[k] * (1 - dc[k]) * (1 - dg[k]) * eff
        act = Wt[k] * act_k * resp / 2.0 * (1 - dg)
        act[k] = act_k
        v = act + noise * rng.standard_normal(N)
        stims.append((k, f, v))
        pre_noise[(k, f)] = rng.standard_normal()
        if truth in ("tool", "mixed"):
            dc[k] = 1 - (1 - dc[k]) * h
        if truth in ("neuron", "mixed"):
            dg = 1 - (1 - dg) * np.exp(-kappa * np.clip(act, 0, None))
    pos = rng.normal(size=(N, 3))
    near = []
    for k in range(N):
        d = np.linalg.norm(pos - pos[k], axis=1)
        d[k] = np.inf
        near.append(set(np.argsort(d)[:3].tolist()))
    return dict(stims=stims, pre=lambda k, f: pre_noise.get((k, f), 0.0), near=near, classes=list(classes), T=T)


def rows_net(w, window=WINDOW):
    """Exploratory (8 Nov, after T1 was abandoned): activity covariate from network drive only (no lagged own
    response), as the earlier within-neuron drive test; L as T1."""
    stims = w["stims"]
    count = defaultdict(int)
    for k, _, _ in stims:
        count[k] += 1
    out = []
    for k, f, v in stims:
        a = v[k]
        if count[k] < 2 or not (np.isfinite(a) and a > 0) or w["near"][k] is None:
            continue
        pre = w["pre"](k, f)
        if not np.isfinite(pre):
            continue
        before = [(j, g, u) for j, g, u in stims if f - window <= g and g + POST <= f]
        L = int(any(j == k for j, _, _ in before))
        own = [max(u[k], 0.0) for j, _, u in before if j == k and np.isfinite(u[k])]
        dr = [max(u[k], 0.0) for j, _, u in before if j != k and np.isfinite(u[k]) and _drive_ok(w, j, k)]
        out.append(dict(unit=k, loga=float(np.log(a)), order=f / w["T"], pre=float(pre), nother=len(dr) + 0.0,
                        L=L, A=float(max(dr)) if dr else 0.0, own=float(max(own)) if own else np.nan))
    return out


def light_share_net(b, rs, C):
    iL, iA = C.index("L"), C.index("A")
    own = np.nanmean([r["own"] for r in rs if r["L"] == 1]) if any(r["L"] == 1 for r in rs) else np.nan
    tot = b[iL]
    return ((tot - b[iA] * own) / tot if tot != 0 else np.nan), tot, own
