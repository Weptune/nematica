"""Behaviour-state switching dynamics: forward and reverse each get their own linear dynamics,
and neural activity decides when the worm switches.

Why: a static warp of linear-Gaussian dynamics can fix skewed activity distributions or
reversal-state dwell times, not both (scripts/run_warp.py). Real worms switch between
discrete motor states, and the switching itself shapes both. The state is labelled in
every recording (reversal events), so the model is fitted directly, without inference:

    s_t in {forward, reverse}           from the recorded reversal labels [M]
    v_t = A_{s_t} [v_{t-1..t-L}, 1] + e,   e ~ N(0, Sigma_{s_t})     one VAR per state
    P(s_{t+1} != s_t | v_t)   logistic regression per current state, pooled over worms

v is the forecasters' state (core classes, velocity, reversal channel). The reversal
channel is set from the simulated state, so behaviour and state always agree. With
`lam`, each training worm gets its own per-state dynamics shrunk toward the pooled ones
(as IndividualVAR); switching stays pooled because each worm has only ~30 reversals.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..bench.sample import BenchSample
from .forecasters import StateSpace


def _lagged(v: np.ndarray, lags: int) -> np.ndarray:
    T = v.shape[1]
    cols = [v[:, lags - 1 - l: T - 1 - l].T for l in range(lags)]
    return np.hstack(cols + [np.ones((T - lags, 1))])


def _logistic_fit(X: np.ndarray, y: np.ndarray, l2: float = 1.0, iters: int = 50) -> np.ndarray:
    """L2-regularised logistic regression by Newton's method (intercept = last column, unpenalised)."""
    w = np.zeros(X.shape[1])
    pen = np.full(X.shape[1], l2)
    pen[-1] = 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ w, -30, 30)))
        g = X.T @ (p - y) + pen * w
        H = (X * (p * (1 - p))[:, None]).T @ X + np.diag(pen) + 1e-6 * np.eye(len(w))
        step = np.linalg.solve(H, g)
        w -= step
        if np.max(np.abs(step)) < 1e-6:
            break
    return w


@dataclass
class SwitchingVAR:
    space: StateSpace
    lags: int = 3
    lam: float | None = None            # None = shared dynamics; else per-worm shrinkage
    ridge: float = 10.0
    switch_l2: float = 10.0
    A: list = field(default_factory=list)          # pooled, per state: (F, k)
    L: list = field(default_factory=list)
    worm_A: dict = field(default_factory=dict)     # origin -> [A_fwd, A_rev]
    worm_L: dict = field(default_factory=dict)
    names: list = field(default_factory=list)
    switch: list = field(default_factory=list)     # per current state: logistic weights
    info: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return "switch_var" + str(self.lags) + ("" if self.lam is None else f"_indiv_lam{self.lam:g}")

    # ---------------------------------------------------------------- data
    def _worm(self, s: BenchSample):
        v, mask = self.space.encode(s)
        state = (np.asarray(s.behaviour["reversing"]) > 0.5).astype(int)
        F = _lagged(v, self.lags)                   # predicts v[:, lags:]
        Y = v[:, self.lags:].T
        st = state[self.lags:]
        M = np.broadcast_to(mask, Y.shape)
        return v, state, F, Y, st, M

    def _solve(self, F, Y, ridge, prior=None, lam=0.0):
        G = F.T @ F + ridge * np.eye(F.shape[1])
        rhs = F.T @ Y
        if prior is not None:
            G = G + lam * np.eye(F.shape[1])
            rhs = rhs + lam * prior
        return np.linalg.solve(G, rhs)

    @staticmethod
    def _chol(R, M):
        R = R * M
        cov = R.T @ R / max(len(R), 1) + 1e-6 * np.eye(R.shape[1])
        return np.linalg.cholesky(cov)

    # ---------------------------------------------------------------- fit
    def fit(self, train, val=None):
        data = [self._worm(s) for s in train]
        k = self.space.k
        self.A, self.L = [], []
        for state in (0, 1):
            F = np.vstack([d[2][d[4] == state] for d in data])
            Y = np.vstack([d[3][d[4] == state] for d in data])
            M = np.vstack([d[5][d[4] == state] for d in data])
            A = self._solve(F, Y, self.ridge)
            self.A.append(A)
            self.L.append(self._chol(Y - F @ A, M))
        if self.lam is not None:
            for s, d in zip(train, data):
                As, Ls = [], []
                for state in (0, 1):
                    sel = d[4] == state
                    F, Y, M = d[2][sel], d[3][sel], d[5][sel]
                    if sel.sum() < 20:                      # too few frames: use pooled
                        As.append(self.A[state])
                        Ls.append(self.L[state])
                        continue
                    A = self._solve(F, Y, 0.0, prior=self.A[state], lam=self.lam)
                    As.append(A)
                    Ls.append(self._chol(Y - F @ A, M))
                self.worm_A[s.origin], self.worm_L[s.origin] = As, Ls
            self.names = [s.origin for s in train]
        # switching: from each state, does the next frame leave it? features = v_t (no reversal row) + 1
        self.switch = []
        for state in (0, 1):
            X, y = [], []
            for v, st, *_ in data:
                cur, nxt = st[:-1], st[1:]
                sel = cur == state
                X.append(np.hstack([v[:-1, :-1][:, sel].T, np.ones((sel.sum(), 1))]))
                y.append((nxt[sel] != state).astype(float))
            X, y = np.vstack(X), np.concatenate(y)
            self.switch.append(_logistic_fit(X, y, self.switch_l2))
        self.info = {"lam": self.lam, "reversing_fraction_train": round(float(np.mean([d[4].mean() for d in data])), 3)}
        return self

    # ---------------------------------------------------------------- simulate
    def generate(self, template: BenchSample, rng: np.random.Generator, which: int = 0,
                 burn: int = 300, clip: float = 8.0) -> BenchSample:
        k = self.space.k
        if self.lam is not None:
            origin = self.names[which % len(self.names)]
            A, L = self.worm_A[origin], self.worm_L[origin]
        else:
            origin, A, L = None, self.A, self.L
        rev_hi = (1 - self.space.beh_mean[1]) / self.space.beh_sd[1]     # z-scored reversal channel
        rev_lo = (0 - self.space.beh_mean[1]) / self.space.beh_sd[1]
        T = template.x.shape[1]
        hist = [np.zeros(k) for _ in range(self.lags)]
        state = 0
        out = np.empty((k, T + burn))
        for t in range(T + burn):
            f = np.concatenate(hist[::-1] + [np.ones(1)])
            v = f @ A[state] + L[state] @ rng.standard_normal(k)
            v = np.clip(v, -clip, clip)
            v[-1] = rev_hi if state == 1 else rev_lo
            out[:, t] = v
            hist = hist[1:] + [v]
            z = np.concatenate([v[:-1], [1.0]]) @ self.switch[state]
            if rng.random() < 1 / (1 + np.exp(-np.clip(z, -30, 30))):
                state = 1 - state
        s = self.space.decode(out[:, burn:], template, self.name)
        if origin is not None:
            s.name = f"{self.name}:{origin}"
        return s
