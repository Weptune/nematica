"""A ladder of next-step forecasters, used as simulators (arc 1: forecasting vs fidelity).

Every model lives in the same state space as JointVAR: the core neuron classes (z-scored,
unobserved classes imputed at 0 [A]) plus z-scored velocity and reversal state. Every model
is fitted on TRAINING worms to predict the next frame, with its ridge penalty chosen on
VALIDATION worms by one-step R^2. As a simulator it is run forward on its own output with
Gaussian innovations whose covariance is the training residual covariance, which is how a
forecaster is normally turned into a generative model.

Ladder (roughly increasing capacity):
    diag_ar1   each variable predicted from its own previous value
    diag_ar4   each variable from its own previous 4 values
    var1       all variables from all previous values (one lag)
    var3       all variables, three lags
    esn400     echo-state network, 400 tanh units, linear readout
    esn1500    echo-state network, 1500 tanh units, linear readout

Forecasting skill is measured on TEST worms from the true history: one-step R^2 and
5-step (3 s) R^2 from deterministic rollouts, over observed core classes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from ..bench.sample import BenchSample
from ..data.canonical import zscore_rows


# ---------------------------------------------------------------- shared state space

@dataclass
class StateSpace:
    classes: tuple[str, ...]
    core: np.ndarray
    beh_mean: np.ndarray
    beh_sd: np.ndarray

    @classmethod
    def from_train(cls, train: Sequence[BenchSample], min_fraction: float = 0.6) -> "StateSpace":
        frac = np.mean([s.observed for s in train], axis=0)
        vel = np.concatenate([s.behaviour["velocity"] for s in train])
        rev = np.concatenate([s.behaviour["reversing"] for s in train])
        return cls(train[0].classes, np.flatnonzero(frac >= min_fraction),
                   np.array([vel.mean(), rev.mean()]), np.array([vel.std(), rev.std()]))

    @property
    def k(self) -> int:
        return self.core.size + 2

    def encode(self, s: BenchSample) -> tuple[np.ndarray, np.ndarray]:
        """(k, T) state and (k,) mask of which variables are real for this worm."""
        z = np.nan_to_num(s.x[self.core])
        b = (np.stack([s.behaviour["velocity"], s.behaviour["reversing"]]) - self.beh_mean[:, None]) \
            / self.beh_sd[:, None]
        mask = np.concatenate([s.observed[self.core], [True, True]])
        return np.vstack([z, b]), mask

    def decode(self, v: np.ndarray, template: BenchSample, name: str) -> BenchSample:
        T = template.x.shape[1]
        out = np.full((len(self.classes), T), np.nan)
        out[self.core] = v[:-2, :T]
        out[~template.observed] = np.nan
        beh = v[-2:, :T] * self.beh_sd[:, None] + self.beh_mean[:, None]
        behaviour = {"velocity": beh[0], "reversing": (beh[1] > 0.5).astype(float)}
        return BenchSample(f"{name}:{template.origin}", self.classes, zscore_rows(out),
                           template.dt, origin=None, behaviour=behaviour)


# ---------------------------------------------------------------- feature maps

class LagFeatures:
    """Linear models: features are the previous `lags` states (optionally only own history)."""

    def __init__(self, k: int, lags: int, diagonal: bool):
        self.k, self.lags, self.diagonal = k, lags, diagonal

    @property
    def warmup(self) -> int:
        return self.lags

    def run(self, v: np.ndarray) -> np.ndarray:
        """Features for predicting v[:, t] from history, for t = lags..T-1 -> (T-lags, F)."""
        T = v.shape[1]
        cols = [v[:, self.lags - 1 - l: T - 1 - l].T for l in range(self.lags)]
        return np.hstack(cols)

    def step_init(self, hist: np.ndarray):
        """State holding the `lags` frames BEFORE the last column of hist; the last column is
        then fed with step(), exactly as in the ESN."""
        return list(hist[:, -self.lags - 1:-1].T)

    def step(self, state, v_t):
        state = state[1:] + [v_t]
        return state, np.concatenate(state[::-1])


class ESNFeatures:
    """Echo-state network: fixed random tanh reservoir driven by the state; features
    [reservoir, current state, 1]."""

    def __init__(self, k: int, n: int, seed: int = 0, radius: float = 0.9, leak: float = 0.5,
                 in_scale: float = 0.3, density: float = 0.05):
        rng = np.random.default_rng(seed)
        W = rng.standard_normal((n, n)) * (rng.random((n, n)) < density)
        eig = np.max(np.abs(np.linalg.eigvals(W))) if n <= 600 else _power_radius(W)
        self.W = W * (radius / eig)
        self.U = rng.uniform(-in_scale, in_scale, (n, k))
        self.b = rng.uniform(-0.1, 0.1, n)
        self.leak, self.n, self.k = leak, n, k

    warmup = 1

    def _next(self, h, v_t):
        return (1 - self.leak) * h + self.leak * np.tanh(self.W @ h + self.U @ v_t + self.b)

    def run(self, v: np.ndarray) -> np.ndarray:
        T = v.shape[1]
        h = np.zeros(self.n)
        feats = np.empty((T - 1, self.n + self.k + 1))
        for t in range(T - 1):
            h = self._next(h, v[:, t])
            feats[t] = np.concatenate([h, v[:, t], [1.0]])
        return feats

    def step_init(self, hist: np.ndarray):
        h = np.zeros(self.n)
        for t in range(hist.shape[1] - 1):
            h = self._next(h, hist[:, t])
        return h

    def step(self, h, v_t):
        h = self._next(h, v_t)
        return h, np.concatenate([h, v_t, [1.0]])


def _power_radius(W, iters: int = 200) -> float:
    x = np.random.default_rng(1).standard_normal(W.shape[0])
    lam = 1.0
    for _ in range(iters):
        y = W @ (W @ x)
        lam = np.sqrt(np.linalg.norm(y) / max(np.linalg.norm(x), 1e-12))
        x = y / max(np.linalg.norm(y), 1e-12)
    return float(lam)


# ---------------------------------------------------------------- the forecaster

@dataclass
class Forecaster:
    name: str
    space: StateSpace
    feats: object
    diagonal: bool = False
    ridge: float = 1.0
    Wout: np.ndarray | None = None          # (F, k) or per-variable list for diagonal
    L: np.ndarray | None = None              # Cholesky of residual covariance
    info: dict = field(default_factory=dict)

    # -- design matrices
    def _xy(self, samples):
        Xs, Ys, Ms = [], [], []
        for s in samples:
            v, mask = self.space.encode(s)
            F = self.feats.run(v)
            Y = v[:, self.feats.warmup:].T
            Xs.append(F)
            Ys.append(Y)
            Ms.append(np.broadcast_to(mask, Y.shape))
        return np.vstack(Xs), np.vstack(Ys), np.vstack(Ms)

    def _solve(self, X, Y, M, ridge):
        k = Y.shape[1]
        if not self.diagonal:
            Xa = X
            G = Xa.T @ Xa + ridge * np.eye(Xa.shape[1])
            return np.linalg.solve(G, Xa.T @ Y)
        lags = self.feats.lags
        W = np.zeros((lags, k))
        for j in range(k):
            Xj = X[:, [j + l * k for l in range(lags)]]
            m = M[:, j]
            G = Xj[m].T @ Xj[m] + ridge * np.eye(lags)
            W[:, j] = np.linalg.solve(G, Xj[m].T @ Y[m, j])
        return W

    def _predict(self, X, W):
        if not self.diagonal:
            return X @ W
        k = self.space.k
        lags = self.feats.lags
        return np.stack([X[:, [j + l * k for l in range(lags)]] @ W[:, j] for j in range(k)], axis=1)

    def fit(self, train, val, ridges=(0.01, 0.1, 1, 10, 100, 1000)):
        X, Y, M = self._xy(train)
        Xv, Yv, Mv = self._xy(val)
        best = None
        for r in ridges:
            W = self._solve(X, Y, M, r)
            P = self._predict(Xv, W)
            r2 = _masked_r2(Yv, P, Mv, self.space.core.size)
            if best is None or r2 > best[1]:
                best = (r, r2, W)
        self.ridge, self.Wout = best[0], self._solve(X, Y, M, best[0])
        R = (Y - self._predict(X, self.Wout)) * M
        cov = R.T @ R / max(len(R), 1) + 1e-6 * np.eye(R.shape[1])
        self.L = np.linalg.cholesky(cov)
        self.info = {"ridge": best[0], "val_r2_1step": round(best[1], 4)}
        return self

    # -- forecasting skill
    def one_step_r2(self, samples) -> float:
        X, Y, M = self._xy(samples)
        return _masked_r2(Y, self._predict(X, self.Wout), M, self.space.core.size)

    def multi_step_r2(self, samples, horizon: int = 5, stride: int = 10, context: int = 50) -> float:
        num = den = 0.0
        for s in samples:
            v, mask = self.space.encode(s)
            c = mask[: self.space.core.size]
            T = v.shape[1]
            for t0 in range(context, T - horizon, stride):
                state = self.feats.step_init(v[:, t0 - context: t0 + 1])
                cur = v[:, t0]
                for h in range(horizon):
                    state, f = self.feats.step(state, cur)
                    cur = self._predict(f[None, :], self.Wout)[0]
                target = v[: self.space.core.size, t0 + horizon]
                pred = cur[: self.space.core.size]
                num += np.sum(((target - pred) ** 2)[c])
                den += np.sum((target[c]) ** 2)   # z-scored: variance about 0
        return float(1 - num / den) if den > 0 else np.nan

    # -- simulation
    def generate(self, template: BenchSample, rng: np.random.Generator, burn: int = 300,
                 clip: float = 8.0) -> BenchSample:
        T = template.x.shape[1]
        k = self.space.k
        hist = np.zeros((k, max(self.feats.warmup, 1) + 1))
        state = self.feats.step_init(hist)
        cur = hist[:, -1]
        out = np.empty((k, T + burn))
        for t in range(T + burn):
            state, f = self.feats.step(state, cur)
            cur = self._predict(f[None, :], self.Wout)[0] + self.L @ rng.standard_normal(k)
            cur = np.clip(cur, -clip, clip)           # guard against runaway feedback [A]
            out[:, t] = cur
        return self.space.decode(out[:, burn:], template, self.name)


def _masked_r2(Y, P, M, n_core) -> float:
    Yc, Pc, Mc = Y[:, :n_core], P[:, :n_core], M[:, :n_core]
    num = np.sum(((Yc - Pc) ** 2)[Mc])
    den = np.sum(((Yc - Yc.mean(axis=0)) ** 2)[Mc])
    return float(1 - num / den)


def ladder(space: StateSpace, seed: int = 0) -> list[Forecaster]:
    k = space.k
    return [
        Forecaster("diag_ar1", space, LagFeatures(k, 1, True), diagonal=True),
        Forecaster("diag_ar4", space, LagFeatures(k, 4, True), diagonal=True),
        Forecaster("var1", space, LagFeatures(k, 1, False)),
        Forecaster("var3", space, LagFeatures(k, 3, False)),
        Forecaster("esn400", space, ESNFeatures(k, 400, seed=seed)),
        Forecaster("esn1500", space, ESNFeatures(k, 1500, seed=seed)),
    ]


# ---------------------------------------------------------------- individual worms

@dataclass
class IndividualVAR:
    """One linear model per TRAINING worm, shrunk toward the pooled model:

        W_i = argmin |Y_i - X_i W|^2 + lam |W - W_pool|^2
            = (X_i'X_i + lam I)^-1 (X_i'Y_i + lam W_pool)

    lam is chosen by within-worm forecasting: fit on each training worm's first half,
    predict its second half. As a simulator it is a population of digital individuals:
    sample j is generated by the model of training worm j (mod the number of worms).
    """
    pooled: Forecaster
    mode: str = "full"       # "full" | "noise_only" (pooled W, own noise) | "shuffled" (scrambled deviation)
    lam: float = 0.0
    W: list = field(default_factory=list)
    L: list = field(default_factory=list)
    names: list = field(default_factory=list)
    info: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return {"full": "indiv_", "noise_only": "indivnoise_", "shuffled": "indivshuf_"}[self.mode] + self.pooled.name

    def _xy_one(self, s, sl=slice(None)):
        v, mask = self.pooled.space.encode(s)
        v = v[:, sl]
        F = self.pooled.feats.run(v)
        Y = v[:, self.pooled.feats.warmup:].T
        return F, Y, np.broadcast_to(mask, Y.shape)

    def _fit_one(self, F, Y, lam):
        G = F.T @ F + lam * np.eye(F.shape[1])
        return np.linalg.solve(G, F.T @ Y + lam * self.pooled.Wout)

    def fit(self, train, val, lams=(10, 100, 1000, 3000, 10000, 1e5)):
        self.pooled.fit(train, val)
        best = None
        for lam in lams:
            num = den = 0.0
            for s in train:
                T = s.x.shape[1]
                F1, Y1, _ = self._xy_one(s, slice(0, T // 2))
                F2, Y2, M2 = self._xy_one(s, slice(T // 2, T))
                P = F2 @ self._fit_one(F1, Y1, lam)
                n = self.pooled.space.core.size
                num += np.sum(((Y2 - P)[:, :n] ** 2)[M2[:, :n]])
                den += np.sum(((Y2 - Y2.mean(0))[:, :n] ** 2)[M2[:, :n]])
            r2 = 1 - num / den
            if best is None or r2 > best[1]:
                best = (lam, r2)
        # pooled model on the same within-worm second-half task, for comparison
        num = den = 0.0
        for s in train:
            T = s.x.shape[1]
            F2, Y2, M2 = self._xy_one(s, slice(T // 2, T))
            P = F2 @ self.pooled.Wout
            n = self.pooled.space.core.size
            num += np.sum(((Y2 - P)[:, :n] ** 2)[M2[:, :n]])
            den += np.sum(((Y2 - Y2.mean(0))[:, :n] ** 2)[M2[:, :n]])
        self.lam = best[0]
        self.info = {"lam": best[0], "within_worm_r2_individual": round(best[1], 4),
                     "within_worm_r2_pooled": round(1 - num / den, 4), "ridge": self.pooled.ridge}
        self.W, self.L, self.names = [], [], []
        for s in train:
            F, Y, M = self._xy_one(s)
            W = self._fit_one(F, Y, self.lam)
            R = (Y - F @ W) * M
            cov = R.T @ R / len(R) + 1e-6 * np.eye(R.shape[1])
            self.W.append(W)
            self.L.append(np.linalg.cholesky(cov))
            self.names.append(s.origin)
        return self

    def one_step_r2(self, samples) -> float:          # a new worm only has the pooled model
        return self.pooled.one_step_r2(samples)

    def multi_step_r2(self, samples, **kw) -> float:
        return self.pooled.multi_step_r2(samples, **kw)

    def generate(self, template: BenchSample, rng: np.random.Generator, which: int,
                 burn: int = 300, clip: float = 8.0) -> BenchSample:
        p = self.pooled
        i = which % len(self.W)
        W, L = self.W[i], self.L[i]
        if self.mode == "noise_only":                 # control: individuality in the noise only
            W = p.Wout
        elif self.mode == "shuffled":                 # control: same-size deviation, structure destroyed
            dev = (self.W[i] - p.Wout).ravel().copy()
            np.random.default_rng(10_000 + which).shuffle(dev)
            W = p.Wout + dev.reshape(p.Wout.shape)
        k = p.space.k
        hist = np.zeros((k, max(p.feats.warmup, 1) + 1))
        state = p.feats.step_init(hist)
        cur = hist[:, -1]
        T = template.x.shape[1]
        out = np.empty((k, T + burn))
        for t in range(T + burn):
            state, f = p.feats.step(state, cur)
            cur = np.clip(f @ W + L @ rng.standard_normal(k), -clip, clip)
            out[:, t] = cur
        s = p.space.decode(out[:, burn:], template, self.name)
        s.name = f"{self.name}:{self.names[i]}"       # the individual it came from
        return s
