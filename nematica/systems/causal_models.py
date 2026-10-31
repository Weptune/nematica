"""Arc 4: brain models that can be stimulated, for the causal levels.

ClassVAR    a pooled ridge VAR(p) on class-level activity (z-scored per worm), fitted on the
            atlas training worms: either spontaneous frames only (no stimulation in the
            previous 30 s) or all frames. Missing classes enter as zero (the mean) and are
            never targets [A]; in simulation, classes a worm does not show stay at zero, as in training.
            Where the fitted dynamics are explosive for a worm's class set, they are scaled to
            spectral radius 0.99 [A].

Stimulation protocol (the same for every model): the model runs the worm's whole recording
length with its own noise (diagonal Gaussian residuals [A]); at each of the worm's
stimulations, the stimulated class is clamped for 30 s to its pre-pulse model value plus the
stimulated neuron's own measured response (in its SD units) [M]. The simulated recording then
goes through exactly the response pipeline used for real worms.
"""

from __future__ import annotations

import numpy as np

from ..bench.causal import window
from ..data.pumpprobe import PumpProbe


def class_matrix(rec: PumpProbe, classes) -> np.ndarray:
    """(len(classes), T) class means of per-neuron z-scores; NaN where not observed."""
    T = rec.n_frames
    out = np.full((len(classes), T), np.nan)
    idx = {c: i for i, c in enumerate(classes)}
    groups: dict = {}
    for j, c in enumerate(rec.classes):
        if c in idx:
            groups.setdefault(c, []).append(j)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (rec.x - np.nanmean(rec.x, axis=1, keepdims=True)) / np.nanstd(rec.x, axis=1, keepdims=True)
    for c, rows in groups.items():
        with np.errstate(invalid="ignore"):
            out[idx[c]] = np.nanmean(z[rows], axis=0) if len(rows) > 1 else z[rows[0]]
    return out


def spontaneous_mask(rec: PumpProbe) -> np.ndarray:
    _, npost = window(rec.dt)
    m = np.ones(rec.n_frames, bool)
    for f in rec.all_stim_frames:
        m[max(f, 0):f + npost] = False
    return m


class ClassVAR:
    def __init__(self, lags: int = 3, frames: str = "spontaneous", min_fraction: float = 0.3,
                 ridges=(1.0, 10.0, 100.0, 1000.0, 10000.0), max_radius: float = 0.99,
                 protocol: str = "clamp", fixed_ridge: float | None = None, coupling: str = "full",
                 features: str = "linear", penalty: str = "ridge", theta: float = 1.0):
        self.lags, self.frames, self.min_fraction, self.ridges = lags, frames, min_fraction, ridges
        self.max_radius, self.protocol, self.fixed_ridge = max_radius, protocol, fixed_ridge
        self.coupling = coupling       # "full", or "diagonal": each class driven only by its own past
        self.features = features       # "linear", or "relu": plus rectified copies of the last frame,
                                       # so influence can depend on whether a source is strongly active
        self.penalty, self.theta = penalty, theta     # "ridge" or "lasso" (sparse coupling)
        if penalty == "lasso":
            self.ridges = (1e-3, 3e-3, 1e-2, 3e-2)
        self.name = (f"var{lags}_{frames}" + ("" if coupling == "full" else f"_{coupling}")
                     + ("" if features == "linear" else f"_{features}") + ("" if penalty == "ridge" else f"_{penalty}")
                     + ("" if protocol == "clamp" else f"@{protocol}"))

    # -------------------------------------------------------------- fitting
    def _design(self, recs):
        p, C = self.lags, len(self.classes)
        Xs, Ys = [], []
        for r in recs:
            z = class_matrix(r, self.classes)
            spont = spontaneous_mask(r)
            zf = np.nan_to_num(z)
            T = z.shape[1]
            if self.frames == "spontaneous":
                ok = np.array([spont[t - p:t + 1].all() for t in range(p, T)])
            elif self.frames == "stim":          # only frames within 30 s after a stimulation
                ok = ~spont[p:T]
            else:
                ok = np.ones(T - p, bool)
            ts = np.arange(p, T)[ok]
            if ts.size == 0:
                continue
            blocks = [zf[:, ts - L].T for L in range(1, p + 1)]
            if self.features == "relu":
                last = zf[:, ts - 1].T
                blocks += [np.maximum(last - self.theta, 0), np.maximum(-last - self.theta, 0)]
            X = np.hstack(blocks + [np.ones((ts.size, 1))])
            Xs.append(X)
            Ys.append(z[:, ts].T)
        return np.vstack(Xs), np.vstack(Ys)

    def _solve(self, X, Y, lam):
        W = np.zeros((X.shape[1], Y.shape[1]))
        C = Y.shape[1]
        for j in range(C):
            m = np.isfinite(Y[:, j])
            if m.sum() < 50:
                continue
            cols = (np.arange(X.shape[1]) if self.coupling == "full"
                    else np.r_[[L * C + j for L in range(self.lags)], X.shape[1] - 1])
            Xm = X[np.ix_(m, cols)]
            if self.penalty == "lasso":
                from sklearn.linear_model import Lasso
                las = Lasso(alpha=lam, fit_intercept=True, max_iter=2000, tol=1e-3, selection="random",
                            random_state=0).fit(Xm[:, :-1], Y[m, j])
                W[cols[:-1], j] = las.coef_
                W[cols[-1], j] = las.intercept_
                continue
            pen = np.full(len(cols), lam)
            pen[-1] = 0.0
            W[cols, j] = np.linalg.solve(Xm.T @ Xm + np.diag(pen), Xm.T @ Y[m, j])
        return W

    def fit(self, train, val):
        from collections import Counter
        cnt = Counter(c for r in train for c in set(r.classes) if c)
        self.classes = sorted(c for c, n in cnt.items() if n >= self.min_fraction * len(train))
        X, Y = self._design(train)
        if self.fixed_ridge is not None:                 # e.g. one worm's own model: no validation worms
            self.W = self._solve(X, Y, self.fixed_ridge)
            R = Y - X @ self.W
            self.noise_sd = np.sqrt(np.nanmean(R ** 2, axis=0))
            self.noise_sd[~np.isfinite(self.noise_sd)] = 1.0
            self.radius = self.spectral_radius()
            self.info = {"radius": round(self.radius, 4), "ridge": self.fixed_ridge, "rows": int(X.shape[0])}
            return self
        Xv, Yv = self._design(val)
        best = None
        for lam in self.ridges:
            W = self._solve(X, Y, lam)
            P = Xv @ W
            m = np.isfinite(Yv)
            r2 = 1 - np.sum((Yv - P)[m] ** 2) / np.sum((Yv - np.nanmean(Yv, axis=0))[m] ** 2)
            if best is None or r2 > best[1]:
                best = (lam, r2, W)
        X = np.vstack([X, Xv])
        Y = np.vstack([Y, Yv])
        self.W = self._solve(X, Y, best[0])
        R = Y - X @ self.W
        self.noise_sd = np.sqrt(np.nanmean(R ** 2, axis=0))
        self.noise_sd[~np.isfinite(self.noise_sd)] = 1.0
        self.radius = self.spectral_radius()
        self.info = {"radius": round(self.radius, 4), "ridge": best[0], "val_r2": round(float(best[1]), 4), "classes": len(self.classes),
                     "rows": int(X.shape[0])}
        return self

    def spectral_radius(self, seen=None) -> float:
        C, p = len(self.classes), self.lags
        A = self.W[:p * C].reshape(p, C, C)
        if seen is not None:
            A = A[:, seen][:, :, seen]
            C = int(np.sum(seen))
        comp = np.zeros((p * C, p * C))
        comp[:C, :] = np.hstack([A[L].T for L in range(p)])
        if p > 1:
            comp[C:, :-C] = np.eye((p - 1) * C)
        return float(np.abs(np.linalg.eigvals(comp)).max())

    def _step(self, z, t, A, b):
        p = self.lags
        nxt = b + sum(z[:, t - L] @ A[L - 1] for L in range(1, p + 1))
        if self.features == "relu":
            C = len(self.classes)
            last = z[:, t - 1]
            Np, Nm = self.W[p * C:p * C + C], self.W[p * C + C:p * C + 2 * C]
            nxt = nxt + np.maximum(last - self.theta, 0) @ Np + np.maximum(-last - self.theta, 0) @ Nm
            nxt = np.clip(nxt, -10, 10)          # rectified terms can grow without bound [A]
        return nxt

    # -------------------------------------------------------------- stimulation
    def simulate(self, rec: PumpProbe, rng: np.random.Generator, burn: int = 200) -> PumpProbe:
        """A simulated version of `rec`: the model's classes observed in this worm, one row
        each, stimulated on the worm's schedule."""
        C, p = len(self.classes), self.lags
        idx = {c: i for i, c in enumerate(self.classes)}
        T = rec.n_frames
        npre, npost = window(rec.dt)
        sd = np.nanstd(rec.x, axis=1)
        clamp = {}                                     # frame -> (class index, offset from baseline)
        pulse = {}                                     # frame -> (class index, input size)
        stims_out = []
        own = [c for c in sorted(set(rec.classes)) if c in idx]
        row_of = {c: i for i, c in enumerate(own)}
        for k, f in rec.stims:
            c = rec.classes[k]
            if c not in idx or f - npre < 0 or f + npost > T or not sd[k] > 0:
                continue
            self_tr = (rec.x[k, f:f + npost] - np.nanmean(rec.x[k, f - npre:f])) / sd[k]
            if self.protocol == "pulse":
                # a brief input instead of a clamp: one frame of drive, sized to the stimulated
                # neuron's measured peak in the first 5 s, then the dynamics run freely [A]
                pk = np.nanmax(self_tr[:npre + 1]) if np.isfinite(self_tr[:npre + 1]).any() else np.nan
                if np.isfinite(pk):
                    pulse[f] = (idx[c], float(pk))
            else:
                for t, v in enumerate(self_tr):
                    if np.isfinite(v):
                        clamp[f + t] = (idx[c], f, float(v))
            stims_out.append((row_of[c], f))
        # classes this worm does not show stay at zero, as missing classes did in training
        seen = np.zeros(C, bool)
        seen[[idx[c] for c in own]] = True
        z = np.zeros((C, T + burn))
        A = self.W[:p * C].reshape(p, C, C).copy()     # A[L-1][from, to]
        # the fitted dynamics are slightly explosive for some worms' class sets (slow drifts in
        # the recordings); scaling lag L by g**L scales every eigenvalue by g, so the system
        # is made just stable (radius 0.99) where needed [A]
        rad = self.spectral_radius(seen)
        g = min(1.0, self.max_radius / rad) if rad > 0 else 1.0
        for L in range(1, p + 1):
            A[L - 1] *= g ** L
        self.last_gain = g
        if pulse:
            # size pulses in each class's own SD units: SD of a free run of the same dynamics
            zz = np.zeros((C, 1500 + p))
            for t in range(p, zz.shape[1]):
                zz[:, t] = self._step(zz, t, A, b) + self.noise_sd * rng.standard_normal(C)
                zz[~seen, t] = 0.0
            sd_free = np.std(zz[:, 300:], axis=1)
            pulse = {f: (ci, v * sd_free[ci]) for f, (ci, v) in pulse.items()}
        b = self.W[-1]
        base = {}
        for t in range(p, T + burn):
            nxt = self._step(z, t, A, b)
            nxt += self.noise_sd * rng.standard_normal(C)
            nxt[~seen] = 0.0
            tt = t - burn
            if tt in pulse:
                nxt[pulse[tt][0]] += pulse[tt][1]
            if tt in clamp:
                ci, f0, v = clamp[tt]
                if (ci, f0) not in base:
                    base[(ci, f0)] = z[ci, t - 1]
                nxt[ci] = base[(ci, f0)] + v
            z[:, t] = nxt
        x = z[[idx[c] for c in own], burn:]
        return PumpProbe(uid=rec.uid, x=x, names=own, classes=own, stims=stims_out, dt=rec.dt,
                         all_stim_frames=list(rec.all_stim_frames))


class CreamerCausal:
    """The published Creamer, Leifer & Pillow (2024) linear dynamical systems (fitted to this
    atlas, 154 named neurons, 2 Hz, one lag) under the same stimulation protocol: the
    stimulated neuron is clamped to its pre-pulse value plus its own measured response, the
    rest evolve with the published dynamics and noise (y = x + v). Neuron-level rows for the
    worm's named neurons the model has. The published parameters were fitted to atlas worms,
    possibly including the scored ones [L: in-sample unless shown otherwise]."""

    def __init__(self, variant: str = "connectome_constrained", folder=None, protocol: str = "clamp"):
        from .published import DEFAULT_DIR
        from pathlib import Path
        z = np.load(Path(folder or DEFAULT_DIR) / f"{variant}.npz")
        self.variant, self.protocol = variant, protocol
        self.name = f"creamer2024_{variant}" + ("" if protocol == "clamp" else f"@{protocol}")
        self.A, self.Q, self.R = z["A"], z["Q"], z["R"]
        self.cells = [str(c) for c in z["cell_ids"]]
        self.Lq = np.linalg.cholesky(self.Q + 1e-12 * np.eye(len(self.Q)))
        self.sr = np.sqrt(np.clip(np.diag(self.R), 0, None))
        from scipy.linalg import solve_discrete_lyapunov
        # stationary SD of each neuron, so a pulse can be sized in that neuron's own SD units
        self.stat_sd = np.sqrt(np.clip(np.diag(solve_discrete_lyapunov(self.A, self.Q)), 1e-12, None)
                               + np.clip(np.diag(self.R), 0, None))
        self.info = {"neurons": len(self.cells),
                     "radius": round(float(np.max(np.abs(np.linalg.eigvals(self.A)))), 4)}

    def fit(self, train=None, val=None):
        return self

    def simulate(self, rec: PumpProbe, rng: np.random.Generator, burn: int = 600) -> PumpProbe:
        from ..data.pumpprobe import neuron_class
        n = len(self.cells)
        cell_of = {c.upper(): i for i, c in enumerate(self.cells)}
        T = rec.n_frames
        npre, npost = window(rec.dt)
        sd = np.nanstd(rec.x, axis=1)
        own = sorted({rec.names[j].upper() for j, c in enumerate(rec.classes) if c and rec.names[j].upper() in cell_of})
        row_of = {nm: i for i, nm in enumerate(own)}
        clamp, stims_out, pulse = {}, [], {}
        for k, f in rec.stims:
            nm = rec.names[k].upper()
            if nm not in cell_of or nm not in row_of or f - npre < 0 or f + npost > T or not sd[k] > 0:
                continue
            tr = (rec.x[k, f:f + npost] - np.nanmean(rec.x[k, f - npre:f])) / sd[k]
            if self.protocol == "pulse":
                pk = np.nanmax(tr[:npre + 1]) if np.isfinite(tr[:npre + 1]).any() else np.nan
                if np.isfinite(pk):
                    pulse[f] = (cell_of[nm], float(pk) * float(self.stat_sd[cell_of[nm]]))
            else:
                for t, v in enumerate(tr):
                    if np.isfinite(v):
                        clamp[f + t] = (cell_of[nm], f, float(v))
            stims_out.append((row_of[nm], f))
        x = np.zeros(n)
        out = np.empty((n, T))
        base = {}
        for t in range(-burn, T):
            x = self.A @ x + self.Lq @ rng.standard_normal(n)
            if t in pulse:
                x[pulse[t][0]] += pulse[t][1]
            if t in clamp:
                ci, f0, v = clamp[t]
                if (ci, f0) not in base:
                    base[(ci, f0)] = float(out[ci, t - 1]) if t > 0 else 0.0
                x[ci] = base[(ci, f0)] + v
            if t >= 0:
                out[:, t] = x + self.sr * rng.standard_normal(n)
        rows = [cell_of[nm] for nm in own]
        return PumpProbe(uid=rec.uid, x=out[rows], names=own, classes=[neuron_class(nm) for nm in own],
                         stims=stims_out, dt=rec.dt, all_stim_frames=list(rec.all_stim_frames))
