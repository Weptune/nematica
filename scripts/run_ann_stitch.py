"""Artificial lab D: is the watching limit the data or the method?

Lab C showed that under atlas-like recording (half the units per recording, 30% never seen)
even a linear watcher handed the TRUE hidden drives stays far below poking. Two things could
cause that gap:
  method   the watcher fills unseen units with zeros, so every regression omits half its
           inputs. A watcher that STITCHES recordings together (each pair of units learned
           only from recordings where both were seen) removes this problem without new data.
  data     units that are never recorded mediate effects that no watcher can see.

Recording designs (40 hours, worm-calibrated brains: rho 1.3, kicks 6 held for 4 s):
  every       every unit in every recording
  rotating    half the units per recording, none permanently hidden
  atlas       half per recording, 30% never seen (the worm atlas situation)
Brains: seeds 0 and 1, with no hidden drive and with slow hidden drives at 25% (90 s).
Watchers (all linear, all kicked in silico by clamping, as in lab C):
  plain       the current watching copy (unseen units as zeros)
  stitched    lag-0 and lag-1 covariances pooled pairwise across recordings, A = C1 C0^-1
  stitched_hp the same after removing each unit's 30 s moving average (slow drives)
  (a fixed ridge of 0.01 and a fixed 30 s window were used first; the held-out choice was
  added after the fixed ridge failed with 5 hours of individuals; an automatic window choice was
  tried and dropped, see HP_WINDOWS)
  latent      (only with --latent m; not run so far) m extra hidden dimensions inferred by EM
and poking for reference: the plain average response, and the same with a drift-corrected
baseline (a line between the 10 frames before the kick and the 10 after the response window).
The *_cv watchers choose the ridge on held-out recordings, with no poke data; the drift window
is fixed at 30 s (lab C's smoothing, chosen before any of these scores). Every estimate is scored on the same pairs (both units
never hidden by design, seen while watching, and poked at least once): correlation with the
true K. Output: docs/figures/ann_stitch.csv (resumable; every row records its settings).

Commands behind docs/figures/ann_stitch.csv:
  python scripts/run_ann_stitch.py
  python scripts/run_ann_stitch.py --designs atlas --shares 0.25 --hours 2.5
  python scripts/run_ann_stitch.py --designs atlas --shares 0.25 --hours 10
  python scripts/run_ann_stitch.py --designs atlas --shares 0.25 --tau 10
  python scripts/run_ann_stitch.py --designs atlas --shares 0.25 --sigma 0.3
  python scripts/run_ann_stitch.py --designs atlas --shares 0.25 --sigma 0.3 --hours 5
  worm-shaped (113 individuals; 2.5 min of watching each, 37 min of poking each, as the atlas):
  python scripts/run_ann_stitch.py --designs atlas --shares 0.25 --sigma 0.3 --hours 4.71 --frames 300 --poke-hours 69.7 --poke-frames 4440
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica import annlab as L  # noqa: E402

OUT = Path("docs/figures/ann_stitch.csv")
CLAMP = 0.95
HP = 60


def smooth(a, w=None):
    w = HP if w is None else w
    k = np.ones(w) / w
    pad = np.pad(a, ((w // 2, w - 1 - w // 2), (0, 0)), mode="edge")
    return np.apply_along_axis(lambda c: np.convolve(c, k, mode="valid"), 0, pad)


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


def shrink(W):
    r = np.abs(np.linalg.eigvals(W)).max()
    return W * (0.999 / r) if r > 0.999 else W


def unit_means(recs, n):
    s, c = np.zeros(n), np.zeros(n)
    for y, obs, _ in recs:
        s[obs] += np.nanmean(y[:, obs], 0)
        c[obs] += 1
    return s / np.maximum(c, 1)


def fit_plain(recs, n, ridge=1.0):
    d = n + 1
    XtX, XtY = np.zeros((n, d, d)), np.zeros((n, d))
    for y, obs, _ in recs:
        X = np.hstack([np.nan_to_num(y[:-1]), np.ones((len(y) - 1, 1))])
        G = X.T @ X
        for i in np.flatnonzero(obs):
            XtX[i] += G
            XtY[i] += X.T @ y[1:, i]
    W = np.zeros((n, n))
    for i in range(n):
        if XtX[i].any():
            W[i] = np.linalg.solve(XtX[i] + ridge * np.eye(d), XtY[i])[:n]
    return shrink(W)


def pooled_cov(recs, n, highpass=False):
    S0, N0, S1, N1 = (np.zeros((n, n)) for _ in range(4))
    for y, obs, _ in recs:
        o = np.flatnonzero(obs)
        Y = y[:, o]
        Y = Y - (smooth(Y) if highpass else Y.mean(0))
        S0[np.ix_(o, o)] += Y.T @ Y
        N0[np.ix_(o, o)] += len(Y)
        S1[np.ix_(o, o)] += Y[1:].T @ Y[:-1]
        N1[np.ix_(o, o)] += len(Y) - 1
    seen = np.diag(N0) > 0
    C0 = np.where(N0 > 0, S0 / np.maximum(N0, 1), 0.0)
    C1 = np.where(N1 > 0, S1 / np.maximum(N1, 1), 0.0)
    return C0, C1, seen


def fit_stitched(recs, n, highpass=False, ridge=0.01):
    C0, C1, seen = pooled_cov(recs, n, highpass)
    e = np.flatnonzero(seen)
    A0 = C0[np.ix_(e, e)]
    A0 = (A0 + A0.T) / 2
    w, V = np.linalg.eigh(A0)
    floor = 1e-3 * w.max()
    A0 = (V * np.maximum(w, floor)) @ V.T
    lam = ridge * np.trace(A0) / len(e)
    A = C1[np.ix_(e, e)] @ np.linalg.inv(A0 + lam * np.eye(len(e)))
    W = np.zeros((n, n))
    W[np.ix_(e, e)] = A
    return shrink(W)


RIDGES = (0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0)
HP_WINDOWS = (20, 60, 120, 240)   # NOT chosen automatically: held-out losses on differently
# filtered data are not comparable (shorter windows always look better). The 30 s window
# (60 frames) is the smoothing lab C used before any of these scores; sensitivity is reported.


def K_poke_detrended(recs, n, base=10):
    """Average poke response with the baseline drawn as a line between the 10 frames before
    the kick and the 10 frames after the response window (drift correction for poking)."""
    tot, cnt = np.zeros((n, n)), np.zeros((n, n))
    W = L.WIN
    ramp = (np.arange(W) + 0.5) / W
    for y, obs, kicks in recs:
        for f, j in kicks.items():
            if f - base < 0 or f + W + base > len(y):
                continue
            b0 = y[f - base:f].mean(axis=0)
            b1 = y[f + W:f + W + base].mean(axis=0)
            line = b0[None, :] + ramp[:, None] * (b1 - b0)[None, :]
            resp = (y[f:f + W] - line).sum(axis=0)
            tot[obs, j] += resp[obs]
            cnt[obs, j] += 1
    return np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)


def fit_stitched_cv(recs, n, highpass=False):
    """Ridge (and, with highpass, the drift window) chosen without any poke data: fit on even
    recordings, test on odd and vice versa; the loss is how well A predicts the held-out lag-1
    covariances from the held-out lag-0 covariances, over pairs seen together in the held-out
    half."""
    global HP
    halves = [recs[0::2], recs[1::2]]
    windows = (HP,)          # the drift window stays fixed at 30 s (see HP_WINDOWS note)
    keep = HP
    best, best_loss = None, np.inf
    for hp in windows:
        HP = hp
        loss = np.zeros(len(RIDGES))
        for a, b in ((0, 1), (1, 0)):
            C0b, C1b, _ = pooled_cov(halves[b], n, highpass)
            Nb = np.zeros((n, n))
            for _, obs, _ in halves[b]:
                Nb[np.ix_(obs, obs)] += 1
            ok = Nb > 0
            for k, r in enumerate(RIDGES):
                A = fit_stitched(halves[a], n, highpass, ridge=r)
                loss[k] += np.sum((C1b - A @ C0b)[ok] ** 2)
        k = int(np.argmin(loss))
        if loss[k] < best_loss:
            best_loss, best = loss[k], (hp, RIDGES[k])
    HP = best[0]
    W = fit_stitched(recs, n, highpass, ridge=best[1])
    HP = keep
    return W, best


def fit_latent(recs, n, m=8, iters=25, highpass=True, seed=0):
    """Linear state space with every ever-seen unit as an observed state plus m hidden
    dimensions:  z_t = A z_{t-1} + noise,  y_t = z_t[seen units of this recording] + noise.
    Fitted by EM with a steady-state Kalman smoother per recording (the seen set is fixed
    within a recording). Starts from the stitched solution with small random links to the
    hidden dimensions. Returns the unit-to-unit kick response including paths through the
    hidden dimensions."""
    C0, C1, seen = pooled_cov(recs, n, highpass)
    e = np.flatnonzero(seen)
    p = len(e)
    d = p + m
    rng = np.random.default_rng(seed)
    A = np.zeros((d, d))
    A[:p, :p] = fit_stitched(recs, n, highpass)[np.ix_(e, e)]
    A[p:, p:] = 0.9 * np.eye(m)
    A[:p, p:] = 0.05 * rng.standard_normal((p, m))
    A[p:, :p] = 0.05 * rng.standard_normal((m, p))
    Q = np.eye(d) * 0.1
    Q[:p, :p] = np.diag(np.maximum(np.diag(C0)[e] * 0.3, 1e-3))
    R = np.full(p, 0.01)
    data = []
    for y, obs, _ in recs:
        o = np.flatnonzero(obs[e])
        Y = y[:, e[o]]
        Y = Y - (smooth(Y) if highpass else Y.mean(0))
        data.append((o, Y))
    for it in range(iters):
        Szz = np.zeros((d, d))      # sum E[z_t z_t']   for t = 1..T-1 (as predictors)
        Sz1z = np.zeros((d, d))     # sum E[z_t z_{t-1}']
        Szz_next = np.zeros((d, d))  # sum E[z_t z_t']  for t = 2..T (as targets)
        Syy = np.zeros(p)
        Syz = np.zeros(p)
        Szz_d = np.zeros(p)
        cntR = np.zeros(p)
        T_all = 0
        for o, Y in data:
            T = len(Y)
            Cm = np.zeros((len(o), d))
            Cm[np.arange(len(o)), o] = 1.0
            Rm = np.diag(R[o])
            # steady-state filter covariance by iterating the Riccati equation
            P = Q.copy()
            for _ in range(200):
                Pp = A @ P @ A.T + Q
                S = Cm @ Pp @ Cm.T + Rm
                Kg = np.linalg.solve(S, Cm @ Pp).T
                Pn = Pp - Kg @ Cm @ Pp
                if np.abs(Pn - P).max() < 1e-7:
                    P = Pn
                    break
                P = Pn
            Pp = A @ P @ A.T + Q
            S = Cm @ Pp @ Cm.T + Rm
            Kg = np.linalg.solve(S, Cm @ Pp).T
            P = Pp - Kg @ Cm @ Pp
            J = P @ A.T @ np.linalg.inv(Pp)
            # smoothed covariance (steady state): Ps = P + J (Ps - Pp) J'
            Ps = P.copy()
            for _ in range(200):
                Pn = P + J @ (Ps - Pp) @ J.T
                if np.abs(Pn - Ps).max() < 1e-7:
                    Ps = Pn
                    break
                Ps = Pn
            Pcross = Ps @ J.T  # Cov(z_t, z_{t-1} | all)  =  Ps_t J_{t-1}'
            # filter
            F = np.empty((T, d))
            z = np.zeros(d)
            IKC = np.eye(d) - Kg @ Cm
            for t in range(T):
                z = IKC @ (A @ z) + Kg @ Y[t]
                F[t] = z
            # smoother
            Zs = np.empty((T, d))
            Zs[-1] = F[-1]
            for t in range(T - 2, -1, -1):
                Zs[t] = F[t] + J @ (Zs[t + 1] - A @ F[t])
            Szz += Zs[:-1].T @ Zs[:-1] + (T - 1) * Ps
            Szz_next += Zs[1:].T @ Zs[1:] + (T - 1) * Ps
            Sz1z += Zs[1:].T @ Zs[:-1] + (T - 1) * Pcross
            Syy[o] += (Y ** 2).sum(0)
            Syz[o] += (Y * Zs[:, o]).sum(0)
            Szz_d[o] += (Zs[:, o] ** 2).sum(0) + T * np.diag(Ps)[o]
            cntR[o] += T
            T_all += T - 1
        A = Sz1z @ np.linalg.inv(Szz + 1e-3 * np.eye(d))
        Q = (Szz_next - A @ Sz1z.T) / T_all
        Q = (Q + Q.T) / 2 + 1e-6 * np.eye(d)
        R = np.maximum((Syy - 2 * Syz + Szz_d) / np.maximum(cntR, 1), 1e-4)
        A = shrink(A)
    # unit-to-unit clamped kick response through the full state, read on units only
    mu = unit_means(recs, n)
    K = np.zeros((n, n))
    for jj, j in enumerate(e):
        z, acc = np.zeros(d), np.zeros(d)
        for t in range(L.WIN):
            if t < L.KICK_FRAMES:
                z[jj] = CLAMP - mu[j]
            acc += z
            z = A @ z
        K[e, j] = acc[:p]
    return K


def recordings(br, hours, rng, hidden, seen, sigma, ind_seed, poke=False, frames=None):
    """Like annlab.recordings, with recordings of `frames` frames; with sigma > 0 each
    recording is a different individual."""
    frames = frames or L.FRAMES
    n_rec = max(1, int(round(hours * 3600 / (frames / 2))))
    out = []
    for r in range(n_rec):
        b = L.individual(br, sigma, ind_seed * 1000 + r) if sigma > 0 else br
        obs = (rng.random(br.n) < seen) & ~hidden
        kicks = None
        if poke:
            targets = np.flatnonzero(obs)
            kicks = {f: int(rng.choice(targets)) for f in range(L.EVERY, frames - L.WIN, L.EVERY)}
        out.append((L.record(b, rng, obs, kicks, frames=frames), obs, kicks))
    return out


DESIGNS = {"every": (1.0, 0.0), "rotating": (0.5, 0.0), "atlas": (0.5, 0.3)}
PARAMS = ("seed", "share", "design", "hours", "frames", "poke_hours", "poke_frames", "sigma", "tau")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--shares", default="0,0.25")
    ap.add_argument("--designs", default="every,rotating,atlas")
    ap.add_argument("--hours", type=float, default=40.0, help="hours of watching")
    ap.add_argument("--frames", type=int, default=L.FRAMES, help="frames per watching recording (2 per s)")
    ap.add_argument("--poke-hours", type=float, default=None, help="hours of poking (default: = --hours)")
    ap.add_argument("--poke-frames", type=int, default=None, help="frames per poking recording (default: = --frames)")
    ap.add_argument("--tau", type=float, default=90.0, help="hidden drive timescale (s)")
    ap.add_argument("--sigma", type=float, default=0.0,
                    help="if > 0, every recording comes from a different individual (W x (1 + sigma N))")
    ap.add_argument("--latent", type=int, default=0, help="also run the latent EM watcher with this many dims")
    ap.add_argument("--iters", type=int, default=25)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    L.KICK, L.KICK_FRAMES = 6.0, 8
    ph = args.poke_hours if args.poke_hours is not None else args.hours
    pf = args.poke_frames or args.frames
    out = Path(args.out)
    rows = list(csv.DictReader(out.open(encoding="utf-8"))) if out.exists() else []
    done = {tuple(r[k] for k in PARAMS) + (r["watcher"],) for r in rows}

    def save():
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(PARAMS) + ["watcher", "score", "pairs", "choice"])
            w.writeheader()
            w.writerows(rows)

    for seed in [int(s) for s in args.seeds.split(",")]:
        for share in [float(s) for s in args.shares.split(",")]:
            br = L.make_brain(rho=1.3, share=share, k=3, tau=args.tau, seed=seed, q=0.2)
            K = L.true_K(br, np.random.default_rng(100 + seed))
            for dname in args.designs.split(","):
                seen_frac, hid = DESIGNS[dname]
                hidden = L.design(br.n, np.random.default_rng(200 + seed), hid) if hid > 0 else np.zeros(br.n, bool)
                par = dict(seed=seed, share=share, design=dname, hours=args.hours, frames=args.frames,
                           poke_hours=ph, poke_frames=pf, sigma=args.sigma, tau=args.tau)
                key0 = tuple(str(par[k]) for k in PARAMS)
                tag = int(share * 100) + int(args.sigma * 1000) + int(args.hours * 10)
                recs = recordings(br, args.hours, np.random.default_rng(5000 + 10 * seed + tag), hidden,
                                  seen_frac, args.sigma, 7000 + seed, frames=args.frames)
                precs = recordings(br, ph, np.random.default_rng(6000 + 10 * seed + tag), hidden,
                                   seen_frac, args.sigma, 8000 + seed, poke=True, frames=pf)
                mu = unit_means(recs, br.n)
                Kp = L.K_poke(precs, br.n)
                Kpd = K_poke_detrended(precs, br.n)
                seen_w = np.zeros(br.n, bool)
                for _, obs, _ in recs:
                    seen_w |= obs
                # every estimate is scored on the same pairs: never hidden by design, seen while
                # watching, and poked at least once
                mask = (~np.eye(br.n, dtype=bool) & ~hidden[:, None] & ~hidden[None, :]
                        & seen_w[:, None] & seen_w[None, :] & np.isfinite(Kp) & np.isfinite(Kpd))
                choice = {}

                def cv(hp):
                    W, c = fit_stitched_cv(recs, br.n, highpass=hp)
                    choice["c"] = f"ridge {c[1]}"
                    return K_clamped(W, mu)

                watchers = {
                    "plain": lambda: K_clamped(fit_plain(recs, br.n), mu),
                    "stitched_cv": lambda: cv(False),
                    "stitched_hp_cv": lambda: cv(True),
                    "poking": lambda: Kp,
                    "poking_detrended": lambda: Kpd,
                }
                if args.latent:
                    watchers["latent"] = lambda: fit_latent(recs, br.n, m=args.latent, iters=args.iters, seed=seed)
                for name, fn in watchers.items():
                    if key0 + (name,) in done:
                        continue
                    choice.clear()
                    sc = L.score(fn(), K, mask)
                    rows.append({**par, "watcher": name, "score": round(sc, 4), "pairs": int(mask.sum()),
                                 "choice": choice.get("c", "")})
                    print(rows[-1], flush=True)
                    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
