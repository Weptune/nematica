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


def sense(d: np.ndarray, facing_out: np.ndarray | None = None, scale: float = SENSE_SCALE_MM) -> np.ndarray:
    """[proximity, its change] and, with `facing_out` (cosine between facing and the outward
    arena normal), proximity x facing: high when close AND heading into the copper."""
    x = np.exp(-np.maximum(np.asarray(d, float), -0.5) / scale)
    dx = np.diff(x, prepend=x[:1])
    if facing_out is None:
        return np.vstack([x, dx])
    return np.vstack([x, dx, x * np.asarray(facing_out, float)])


class SensoryVAR:
    def __init__(self, gamma: float = 0.5, lam: float = 300.0, senses: bool = True,
                 hazard_from: str = "brain", ridges=(0.01, 0.1, 1, 10, 100, 1000),
                 directional: bool = False, reversals: str = "hazard", speed_map: bool = False,
                 sense_scales=(SENSE_SCALE_MM,), per_worm_rates: bool = False):
        """hazard_from: "brain" (core classes and velocity), "speed" (velocity only) or "none"
        (constant rates); copper proximity is added to any of them when `senses` is on.
        directional: add proximity x facing-the-copper to the senses.
        reversals: "hazard" (discrete events from fitted logistic rates) or "hysteresis"
        (the brain's own reversal channel read with hysteresis, thresholds fitted on training
        worms driven by their recorded copper input, as `Debounced`)."""
        self.gamma, self.lam, self.senses, self.ridges = gamma, lam, senses, ridges
        self.hazard_from, self.directional, self.reversals = hazard_from, directional, reversals
        self.speed_map = speed_map
        self.sense_scales = tuple(sense_scales)
        self.scale = self.sense_scales[0]
        self.per_worm_rates = per_worm_rates
        self.offsets: dict = {}
        self.names: list = []
        self.info: dict = {}

    @property
    def name(self) -> str:
        n = "closed_loop_" + ("senses" if self.senses else "blind")
        if self.reversals == "hysteresis":
            return n + "_hyst" + ("_dir" if self.directional and self.senses else "")
        return n + ("" if self.hazard_from == "brain" else "_" + self.hazard_from) \
            + ("_dir" if self.directional and self.senses else "")

    def _sense(self, s: BenchSample):
        return sense(s.behaviour["dist_to_boundary"], s.behaviour["facing_out"] if self.directional else None,
                     self.scale)

    # ------------------------------------------------------------------ data
    def _xy(self, s: BenchSample):
        v, mask = self.space.encode(s)
        T = v.shape[1]
        cols = [v[:, LAGS - 1 - l: T - 1 - l].T for l in range(LAGS)]
        if self.senses:
            e = self._sense(s)
            cols.append(e[:, LAGS - 1: T - 1].T)
        F = np.hstack(cols)
        Y = v[:, LAGS:].T
        return F, Y, np.broadcast_to(mask, Y.shape)

    COMMAND = ("AVA", "AVE", "AIB", "RIM", "AVB", "RIB")

    def _hz_rows(self):
        n_core = self.space.core.size
        if self.hazard_from == "brain":
            return np.arange(n_core + 1)
        if self.hazard_from == "command":
            names = [self.space.classes[c] for c in self.space.core]
            return np.array([i for i, c in enumerate(names) if c in self.COMMAND] + [n_core])
        return np.array([n_core]) if self.hazard_from == "speed" else np.array([], dtype=int)

    def _features(self, hist, e_prev):
        f = np.concatenate(hist[::-1])
        return np.concatenate([f, e_prev]) if self.senses else f

    # ------------------------------------------------------------------ fit
    def _hazard_data(self, samples, state):
        Xh, yh = [], []
        for s in samples:
            v, _ = self.space.encode(s)
            st = (np.asarray(s.behaviour["reversing"]) > 0.5).astype(int)
            cur, nxt = st[:-1], st[1:]
            sel = cur == state
            cols = [v[self._hz_rows(), :-1]]
            if self.senses:
                cols.append(self._sense(s)[:, :-1])
            Xh.append(np.vstack(cols + [np.ones((1, len(cur)))])[:, sel].T)
            yh.append((nxt[sel] != state).astype(float))
        return np.vstack(Xh), np.concatenate(yh)

    def _fit_hazards(self, train):
        """Reversal hazards: from forward, P(start next frame); from reversing, P(end next
        frame); logistic, pooled over training worms [L]."""
        return [_logistic_fit(*self._hazard_data(train, state), l2=10.0) for state in (0, 1)]

    def _choose_scale(self, train, val):
        """Sense length scale: the candidate whose hazards best predict the validation worms'
        reversal starts and ends (log likelihood) [L]."""
        scores = {}
        for sc in self.sense_scales:
            self.scale = sc
            hz = self._fit_hazards(train)
            ll = 0.0
            for state in (0, 1):
                X, y = self._hazard_data(val, state)
                p = np.clip(1 / (1 + np.exp(-np.clip(X @ hz[state], -30, 30))), 1e-9, 1 - 1e-9)
                ll += float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
            scores[sc] = ll
        self.scale = max(scores, key=scores.get)
        return scores

    def fit(self, train, val):
        self.space = CalciumStateSpace.from_train(train, gamma=self.gamma)
        scale_scores = self._choose_scale(train, val) if self.senses and len(self.sense_scales) > 1 else None
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
        self.hazard = self._fit_hazards(train)
        self.info = {"ridge": best[0], "val_r2": round(float(best[1]), 4), "sense_scale_mm": self.scale}
        if scale_scores:
            self.info["scale_val_ll"] = {k: round(v, 1) for k, v in scale_scores.items()}
        if self.reversals == "hysteresis":
            self._fit_thresholds(train)
        if self.per_worm_rates and self.reversals == "hazard":
            self._fit_offsets(train)
        # speed per state: real crawling is bimodal (forward ~ +0.09, reversing ~ -0.08 mm/s)
        # while the brain's velocity channel is unimodal. With `speed_map`, the channel's
        # normal score is mapped through the training worms' speed quantiles for the current
        # state, so the brain still sets when the worm is fast or slow [A]
        grid = np.linspace(0.005, 0.995, 199)
        vel = np.concatenate([s.behaviour["velocity"] for s in train])
        rv = np.concatenate([np.asarray(s.behaviour["reversing"]) > 0.5 for s in train])
        self.speed_q = (np.quantile(np.abs(vel[~rv]), grid), np.quantile(np.abs(vel[rv]), grid))
        if self.senses:
            k = self.space.k
            self.info["onset_logodds_senses"] = [round(float(c), 3) for c in self.hazard[0][len(self._hz_rows()):-1]]
        return self

    def _open_loop_drive(self, s: BenchSample, which: int, rng):
        """The brain driven by a real worm's recorded copper input (no body): returns the
        raw reversal channel, for fitting the hysteresis thresholds."""
        W, L = self.W[self.names[which]], self.L[self.names[which]]
        k = self.space.k
        e_all = self._sense(s) if self.senses else None
        hist = [np.zeros(k) for _ in range(LAGS)]
        out = np.empty(s.x.shape[1])
        for i in range(s.x.shape[1]):
            f = self._features(hist, e_all[:, max(i - 1, 0)]) if self.senses else self._features(hist, None)
            v = np.clip(f @ W + L @ rng.standard_normal(k), -8, 8)
            hist = hist[1:] + [v]
            out[i] = v[-1] * self.space.beh_sd[1] + self.space.beh_mean[1]
        return out

    def _open_loop_states(self, s: BenchSample, which: int, rng, off):
        """Brain + reversal hazards driven by a real worm's recorded copper input (no body);
        `off` = (onset, end) log-odds offsets. Returns the 0/1 reversal state per frame."""
        W, L = self.W[self.names[which]], self.L[self.names[which]]
        k = self.space.k
        bm, bs = self.space.beh_mean, self.space.beh_sd
        z_rev = [(0 - bm[1]) / bs[1], (1 - bm[1]) / bs[1]]
        e_all = self._sense(s) if self.senses else None
        hist = [np.zeros(k) for _ in range(LAGS)]
        T = s.x.shape[1]
        states = np.zeros(T)
        state = 0
        rows = self._hz_rows()
        for i in range(T):
            e = e_all[:, max(i - 1, 0)] if self.senses else None
            v = np.clip(self._features(hist, e) @ W + L @ rng.standard_normal(k), -8, 8)
            v[-1] = z_rev[state]
            hist = hist[1:] + [v]
            states[i] = state
            hz = np.concatenate([v[rows], e if self.senses else [], [1.0]]) @ self.hazard[state] + off[state]
            if rng.random() < 1 / (1 + np.exp(-np.clip(hz, -30, 30))):
                state = 1 - state
        return states

    def _fit_offsets(self, train, pseudo: float = 5.0, n_rep: int = 2):
        """Per-worm reversal rates [L]. For each training worm, onset and end log-odds offsets
        are set (bisection, open loop with that worm's recorded copper input) so its model
        reproduces the worm's own onset rate and mean bout length, each shrunk toward the
        pooled value in log units with weight n / (n + pseudo), n = the worm's onsets.
        Without this every model worm shares one rate, which the ruler calls too typical."""
        from .forecasters import Debounced
        stats = [Debounced._stats(s.behaviour["reversing"], s.dt) for s in train]
        pooled_rate = np.log(sum(x[0] for x in stats) / sum(x[1] for x in stats))
        pooled_dur = np.log(np.mean(np.concatenate([x[2] for x in stats])))
        for i, (s, (n, minutes, durs)) in enumerate(zip(train, stats)):
            w = n / (n + pseudo)
            tr = w * (np.log(max(n, 0.5) / minutes)) + (1 - w) * pooled_rate
            td = w * (np.log(np.mean(durs)) if n else pooled_dur) + (1 - w) * pooled_dur
            off = [0.0, 0.0]
            for state, target, sign in ((0, tr, 1.0), (1, td, -1.0)):
                lo, hi = -4.0, 4.0
                for _ in range(9):
                    mid = 0.5 * (lo + hi)
                    off[state] = mid
                    got = []
                    for rep in range(n_rep):
                        st = self._open_loop_states(s, i, np.random.default_rng(100 * i + rep), off)
                        n2, m2, d2 = Debounced._stats(st, s.dt)
                        got.append(np.log(max(n2, 0.5) / m2) if state == 0 else np.log(np.mean(d2) if n2 else s.dt))
                    # onsets rise with the onset offset; bout length falls with the end offset
                    if sign * (np.mean(got) - target) > 0:
                        hi = mid
                    else:
                        lo = mid
                off[state] = 0.5 * (lo + hi)
            self.offsets[self.names[i]] = tuple(off)
        self.info["rate_offsets_sd"] = [round(float(np.std([o[j] for o in self.offsets.values()])), 3) for j in (0, 1)]

    def _fit_thresholds(self, train):
        from .forecasters import Debounced, hysteresis
        st = Debounced._stats
        n, minutes, durs = zip(*(st(s.behaviour["reversing"], s.dt) for s in train))
        target = np.array([np.log(sum(n) / sum(minutes)), np.log(np.median(np.concatenate(durs)))])
        rng = np.random.default_rng(12345)
        drives = [(self._open_loop_drive(s, i, rng), s.dt) for i, s in enumerate(train)]
        best = None
        for lo in np.linspace(-0.3, 0.6, 19):
            for hi in np.linspace(0.3, 1.5, 25):
                if hi < lo:
                    continue
                n, minutes, durs = zip(*(st(hysteresis(d, lo, hi), dt) for d, dt in drives))
                if sum(n) < 5:
                    continue
                got = np.array([np.log(sum(n) / sum(minutes)), np.log(np.median(np.concatenate(durs)))])
                loss = float(np.sum((got - target) ** 2))
                if best is None or loss < best[0]:
                    best = (loss, lo, hi)
        self.thresholds = (float(best[1]), float(best[2]))
        self.info.update({"rev_lo": round(best[1], 3), "rev_hi": round(best[2], 3)})

    # ------------------------------------------------------------------ closed loop
    def simulate(self, template: BenchSample, arena_radius_mm: float, start_dist_mm: float,
                 library: MotionLibrary, rng: np.random.Generator, which: int, t: np.ndarray,
                 burn: int = 300, clip: float = 8.0):
        """Returns the BenchSample (neural, behaviour incl. dist_to_boundary), body angles (T, K),
        head path (T, 2) in arena coordinates (centre at the origin)."""
        origin = self.names[which % len(self.names)]
        W, L = self.W[origin], self.L[origin]
        off = self.offsets.get(origin, (0.0, 0.0))
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
        facing = lambda: float(np.cos(H + np.pi - np.arctan2(head[1], head[0])))  # noqa: E731
        fo = np.array([facing(), facing()]) if self.directional else None
        # burn-in of the brain while the worm rests at its start
        for _ in range(burn):
            e = sense(np.array([d_now, d_now]), fo, self.scale)[:, -1]
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
        hyst = self.reversals == "hysteresis"
        states = np.zeros(T)
        for i in range(T):
            x_now = np.exp(-max(d_now, -0.5) / self.scale)
            x_prev = np.exp(-max(d_prev, -0.5) / self.scale)
            e = np.array([x_now, x_now - x_prev] + ([x_now * facing()] if self.directional else []))
            v = np.clip(self._features(hist, e) @ W + L @ rng.standard_normal(k), -clip, clip)
            if hyst:                       # the brain's own channel decides, read with hysteresis
                raw = v[-1] * bs[1] + bm[1]
                lo, hi = self.thresholds
                state = int(raw >= lo) if state else int(raw > hi)
            else:
                v[-1] = z_rev[state]
            hist = hist[1:] + [v]
            out[:, i] = v
            if self.speed_map:
                from scipy.special import ndtr
                u = float(ndtr(v[-2] if state == 0 else -v[-2]))
                speed = float(np.interp(u, np.linspace(0.005, 0.995, 199), self.speed_q[state]))
            else:
                speed = abs(float(np.clip(v[-2] * bs[0] + bm[0], -0.4, 0.4)))
            vel = -speed if state == 1 else speed
            rev = float(state)
            states[i] = state
            if not hyst:
                hz = np.concatenate([v[self._hz_rows()], e if self.senses else [], [1.0]]) @ self.hazard[state] \
                    + off[state]
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
        s.behaviour["reversing"] = states
        return s, angles, path, stepper.continued / max(stepper.steps - 1, 1)
