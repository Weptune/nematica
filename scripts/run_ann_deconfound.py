"""Artificial lab A, last check on watching: can the hidden drives be taken out?

Slow hidden drives at 25% of input (90 s), 40 hours, brain seed 0; every unit recorded, and
then atlas-like recording (half the units each time, 30% never; patterns estimated from
each recording's seen units).
Linear watchers that also get the drives as inputs:
  oracle        the true drives (an upper bound no experiment has)
  slow PCs, k   the k strongest patterns of activity smoothed over 30 s, estimated from
                the recordings themselves (k = 3 drives in truth)
and, for comparison, the plain linear watcher and poking. Kicks held (0.95 for 4 s).
Output: docs/figures/ann_deconfound.csv

Usage:  python scripts/run_ann_deconfound.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica import annlab as L  # noqa: E402

CLAMP = 0.95


def record_with_drives(br, rng, frames=L.FRAMES, burn=400):
    n, k = br.n, br.D.shape[1]
    x, s = np.zeros(n), np.zeros(k)
    y, S = np.empty((frames, n)), np.empty((frames, k))
    for t in range(-burn, frames):
        s = br.drive_step(s, rng)
        x = br.step(x, s, rng.standard_normal(n))
        if t >= 0:
            y[t] = np.tanh(x) + br.r * rng.standard_normal(n)
            S[t] = s
    return y, S


def smooth(a, w=60):
    k = np.ones(w) / w
    return np.apply_along_axis(lambda c: np.convolve(c, k, mode="same"), 0, a)


def fit_with_inputs(ys, us, ridge=1.0):
    X = np.concatenate([np.hstack([y[:-1], u[:-1]]) for y, u in zip(ys, us)])
    Y = np.concatenate([y[1:] for y in ys])
    X1 = np.hstack([X, np.ones((len(X), 1))])
    B = np.linalg.solve(X1.T @ X1 + ridge * np.eye(X1.shape[1]), X1.T @ Y)
    n = ys[0].shape[1]
    W = B[:n].T
    r = np.abs(np.linalg.eigvals(W)).max()
    if r > 0.999:
        W *= 0.999 / r
    return W, np.concatenate(ys).mean(0)


def K_clamped(W, mu):
    n = len(W)
    K = np.zeros((n, n))
    for j in range(n):
        z, acc = np.zeros(n), np.zeros(n)
        for t in range(L.WIN):
            if t < L.KICK_FRAMES:
                z[j] = CLAMP - mu[j]
            acc += z
            z = W @ z
        K[:, j] = acc
    return K


def fit_partial(recs, us, n, ridge=1.0):
    """Linear watcher on atlas-like recordings (unseen units as zeros, each target fitted only
    where seen), with per-recording extra inputs `us`."""
    k = us[0].shape[1]
    d = n + k + 1
    XtX, XtY = np.zeros((n, d, d)), np.zeros((n, d))
    mu_s, mu_n = np.zeros(n), np.zeros(n)
    for (y, obs, _), u in zip(recs, us):
        X = np.hstack([np.nan_to_num(y[:-1]), u[:-1], np.ones((len(y) - 1, 1))])
        G = X.T @ X
        for i in np.flatnonzero(obs):
            XtX[i] += G
            XtY[i] += X.T @ y[1:, i]
        mu_s[obs] += np.nanmean(y[:, obs], 0)
        mu_n[obs] += 1
    W = np.zeros((n, n))
    for i in range(n):
        if XtX[i].any():
            W[i] = np.linalg.solve(XtX[i] + ridge * np.eye(d), XtY[i])[:n]
    r = np.abs(np.linalg.eigvals(W)).max()
    if r > 0.999:
        W *= 0.999 / r
    return W, mu_s / np.maximum(mu_n, 1)


def atlas_like(rows):
    br = L.make_brain(rho=1.3, share=0.25, tau=90.0, seed=0, q=0.2)
    K = L.true_K(br, np.random.default_rng(100))
    hidden = L.design(br.n, np.random.default_rng(200))
    mask = ~np.eye(br.n, dtype=bool) & ~hidden[:, None] & ~hidden[None, :]
    recs = L.recordings(br, 40.0, np.random.default_rng(402), hidden)
    us = {"plain": [np.zeros((len(y), 0)) for y, _, _ in recs]}
    for k in (3, 6):
        out = []
        for y, obs, _ in recs:
            sm = smooth(y[:, obs] - np.nanmean(y[:, obs], 0))
            u_, s_, vt = np.linalg.svd(sm, full_matrices=False)
            sc = u_[:, :k] * s_[:k]
            out.append((sc - sc.mean(0)) / sc.std(0))
        us[f"slow_pcs_{k}"] = out
    for name, u in us.items():
        W, mu = fit_partial(recs, u, br.n)
        rows.append({"recording": "atlas-like", "watcher": name, "score": round(L.score(K_clamped(W, mu), K, mask), 4)})
        print(rows[-1], flush=True)
    P = L.recordings(br, 40.0, np.random.default_rng(403), hidden, poke=True)
    rows.append({"recording": "atlas-like", "watcher": "poking", "score": round(L.score(L.K_poke(P, br.n), K, mask), 4)})
    print(rows[-1], flush=True)


def main() -> int:
    L.KICK, L.KICK_FRAMES = 6.0, 8
    br = L.make_brain(rho=1.3, share=0.25, tau=90.0, seed=0, q=0.2)
    K = L.true_K(br, np.random.default_rng(100))
    mask = ~np.eye(br.n, dtype=bool)
    rng = np.random.default_rng(400)
    n_rec = int(round(40 * 3600 / (L.FRAMES / 2)))
    data = [record_with_drives(br, rng) for _ in range(n_rec)]
    ys = [d[0] for d in data]
    rows = []
    none = [np.zeros((len(y), 0)) for y in ys]
    res = {"plain": fit_with_inputs(ys, none), "oracle_true_drives": fit_with_inputs(ys, [d[1] for d in data])}
    allz = np.concatenate([smooth(y - y.mean(0)) for y in ys])
    _, _, vt = np.linalg.svd(allz[::10], full_matrices=False)
    for k in (3, 6, 12):
        us = [smooth(y - y.mean(0)) @ vt[:k].T for y in ys]
        res[f"slow_pcs_{k}"] = fit_with_inputs(ys, us)
    for name, (W, mu) in res.items():
        rows.append({"recording": "every unit", "watcher": name, "score": round(L.score(K_clamped(W, mu), K, mask), 4)})
        print(rows[-1], flush=True)
    hidden = np.zeros(br.n, bool)
    P = L.recordings(br, 40.0, np.random.default_rng(401), hidden, poke=True, seen=1.0)
    rows.append({"recording": "every unit", "watcher": "poking", "score": round(L.score(L.K_poke(P, br.n), K, mask), 4)})
    print(rows[-1])
    atlas_like(rows)
    with Path("docs/figures/ann_deconfound.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
