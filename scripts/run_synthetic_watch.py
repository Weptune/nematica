"""Can a brain's cause and effect be learned by watching it? A synthetic worm with known
ground truth answers it.

Ground truth: one of Creamer et al.'s published linear dynamical systems of 154 neurons,
x(t+1) = A x(t) + w, y = x + v, at 2 Hz. Ongoing activity and poke responses come from the
same dynamics, so the question is well posed. True cause and effect: the response of every
neuron i, summed over 30 s, to a unit kick of neuron j (noise off): K[i, j].

It is recorded the way the atlas was: recordings of 37 minutes, with
  full      every neuron observed, no measurement noise
  noisy     every neuron observed, with the model's own measurement noise
  partial   each recording observes a random half of the neurons, with noise
  hidden    as partial, and 30% of the neurons are never observed in any recording
  driveNN   as hidden, plus three slow shared drives that are never observed, carrying NN%
            of the input to each neuron (real worm activity is dominated by a few brain-wide
            signals)

Two ways to learn K:
  watching  a linear model fitted to ongoing activity only (unseen neurons as zero inputs,
            each target fitted only where observed: the NEMATICA watching models' method),
            then kicked and run forward
  poking    kicks to observed neurons every 30 s, as in the atlas; K[i, j] estimated as the
            mean summed response of i after kicks of j (no model)

Score: correlation between the estimate and the true K over off-diagonal pairs of neurons
that are not hidden (for poking, pairs with at least one kick observed).

Usage:  python scripts/run_synthetic_watch.py [--model connectome_constrained]
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.systems.published import DEFAULT_DIR  # noqa: E402

FRAMES = 4440           # 37 minutes at 2 Hz
WIN = 60                # 30 s response window
EVERY = 60              # one kick per 30 s


def true_K(A: np.ndarray) -> np.ndarray:
    n = len(A)
    K = np.zeros((n, n))
    x = np.eye(n)
    for _ in range(WIN):
        K += x
        x = A @ x
    return K


def simulate(A, Lq, sr, frames, rng, kicks=None, burn=600, D=None):
    """One recording; kicks: dict frame -> neuron (unit kick to the state). D (n, k): loadings
    of k shared, unobserved drives (slow, AR(1) with a 10 s timescale) added to the noise."""
    n = len(A)
    x = np.zeros(n)
    y = np.empty((frames, n))
    k = 0 if D is None else D.shape[1]
    s = np.zeros(k)
    a = np.exp(-0.5 / 10.0)
    for t in range(-burn, frames):
        x = A @ x + Lq @ rng.standard_normal(n)
        if k:
            s = a * s + np.sqrt(1 - a * a) * rng.standard_normal(k)
            x += D @ s
        if kicks and t in kicks:
            x[kicks[t]] += 1.0
        if t >= 0:
            y[t] = x + sr * rng.standard_normal(n)
    return y


def fit_watching(recs, n, ridge=1.0):
    """recs: list of (y (T, n) with NaN where unobserved). Linear model y(t+1) = W y(t)."""
    XtX = np.zeros((n, n, n))                       # per target: Gram over its observed frames
    XtY = np.zeros((n, n))
    for y in recs:
        obs = np.isfinite(y[0])
        X = np.nan_to_num(y[:-1])
        Y = y[1:]
        G = X.T @ X
        for i in np.flatnonzero(obs):
            XtX[i] += G
            XtY[i] += X.T @ Y[:, i]
    W = np.zeros((n, n))
    for i in range(n):
        if XtX[i].any():
            W[i] = np.linalg.solve(XtX[i] + ridge * np.eye(n), XtY[i])
    r = np.abs(np.linalg.eigvals(W)).max()
    if r > 0.999:
        W *= 0.999 / r
    return W


def score(K_hat, K, mask):
    a, b = K_hat[mask], K[mask]
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 20 or np.std(a[ok]) == 0:
        return np.nan
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def shared_drive(Lq, share: float, k: int, rng) -> np.ndarray:
    """Loadings so that shared drives carry `share` of each step's input variance on average."""
    n = len(Lq)
    D = rng.standard_normal((n, k))
    q = np.mean(np.diag(Lq) ** 2)
    D *= np.sqrt(share / (1 - share) * q / k)
    return D


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="connectome_constrained")
    ap.add_argument("--hours", default="0.6,2.5,10,40,70")
    ap.add_argument("--regimes", default="full,noisy,partial,hidden,drive25,drive50,drive75")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    z = np.load(Path(DEFAULT_DIR) / f"{args.model}.npz")
    A, Q, R = z["A"], z["Q"], z["R"]
    n = len(A)
    Lq = np.linalg.cholesky(Q + 1e-12 * np.eye(n))
    sr = np.sqrt(np.clip(np.diag(R), 0, None))
    K = true_K(A)
    rng = np.random.default_rng(0)
    hidden = rng.random(n) < 0.3
    off = ~np.eye(n, dtype=bool)
    rows = []
    for regime in args.regimes.split(","):
        D = shared_drive(Lq, int(regime[5:]) / 100, 3, np.random.default_rng(7)) if regime.startswith("drive") else None
        for hours in [float(h) for h in args.hours.split(",")]:
            t0 = time.time()
            n_rec = max(1, int(round(hours * 3600 / (FRAMES / 2))))
            g = np.random.default_rng(1)
            watch, poke_sum, poke_n = [], np.zeros((n, n)), np.zeros((n, n))
            for k in range(n_rec):
                if regime == "full":
                    obs = np.ones(n, bool)
                elif regime == "noisy":
                    obs = np.ones(n, bool)
                else:
                    obs = g.random(n) < 0.5
                    if regime == "hidden" or regime.startswith("drive"):
                        obs &= ~hidden
                noise = sr if regime != "full" else 0 * sr
                # watching: an unstimulated recording
                y = simulate(A, Lq, noise, FRAMES, g, D=D)
                y[:, ~obs] = np.nan
                watch.append(y)
                # poking: a separate recording of the same length with a kick every 30 s
                targets = np.flatnonzero(obs)
                kicks = {f: int(g.choice(targets)) for f in range(EVERY, FRAMES - WIN, EVERY)}
                yp = simulate(A, Lq, noise, FRAMES, g, kicks, D=D)
                for f, j in kicks.items():
                    base = yp[f - 10:f].mean(axis=0)
                    resp = (yp[f:f + WIN] - base).sum(axis=0)
                    poke_sum[obs, j] += resp[obs]
                    poke_n[obs, j] += 1
            W = fit_watching(watch, n)
            K_w = true_K(W)
            K_p = np.where(poke_n > 0, poke_sum / np.maximum(poke_n, 1), np.nan)
            mask = off & ~hidden[:, None] & ~hidden[None, :] if regime not in ("full", "noisy", "partial") else off
            n_kicks = int(poke_n.sum() // max(1, (poke_n > 0).sum(axis=0).mean()))
            row = {"model": args.model, "regime": regime, "hours": hours, "recordings": n_rec,
                   "watching": round(score(K_w, K, mask), 3), "poking": round(score(K_p, K, mask), 3),
                   "kicks": n_rec * len(range(EVERY, FRAMES - WIN, EVERY)),
                   "pairs_poked": int(((poke_n > 0) & mask).sum())}
            rows.append(row)
            print(row, f"({time.time() - t0:.0f} s)", flush=True)
    out = Path(args.out or f"docs/figures/synthetic_watch_{args.model}.csv")
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
