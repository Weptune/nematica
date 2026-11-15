"""Synthetic systems with known internal share and timescales (docs/SLOW.md, section 6)."""
from __future__ import annotations

import numpy as np

from ..map.synthetic import ou


def repeated(rng, R=20, T=900, N=200, share=0.5, tau_locked=10.0, tau_internal=40.0, K=10, gap=300,
             continuous=True):
    """R repeats of T samples. Stimulus-locked part: K OU latents with time constant tau_locked, identical
    on every repeat; internal part: K OU latents with tau_internal, running continuously through the
    repeats and the gaps between them (continuous=True) or drawn fresh per repeat. Each unit mixes the
    two with weights giving `share` of its variance to the internal part. Returns (R, T, N)."""
    Ls = rng.standard_normal((K, N)) / np.sqrt(K)
    Li = rng.standard_normal((K, N)) / np.sqrt(K)
    s = ou(T, np.full(K, tau_locked), rng, K) @ Ls
    if continuous:
        e_long = ou(R * (T + gap), np.full(K, tau_internal), rng, K) @ Li
        e = np.stack([e_long[r * (T + gap) + gap: r * (T + gap) + gap + T] for r in range(R)])
    else:
        e = np.stack([ou(T, np.full(K, tau_internal), rng, K) @ Li for _ in range(R)])
    s = s / s.std(0)
    e = e / e.reshape(-1, N).std(0)
    return np.sqrt(1 - share) * s[None] + np.sqrt(share) * e


def continuous(rng, R=20, T=900, N=200, share=0.5, tau_locked=10.0, tau_internal=40.0, K=10, lead=2000):
    """One continuous run: `lead` steps of internal-only activity, then R back-to-back repeats of a T-step
    clip (stimulus-locked part identical on every repeat; internal part continuous through everything).
    Returns (A, starts): A is (lead + R*T) x N, starts the native start step of each repeat."""
    Ls = rng.standard_normal((K, N)) / np.sqrt(K)
    Li = rng.standard_normal((K, N)) / np.sqrt(K)
    s = ou(T, np.full(K, tau_locked), rng, K) @ Ls
    s = s / s.std(0)
    total = lead + R * T
    e = ou(total, np.full(K, tau_internal), rng, K) @ Li
    e /= e.std(0)
    # memory (SLOW_LOG 19:20): built in float32 and in place; the same random draws as before, so values
    # differ from the float64 version only by rounding
    A = (np.sqrt(share) * e).astype(np.float32)
    del e
    sl = (np.sqrt(1 - share) * s).astype(np.float32)
    for r in range(R):
        A[lead + r * T: lead + (r + 1) * T] += sl
    if lead:
        A[:lead] += (np.sqrt(1 - share) * (ou(lead, np.full(K, tau_locked), rng, K) @ Ls
                                           / np.sqrt((Ls ** 2).sum(0)).clip(1e-9))).astype(np.float32)
    return A, [lead + r * T for r in range(R)]
