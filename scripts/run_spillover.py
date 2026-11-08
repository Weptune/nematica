"""How much of the signal propagation atlas is off-target stimulation? (pre-registered 8 Nov 2026, README section
of that name.)

Usage:  python scripts/run_spillover.py calib|worms
Output: docs/figures/spillover.txt (appended), docs/figures/spillover_pairs.csv
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica.bench import causal  # noqa: E402
import run_individuality as RI  # noqa: E402

OUT = ROOT / "docs" / "figures" / "spillover.txt"


def log(s):
    print(s, flush=True)
    with OUT.open("a") as fh:
        fh.write(s + "\n")


class Amp:
    def __init__(self, rec):
        self.rec = rec
        self.sd = causal.unit_sd(rec, "fluct")
        self.npre, self.npost = causal.window(rec.dt)
        self.namp = int(round(causal.AMP_S / rec.dt)) + 1

    def __call__(self, j, f):
        x = self.rec.x
        T = x.shape[1]
        if f - self.npre < 0 or f + self.npost > T or not self.sd[j] > 0:
            return np.nan
        pre, post = x[j, f - self.npre:f], x[j, f:f + self.npost]
        if np.isfinite(pre).sum() < 5 or np.isfinite(post).mean() < 0.8:
            return np.nan
        seg = ((post - np.nanmean(pre)) / self.sd[j])[:self.namp]
        fin = np.isfinite(seg)
        return float(seg[fin].mean()) if fin.any() else np.nan


def worm_tables(recs, nears):
    """Per worm: list of pokes (k, class, a_target, [(class_n, a_n)], {resp class: mean amp}), and its map."""
    tabs, maps = [], []
    for r, nr in zip(recs, nears):
        amp = Amp(r)
        cl = r.classes
        named = [j for j, c in enumerate(cl) if c]
        pokes = []
        for k, f in r.stims:
            ci = cl[k]
            if not ci or nr[k] is None:
                continue
            at = amp(k, f)
            nb = [(cl[n], amp(n, f)) for n in nr[k]]
            resp = defaultdict(list)
            for j in named:
                if j == k or cl[j] == ci or nr[j] is None or j in nr[k] or k in nr[j]:
                    continue
                v = amp(j, f)
                if np.isfinite(v):
                    resp[cl[j]].append(v)
            pokes.append((k, ci, at, nb, {c: float(np.mean(v)) for c, v in resp.items()}))
        tabs.append(pokes)
        m = defaultdict(list)
        for _, ci, _, _, resp in pokes:
            for cj, v in resp.items():
                m[(ci, cj)].append(v)
        maps.append({key: float(np.mean(v)) for key, v in m.items()})
    return tabs, maps


def rows_for(tabs, maps):
    n = len(tabs)
    sums, cnt = defaultdict(float), defaultdict(int)
    for m in maps:
        for key, v in m.items():
            sums[key] += v
            cnt[key] += 1
    own = defaultdict(list)
    for pokes in tabs:
        for _, ci, at, _, _ in pokes:
            if np.isfinite(at):
                own[ci].append(at)
    A = {c: float(np.median(v)) for c, v in own.items() if len(v) >= 3 and np.median(v) > 0}
    rows = []
    for w in range(n):
        def M(key):
            c = cnt[key] - (1 if key in maps[w] else 0)
            if c < 2:
                return np.nan
            return (sums[key] - maps[w].get(key, 0.0)) / c
        acc = defaultdict(lambda: [[], [], []])
        for _, ci, at, nb, resp in tabs[w]:
            if ci not in A or not np.isfinite(at):
                continue
            for cj, r in resp.items():
                mij = M((ci, cj))
                if not np.isfinite(mij):
                    continue
                q = at / A[ci] * mij
                p = 0.0
                for cn, an in nb:
                    if not cn or cn == cj or cn not in A or not np.isfinite(an):
                        continue
                    mn = M((cn, cj))
                    if np.isfinite(mn):
                        p += an / A[cn] * mn
                a = acc[(ci, cj)]
                a[0].append(r); a[1].append(q); a[2].append(p)
        for key, (r, q, p) in acc.items():
            rows.append((w, key, float(np.mean(r)), float(np.mean(q)), float(np.mean(p))))
    return rows


def fit(rows, weights=None):
    groups = defaultdict(list)
    for idx, row in enumerate(rows):
        groups[row[1]].append(idx)
    r = np.array([x[2] for x in rows]); q = np.array([x[3] for x in rows]); p = np.array([x[4] for x in rows])
    w = np.ones(len(rows)) if weights is None else weights
    X = np.zeros((len(rows), 2)); y = np.zeros(len(rows))
    for idx in groups.values():
        idx = np.array(idx)
        ww = w[idx]
        if ww.sum() == 0 or (ww > 0).sum() < 2:
            continue
        for col, v in enumerate((q, p)):
            X[idx, col] = v[idx] - np.average(v[idx], weights=ww)
        y[idx] = r[idx] - np.average(r[idx], weights=ww)
    sw = np.sqrt(w)
    b = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
    return b


def estimate(recs, nears, boot=1000, seed=0):
    tabs, maps = worm_tables(recs, nears)
    rows = rows_for(tabs, maps)
    b = fit(rows)
    rng = np.random.default_rng(seed)
    W = np.array([x[0] for x in rows])
    bs = []
    for _ in range(boot):
        c = np.bincount(rng.integers(0, len(recs), len(recs)), minlength=len(recs)).astype(float)
        bs.append(fit(rows, c[W]))
    bs = np.array(bs)
    lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
    return b, lo, hi, rows


def crosstalk_recs(n_ind=60, k=0.3):
    """Ring lab networks with no real spillover; each neighbour's recorded trace gets k times the target's recorded change."""
    recs, nears, nbrc = RI.lab_ring(0.0, n_ind=n_ind)
    out = []
    for r, nr in zip(recs, nears):
        x = r.x.copy()
        npre = 10
        for tk, f in r.stims:
            if f - npre < 0:
                continue
            base = np.nanmean(r.x[tk, f - npre:f])
            seg = r.x[tk, f:f + 60] - base
            for n in nr[tk]:
                x[n, f:f + len(seg)] += k * seg
        import dataclasses
        out.append(dataclasses.replace(r, x=x))
    return out, nears


def calib():
    log("CALIBRATION (lab ring: real spillover 0.3 -> gamma interval above 0.5; pure crosstalk 0.3 -> includes 0 and below 0.5)")
    recs, nears, _ = RI.lab_ring(0.3)
    b, lo, hi, rows = estimate(recs, nears, boot=300)
    log(f"  real spillover: beta {b[0]:+.3f} [{lo[0]:+.3f}, {hi[0]:+.3f}]; gamma {b[1]:+.3f} [{lo[1]:+.3f}, {hi[1]:+.3f}]; rows {len(rows)}")
    ok_a = lo[1] > 0.5
    recs2, nears2 = crosstalk_recs()
    b2, lo2, hi2, rows2 = estimate(recs2, nears2, boot=300)
    log(f"  crosstalk: beta {b2[0]:+.3f} [{lo2[0]:+.3f}, {hi2[0]:+.3f}]; gamma {b2[1]:+.3f} [{lo2[1]:+.3f}, {hi2[1]:+.3f}]; rows {len(rows2)}")
    ok_b = lo2[1] <= 0 <= hi2[1] and hi2[1] < 0.5
    log(f"CALIBRATION result: (a) {'pass' if ok_a else 'FAIL'}, (b) {'pass' if ok_b else 'FAIL'} -> {'PASS' if ok_a and ok_b else 'FAIL'}")


def worms():
    recs, nears = RI.worm_set(RI.WT)
    b, lo, hi, rows = estimate(recs, nears)
    log(f"WORMS ({len(recs)}): beta {b[0]:+.3f} [{lo[0]:+.3f}, {hi[0]:+.3f}]; gamma {b[1]:+.3f} [{lo[1]:+.3f}, {hi[1]:+.3f}]; rows {len(rows)}")
    v = "real off-target activation" if lo[1] > 0.3 else ("mostly crosstalk" if lo[1] <= 0 <= hi[1] and hi[1] < 0.3 else "inconclusive")
    log(f"WORMS verdict: {v}")
    per = defaultdict(list)
    for w, key, r, q, p in rows:
        per[key].append((r, p))
    out = []
    for key, v in per.items():
        if len(v) < 8:
            continue
        v = np.array(v)
        mr, mp = v[:, 0].mean(), v[:, 1].mean()
        out.append({"source": key[0], "responder": key[1], "worms": len(v), "mean_response": round(float(mr), 4),
                    "mean_spillover_pred": round(float(mp), 4),
                    "attributable_share": round(float(b[1] * mp / mr), 4) if mr != 0 else None})
    with (ROOT / "docs" / "figures" / "spillover_pairs.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(out[0]))
        wr.writeheader()
        wr.writerows(out)
    strong = sorted(out, key=lambda d: -abs(d["mean_response"]))[:max(1, len(out) // 10)]
    share = [d["attributable_share"] for d in strong if d["attributable_share"] is not None]
    log(f"IMPACT: {len(out)} pairs in >= 8 worms; strongest 10% ({len(strong)}): median attributable share {np.median(share):+.3f}; "
        f"with more than half attributable: {sum(s > 0.5 for s in share)}")


if __name__ == "__main__":
    {"calib": calib, "worms": worms}[sys.argv[1]]()
