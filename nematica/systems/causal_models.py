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
                 features: str = "linear", penalty: str = "ridge", theta: float = 1.0,
                 innovations: str = "gaussian"):
        self.lags, self.frames, self.min_fraction, self.ridges = lags, frames, min_fraction, ridges
        self.max_radius, self.protocol, self.fixed_ridge = max_radius, protocol, fixed_ridge
        self.coupling = coupling       # "full", or "diagonal": each class driven only by its own past
        self.features = features       # "linear", or "relu": plus rectified copies of the last frame,
                                       # so influence can depend on whether a source is strongly active
        self.penalty, self.theta = penalty, theta     # "ridge" or "lasso" (sparse coupling)
        self.innovations = innovations                # "gaussian", or "student": heavy-tailed shocks,
                                                      # mostly small with occasional large ones
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
        with np.errstate(invalid="ignore", divide="ignore"):
            k = np.nanmean(R ** 4, axis=0) / np.nanmean(R ** 2, axis=0) ** 2 - 3.0
        # Student-t degrees of freedom matching each class's residual excess kurtosis (6 / (nu - 4))
        self.nu = np.where(np.isfinite(k) & (k > 0.2), np.clip(4.0 + 6.0 / np.maximum(k, 1e-6), 4.1, 30.0), 30.0)
        self.radius = self.spectral_radius()
        self.info = {"radius": round(self.radius, 4), "ridge": best[0], "median_nu": round(float(np.median(self.nu)), 2), "val_r2": round(float(best[1]), 4), "classes": len(self.classes),
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

    def _shock(self, rng, C):
        if self.innovations == "student":
            nu = self.nu
            return rng.standard_t(nu) * np.sqrt((nu - 2) / nu)      # unit variance
        return rng.standard_normal(C)

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
    def simulate(self, rec: PumpProbe, rng: np.random.Generator, burn: int = 200,
                 noise_gain: np.ndarray | None = None) -> PumpProbe:
        """A simulated version of `rec`: the model's classes observed in this worm, one row
        each, stimulated on the worm's schedule. `noise_gain` (length burn + frames) scales
        the driving noise frame by frame (quiet and active regimes)."""
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
        b = self.W[-1]
        if pulse:
            # size pulses in each class's own SD units: SD of a free run of the same dynamics
            zz = np.zeros((C, 1500 + p))
            for t in range(p, zz.shape[1]):
                zz[:, t] = self._step(zz, t, A, b) + self.noise_sd * rng.standard_normal(C)
                zz[~seen, t] = 0.0
            sd_free = np.std(zz[:, 300:], axis=1)
            pulse = {f: (ci, v * sd_free[ci]) for f, (ci, v) in pulse.items()}
        base = {}
        for t in range(p, T + burn):
            nxt = self._step(z, t, A, b)
            nxt += self.noise_sd * self._shock(rng, C) * (1.0 if noise_gain is None else noise_gain[t])
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


class HybridKernel:
    """Two separately learned parts (arc 4, ingredient hunt):

        ongoing dynamics   a VAR fitted on stimulation-free frames (what watching teaches)
        causal kernels     for each pair of classes (i stimulated, j responding), the mean echo
                           of j over the training worms' stimulations of i, in units of j's
                           pre-stimulus fluctuations, shrunk toward zero with weight n / (n + 2)
                           (what poking teaches) [L]

    In simulation the VAR runs unstimulated; at each stimulation the stimulated class follows its
    neuron's measured response and every other class receives its kernel (scaled to that class's
    own fluctuation size in the simulation). `mask` restricts kernels to pairs allowed by a
    wiring matrix (class_wiring: A[to, from]); None allows every pair."""

    def __init__(self, lags: int = 3, shrink: float = 2.0, mask: str | None = None, seed: int = 0,
                 background: str = "spontaneous", obs_noise: bool = False, heavy: bool = False,
                 regimes: bool = False, obs_fit: bool = False, lowrank: int = 0):
        self.lags, self.shrink, self.mask, self.seed = lags, shrink, mask, seed
        self.background = background     # which frames the ongoing-dynamics VAR learns from
        self.obs_noise = obs_noise       # split each class's variability into slow dynamics and
                                         # white measurement noise (see _noise_fractions) [A]
        self.heavy = heavy               # heavy-tailed shocks in the ongoing dynamics
        self.regimes = regimes           # quiet and active regimes: the driving noise switches
                                         # between a low and a high gain, hidden Markov [A],
                                         # calibrated on training worms (calibrate_regimes) [L]
        self.regime = None
        self.lowrank = lowrank           # ongoing dynamics from a few shared modes (LowRankVAR) if > 0
        self.obs_fit = obs_fit           # measurement-noise share chosen on training worms so that
                                         # 'spread' at random moments matches them [L]
        self.name = ("hybrid_kernels" + (f"_{mask}" if mask else "") + ("" if background == "spontaneous" else f"_bg{background}")
                     + ("_obs" if obs_noise else "") + ("_heavy" if heavy else "") + ("_regimes" if regimes else "")
                     + ("_obsfit" if obs_fit else "") + (f"_lowrank{lowrank}" if lowrank else ""))

    def _gain(self, n: int, rng: np.random.Generator) -> np.ndarray:
        """A two-state Markov chain (quiet, active) with the calibrated share of quiet time and
        mean dwell, mapped to noise gains whose mean square is 1."""
        pq, dwell, gq = self.regime
        ga = np.sqrt(max((1 - pq * gq ** 2) / (1 - pq), 1e-6))
        leave_q, leave_a = 1.0 / dwell, (1.0 / dwell) * pq / (1 - pq)
        st = rng.random() < pq
        out = np.empty(n)
        for t in range(n):
            out[t] = gq if st else ga
            if rng.random() < (leave_q if st else leave_a):
                st = not st
        return out

    def calibrate_regimes(self, train, n_worms: int = 6, seed: int = 0):
        """Choose (share quiet, mean dwell in frames, quiet gain) so that the model's 'spread' at
        random moments matches the training worms' (5th, 50th, 95th percentiles) [L]."""
        from dataclasses import replace as _replace
        from ..bench.perturbational import pci_set
        rng = np.random.default_rng(seed)
        npre, npost = window(train[0].dt)

        def at_random(rec):
            fr = rng.integers(npre, rec.n_frames - npost, len(rec.stims))
            return _replace(rec, stims=[(k, int(f)) for (k, _), f in zip(rec.stims, fr)])

        pick = [train[i] for i in rng.choice(len(train), size=min(n_worms, len(train)), replace=False)]
        target = np.percentile(np.concatenate([pci_set(at_random(r)).spread for r in pick]), [5, 50, 95])
        kernels, self.kernels = self.kernels, {}
        best = None
        for pq in (0.3, 0.5, 0.7):
            for dwell in (30.0, 60.0, 120.0):
                for gq in (0.15, 0.3, 0.5):
                    self.regime = (pq, dwell, gq)
                    got = np.percentile(np.concatenate([pci_set(at_random(self.simulate(r, np.random.default_rng(7)))).spread
                                                        for r in pick]), [5, 50, 95])
                    loss = float(np.sum((got - target) ** 2))
                    if best is None or loss < best[0]:
                        best = (loss, self.regime, got)
        self.kernels = kernels
        self.regime = best[1]
        self.info.update({"regime": best[1], "random_spread_target": np.round(target, 3).tolist(),
                          "random_spread_model": np.round(best[2], 3).tolist()})
        return self

    @staticmethod
    def _noise_fractions(recs, classes) -> np.ndarray:
        """Per class, the share of variance that is white measurement noise, from the
        autocovariance of stimulation-free activity: for slow dynamics plus white noise,
        gamma(0) = signal + noise while gamma(1)^2 / gamma(2) estimates the signal alone.
        Median over worms, clipped to [0, 0.8]."""
        fr = {c: [] for c in classes}
        for r in recs:
            z = class_matrix(r, classes)
            m = spontaneous_mask(r)
            for i, c in enumerate(classes):
                v = z[i, m]
                v = v[np.isfinite(v)]
                if v.size < 200:
                    continue
                v = v - v.mean()
                g0, g1, g2 = (np.mean(v * v), np.mean(v[1:] * v[:-1]), np.mean(v[2:] * v[:-2]))
                if g2 > 1e-9 and g0 > 0:
                    fr[c].append(float(np.clip((g0 - g1 ** 2 / g2) / g0, 0, 0.8)))
        return np.array([np.median(fr[c]) if fr[c] else 0.0 for c in classes])

    def fit(self, train, val):
        from ..bench.perturbational import event_matrices
        if self.lowrank:
            self.var = LowRankVAR(k=self.lowrank, lags=self.lags, frames=self.background).fit(train, val)
        else:
            self.var = ClassVAR(lags=self.lags, frames=self.background,
                                innovations="student" if self.heavy else "gaussian").fit(train, val)
        if self.obs_noise:
            self.noise_frac = self._noise_fractions(list(train) + list(val), self.var.classes)
        acc: dict = {}
        for r in list(train) + list(val):
            for e in event_matrices(r, keep=True):
                for c, row in zip(e["classes"], e["R"]):
                    a = acc.setdefault((e["stim_class"], c), [np.zeros_like(row), 0])
                    a[0] += np.nan_to_num(row)
                    a[1] += 1
        self.kernels = {k: s / (n + self.shrink) for k, (s, n) in acc.items()}
        if self.mask:
            from .wiring import class_wiring, shuffled_wiring
            cls = sorted({c for k in self.kernels for c in k})
            A = class_wiring(cls)
            if self.mask == "shuffled":
                A = shuffled_wiring(A, self.seed)
            idx = {c: i for i, c in enumerate(cls)}
            self.kernels = {k: v for k, v in self.kernels.items() if A[idx[k[1]], idx[k[0]]]}
        self.info = {**self.var.info, "kernels": len(self.kernels)}
        if self.regimes:
            self.calibrate_regimes(list(train))
        if self.obs_fit:
            self.calibrate_obs(list(train))
        return self

    def calibrate_obs(self, train, n_worms: int = 6, seed: int = 0, grid=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5)):
        """Choose one measurement-noise share for all classes so that 'spread' at random moments
        matches the training worms (5th, 50th, 95th percentiles) [L]."""
        from dataclasses import replace as _replace
        from ..bench.perturbational import pci_set
        rng = np.random.default_rng(seed)
        npre, npost = window(train[0].dt)

        def at_random(rec):
            fr = rng.integers(npre, rec.n_frames - npost, len(rec.stims))
            return _replace(rec, stims=[(k, int(f)) for (k, _), f in zip(rec.stims, fr)])

        pick = [train[i] for i in rng.choice(len(train), size=min(n_worms, len(train)), replace=False)]
        target = np.percentile(np.concatenate([pci_set(at_random(r)).spread for r in pick]), [5, 50, 95])
        kernels, self.kernels = self.kernels, {}
        self.obs_noise = True
        best = None
        for f in grid:
            self.noise_frac = np.full(len(self.var.classes), f)
            got = np.percentile(np.concatenate([pci_set(at_random(self.simulate(r, np.random.default_rng(7)))).spread
                                                for r in pick]), [5, 50, 95])
            loss = float(np.sum((got - target) ** 2))
            if best is None or loss < best[0]:
                best = (loss, f, got)
        self.kernels = kernels
        self.noise_frac = np.full(len(self.var.classes), best[1])
        self.info.update({"obs_share": best[1], "random_spread_target": np.round(target, 3).tolist(),
                          "random_spread_model": np.round(best[2], 3).tolist()})
        return self

    def simulate(self, rec: PumpProbe, rng: np.random.Generator) -> PumpProbe:
        from dataclasses import replace
        npre, npost = window(rec.dt)
        quiet = replace(rec, stims=[])
        gain = self._gain(quiet.n_frames + 200, rng) if self.regime else None
        if self.obs_noise:
            # dynamics driven only by the non-measurement part of the residuals; the measurement
            # part is added afterwards as white noise of the same total size [A]
            keep = self.var.noise_sd.copy()
            self.var.noise_sd = keep * np.sqrt(1 - self.noise_frac)
            bg = self.var.simulate(quiet, rng, noise_gain=gain)
            self.var.noise_sd = keep
        else:
            bg = self.var.simulate(quiet, rng, noise_gain=gain)   # ongoing activity, no stimulation
        x = bg.x.copy()
        if self.obs_noise:
            ci = {c: i for i, c in enumerate(self.var.classes)}
            f = np.array([self.noise_frac[ci[c]] for c in bg.classes])
            sdx = x.std(axis=1, keepdims=True)
            x = x + rng.standard_normal(x.shape) * sdx * np.sqrt(f / np.clip(1 - f, 0.2, None))[:, None]
        T = x.shape[1]
        row = {c: i for i, c in enumerate(bg.classes)}
        stims = [(k, f) for k, f in rec.stims if rec.classes[k] in row and f - npre >= 0 and f + npost <= T]
        # each class's pre-stimulus fluctuation size in the simulation
        devs = [[] for _ in range(len(x))]
        for _, f in stims:
            pre = x[:, f - npre:f]
            d = pre - pre.mean(axis=1, keepdims=True)
            for j in range(len(x)):
                devs[j].append(d[j])
        fl = np.array([np.std(np.concatenate(d)) if d else 1.0 for d in devs])
        sd = np.nanstd(rec.x, axis=1)
        out_stims = []
        for k, f in stims:
            ci = rec.classes[k]
            i = row[ci]
            if not sd[k] > 0:
                continue
            own = (rec.x[k, f:f + npost] - np.nanmean(rec.x[k, f - npre:f])) / sd[k]
            x[i, f:f + npost] = x[i, f - 1] + np.nan_to_num(own) * np.std(x[i])
            for cj, j in row.items():
                h = self.kernels.get((ci, cj))
                if h is not None and j != i:
                    x[j, f:f + npost] += h[:npost] * fl[j]
            out_stims.append((i, f))
        return PumpProbe(uid=rec.uid, x=x, names=bg.names, classes=bg.classes, stims=out_stims, dt=rec.dt,
                         all_stim_frames=list(rec.all_stim_frames))


class LowRankVAR:
    """Ongoing dynamics as a few shared brain-wide modes plus private activity (arc 4,
    'merge rest and poke'). Real worm brains are low-dimensional (a handful of modes carries
    most of the variance); a full class-level VAR spreads activity over too many dimensions.

        z_t = U s_t + e_t        U: top-k principal directions of training activity [L]
        s_t = VAR(lags) on the k modes (ridge)                                       [L]
        e_t = per-class AR(1), private to each class                                [L]

    Same simulate() interface as ClassVAR (unseen classes stay at zero; noise_gain scales the
    driving noise frame by frame; noise_sd scales the private noise)."""

    def __init__(self, k: int = 6, lags: int = 3, frames: str = "spontaneous", min_fraction: float = 0.3,
                 ridges=(1.0, 10.0, 100.0, 1000.0)):
        self.k, self.lags, self.frames, self.min_fraction, self.ridges = k, lags, frames, min_fraction, ridges
        self.name = f"lowrank{k}_var{lags}_{frames}"

    def _series(self, recs):
        out = []
        for r in recs:
            z = class_matrix(r, self.classes)
            use = spontaneous_mask(r) if self.frames == "spontaneous" else np.ones(r.n_frames, bool)
            out.append((np.nan_to_num(z), np.isfinite(z), use))
        return out

    def fit(self, train, val):
        from collections import Counter
        cnt = Counter(c for r in train for c in set(r.classes) if c)
        self.classes = sorted(c for c, n in cnt.items() if n >= self.min_fraction * len(train))
        tr = self._series(list(train) + list(val))
        X = np.hstack([z[:, u] for z, _, u in tr])
        U, S, _ = np.linalg.svd(X - X.mean(axis=1, keepdims=True), full_matrices=False)
        self.U = U[:, :self.k]
        self.var_explained = float((S[:self.k] ** 2).sum() / (S ** 2).sum())
        p = self.lags
        Xs, Ys, E0, E1 = [], [], [], []
        for z, obs, use in tr:
            s = self.U.T @ z
            e = z - self.U @ s
            T = z.shape[1]
            ts = np.array([t for t in range(p, T) if use[t - p:t + 1].all()])
            if ts.size == 0:
                continue
            Xs.append(np.hstack([s[:, ts - L].T for L in range(1, p + 1)] + [np.ones((ts.size, 1))]))
            Ys.append(s[:, ts].T)
            E0.append(np.where(obs[:, ts - 1], e[:, ts - 1], np.nan))
            E1.append(np.where(obs[:, ts], e[:, ts], np.nan))
        Xa, Ya = np.vstack(Xs), np.vstack(Ys)
        pen = np.full(Xa.shape[1], 100.0)
        pen[-1] = 0
        self.Ws = np.linalg.solve(Xa.T @ Xa + np.diag(pen), Xa.T @ Ya)
        R = Ya - Xa @ self.Ws
        self.latent_cov = np.cov(R.T) + 1e-6 * np.eye(self.k)
        self.Lq = np.linalg.cholesky(self.latent_cov)
        e0, e1 = np.hstack(E0), np.hstack(E1)
        with np.errstate(invalid="ignore"):
            num = np.nansum(e0 * e1, axis=1)
            den = np.nansum(e0 * e0, axis=1)
            self.a = np.clip(np.where(den > 0, num / den, 0.0), 0.0, 0.98)
            res = e1 - self.a[:, None] * e0
            self.noise_sd = np.sqrt(np.nanmean(res ** 2, axis=1))
        self.noise_sd[~np.isfinite(self.noise_sd)] = 0.1
        self.noise_sd0 = self.noise_sd.copy()
        A = self.Ws[:-1].reshape(p, self.k, self.k)
        comp = np.zeros((p * self.k, p * self.k))
        comp[:self.k, :] = np.hstack([A[L].T for L in range(p)])
        if p > 1:
            comp[self.k:, :-self.k] = np.eye((p - 1) * self.k)
        rad = float(np.abs(np.linalg.eigvals(comp)).max())
        self.gain = min(1.0, 0.99 / rad) if rad > 0 else 1.0
        self.info = {"k": self.k, "var_explained": round(self.var_explained, 3), "latent_radius": round(rad, 4)}
        return self

    def simulate(self, rec: PumpProbe, rng: np.random.Generator, burn: int = 200,
                 noise_gain: np.ndarray | None = None) -> PumpProbe:
        C, p, k = len(self.classes), self.lags, self.k
        idx = {c: i for i, c in enumerate(self.classes)}
        own = [c for c in sorted(set(rec.classes)) if c in idx]
        seen = np.zeros(C, bool)
        seen[[idx[c] for c in own]] = True
        T = rec.n_frames
        A = self.Ws[:-1].reshape(p, k, k).copy()
        for L in range(1, p + 1):
            A[L - 1] *= self.gain ** L
        b = self.Ws[-1]
        lat_scale = float(np.mean(self.noise_sd) / max(np.mean(self.noise_sd0), 1e-9))
        s = np.zeros((k, T + burn))
        e = np.zeros(C)
        z = np.zeros((C, T + burn))
        for t in range(p, T + burn):
            g = 1.0 if noise_gain is None else noise_gain[t]
            s[:, t] = b + sum(s[:, t - L] @ A[L - 1] for L in range(1, p + 1)) + g * lat_scale * (self.Lq @ rng.standard_normal(k))
            e = self.a * e + g * self.noise_sd * rng.standard_normal(C)
            z[:, t] = np.where(seen, self.U @ s[:, t] + e, 0.0)
        x = z[[idx[c] for c in own], burn:]
        return PumpProbe(uid=rec.uid, x=x, names=own, classes=own, stims=[], dt=rec.dt,
                         all_stim_frames=list(rec.all_stim_frames))
