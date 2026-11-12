"""Synthetic populations with known properties, for the calibration gate (docs/MAP.md, C1 to C3).

A latent linear system: K latent OU processes with power-law variances (exponent `alpha`), a share `slow`
of the latent variance carried by slow latents, loadings that rotate by `drift` radians over the recording,
unit gains on the first latent with lognormal spread `coupling`, private OU noise with variance ratio
`private` and per-unit timescales with log-spread `tau_spread`, and an output nonlinearity |x|^`power`.
"""
from __future__ import annotations

import numpy as np

DEFAULT = dict(N=300, T=8000, alpha=1.0, slow=0.3, drift=0.0, coupling=0.3, private=1.0, tau_spread=0.2,
               power=1.0, tau_fast=4.0, tau_slow=60.0, K=100)


def ou(T, tau, rng, n=1):
    a = np.exp(-1.0 / np.asarray(tau, float))
    x = np.zeros((T, n))
    e = rng.standard_normal((T, n)) * np.sqrt(1 - a ** 2)
    for t in range(1, T):
        x[t] = a * x[t - 1] + e[t]
    return x


def population(rng, **kw):
    p = {**DEFAULT, **kw}
    N, T, K = p["N"], p["T"], min(p["K"], p["N"])
    var = np.arange(1, K + 1, dtype=float) ** -p["alpha"]
    var /= var.sum()
    order = rng.permutation(K)                       # slow latents: a random subset carrying `slow` of the variance
    slow = np.zeros(K, bool)
    acc = 0.0
    for k in order:
        if acc + var[k] <= p["slow"] + 1e-9:
            slow[k] = True
            acc += var[k]
    taus = np.where(slow, p["tau_slow"], p["tau_fast"])
    Zl = ou(T, taus, rng, K) * np.sqrt(var)
    L0 = np.linalg.qr(rng.standard_normal((N, K)))[0] * np.sqrt(N)
    L1 = np.linalg.qr(rng.standard_normal((N, K)))[0] * np.sqrt(N)
    gains = np.exp(rng.standard_normal(N) * p["coupling"])
    L0[:, 0] = np.abs(L0[:, 0]).mean() * gains           # first latent: shared drive with unit-specific gains
    L1[:, 0] = L0[:, 0]
    th = np.linspace(0, p["drift"], T)[:, None]
    X = np.cos(th) * (Zl @ L0.T) + np.sin(th) * (Zl @ L1.T)
    X /= X.std() + 1e-12
    utau = p["tau_fast"] * np.exp(rng.standard_normal(N) * p["tau_spread"] * np.log(10))
    X = X + ou(T, utau, rng, N) * np.sqrt(p["private"])
    if p["power"] != 1.0:
        X = np.sign(X) * np.abs(X) ** p["power"]
    return X
