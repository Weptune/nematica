"""Brain signatures, measured the same way on real worms and on any artificial system.

Input: recordings in the atlas format (nematica.data.pumpprobe.PumpProbe), one per run ("animal"), with
`stims` (unit row, frame) for each push and `all_stim_frames`. Units are grouped by `classes` (in worms,
left and right partners of a neuron type share a class; in an artificial system each unit is its own
class, and a unit keeps its name across runs).

The definitions are those of the project's cross-system comparison (README "The six axes",
scripts/run_ladder.py and scripts/run_week1.py, which are the research versions of this code; a test
checks they agree on the atlas), plus three rest signatures from the emulator work. Frame constants are
in atlas frames of 0.5 s; recordings at another step length are resampled to 0.5 s first (test.py).

SIGNATURES (name: what it measures; worm value from the atlas in brackets)
  rest_dim       share of resting variance in the top 3 patterns (0.43): how few patterns the activity uses
  slow_share     share of each unit's activity that is slow (lags 10 to 40 s) (about 0.7)
  correlation    mean absolute correlation between units at rest
  timescale      median time for a unit's activity autocorrelation to fall to 0.5, seconds
  echo_breadth   share of units a single push moves by more than 1 SD (0.085)
  evoked_share   share of the change after a push that the push caused, against moments with no push (0.42)
  tiring         log change of a unit's own response when pushed a second time, against matched controls (-0.42)
  watch_share    how well a linear model fitted at rest predicts push responses, as a share of how well
                 runs agree with each other (0.61): "can you copy it by watching it?"
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Sequence

import numpy as np

POST, PRE, EXCL = 30, 20, 60            # 15 s after, 10 s before a push; 30 s excluded after any push
SLOW_LAGS = (20, 40, 80)                 # 10, 20, 40 s

SIGNATURES = ("rest_dim", "slow_share", "correlation", "timescale", "echo_breadth", "evoked_share",
              "tiring", "watch_share")
LABELS = {"rest_dim": "few patterns at rest", "slow_share": "slow activity", "correlation": "units move together",
          "timescale": "timescale", "echo_breadth": "push spread", "evoked_share": "push stands out",
          "tiring": "tiring on a second push", "watch_share": "copyable by watching"}
ABOUT = {
    "rest_dim": "Share of resting variance in the 3 strongest patterns: how few patterns the activity uses.",
    "slow_share": "Share of each unit's activity that is slow (still correlated 10 to 40 s later).",
    "correlation": "Mean absolute correlation between units at rest.",
    "timescale": "Median time for a unit's activity to become half-forgotten (autocorrelation 0.5), in seconds.",
    "echo_breadth": "Share of units that a single push moves by more than 1 SD.",
    "evoked_share": "How much of the change after a push is caused by the push, against moments with no push.",
    "tiring": "Log change in a unit's own response when it is pushed a second time, against matched controls. "
              "Negative = it answers less.",
    "watch_share": "How well a linear model fitted only to resting activity predicts the push responses, as a share "
                   "of how well runs agree with each other. Real worms: poorly.",
}


class Run:
    """One recording prepared for the signatures (the research code's `Worm`)."""

    def __init__(self, r, valid_fn: Callable[[str], bool] | None = None):
        self.r = r
        X = r.x
        N, T = X.shape
        self.N, self.T = N, T
        valid_fn = valid_fn or (lambda c: True)
        self.valid = np.array([bool(c) and valid_fn(c) for c in r.classes])
        unp = np.ones(T, bool)
        for f in r.all_stim_frames:
            unp[max(f, 0):f + EXCL] = False
        self.unpoked = unp
        with np.errstate(all="ignore"):
            sd = np.nanstd(np.where(unp, X, np.nan), axis=1)
        sd[~(sd > 0)] = np.nan
        self.sd = sd
        self.stims = []
        for k, f in r.stims:
            if not self.valid[k] or f - PRE < 0 or f + POST > T:
                continue
            self.stims.append((k, f, self.change(f)))

    def change(self, f):
        X = self.r.x
        with np.errstate(all="ignore"):
            return (np.nanmean(X[:, f:f + POST], axis=1) - np.nanmean(X[:, f - PRE:f], axis=1)) / self.sd

    def class_resp(self):
        acc = defaultdict(list)
        cl = self.r.classes
        for k, f, v in self.stims:
            for j in range(self.N):
                if j != k and self.valid[j] and cl[j] != cl[k] and np.isfinite(v[j]):
                    acc[(cl[k], cl[j])].append(v[j])
        return {p: float(np.mean(v)) for p, v in acc.items()}

    def class_activity(self):
        X = self.r.x
        with np.errstate(all="ignore"):
            z = (X - np.nanmean(X, axis=1, keepdims=True)) / np.nanstd(X, axis=1, keepdims=True)
        act = defaultdict(list)
        for j, c in enumerate(self.r.classes):
            if self.valid[j]:
                act[c].append(z[j])
        with np.errstate(all="ignore"):
            return {c: np.nanmean(v, axis=0) for c, v in act.items()}


def agree(a, b, min_pairs=20):
    ks = [k for k in a if k in b]
    if len(ks) < min_pairs:
        return np.nan
    u, v = np.array([a[k] for k in ks]), np.array([b[k] for k in ks])
    if u.std() == 0 or v.std() == 0:
        return np.nan
    return float(np.corrcoef(u, v)[0, 1])


def fit_watching(train, ridge=1.0):
    acts = [w.class_activity() for w in train]
    C = sorted({c for a in acts for c in a})
    ix = {c: i for i, c in enumerate(C)}
    XtX, XtY = np.zeros((len(C), len(C))), np.zeros((len(C), len(C)))
    for w, act in zip(train, acts):
        Z = np.zeros((w.T, len(C)))
        seen = np.zeros(len(C), bool)
        for c, a in act.items():
            Z[:, ix[c]] = np.nan_to_num(a)
            seen[ix[c]] = True
        ok = w.unpoked[:-1] & w.unpoked[1:]
        X, Y = Z[:-1][ok], Z[1:][ok]
        XtX += X.T @ X
        XtY += X.T @ (Y * seen)
    A = np.linalg.solve(XtX + ridge * np.eye(len(C)), XtY).T
    rad = np.abs(np.linalg.eigvals(A)).max()
    if rad >= 0.99:
        A *= 0.99 / rad
    pred = {}
    for i, ci in enumerate(C):
        z, acc = np.zeros(len(C)), np.zeros(len(C))
        for _ in range(POST):
            z = A @ z
            z[i] = 1.0
            acc += z
        for j, cj in enumerate(C):
            if j != i:
                pred[(ci, cj)] = acc[j] / POST
    return pred


def watch_share(runs):
    R = [w.class_resp() for w in runs]
    shares = []
    for fold in range(3):
        pool = [i for i in range(len(runs)) if i % 3 == fold]
        train = [runs[i] for i in range(len(runs)) if i % 3 != fold]
        pred = fit_watching(train)
        w2w = [agree(R[a], R[b]) for x, a in enumerate(pool) for b in pool[x + 1:]]
        wat = [agree(pred, R[i]) for i in pool]
        with np.errstate(all="ignore"):
            shares.append(np.nanmedian(wat) / np.nanmedian(w2w))
    return float(np.mean(shares)), float(np.nanmedian([agree(R[a], R[b]) for a in range(len(R)) for b in range(a + 1, len(R))]))


def echo_breadth(runs):
    vals = []
    for w in runs:
        cl = w.r.classes
        for k, f, v in w.stims:
            per = defaultdict(list)
            for j in range(w.N):
                if j != k and w.valid[j] and cl[j] != cl[k] and np.isfinite(v[j]):
                    per[cl[j]].append(v[j])
            if len(per) >= 10:
                m = np.array([np.mean(x) for x in per.values()])
                vals.append(float(np.mean(np.abs(m) > 1.0)))
    return float(np.median(vals)) if vals else np.nan


def _rest_matrix(w):
    act = w.class_activity()
    if len(act) < 10:
        return None
    Z = np.array([a[w.unpoked] for a in act.values()])
    Z = Z[:, np.isfinite(Z).mean(0) > 0.5] if Z.shape[1] else Z
    if Z.shape[1] < 60:
        return None
    with np.errstate(all="ignore"):
        Z = (Z - np.nanmean(Z, 1, keepdims=True)) / np.nanstd(Z, 1, keepdims=True)
    return np.nan_to_num(Z)


def rest_dim(runs):
    vals = []
    for w in runs:
        Z = _rest_matrix(w)
        if Z is None:
            continue
        ev = np.linalg.svd(Z - Z.mean(1, keepdims=True), compute_uv=False) ** 2
        vals.append(float(ev[:3].sum() / ev.sum()))
    return float(np.median(vals)) if vals else np.nan


def correlation(runs):
    vals = []
    for w in runs:
        Z = _rest_matrix(w)
        if Z is None:
            continue
        c = np.corrcoef(Z)
        c = c[np.triu_indices_from(c, 1)]
        c = c[np.isfinite(c)]
        if c.size:
            vals.append(float(np.mean(np.abs(c))))
    return float(np.median(vals)) if vals else np.nan


def _acf(v, L):
    v = v - v.mean()
    d = np.dot(v, v)
    return float(np.dot(v[L:], v[:-L]) / d) if d > 0 else np.nan


def slow_share(runs):
    """Per class and run: autocorrelation of the whole activity at 10, 20 and 40 s, log-linearly
    extrapolated to lag 0 (the slow part's share), clipped to [0, 1]; median over classes and runs."""
    vals = []
    for w in runs:
        for a in w.class_activity().values():
            v = np.asarray(a, float)
            if np.isfinite(v).mean() < 0.95:
                continue
            v = np.where(np.isfinite(v), v, np.nanmean(v))
            d = np.array([_acf(v, L) for L in SLOW_LAGS])
            if not np.isfinite(d).all() or (d <= 0.01).any():
                vals.append(0.0)
                continue
            sl, ic = np.polyfit(SLOW_LAGS, np.log(d), 1)
            vals.append(float(np.clip(np.exp(ic), 0, 1)))
    return float(np.median(vals)) if vals else np.nan


def timescale(runs, dt=0.5, max_s=120.0):
    vals = []
    for w in runs:
        for a in w.class_activity().values():
            v = np.asarray(a, float)
            if np.isfinite(v).mean() < 0.95:
                continue
            v = np.where(np.isfinite(v), v, np.nanmean(v))
            v = v - v.mean()
            n = v.size
            f = np.fft.rfft(v, 2 * n)
            ac = np.fft.irfft(f * np.conj(f))[:n]
            if ac[0] <= 0:
                continue
            ac = ac / ac[0]
            m = min(n - 1, int(max_s / dt))
            below = np.flatnonzero(ac[:m + 1] < 0.5)
            vals.append(float(below[0] * dt) if below.size else max_s)
    return float(np.median(vals)) if vals else np.nan


def evoked_share(runs):
    fl, ev = [], []
    for w in runs:
        for t in range(PRE, w.T - POST, 5):
            if not w.unpoked[t - PRE:t + POST].all():
                continue
            v = w.change(t)[w.valid]
            v = v[np.isfinite(v)]
            if len(v) >= 10:
                fl.append(np.mean(v ** 2))
        for k, f, v in w.stims:
            m = w.valid.copy()
            m[k] = False
            vv = v[m]
            vv = vv[np.isfinite(vv)]
            if len(vv) >= 10:
                ev.append(np.mean(vv ** 2))
    if not fl or not ev:
        return np.nan
    return float((np.mean(ev) - np.mean(fl)) / np.mean(ev))


def _repeat_pairs(w, all_valid=True):
    """Repeat pairs (a unit's first and second push) and matched control pairs (first pushes of two
    different units at a similar gap and time) for one run: lists of (log echo ratio, log own-response
    ratio). The research code's B1 pairs."""
    cl = w.r.classes
    by = defaultdict(list)
    for k, f, v in w.stims:
        by[k].append((f, v))
    first = sorted((s[0][0], k, s[0][1]) for k, s in by.items())

    def echo(k, v):
        m = w.valid.copy()
        m[k] = False
        if not all_valid:
            m &= np.array([c != cl[k] for c in cl])
        vv = v[m]
        vv = vv[np.isfinite(vv)]
        return np.sqrt(np.mean(vv ** 2)) if len(vv) >= 10 else np.nan

    def ratio(k1, v1, k2, v2):
        e1, e2 = echo(k1, v1), echo(k2, v2)
        le = np.log(e2 / e1) if e1 > 0 and e2 > 0 else np.nan
        a1, a2 = v1[k1], v2[k2]
        la = np.log(a2 / a1) if (np.isfinite(a1) and np.isfinite(a2) and a1 > 0 and a2 > 0) else np.nan
        return le, la

    reps, ctls = [], []
    for k, s in by.items():
        if len(s) < 2:
            continue
        s = sorted(s, key=lambda t: t[0])
        (f1, v1), (f2, v2) = s[0], s[1]
        rep = ratio(k, v1, k, v2)
        gap = f2 - f1
        tol = max(0.2 * gap, 60)
        cand = []
        for a in range(len(first)):
            for b in range(a + 1, len(first)):
                fx, kx, vx = first[a]
                fy, ky, vy = first[b]
                if kx == ky or abs((fy - fx) - gap) > tol:
                    continue
                cand.append((abs(fx - f1), kx, vx, ky, vy))
        cand.sort(key=lambda t: t[0])
        cs = [ratio(kx, vx, ky, vy) for _, kx, vx, ky, vy in cand[:5]]
        if np.isfinite(rep[0]) and any(np.isfinite(c[0]) for c in cs):
            reps.append(rep)
            ctls.append(cs)
    return reps, ctls


def tiring(runs, all_valid=True):
    """Mean over runs of: mean log ratio of a unit's own response at its second push over its first,
    minus the same over matched control pairs (the research code's B1 'D target')."""
    per = []
    for w in runs:
        reps, ctls = _repeat_pairs(w, all_valid)
        if not reps:
            continue
        la_r = np.array([r[1] for r in reps])
        la_c = np.array([c[1] for cs in ctls for c in cs])
        if np.isfinite(la_r).any() and np.isfinite(la_c).any():
            per.append(np.nanmean(la_r) - np.nanmean(la_c))
    return float(np.mean(per)) if per else np.nan


def poked_response(runs):
    """Median change of the pushed unit itself, in SD: checks the pushes were real and strong enough."""
    v = [s[2][s[0]] for w in runs for s in w.stims if np.isfinite(s[2][s[0]])]
    return float(np.median(v)) if v else np.nan


def measure(recordings: Sequence, valid_fn: Callable[[str], bool] | None = None, dt: float = 0.5) -> dict:
    runs = [Run(r, valid_fn) for r in recordings]
    ws, rel = watch_share(runs)
    return {"rest_dim": rest_dim(runs), "slow_share": slow_share(runs), "correlation": correlation(runs),
            "timescale": timescale(runs, dt), "echo_breadth": echo_breadth(runs), "evoked_share": evoked_share(runs),
            "tiring": tiring(runs, all_valid=False), "watch_share": ws,
            "reliability": rel, "poked_response": poked_response(runs),
            "n_runs": len(runs), "n_pushes": int(sum(len(w.stims) for w in runs)),
            "units_per_run": float(np.median([w.valid.sum() for w in runs]))}
