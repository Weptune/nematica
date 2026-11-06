"""Mouse touch cortex: the core tests in a second species (pre-registered 6 Nov 2026; README section
"Mouse touch cortex: the core tests in a second species").

Data (local only, never redistributed): Dalgleish et al. 2020, 11 sessions. Per session folder: Fc.npy
(cells x volume frames, all acquisitions concatenated), iscell.npy, rois.npz (med, iplane,
frames_per_file), *_paqanalysis.mat (stimulation and lick times per acquisition).

Usage: python scripts/run_touch_tests.py [--dry]
Output: docs/figures/touch_tests.txt, docs/figures/touch_sessions.csv
"""
from __future__ import annotations

import csv
import glob
import os
import sys
from math import comb
from pathlib import Path

import h5py
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data" / "derived" / "touch_x" / "touch"
FC = Path("/mnt/user-data/uploads/nematica/data/derived/touch")
FIG = ROOT / "docs" / "figures"
PLANES = 4
VPS = 26.77557 / PLANES                     # volumes per second
f = lambda s: int(round(s * VPS))           # noqa: E731
RESP, PRE, LATE = (f(0.3), f(1.2)), f(1.0), (f(2.0), f(4.0))
REST_AFTER_STIM, REST_FROM_LICK, LICK_WIN = f(3.0), f(2.0), (f(1.0), f(2.0))
STATE_PRE = f(2.0)


def events(sess):
    """(volume frame, kind) with kind = 'laser' or 'catch'; lick volume frames. Acquisitions concatenated."""
    rois = np.load(META / sess / "rois.npz")
    fpf = list(rois["frames_per_file"])
    paqs = sorted(glob.glob(str(META / sess / "*_paqanalysis.mat")))
    if len(paqs) != len(fpf):
        raise ValueError(f"{sess}: {len(paqs)} paq files, {len(fpf)} acquisitions")
    ev, licks, off = [], [], 0
    for p, n in zip(paqs, fpf):
        h = h5py.File(p, "r")
        s = h["pa/stims"]
        for ch, kind in ((5, "catch"), (6, "laser")):
            o = h[s["in"][ch, 0]]
            if not isinstance(o, h5py.Group):
                continue
            fr = o["frames"][()]
            arrs = [h[r][()].ravel() for r in fr.ravel()] if fr.dtype == object else [fr.ravel()]
            for a in arrs:
                ev += [(off + int(x) // PLANES, kind) for x in a if int(x) // PLANES < n]
        licks += [off + int(x) // PLANES for x in h["pa/licks/frames"][()].ravel() if int(x) // PLANES < n]
        off += int(n)
    return sorted(ev), np.array(sorted(licks)), off


def session(sess, dry=False):
    ev, licks, T = events(sess)
    rois = np.load(META / sess / "rois.npz")
    med, ip = rois["med"].astype(float), rois["iplane"]
    keep = np.load(META / sess / "iscell.npy")[:, 0] == 1
    lickfree = lambda t: not np.any((licks >= t - LICK_WIN[0]) & (licks <= t + LICK_WIN[1]))  # noqa: E731
    ok = lambda t: t - PRE >= 0 and t + LATE[1] < T  # noqa: E731
    laser = [t for t, k in ev if k == "laser" and ok(t) and lickfree(t)]
    catch = [t for t, k in ev if k == "catch" and ok(t) and lickfree(t)]
    info = dict(session=sess, frames=T, laser_trials=len(laser), catch_trials=len(catch), cells=int(keep.sum()))
    if dry:
        return info
    F = np.load(FC / sess / "Fc.npy", mmap_mode="r")
    if F.shape[1] != T:
        raise ValueError(f"{sess}: Fc has {F.shape[1]} frames, acquisitions {T}")
    X = np.asarray(F[keep], dtype=np.float32)
    med, ip = med[keep], ip[keep]
    X /= np.median(X, axis=1, keepdims=True)
    rest = np.ones(T, bool)
    for t, _ in ev:
        rest[t: t + REST_AFTER_STIM] = False
    for t in licks:
        rest[max(0, t - REST_FROM_LICK): t + REST_FROM_LICK] = False
    mu, sd = X[:, rest].mean(1, keepdims=True), X[:, rest].std(1, keepdims=True) + 1e-6
    X = (X - mu) / sd
    resp = lambda t, w=RESP: X[:, t + w[0]: t + w[1]].mean(1) - X[:, t - PRE: t].mean(1)  # noqa: E731
    R = np.array([resp(t) for t in laser]).T                     # cells x trials
    C = np.array([resp(t) for t in catch]).T if catch else np.zeros((X.shape[0], 1))
    odd, even = R[:, 0::2].mean(1), R[:, 1::2].mean(1)
    # amendment 1: targets from single trials (each trial hits only a subset of the 200 targets)
    Ro = R[:, 0::2]
    hits = (Ro > 3).sum(1)
    tgt = (hits >= 3) & (hits >= 0.1 * Ro.shape[1]) & ((C > 3).mean(1) <= 0.05)
    tile = med - np.floor(med / 512) * 512
    near = np.zeros(len(tgt), bool)
    for j in np.where(tgt)[0]:
        same = ip == ip[j]
        near |= same & (np.hypot(*(tile - tile[j]).T) < 15)
    non = ~tgt & ~near
    info.update(targets=int(tgt.sum()), non_targets=int(non.sum()))
    if tgt.sum() < 10 or len(laser) < 20:
        info["included"] = 0
        return info
    info["included"] = 1
    # T1: watching (mean resting correlation with targets) and distance, same plane as a target
    Z = X[:, rest]
    corr = (Z[non] @ Z[tgt].T) / Z.shape[1]
    watch = corr.mean(1)
    tplanes = set(ip[tgt].tolist())
    dist = np.full(non.sum(), np.nan)
    tn, tt = tile[non], tile[tgt]
    for k, (pl, xy) in enumerate(zip(ip[non], tn)):
        if pl in tplanes:
            dist[k] = np.min(np.hypot(*(tt[ip[tgt] == pl] - xy).T))
    m = np.isfinite(dist)
    y = even[non]
    info["t1_watch"] = float(spearmanr(watch[m], y[m]).statistic)
    info["t1_distance"] = float(spearmanr(-dist[m], y[m]).statistic)
    info["t1_ceiling"] = float(spearmanr(R[non][m][:, 0::2].mean(1), R[non][m][:, 1::2].mean(1)).statistic)
    info["t1_cells"] = int(m.sum())
    # T2: tiring, network beyond its input
    respnd = non & (even >= 0.5)
    def slope(v):
        v = np.log(np.where(v > 0, v, np.nan)); x = np.arange(len(v), dtype=float); k = np.isfinite(v)
        if k.sum() < 10:
            return np.nan
        x, v = x[k] - x[k].mean(), v[k]
        return float((x * (v - v.mean())).sum() / (x * x).sum())
    Rt = np.where(R[tgt] > 3, R[tgt], np.nan)          # amendment 1: a target's response when it was hit
    with np.errstate(all="ignore"):
        info["t2_target_slope"] = slope(np.nanmean(Rt, 0))
    info["t2_network_slope"] = slope(R[respnd].mean(0)) if respnd.sum() >= 5 else np.nan
    info["t2_responding"] = int(respnd.sum())
    info["t2_diff"] = info["t2_network_slope"] - info["t2_target_slope"]
    # T3: state dependence along the first resting component of non-target cells
    Zn = Z[non] - Z[non].mean(1, keepdims=True)
    u = np.linalg.svd(Zn, full_matrices=False)[0][:, 0]
    if u.mean() < 0:
        u = -u
    state = np.array([u @ X[non][:, t - STATE_PRE: t].mean(1) for t in laser])
    lo_, hi_ = np.percentile(state, [100 / 3, 200 / 3])
    hi, lo = state >= hi_, state <= lo_
    Rn = R[non]
    s_obs = np.corrcoef(Rn[:, hi].mean(1), Rn[:, lo].mean(1))[0, 1]
    rng = np.random.default_rng(7)
    idx = np.where(hi | lo)[0]
    null = []
    for _ in range(500):
        perm = rng.permutation(idx)
        a, b = perm[: hi.sum()], perm[hi.sum(): hi.sum() + lo.sum()]
        null.append(np.corrcoef(Rn[:, a].mean(1), Rn[:, b].mean(1))[0, 1])
    info["t3_S"] = float(s_obs - np.mean(null))
    # T4: sparseness and persistence
    late = np.array([resp(t, LATE) for t in laser[1::2]]).T.mean(1)
    on = non & (even > 1)
    info["t4_share_responding"] = float(on.sum() / non.sum())
    info["t4_share_sustained"] = float((late[on] > 1).mean()) if on.sum() else np.nan
    return info


def boot_ci(v, seed=0, n=2000):
    rng = np.random.default_rng(seed)
    b = [np.median(v[rng.integers(0, len(v), len(v))]) for _ in range(n)]
    return np.percentile(b, [2.5, 97.5])


def main():
    dry = "--dry" in sys.argv
    sessions = sorted(d for d in os.listdir(META) if (META / d).is_dir())
    rows = []
    for s in sessions:
        r = session(s, dry)
        rows.append(r)
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    if dry:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (FIG / "touch_sessions.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, restval="")
        w.writeheader()
        w.writerows(rows)
    inc = [r for r in rows if r.get("included")]
    L = [f"{len(rows)} sessions, {len(inc)} included"]
    g = lambda k: np.array([r[k] for r in inc if np.isfinite(r.get(k, np.nan))])  # noqa: E731
    d = g("t1_watch") - g("t1_distance") if len(g("t1_watch")) == len(g("t1_distance")) else np.array([])
    lo, hi = boot_ci(d)
    L.append(f"T1 medians: ceiling {np.median(g('t1_ceiling')):+.3f}, watching {np.median(g('t1_watch')):+.3f}, "
             f"distance {np.median(g('t1_distance')):+.3f}; watching minus distance {np.median(d):+.3f} [95%: {lo:+.3f}, {hi:+.3f}], "
             f"positive in {(d > 0).sum()} of {len(d)}")
    L.append("  T1 verdict: " + ("watching beats distance" if lo > 0 else "watching loses to distance" if hi < 0 else "no difference detected"))
    t2 = g("t2_diff")
    lo2, hi2 = boot_ci(t2, 1)
    neg = int((t2 < 0).sum()); n = len(t2)
    p = min(1.0, 2 * sum(comb(n, k) for k in range(0, min(neg, n - neg) + 1)) / 2 ** n)
    L.append(f"T2: target slope median {np.median(g('t2_target_slope')):+.4f}, network slope {np.median(g('t2_network_slope')):+.4f}; "
             f"network minus target {np.median(t2):+.4f} [95%: {lo2:+.4f}, {hi2:+.4f}], {neg} of {n} below 0, sign test p = {p:.3g}")
    L.append("  T2 verdict: " + ("the network tires" if np.median(t2) < 0 and p < 0.05 else "no detectable tiring" if lo2 <= 0 <= hi2 else "inconclusive"))
    t3 = g("t3_S")
    lo3, hi3 = boot_ci(t3, 2)
    rng = np.random.default_rng(3)
    flips = [np.median(t3 * rng.choice([-1, 1], len(t3))) for _ in range(10000)]
    p3 = (np.sum(np.array(flips) <= np.median(t3)) + 1) / 10001
    L.append(f"T3: S median {np.median(t3):+.4f} [95%: {lo3:+.4f}, {hi3:+.4f}], sign-flip p = {p3:.4f}")
    L.append("  T3 verdict: " + ("state dependence" if np.median(t3) < 0 and p3 < 0.05 else "none detected" if (lo3 <= 0 <= hi3 and lo3 > -0.05) else "inconclusive"))
    L.append(f"T4: share of non-target cells responding (> 1 SD) median {np.median(g('t4_share_responding')):.3f}; "
             f"of those, still responding 2 to 4 s later {np.median(g('t4_share_sustained')):.3f}")
    text = "\n".join(L)
    print(text)
    (FIG / "touch_tests.txt").write_text(text + "\n")


def explore():
    """Exploratory checks added after the pre-registered run (review 4 asked for the code): T1 against
    catch-trial 'responses' (no laser), and T1 on laser minus catch responses."""
    src = open(__file__).read()
    body = src.split("def session(sess, dry=False):")[1].split("    # T2:")[0]
    ns = {}
    exec(compile("def _s(sess, dry=False):" + body + "    return watch, dist, m, R, C, non, even\n", "x", "exec"), globals(), ns)
    rows = []
    for r in csv.DictReader((FIG / "touch_sessions.csv").open()):
        if r.get("included") != "1":
            continue
        watch, dist, m, R, C, non, even = ns["_s"](r["session"])
        y = even[non][m]
        yc = C[non][m].mean(1)
        rows.append((spearmanr(watch[m], y).statistic, spearmanr(watch[m], yc).statistic,
                     spearmanr(watch[m], y - yc).statistic, spearmanr(-dist[m], y - yc).statistic))
    o = np.array(rows)
    print(f"watching vs laser {np.median(o[:, 0]):+.3f}, vs catch {np.median(o[:, 1]):+.3f} (laser better in {(o[:, 0] > o[:, 1]).sum()} of {len(o)}); "
          f"on laser minus catch: watching {np.median(o[:, 2]):+.3f}, distance {np.median(o[:, 3]):+.3f}, watching minus distance positive in {(o[:, 2] > o[:, 3]).sum()} of {len(o)}")


if __name__ == "__main__":
    explore() if "--explore" in sys.argv else main()
