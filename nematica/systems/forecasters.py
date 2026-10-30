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

    def unwarp(self, z: np.ndarray, source: str | None = None) -> np.ndarray:  # identity here
        return z

    add_slow = None        # optional callable (source, T) -> (n_core, T), added after unwarp

    def encode(self, s: BenchSample) -> tuple[np.ndarray, np.ndarray]:
        """(k, T) state and (k,) mask of which variables are real for this worm."""
        z = np.nan_to_num(s.x[self.core])
        b = (np.stack([s.behaviour["velocity"], s.behaviour["reversing"]]) - self.beh_mean[:, None]) \
            / self.beh_sd[:, None]
        mask = np.concatenate([s.observed[self.core], [True, True]])
        return np.vstack([z, b]), mask

    def decode(self, v: np.ndarray, template: BenchSample, name: str, source: str | None = None) -> BenchSample:
        T = template.x.shape[1]
        out = np.full((len(self.classes), T), np.nan)
        out[self.core] = self.unwarp(v[:-2, :T], source)
        if self.add_slow is not None:
            out[self.core] += self.add_slow(source, T)
        out[~template.observed] = np.nan
        beh = v[-2:, :T] * self.beh_sd[:, None] + self.beh_mean[:, None]
        behaviour = {"velocity": beh[0], "reversing": (beh[1] > 0.5).astype(float)}
        return BenchSample(f"{name}:{template.origin}", self.classes, zscore_rows(out),
                           template.dt, origin=None, behaviour=behaviour)


@dataclass
class WarpedStateSpace(StateSpace):
    """Gaussian-copula version: each class trace is replaced by its normal scores
    (rank-based, per worm) before modelling, and generated rows are mapped back through an
    empirical quantile function: the source worm's own for per-worm models, pooled over
    training worms otherwise (and for classes the source worm lacks). Linear dynamics in
    the warped space give realistic, skewed activity distributions [A]."""
    pooled_q: dict = field(default_factory=dict)        # core row -> sorted values
    worm_q: dict = field(default_factory=dict)          # origin -> {core row -> sorted values}

    @classmethod
    def from_train(cls, train, min_fraction: float = 0.6) -> "WarpedStateSpace":
        base = StateSpace.from_train(train, min_fraction)
        sp = cls(base.classes, base.core, base.beh_mean, base.beh_sd)
        grid = np.linspace(0, 1, 201)
        for r, ci in enumerate(sp.core):
            vals = [s.x[ci] for s in train if s.observed[ci]]
            if vals:
                sp.pooled_q[r] = np.quantile(np.concatenate(vals), grid)
            for s in train:
                if s.observed[ci]:
                    sp.worm_q.setdefault(s.origin, {})[r] = np.quantile(s.x[ci], grid)
        return sp

    def encode(self, s):
        v, mask = StateSpace.encode(self, s)
        from scipy.stats import norm, rankdata
        z = v[:-2]
        T = z.shape[1]
        for r, ci in enumerate(self.core):
            if s.observed[ci]:
                z[r] = norm.ppf((rankdata(s.x[ci]) - 0.5) / T)
        return v, mask

    def unwarp(self, z, source=None):
        from scipy.stats import norm
        grid = np.linspace(0, 1, 201)
        out = np.empty_like(z)
        for r in range(z.shape[0]):
            row = z[r]
            sd = row.std()
            u = norm.cdf((row - row.mean()) / sd) if sd > 0 else np.full_like(row, 0.5)
            q = self.worm_q.get(source, {}).get(r, self.pooled_q.get(r))
            out[r] = np.interp(u, grid, q) if q is not None else row
        return out


@dataclass
class CalciumStateSpace(WarpedStateSpace):
    """Model the drive behind each calcium trace, not the trace itself.

    encode: drive d_t = y_t - gamma * y_{t-1} (inverse of a first-order calcium decay with
            factor gamma = exp(-dt / tau) [A]), then per-worm normal scores of d
    unwarp: normal scores -> d via the source worm's own drive quantiles (pooled for shared
            models), then calcium is rebuilt: c_t = gamma * c_{t-1} + d_t
    A skewed, spiky drive passed through a slow decay gives what linear-Gaussian dynamics
    cannot: fast rises, slow decays (time asymmetry) and positive skew.
    """
    gamma: float = 0.6

    @classmethod
    def from_train(cls, train, min_fraction: float = 0.6, gamma: float = 0.6) -> "CalciumStateSpace":
        drive = [cls._drive_sample(s, gamma) for s in train]
        w = WarpedStateSpace.from_train(drive, min_fraction)
        sp = cls(w.classes, w.core, w.beh_mean, w.beh_sd, w.pooled_q, w.worm_q)
        sp.gamma = gamma
        return sp

    @staticmethod
    def _drive_sample(s: BenchSample, gamma: float) -> BenchSample:
        x = s.x.copy()
        d = x.copy()
        d[:, 1:] = x[:, 1:] - gamma * x[:, :-1]
        d[:, 0] = x[:, 0] * (1 - gamma)
        return BenchSample(s.name, s.classes, d, s.dt, s.origin, s.behaviour)

    def encode(self, s):
        return WarpedStateSpace.encode(self, self._drive_sample(s, self.gamma))

    def unwarp(self, z, source=None):
        d = WarpedStateSpace.unwarp(self, z, source)
        c = np.empty_like(d)
        c[:, 0] = d[:, 0] / (1 - self.gamma)
        for t in range(1, d.shape[1]):
            c[:, t] = self.gamma * c[:, t - 1] + d[:, t]
        return c


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


class MultiScaleFeatures:
    """Linear features with memory at several timescales: the previous `lags` frames plus the
    mean of each variable over longer windows further back. Windows are (a, b) in frame lags
    (lag l = v[t-1-l]); defaults cover lags 3-15 (about 8 s at 0.6 s frames) and 16-99
    (about 50 s), so a linear model can carry minute-scale structure [A]."""

    def __init__(self, k: int, lags: int = 3, windows=((3, 16), (16, 100))):
        self.k, self.lags, self.windows = k, lags, tuple(windows)
        self.warmup = max(b for _, b in self.windows)

    def run(self, v: np.ndarray) -> np.ndarray:
        T = v.shape[1]
        cs = np.concatenate([np.zeros((self.k, 1)), np.cumsum(v, axis=1)], axis=1)   # cs[:, i] = sum v[:, :i]
        t = np.arange(self.warmup, T)
        cols = [v[:, t - 1 - l].T for l in range(self.lags)]
        for a, b in self.windows:
            cols.append(((cs[:, t - a] - cs[:, t - b]) / (b - a)).T)
        return np.hstack(cols)

    def step_init(self, hist: np.ndarray):
        h = hist[:, :-1]
        if h.shape[1] < self.warmup:
            h = np.hstack([np.zeros((self.k, self.warmup - h.shape[1])), h])
        return h[:, -self.warmup:].copy()

    def step(self, state, v_t):
        state = np.concatenate([state[:, 1:], v_t[:, None]], axis=1)      # newest last
        cols = [state[:, -1 - l] for l in range(self.lags)]
        for a, b in self.windows:
            cols.append(state[:, self.warmup - b: self.warmup - a].mean(axis=1))
        return state, np.concatenate(cols)


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
    fixed_lam: float | None = None   # skip the forecasting-based choice and use this shrinkage
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
        if self.fixed_lam is not None:
            lams = (self.fixed_lam,)
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
        s = p.space.decode(out[:, burn:], template, self.name, source=self.names[i])
        s.name = f"{self.name}:{self.names[i]}"       # the individual it came from
        return s



# ---------------------------------------------------------------- fast / slow

class SlowFastVAR:
    """Fast dynamics plus a per-worm slow brain state.

    Real recordings carry minute-scale trends (a third of the power in periods over 3 min;
    each neuron's slow part correlates about 0.63 with time; half of it one shared component,
    with neurons rising and falling in equal numbers, so not bleaching). A stationary model
    with seconds of memory cannot make that. So:
        slow = 3-minute moving average of each trace,  fast = trace - slow
        fast:  IndividualVAR on a CalciumStateSpace (drive, per-worm marginals), lam fixed
        slow:  per training worm, the top `rank` principal components of its slow part
               (loadings over core classes), driven by independent Ornstein-Uhlenbeck
               latents with time constant `tau_s` [A], smoothed with the same moving
               average and scaled to the worm's own slow variance
    Sample j comes from training worm j: its fast dynamics and its slow loadings.
    """

    def __init__(self, gamma: float = 0.5, lam: float = 300.0, feats: str = "lags3",
                 window_s: float = 180.0, rank: int = 2, tau_s: float = 600.0):
        self.gamma, self.lam, self.feats_kind = gamma, lam, feats
        self.window_s, self.rank, self.tau_s = window_s, rank, tau_s
        self.inner = None
        self.loadings: dict = {}
        self.info: dict = {}

    @property
    def name(self) -> str:
        return f"slowfast_{self.feats_kind}_g{self.gamma:g}_lam{self.lam:g}"

    @property
    def names(self):
        return self.inner.names if self.inner is not None else []

    def _split(self, s: BenchSample):
        from scipy.ndimage import uniform_filter1d
        w = max(3, int(round(self.window_s / s.dt)))
        slow = np.full_like(s.x, np.nan)
        for i in np.flatnonzero(s.observed):
            slow[i] = uniform_filter1d(s.x[i], w, mode="nearest")
        fast = BenchSample(s.name, s.classes, s.x - slow, s.dt, s.origin, s.behaviour)
        return fast, slow

    def fit(self, train, val):
        fast_train, slows = zip(*[self._split(s) for s in train])
        fast_val = [self._split(s)[0] for s in val]
        cs = CalciumStateSpace.from_train(list(fast_train), gamma=self.gamma)
        feats = LagFeatures(cs.k, 3, False) if self.feats_kind == "lags3" else MultiScaleFeatures(cs.k)
        self.inner = IndividualVAR(Forecaster("var3", cs, feats), fixed_lam=self.lam).fit(list(fast_train), fast_val)
        core = cs.core
        self.loadings = {}
        share = []
        for s, slow in zip(train, slows):
            S = np.nan_to_num(slow[core])
            S = S - S.mean(axis=1, keepdims=True)
            U, sv, _ = np.linalg.svd(S, full_matrices=False)
            T = S.shape[1]
            self.loadings[s.origin] = U[:, :self.rank] * (sv[:self.rank] / np.sqrt(T))   # latent unit variance
            share.append(float(np.sum(sv[:self.rank] ** 2) / max(np.sum(sv ** 2), 1e-12)))
        self.dt = train[0].dt
        cs.add_slow = self._slow
        self._rng = np.random.default_rng(0)
        self.info = {**self.inner.info, "slow_rank_share": round(float(np.median(share)), 3)}
        return self

    def _slow(self, source, T):
        from scipy.ndimage import uniform_filter1d
        L = self.loadings.get(source)
        if L is None:
            return 0.0
        a = np.exp(-self.dt / self.tau_s)
        burn = int(3 * self.tau_s / self.dt)
        z = np.zeros((self.rank, T + burn))
        e = self._rng.standard_normal(z.shape) * np.sqrt(1 - a * a)
        for t in range(1, T + burn):
            z[:, t] = a * z[:, t - 1] + e[:, t]
        z = z[:, burn:]
        w = max(3, int(round(self.window_s / self.dt)))
        z = uniform_filter1d(z, w, axis=1, mode="nearest")
        z = (z - z.mean(axis=1, keepdims=True)) / np.maximum(z.std(axis=1, keepdims=True), 1e-9)
        return L @ z

    def generate(self, template, rng, which, **kw):
        self._rng = rng
        s = self.inner.generate(template, rng, which, **kw)
        s.name = s.name.replace(self.inner.name, self.name)
        return s

    def one_step_r2(self, samples):
        return self.inner.one_step_r2([self._split(s)[0] for s in samples])
