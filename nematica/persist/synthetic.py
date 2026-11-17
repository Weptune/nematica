"""Synthetic systems for Study 3's calibration (docs/PERSIST.md section 8): a locked part with a slowly
varying amplitude envelope, and an internal part that is generated (stationary), carried (a state set at
each repeat's onset that decays, with no new variability) or gain-type (a slow random gain on the locked
part). One continuous run of R back-to-back repeats of T native steps; returns (A float32, starts)."""
from __future__ import annotations

import numpy as np

from ..map.synthetic import ou


def envelope(rng, T, kind="normal", sd=0.5):
    """Locked-part amplitude along the clip: exp(sd * slow OU), mean square 1. kind: normal, flat,
    reversed, squared."""
    g = ou(T, np.array([T / 8.0]), rng, 1)[:, 0]
    g = (g - g.mean()) / (g.std() + 1e-12)
    e = np.exp(sd * g)
    if kind == "flat":
        e = np.ones(T)
    elif kind == "reversed":
        e = e[::-1]
    elif kind == "squared":
        e = e ** 2
    return e / np.sqrt((e ** 2).mean())


def system(rng, kind, T, R=10, N=300, share=0.4, K=10, tau_locked=10.0, tau_int=10.0, tau_c=None,
           env_kind="normal", gain_sd=0.3, gain_tau=None, white=0.0):
    Ls = rng.standard_normal((K, N)) / np.sqrt(K)
    Li = rng.standard_normal((K, N)) / np.sqrt(K)
    env = envelope(rng, T, env_kind)
    s = ou(T, np.full(K, tau_locked), rng, K) @ Ls
    s = s / s.std(0)
    s = s * env[:, None]
    s = s / s.std(0)
    total = R * T
    starts = [r * T for r in range(R)]
    if kind == "generated":
        e = ou(total, np.full(K, tau_int), rng, K) @ Li
        e /= e.std(0)
        A = np.sqrt(share) * e
        for r in range(R):
            A[r * T:(r + 1) * T] += np.sqrt(1 - share) * s
    elif kind == "carried":
        t = np.arange(T)[:, None]
        dec = np.exp(-t / (tau_c * T))
        A = np.zeros((total, N))
        for r in range(R):
            z0 = rng.standard_normal(K)
            A[r * T:(r + 1) * T] = (dec * z0[None]) @ Li
        A /= A.std(0)
        A *= np.sqrt(share)
        for r in range(R):
            A[r * T:(r + 1) * T] += np.sqrt(1 - share) * s
    elif kind == "gain":
        g = ou(total, np.array([gain_tau or T / 4.0]), rng, 1)[:, 0]
        g = (g - g.mean()) / (g.std() + 1e-12)
        A = np.zeros((total, N))
        for r in range(R):
            A[r * T:(r + 1) * T] = s * np.exp(gain_sd * g[r * T:(r + 1) * T])[:, None]
    else:
        raise ValueError(kind)
    if white > 0:
        # v0.3: a private white component per unit and step (no lag-2 covariance, so it adds nothing to the
        # lag-2 measures), so that every kind of system can reach the mice's white share (PERSIST_LOG)
        A = A / A.std(0)
        A = np.sqrt(1 - white) * A + np.sqrt(white) * rng.standard_normal(A.shape)
    return A.astype(np.float32), starts
