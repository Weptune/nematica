"""Simple learned baselines, fitted on TRAINING worms only, that generate whole recordings.

Both work directly in the benchmark's measurement space (z-scored class traces at the real
frame rate), because they are fitted to measured data; only the template worm's class mask
is applied afterwards.

    IndependentAR   one AR(p) process per neuron class, pooled across training worms.
                    Captures single-neuron statistics, nothing shared between neurons.
    JointVAR        VAR(1) over the core classes plus velocity and reversal state, pooled
                    across training worms, Gaussian innovations with the fitted covariance.
                    Captures linear correlations, dynamics and behaviour coupling.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..bench.sample import BenchSample
from ..data.canonical import zscore_rows


@dataclass
class IndependentAR:
    classes: tuple[str, ...]
    order: int
    coef: dict           # class -> (order,) AR coefficients
    sigma: dict          # class -> innovation SD

    @classmethod
    def fit(cls, train: list[BenchSample], order: int = 4) -> "IndependentAR":
        classes = train[0].classes
        coef, sigma = {}, {}
        for i, c in enumerate(classes):
            X, Y = [], []
            for s in train:
                if not s.observed[i]:
                    continue
                x = s.x[i]
                M = np.stack([x[order - k - 1: len(x) - k - 1] for k in range(order)], axis=1)
                X.append(M)
                Y.append(x[order:])
            if not X:
                continue
            X, Y = np.concatenate(X), np.concatenate(Y)
            w = np.linalg.lstsq(X, Y, rcond=None)[0]
            coef[c] = w
            sigma[c] = float(np.std(Y - X @ w))
        return cls(classes, order, coef, sigma)

    def generate(self, template: BenchSample, rng: np.random.Generator, burn: int = 200) -> BenchSample:
        T = template.x.shape[1]
        out = np.full((len(self.classes), T), np.nan)
        for i, c in enumerate(self.classes):
            if c not in self.coef or not template.observed[i]:
                continue
            w, sg = self.coef[c], self.sigma[c]
            x = np.zeros(T + burn)
            e = rng.standard_normal(T + burn) * sg
            for t in range(self.order, T + burn):
                x[t] = w @ x[t - self.order: t][::-1] + e[t]
            out[i] = x[burn:]
        return BenchSample(f"independent_ar:{template.origin}", self.classes, zscore_rows(out),
                           template.dt, origin=None)


@dataclass
class JointVAR:
    classes: tuple[str, ...]
    core: np.ndarray     # indices of modelled classes
    A: np.ndarray        # (k+2, k+2) on [core classes, velocity, reversing]
    L: np.ndarray        # Cholesky factor of the innovation covariance
    beh_mean: np.ndarray
    beh_sd: np.ndarray

    @classmethod
    def fit(cls, train: list[BenchSample], min_fraction: float = 0.6, ridge: float = 10.0) -> "JointVAR":
        classes = train[0].classes
        frac = np.mean([s.observed for s in train], axis=0)
        core = np.flatnonzero(frac >= min_fraction)
        vel = np.concatenate([s.behaviour["velocity"] for s in train])
        rev = np.concatenate([s.behaviour["reversing"] for s in train])
        bm = np.array([vel.mean(), rev.mean()])
        bs = np.array([vel.std(), rev.std()])
        XX = np.zeros((core.size + 2, core.size + 2))
        XY = np.zeros_like(XX)
        rows = []
        for s in train:
            z = np.nan_to_num(s.x[core])                       # unobserved classes imputed at 0 [A]
            b = (np.stack([s.behaviour["velocity"], s.behaviour["reversing"]]) - bm[:, None]) / bs[:, None]
            v = np.vstack([z, b])
            X, Y = v[:, :-1], v[:, 1:]
            XX += X @ X.T
            XY += Y @ X.T
            rows.append((X, Y, np.concatenate([s.observed[core], [True, True]])))
        A = XY @ np.linalg.inv(XX + ridge * np.eye(XX.shape[0]))
        res = []
        for X, Y, obs in rows:
            r = Y - A @ X
            r[~obs] = 0.0
            res.append(r)
        R = np.concatenate(res, axis=1)
        cov = R @ R.T / R.shape[1] + 1e-6 * np.eye(R.shape[0])
        return cls(classes, core, A, np.linalg.cholesky(cov), bm, bs)

    def generate(self, template: BenchSample, rng: np.random.Generator, burn: int = 300) -> BenchSample:
        T = template.x.shape[1]
        k = self.A.shape[0]
        v = np.zeros((k, T + burn))
        for t in range(1, T + burn):
            v[:, t] = self.A @ v[:, t - 1] + self.L @ rng.standard_normal(k)
        v = v[:, burn:]
        out = np.full((len(self.classes), T), np.nan)
        out[self.core] = v[:-2]
        out[~template.observed] = np.nan
        beh_raw = v[-2:] * self.beh_sd[:, None] + self.beh_mean[:, None]
        behaviour = {"velocity": beh_raw[0], "reversing": (beh_raw[1] > 0.5).astype(float)}
        return BenchSample(f"joint_var:{template.origin}", self.classes, zscore_rows(out),
                           template.dt, origin=None, behaviour=behaviour)
