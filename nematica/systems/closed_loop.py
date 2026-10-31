"""Closed loop in the copper arena: a model worm that senses copper (arc 5).

    sense      s_t = [exp(-d_t / 0.5 mm), its change from the previous frame], d_t = head
               distance to the copper boundary (negative past it, floored at -0.5 mm) [A form]
    brain      per-worm VAR(3) on the calcium drive (CalciumStateSpace, gamma 0.5), as the
               8/8 model, with s_{t-1} as an extra input when `senses` is on. Pooled fit
               with ridge chosen on validation worms, then each training worm's own fit
               shrunk toward it (lambda 300). Everything fitted on TRAINING worms only [L]
    reversals  discrete events, not a thresholded Gaussian channel (which flickers and
               doubles the onset rate): P(start | forward) and P(end | reversing) per frame
               are logistic in the brain state, plus copper proximity when `senses` is on,
               pooled over training worms [L]. The state is written back into the brain's
               reversal channel, and velocity takes its sign from it [A]
    body       motion matching one frame at a time from real training worms
               (MotionStepper): the brain's velocity and reversal state pick the posture
    loop       brain step -> velocity, reversal -> body step -> head moves -> distance to
               copper -> next brain step

The control is the same model with `senses=False`: identical brain and body, blind to copper.
"""

from __future__ import annotations

import numpy as np

from ..bench.sample import BenchSample
from ..export.virtual_worm import MotionLibrary, MotionStepper
from .forecasters import CalciumStateSpace
from .switching import _logistic_fit

SENSE_SCALE_MM = 0.5
LAGS = 3


def sense(d: np.ndarray) -> np.ndarray:
    x = np.exp(-np.maximum(np.asarray(d, float), -0.5) / SENSE_SCALE_MM)
    dx = np.diff(x, prepend=x[:1])
    return np.vstack([x, dx])


class SensoryVAR:
    def __init__(self, gamma: float = 0.5, lam: float = 300.0, senses: bool = True,
                 hazard_from: str = "brain", ridges=(0.01, 0.1, 1, 10, 100, 1000)):
        """hazard_from: "brain" (core classes and velocity), "speed" (velocity only) or "none"
        (constant rates); copper proximity is added to any of them when `senses` is on."""
        self.gamma, self.lam, self.senses, self.ridges = gamma, lam, senses, ridges
        self.hazard_from = hazard_from
        self.names: list = []
        self.info: dict = {}

    @property
    def name(self) -> str:
        return "closed_loop_" + ("senses" if self.senses else "blind") + ("" if self.hazard_from == "brain" else "_" + self.hazard_from)

    # ------------------------------------------------------------------ data
    def _xy(self, s: BenchSample):
        v, mask = self.space.encode(s)
        T = v.shape[1]
        cols = [v[:, LAGS - 1 - l: T - 1 - l].T for l in range(LAGS)]
        if self.senses:
            e = sense(s.behaviour["dist_to_boundary"])
            cols.append(e[:, LAGS - 1: T - 1].T)
        F = np.hstack(cols)
        Y = v[:, LAGS:].T
        return F, Y, np.broadcast_to(mask, Y.shape)

    def _hz_rows(self):
        n_core = self.space.core.size
        if self.hazard_from == "brain":
            return np.arange(n_core + 1)
        return np.array([n_core]) if self.hazard_from == "speed" else np.array([], dtype=int)

    def _features(self, hist, e_prev):
        f = np.concatenate(hist[::-1])
        return np.concatenate([f, e_prev]) if self.senses else f

    # ------------------------------------------------------------------ fit
    def fit(self, train, val):
        self.space = CalciumStateSpace.from_train(train, gamma=self.gamma)
        n_core = self.space.core.size
        tr = [self._xy(s) for s in train]
        va = [self._xy(s) for s in val]
        X = np.vstack([a[0] for a in tr])
        Y = np.vstack([a[1] for a in tr])
        G0 = X.T @ X
        best = None
        for r in self.ridges:
            W = np.linalg.solve(G0 + r * np.eye(X.shape[1]), X.T @ Y)
            num = den = 0.0
            for F, Yv, M in va:
                P = F @ W
                num += np.sum(((Yv - P)[:, :n_core] ** 2)[M[:, :n_core]])
                den += np.sum(((Yv - Yv.mean(0))[:, :n_core] ** 2)[M[:, :n_core]])
            r2 = 1 - num / den
            if best is None or r2 > best[1]:
                best = (r, r2, W)
        self.W_pool = best[2]
        self.W, self.L, self.names = {}, {}, []
        for s, (F, Yt, M) in zip(train, tr):
            W = np.linalg.solve(F.T @ F + self.lam * np.eye(F.shape[1]), F.T @ Yt + self.lam * self.W_pool)
            R = (Yt - F @ W) * M
            cov = R.T @ R / len(R) + 1e-6 * np.eye(R.shape[1])
            self.W[s.origin], self.L[s.origin] = W, np.linalg.cholesky(cov)
            self.names.append(s.origin)
        # reversal hazards: from forward, P(start next frame); from reversing, P(end next frame)
        n_core = self.space.core.size
        self.hazard = []
        for state in (0, 1):
            Xh, yh = [], []
            for s in train:
                v, _ = self.space.encode(s)
                st = (np.asarray(s.behaviour["reversing"]) > 0.5).astype(int)
                cur, nxt = st[:-1], st[1:]
                sel = cur == state
                cols = [v[self._hz_rows(), :-1]]
                if self.senses:
                    cols.append(sense(s.behaviour["dist_to_boundary"])[:, :-1])
                Xh.append(np.vstack(cols + [np.ones((1, len(cur)))])[:, sel].T)
                yh.append((nxt[sel] != state).astype(float))
            self.hazard.append(_logistic_fit(np.vstack(Xh), np.concatenate(yh), l2=10.0))
        self.info = {"ridge": best[0], "val_r2": round(float(best[1]), 4)}
        if self.senses:
            k = self.space.k
            self.info["onset_logodds_per_unit_proximity"] = round(float(self.hazard[0][len(self._hz_rows())]), 3)
        return self

    # ------------------------------------------------------------------ closed loop
    def simulate(self, template: BenchSample, arena_radius_mm: float, start_dist_mm: float,
                 library: MotionLibrary, rng: np.random.Generator, which: int, t: np.ndarray,
                 burn: int = 300, clip: float = 8.0):
        """Returns the BenchSample (neural, behaviour incl. dist_to_boundary), body angles (T, K),
        head path (T, 2) in arena coordinates (centre at the origin)."""
        origin = self.names[which % len(self.names)]
        W, L = self.W[origin], self.L[origin]
        sp = self.space
        k = sp.k
        bm, bs = sp.beh_mean, sp.beh_sd
        T = template.x.shape[1]
        stepper = MotionStepper(library, seed=int(rng.integers(1 << 30)))
        # start: head at the template worm's starting distance from the centre, random place and heading
        phi = rng.uniform(0, 2 * np.pi)
        head = start_dist_mm * np.array([np.cos(phi), np.sin(phi)])
        H = rng.uniform(0, 2 * np.pi)
        hist = [np.zeros(k) for _ in range(LAGS)]
        d_prev = d_now = arena_radius_mm - np.hypot(*head)
        # burn-in of the brain while the worm rests at its start
        for _ in range(burn):
            e = sense(np.array([d_now, d_now]))[:, -1]
            v = np.clip(self._features(hist, e) @ W + L @ rng.standard_normal(k), -clip, clip)
            v[-1] = (0 - bm[1]) / bs[1]
            hist = hist[1:] + [v]
        out = np.empty((k, T))
        angles = np.empty((T, library.shapes.shape[1]))
        path = np.empty((T, 2))
        dist = np.empty(T)
        vel_prev, rev_prev = 0.0, 0.0
        n_core = sp.core.size
        state = 0
        z_rev = [(0 - bm[1]) / bs[1], (1 - bm[1]) / bs[1]]          # reversal channel values
        for i in range(T):
            x_now = np.exp(-max(d_now, -0.5) / SENSE_SCALE_MM)
            x_prev = np.exp(-max(d_prev, -0.5) / SENSE_SCALE_MM)
            e = np.array([x_now, x_now - x_prev])
            v = np.clip(self._features(hist, e) @ W + L @ rng.standard_normal(k), -clip, clip)
            v[-1] = z_rev[state]
            hist = hist[1:] + [v]
            out[:, i] = v
            speed = abs(float(np.clip(v[-2] * bs[0] + bm[0], -0.4, 0.4)))
            vel = -speed if state == 1 else speed
            rev = float(state)
            hz = np.concatenate([v[self._hz_rows()], e if self.senses else [], [1.0]]) @ self.hazard[state]
            if rng.random() < 1 / (1 + np.exp(-np.clip(hz, -30, 30))):
                state = 1 - state
            shape, turn = stepper.step(vel, vel_prev, rev, rev_prev)
            angles[i] = shape + H
            path[i] = head
            dist[i] = d_now
            if i + 1 < T:
                dt = float(t[i + 1] - t[i])
                fwd = angles[i, 0] + np.pi
                head = head + vel * dt * np.array([np.cos(fwd), np.sin(fwd)])
                H += turn
                d_prev, d_now = d_now, arena_radius_mm - np.hypot(*head)
            vel_prev, rev_prev = vel, rev
        s = sp.decode(out, template, self.name, source=origin)
        s.name = f"{self.name}:{origin}"
        s.behaviour["dist_to_boundary"] = dist
        return s, angles, path, stepper.continued / max(stepper.steps - 1, 1)
