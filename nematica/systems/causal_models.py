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


def pairwise_cov(R: np.ndarray, min_n: int = 200) -> np.ndarray:
    """Covariance of the columns of R (rows = frames) using frames where both are finite."""
    ok = np.isfinite(R).astype(float)
    Z = np.nan_to_num(R)
    n = ok.T @ ok
    with np.errstate(invalid="ignore", divide="ignore"):
        m = (Z.T @ ok) / n                 # mean of column i over frames where j is also seen
        S = (Z.T @ Z) / n - m * m.T
    S[n < min_n] = np.nan
    return S


def factor_fit(S: np.ndarray, k: int, iters: int = 200):
    """Loadings L (C x k) and specific variances psi with L L' + diag(psi) close to S, by
    iterated principal factors on the correlation scale; missing entries of S are filled from
    the current fit (EM-style). Returns loadings in the original units [A]."""
    d = np.sqrt(np.clip(np.diag(S), 1e-9, None))
    Rm = S / np.outer(d, d)
    miss = ~np.isfinite(Rm)
    Rm = np.where(miss, 0.0, Rm)
    np.fill_diagonal(Rm, 1.0)
    h = np.full(len(d), 0.5)
    for _ in range(iters):
        A = Rm.copy()
        np.fill_diagonal(A, h)
        w, V = np.linalg.eigh(A)
        w, V = w[::-1][:k], V[:, ::-1][:, :k]
        Lc = V * np.sqrt(np.clip(w, 0, None))
        fit = Lc @ Lc.T
        Rm = np.where(miss, fit, Rm)
        np.fill_diagonal(Rm, 1.0)
        h = np.clip((Lc ** 2).sum(1), 0.0, 0.98)
    Lc = Lc * np.sqrt(h / np.maximum((Lc ** 2).sum(1), 1e-12))[:, None]
    return Lc * d[:, None], (1 - h) * d ** 2


def lagged_cov(recs, classes, L: int, min_n: int = 500, sym: bool = True) -> np.ndarray:
    """Pooled covariance between z-scored class activity at t + L (rows) and t (columns), all
    frames, frames where both classes are seen; symmetrised unless `sym` is False."""
    C = len(classes)
    S = np.zeros((C, C)); N = np.zeros((C, C)); A = np.zeros((C, C)); B = np.zeros((C, C))
    for r in recs:
        z = class_matrix(r, classes)
        z = (z - np.nanmean(z, axis=1, keepdims=True)) / np.nanstd(z, axis=1, keepdims=True)
        a, b = z[:, L:], z[:, :-L] if L else z
        oa, ob = np.isfinite(a).astype(float), np.isfinite(b).astype(float)
        a0, b0 = np.nan_to_num(a), np.nan_to_num(b)
        S += a0 @ b0.T; N += oa @ ob.T; A += a0 @ ob.T; B += oa @ b0.T
    with np.errstate(invalid="ignore", divide="ignore"):
        M = S / N - (A / N) * (B / N)
    M[N < min_n] = np.nan
    return (M + M.T) / 2 if sym else M


def highpass_rec(rec: PumpProbe, w: int = 80) -> PumpProbe:
    """The recording minus its own centred moving average over w frames (NaN-aware): what is
    left after the slow part is removed."""
    from dataclasses import replace
    k = np.ones(w)
    x = rec.x
    ok = np.isfinite(x)
    num = np.array([np.convolve(np.nan_to_num(r), k, mode="same") for r in x])
    den = np.array([np.convolve(o.astype(float), k, mode="same") for o in ok])
    with np.errstate(invalid="ignore", divide="ignore"):
        lo = num / den
    return replace(rec, x=np.where(ok, x - lo, np.nan))


def drift_params(recs, classes, lags=(240, 480), min_n: int = 200):
    """Per class, an ultra-slow part (minutes): share and per-frame AR coefficient from the
    autocovariance at 2 and 4 minutes, by a log-linear fit; NaN where not estimable [A]."""
    D = np.array([np.diag(lagged_cov(recs, classes, L, min_n=min_n)) for L in lags]).T
    share = np.full(len(classes), np.nan)
    rho = np.full(len(classes), np.nan)
    for i in range(len(classes)):
        d = D[i]
        if np.isfinite(d).all() and (d > 0.01).all():
            sl, ic = np.polyfit(lags, np.log(d), 1)
            rho[i] = float(np.clip(np.exp(sl), 0.995, 0.99995))
            share[i] = float(np.clip(np.exp(ic), 0, 0.8))
    return share, rho


def drift_pool(recs, classes) -> tuple[dict, list]:
    """Per class, the (share, AR coefficient) of the ultra-slow part in every training worm
    that shows the class."""
    pool, allv = {}, []
    for r in recs:
        sh, rh = drift_params([r], classes)
        seen = set(r.classes)
        for i, c in enumerate(classes):
            if c in seen:
                v = (float(sh[i]) if np.isfinite(sh[i]) else 0.0, float(rh[i]) if np.isfinite(rh[i]) else 0.999)
                pool.setdefault(c, []).append(v)
                allv.append(v)
    return pool, allv


class SlowLatent:
    """A few slow brain-wide factors, each an AR(1) with its own timescale, read out by every
    class. Fitted from lagged covariances (lags 20 to 80 frames), which white measurement noise
    and fast dynamics do not reach [A]: C(L) ~ V diag(c_j rho_j^L) V'."""

    def __init__(self, k: int = 3, lags=(20, 40, 80), dyn: bool = False):
        self.k, self.lags = k, lags
        self.dyn = dyn                   # factors interact (a k x k VAR(1) with lead and lag)
        self.A = None

    def _fit_dyn(self, recs, V):
        """Factor dynamics s_t = A s_(t-1) + noise from lagged covariances projected on V,
        G(L) = V' E[x_(t+L) x_t'] V = A^L Sigma, using lags 10 to 82 frames where fast activity
        has decayed: A^2 by least squares over (G(L), G(L+2)), A its principal square root [A]."""
        from scipy.linalg import sqrtm
        Ls = list(range(10, 84, 2))
        G = {L: V.T @ np.nan_to_num(lagged_cov(recs, self.classes, L, sym=False)) @ V for L in Ls}
        num = sum(G[L + 2] @ G[L].T for L in Ls[:-1])
        den = sum(G[L] @ G[L].T for L in Ls[:-1])
        B = num @ np.linalg.inv(den)
        A = np.real(sqrtm(B))
        rad = float(np.abs(np.linalg.eigvals(A)).max())
        if rad > 0.999:
            A *= 0.999 / rad
        P = [np.linalg.matrix_power(A, L) for L in Ls]
        Sig = np.linalg.solve(sum(p.T @ p for p in P), sum(p.T @ G[L] for p, L in zip(P, Ls)))
        Sig = (Sig + Sig.T) / 2
        w, U = np.linalg.eigh(Sig)
        Sig = (U * np.clip(w, 1e-6, None)) @ U.T
        Q = Sig - A @ Sig @ A.T
        w, U = np.linalg.eigh((Q + Q.T) / 2)
        Q = (U * np.clip(w, 1e-8, None)) @ U.T
        self.A, self.Lq, self.Sig = A, np.linalg.cholesky(Q), Sig
        self.Ls_sig = np.linalg.cholesky(Sig)
        ev = np.linalg.eigvals(A)
        return {"slow_dyn_radius": round(rad, 4), "slow_dyn_rotation": round(float(np.abs(np.angle(ev)).max()), 4)}

    def fit(self, recs, classes):
        self.classes = list(classes)
        Cs = {L: lagged_cov(recs, classes, L) for L in self.lags}
        ref = np.nan_to_num(Cs[self.lags[1]])
        w, V = np.linalg.eigh(ref)
        V = V[:, ::-1][:, :self.k]
        self.rho, c0 = [], []
        for j in range(self.k):
            v = V[:, j]
            ok = np.isfinite(Cs[self.lags[0]]).all(0)
            cj = [float(v[ok] @ np.nan_to_num(Cs[L])[np.ix_(ok, ok)] @ v[ok]) for L in self.lags]
            cj = np.clip(cj, 1e-6, None)
            slope, icpt = np.polyfit(self.lags, np.log(cj), 1)
            rho = float(np.clip(np.exp(slope), 0.9, 0.9995))
            self.rho.append(rho)
            c0.append(float(np.exp(icpt)))
        self.rho, self.c0, self.V = np.array(self.rho), np.array(c0), V
        load = V * np.sqrt(self.c0)                         # z units
        dinfo = {}
        if self.dyn:
            dinfo = self._fit_dyn(recs, V)
            load = V @ self.Ls_sig                           # loadings for unit-variance factors
            self.V = V
        # each class's total slow share, from its own lagged autocovariance; the part the shared
        # factors do not explain becomes a private slow AR(1) per class
        D = np.array([[Cs[L][i, i] for L in self.lags] for i in range(len(classes))])
        tot, rp = np.zeros(len(classes)), np.zeros(len(classes))
        for i in range(len(classes)):
            d = np.clip(np.nan_to_num(D[i], nan=1e-6), 1e-6, None)
            sl, ic = np.polyfit(self.lags, np.log(d), 1)
            tot[i], rp[i] = min(float(np.exp(ic)), 0.85), float(np.clip(np.exp(sl), 0.9, 0.9995))
        h = (load ** 2).sum(1)
        self.shrink = np.sqrt(np.minimum(h, tot) / np.maximum(h, 1e-12))
        load = load * self.shrink[:, None]
        self.load = load
        self.priv = np.sqrt(np.clip(tot - (load ** 2).sum(1), 0, None))
        self.rho_p = rp
        self.h = (self.load ** 2).sum(1) + self.priv ** 2
        self.info = {"slow_tau_s": [round(-0.5 / np.log(r), 1) for r in self.rho],
                     "slow_share_median": round(float(np.median(self.h)), 3),
                     "slow_shared_median": round(float(np.median((self.load ** 2).sum(1))), 3), **dinfo}
        return self

    def individual(self, rec: PumpProbe) -> "SlowLatent":
        """A donor worm's version: the pooled factor directions, rescaled by how much of this
        worm's activity is slow (one factor for the worm: median over its classes of own slow
        share / pooled slow share), with the worm's own slow timescale (median over classes) [A]."""
        import copy
        m = copy.copy(self)
        if self.dyn:
            return self._individual_dyn(rec, m, w_own=getattr(self, "w_own", 0.5))
        D = np.array([np.diag(lagged_cov([rec], self.classes, L, min_n=200)) for L in self.lags]).T
        own_tot, own_rho = [], []
        for i in range(len(self.classes)):
            d = D[i]
            if not np.isfinite(d).all() or (d <= 0).any():
                continue
            sl, ic = np.polyfit(self.lags, np.log(d), 1)
            own_tot.append(min(float(np.exp(ic)), 0.95) / max(self.h[i], 1e-3))
            own_rho.append(float(np.clip(np.exp(sl), 0.9, 0.9995)))
        if len(own_tot) < 5:
            return self
        g = float(np.clip(np.median(own_tot), 0.1, 3.0))
        cap = np.sqrt(np.minimum(g * self.h, 0.9) / np.maximum(self.h, 1e-12))
        m.load = self.load * cap[:, None]
        m.priv = self.priv * cap
        m.rho_p = np.full(len(self.classes), float(np.median(own_rho)))
        m.h = (m.load ** 2).sum(1) + m.priv ** 2
        m.donor_scale = g
        return m

    def _individual_dyn(self, rec, m, w_own: float = 0.5):
        """Donor version with factor dynamics: the donor's slow covariance (its lag-20 covariance
        divided by the pooled decay over 20 frames), averaged half and half with the pooled one,
        factored into k loadings and rotated (Procrustes) onto the pooled factor coordinates so
        the pooled dynamics apply; the rest of each class's slow share stays private [A]."""
        Cw = lagged_cov([rec], self.classes, self.lags[0], min_n=200)
        decay = float(np.median(self.rho)) ** self.lags[0]
        pool = self.load @ self.load.T + np.diag(self.priv ** 2)
        Sw = np.where(np.isfinite(Cw), w_own * Cw / decay + (1 - w_own) * pool, pool)
        Sw = (Sw + Sw.T) / 2
        w, U = np.linalg.eigh(Sw)
        Lw = U[:, ::-1][:, :self.k] * np.sqrt(np.clip(w[::-1][:self.k], 0, None))
        Um, _, Vt = np.linalg.svd(Lw.T @ self.load)
        Lw = Lw @ (Um @ Vt)
        h = (Lw ** 2).sum(1)
        tot = np.clip(np.diag(Sw), 0, 0.9)
        Lw = Lw * np.sqrt(np.minimum(h, tot) / np.maximum(h, 1e-12))[:, None]
        m.load = Lw
        m.priv = np.sqrt(np.clip(tot - (Lw ** 2).sum(1), 0, None))
        m.h = (m.load ** 2).sum(1) + m.priv ** 2
        if getattr(self, "drift", False) and getattr(self, "drift_pool", None) is None:
            sh, rh = drift_params([rec], self.classes)
            m.drift_share = np.where(np.isfinite(sh), sh, 0.0)
            m.drift_rho = np.where(np.isfinite(rh), rh, 0.999)
            # the drift's share comes out of the private slow part, total kept at most 0.95
            m.priv = np.sqrt(np.clip(m.priv ** 2 - m.drift_share, 0, None))
            over = (m.load ** 2).sum(1) + m.priv ** 2 + m.drift_share - 0.95
            m.drift_share = np.clip(m.drift_share - np.clip(over, 0, None), 0, None)
            m.h = (m.load ** 2).sum(1) + m.priv ** 2 + m.drift_share
        if getattr(self, "own_rho", False):
            # the donor's own timescale for each class's private slow part (lags 20 to 80)
            D = np.array([np.diag(lagged_cov([rec], self.classes, L, min_n=200)) for L in self.lags]).T
            rp = self.rho_p.copy()
            for i in range(len(self.classes)):
                d = D[i]
                if np.isfinite(d).all() and (d > 0).all():
                    rp[i] = float(np.clip(np.exp(np.polyfit(self.lags, np.log(d), 1)[0]), 0.9, 0.9995))
            m.rho_p = rp
        return m

    def draw(self, T: int, rng: np.random.Generator) -> np.ndarray:
        f = np.zeros((self.k, T))
        if self.A is not None:
            # factor state with unit-variance coordinates: u = Ls_sig^-1 s
            Li = np.linalg.inv(self.Ls_sig)
            Au, Qu = Li @ self.A @ self.Ls_sig, Li @ self.Lq
            f[:, 0] = rng.standard_normal(self.k)
            for t in range(1, T):
                f[:, t] = Au @ f[:, t - 1] + Qu @ rng.standard_normal(self.k)
        else:
            f[:, 0] = rng.standard_normal(self.k)
            e = np.sqrt(1 - self.rho ** 2)
            for t in range(1, T):
                f[:, t] = self.rho * f[:, t - 1] + e * rng.standard_normal(self.k)
        g = np.zeros((len(self.priv), T))
        g[:, 0] = rng.standard_normal(len(self.priv))
        ep = np.sqrt(1 - self.rho_p ** 2)
        nu = getattr(self, "burst_nu", 0.0)
        for t in range(1, T):
            if nu:
                # sparse, heavy-tailed kicks (unit variance): rare long excursions [A]
                e = rng.standard_t(nu, len(self.priv)) * np.sqrt((nu - 2) / nu)
            else:
                e = rng.standard_normal(len(self.priv))
            g[:, t] = self.rho_p * g[:, t - 1] + ep * e
        g /= max(float(np.std(g)), 1e-9) if nu else 1.0
        out = self.load @ f + self.priv[:, None] * g
        ds = getattr(self, "drift_share", None)
        if getattr(self, "drift_pool", None) is not None:
            # each class row draws its ultra-slow part from what training worms showed for
            # that class (worm-class rows; shares of rows with no estimate count as zero) [A]
            ds, dr = np.zeros(len(self.classes)), np.full(len(self.classes), 0.999)
            for i, c in enumerate(self.classes):
                vals = self.drift_pool.get(c) or self.drift_pool_all
                sh, rh = vals[int(rng.integers(len(vals)))]
                ds[i], dr[i] = sh, rh
            ds = ds * getattr(self, "drift_gain", 1.0)   # finite recordings understate minutes-long
                                                          # variance; gain chosen on the selection split [L]
            room = np.clip(0.95 - (self.load ** 2).sum(1), 0, None)
            ds = np.minimum(ds, room)
            self.drift_rho = dr
            pr = np.sqrt(np.clip(self.priv ** 2 - ds, 0, None))
            out = self.load @ f + pr[:, None] * g
        if ds is not None and ds.any():
            u = np.zeros((len(ds), T))
            u[:, 0] = rng.standard_normal(len(ds))
            ed = np.sqrt(1 - self.drift_rho ** 2)
            for t in range(1, T):
                u[:, t] = self.drift_rho * u[:, t - 1] + ed * rng.standard_normal(len(ds))
            out = out + np.sqrt(ds)[:, None] * u
        return out
        # classes x T, z units


class ClassVAR:
    def __init__(self, lags: int = 3, frames: str = "spontaneous", min_fraction: float = 0.3,
                 ridges=(1.0, 10.0, 100.0, 1000.0, 10000.0), max_radius: float = 0.99,
                 protocol: str = "clamp", fixed_ridge: float | None = None, coupling: str = "full",
                 features: str = "linear", penalty: str = "ridge", theta: float = 1.0,
                 innovations: str = "gaussian", innov_k: int = 0):
        self.lags, self.frames, self.min_fraction, self.ridges = lags, frames, min_fraction, ridges
        self.innov_k = innov_k                        # > 0: shocks share innov_k common factors
                                                      # (fitted to the residual covariance) instead
                                                      # of being independent across classes [A]
        self.innov_L = None
        self.innov_n0 = 2000.0                        # pooled-covariance weight for one worm [A]
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

    def _solve(self, X, Y, lam, prior: np.ndarray | None = None):
        """Ridge per target; with `prior`, shrink toward it instead of toward zero."""
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
            rhs = Xm.T @ Y[m, j] + (pen * prior[cols, j] if prior is not None else 0.0)
            W[cols, j] = np.linalg.solve(Xm.T @ Xm + np.diag(pen), rhs)
        return W

    def individual(self, rec: PumpProbe, lam: float = 300.0, shock_only: bool = False) -> "ClassVAR":
        """A copy fitted on one worm's frames, shrunk toward this (pooled) model [L]. With
        `shock_only`, the pooled dynamics are kept and only the common-factor structure of the
        shocks is the worm's own [A]."""
        import copy
        m = copy.copy(self)
        X, Y = self._design([rec])
        if X.shape[0] < 100:
            return self
        if shock_only:
            if self.innov_k:
                m._fit_innov(Y - X @ self.W, prior=self.innov_S, n0=self.innov_n0)
            return m
        m.W = self._solve(X, Y, lam, prior=self.W)
        R = Y - X @ m.W
        sd = np.sqrt(np.nanmean(R ** 2, axis=0))
        m.noise_sd = np.where(np.isfinite(sd) & (sd > 0), sd, self.noise_sd)
        if self.innov_k:
            m._fit_innov(R, prior=self.innov_S, n0=self.innov_n0)
        return m

    def _fit_innov(self, R, prior=None, n0: float = 0.0):
        """Common-factor structure of the shocks. With `prior` (a pooled covariance), the
        worm's own covariance is shrunk toward it: (n S + n0 prior) / (n + n0), n = frames [L]."""
        S = pairwise_cov(R, min_n=100 if prior is not None else 200)
        if prior is not None:
            n = float(np.isfinite(R).any(1).sum())
            S = np.where(np.isfinite(S), (n * S + n0 * prior) / (n + n0), prior)
        else:
            self.innov_S = S
        L, psi = factor_fit(S, self.innov_k)
        tot = np.sqrt((L ** 2).sum(1) + psi)
        scale = self.noise_sd / np.maximum(tot, 1e-9)        # keep each class's shock size
        self.innov_L = L * scale[:, None]
        self.innov_psi = np.sqrt(np.clip(psi, 0, None)) * scale

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
        if self.innov_k:
            self._fit_innov(R)
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
                 noise_gain: np.ndarray | None = None, quiet: np.ndarray | None = None) -> PumpProbe:
        """A simulated version of `rec`: the model's classes observed in this worm, one row
        each, stimulated on the worm's schedule. `noise_gain` (length burn + frames) scales
        the driving noise frame by frame (quiet and active regimes). `quiet` (classes x
        (burn + frames), boolean): where true, that class is decoupled and settles, drifting
        slowly toward its baseline with small noise [A]."""
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
        if getattr(self, "run_unseen", False):       # stitched copies: unrecorded classes keep running
            seen[:] = True
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
            if self.innov_L is not None:
                if self.innovations == "student":
                    # heavy-tailed common and private shocks (unit variance), as for _shock [A]
                    nu_c = float(np.median(self.nu))
                    fz = rng.standard_t(nu_c, self.innov_k) * np.sqrt((nu_c - 2) / nu_c)
                    shock = self.innov_L @ fz + self.innov_psi * self._shock(rng, C)
                else:
                    shock = self.innov_L @ rng.standard_normal(self.innov_k) + self.innov_psi * rng.standard_normal(C)
            else:
                shock = self.noise_sd * self._shock(rng, C)
            nxt += shock * (1.0 if noise_gain is None else noise_gain[t])
            if quiet is not None:
                q = quiet[:, t]
                if q.any():
                    nxt[q] = (getattr(self, "quiet_decay", 0.97) * z[q, t - 1]
                              + getattr(self, "quiet_noise", 0.15) * self.noise_sd[q] * rng.standard_normal(int(q.sum())))
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
        if protocol == "native":
            # the authors' own stimulation model: a learned input filter per neuron, one
            # n x n block per frame since the pulse (45 frames), driven by a unit input at
            # the stimulation frame, as in their stimulus-triggered average maps
            if "B" not in z.files:
                raise ValueError("re-run scripts/fetch_creamer_lds.py to store the input filter")
            n, L = len(self.cells), int(z["input_lags"])
            self.Bk = [z["B"][:, k * n:(k + 1) * n] for k in range(L)]

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
            if self.protocol == "native":
                for k, Bk in enumerate(self.Bk):
                    drive = pulse.setdefault(f + k, np.zeros(n))
                    drive += Bk[:, cell_of[nm]]
            elif self.protocol == "pulse":
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
                if self.protocol == "native":
                    x += pulse[t]
                else:
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
                 regimes: bool = False, obs_fit: bool = False, lowrank: int = 0, obs_smooth: float = 0.0,
                 class_quiet: bool = False, quiet_fit: bool = False, quiet_obs_fit: bool = False,
                 individual: bool = False, gru: int = 0, gru_sampled: bool = False, gru_steps: int = 1500,
                 innov: int = 0, slow: int = 0):
        self.slow = slow                 # > 0: this many slow brain-wide factors added to the
                                         # ongoing activity (SlowLatent) [A]
        self.slow_model = None
        self.slow_indiv = []             # donor worms' slow models (indivslow)
        self.indiv_slow = False
        self.slow_dyn = False
        self.slow_w_own = 0.5
        self.highpass = False
        self.slow_own_rho = False
        self.no_kernels = False
        self.slow_drift = False
        self.slow_drift_pool = False
        self.drift_gain = 1.0     # each row draws its drift from training worm-class rows          # donors' ultra-slow drifts (minutes), class by class
        self.burst_nu = 0.0              # > 2: private slow parts driven by heavy-tailed kicks
        self.coupling = "full"           # "diagonal": each class driven only by its own past
        self.members = False             # observed neuron by neuron, members of a class separate
        self.member_rho, self.member_rho_default = {}, 0.25
        self.innov = innov               # > 0: the VAR's shocks share this many common factors
        self.indiv_shock = False         # individual backgrounds: only the shock structure
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
        self.obs_smooth = obs_smooth     # AR(1) coefficient of the measurement noise (0 = white)
        self.class_quiet = class_quiet   # each class its own quiet/active chain, quiet share from
                                         # training worms (_quiet_shares) [L]; dwell 60 frames [A]
        self.quiet_share = None
        self.quiet_obs_fit = quiet_obs_fit   # the same, jointly with a measurement-noise share
        self.individual = individual     # each simulated worm's background is one training worm's
                                         # own VAR, shrunk toward the pooled one (lambda 300) [L]
        self.indiv = []
        self.gru = gru                   # ongoing dynamics from AtlasGRU (hidden size) if > 0
        self.gru_sampled, self.gru_steps = gru_sampled, gru_steps
        self.quiet_fit = quiet_fit       # per-class quiet strength calibrated on training worms to
                                         # match their echo structure at random moments [L]
        self.obs_fit = obs_fit           # measurement-noise share chosen on training worms so that
                                         # 'spread' at random moments matches them [L]
        self.name = ("hybrid_kernels" + (f"_{mask}" if mask else "") + ("" if background == "spontaneous" else f"_bg{background}")
                     + ("_obs" if obs_noise else "") + ("_heavy" if heavy else "") + ("_regimes" if regimes else "")
                     + ("_obsfit" if obs_fit else "") + (f"_lowrank{lowrank}" if lowrank else "")
                     + (f"_smooth{obs_smooth:g}" if obs_smooth else "") + ("_classquiet" if class_quiet else "") + ("_quietfit" if quiet_fit else "") + ("_quietobsfit" if quiet_obs_fit else "") + ("_indiv" if individual else "") + (f"_gru{gru}" + ("ss" if gru_sampled else "") if gru else "") + (f"_innov{innov}" if innov else "") + (f"_slow{slow}" if slow else ""))
        self._base_name = self.name

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
    def _quiet_shares(recs, classes, n_windows: int = 40, seed: int = 0) -> np.ndarray:
        """Per class, the share of random 30 s windows (in stimulation-free stretches where
        possible) in which the class never moves more than 3 pre-window fluctuation sizes from
        its level in the 5 s before: how often it simply stays out. Median over worms [L]."""
        rng = np.random.default_rng(seed)
        npre, npost = window(recs[0].dt)
        out = {c: [] for c in classes}
        for r in recs:
            z = class_matrix(r, classes)
            T = z.shape[1]
            starts = rng.integers(npre, T - npost, n_windows)
            for i, c in enumerate(classes):
                if not np.isfinite(z[i]).any():
                    continue
                pres = [z[i, f - npre:f] for f in starts]
                dev = np.concatenate([p - np.nanmean(p) for p in pres])
                sd = np.nanstd(dev)
                if not sd > 0:
                    continue
                stay = [np.nanmax(np.abs(z[i, f:f + npost] - np.nanmean(z[i, f - npre:f]))) <= 3 * sd for f in starts]
                out[c].append(float(np.mean(stay)))
        return np.array([np.median(out[c]) if out[c] else 0.0 for c in classes])

    def _quiet_mask(self, n: int, rng: np.random.Generator, dwell: float = 60.0) -> np.ndarray:
        q = np.clip(self.quiet_share, 0.0, 0.95)
        C = len(q)
        leave_q = np.full(C, 1.0 / dwell)
        leave_a = np.where(q < 1, (1.0 / dwell) * q / np.clip(1 - q, 1e-6, None), 1.0)
        st = rng.random(C) < q
        out = np.empty((C, n), bool)
        for t in range(n):
            out[:, t] = st
            flip = rng.random(C) < np.where(st, leave_q, leave_a)
            st = st ^ flip
        return out

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
        if self.gru:
            self.var = AtlasGRU(hidden=self.gru, sampled=self.gru_sampled, steps=self.gru_steps).fit(train, val)
        elif self.lowrank:
            self.var = LowRankVAR(k=self.lowrank, lags=self.lags, frames=self.background).fit(train, val)
        else:
            vt, vv = train, val
            if self.highpass:
                # the fast part only: the VAR learns from activity with its slow part removed [A]
                vt, vv = [highpass_rec(r) for r in train], [highpass_rec(r) for r in val]
                self._hp_train = vt
            self.var = ClassVAR(lags=self.lags, frames=self.background, coupling=self.coupling,
                                innovations="student" if self.heavy else "gaussian", innov_k=self.innov).fit(vt, vv)
        if self.slow:
            self.slow_model = SlowLatent(self.slow, dyn=self.slow_dyn).fit(list(train) + list(val), self.var.classes)
            self.slow_model.burst_nu = self.burst_nu
            if self.slow_drift_pool:
                self.slow_model.drift_pool, self.slow_model.drift_pool_all = drift_pool(list(train), self.var.classes)
                self.slow_model.drift_gain = self.drift_gain
            if self.indiv_slow:
                self.slow_model.w_own = self.slow_w_own
                self.slow_model.own_rho = self.slow_own_rho
                self.slow_model.drift = self.slow_drift
                self.slow_indiv = [self.slow_model.individual(r) for r in train]
        if self.members:
            self.member_rho = self._member_corrs(list(train) + list(val))
            if self.member_rho:
                self.member_rho_default = float(np.median(list(self.member_rho.values())))
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
            from .wiring import class_wiring, class_members_known, shuffled_wiring
            cls = sorted({c for k in self.kernels for c in k})
            A = class_wiring(cls)
            idx = {c: i for i, c in enumerate(cls)}
            if self.mask in ("connectome", "shuffled"):
                if self.mask == "shuffled":
                    A = shuffled_wiring(A, self.seed)
                self.kernels = {k: v for k, v in self.kernels.items() if A[idx[k[1]], idx[k[0]]]}
            elif self.mask.endswith("k"):
                # the wiring question asked only where the wiring is known: links involving a class
                # absent from this connectome (mostly pharyngeal neurons) are kept in every version
                known = class_members_known(cls)
                kn = lambda k: bool(known[idx[k[0]]] and known[idx[k[1]]])
                base = self.mask[:-1]
                if base == "shuffled":
                    ki = np.where(known)[0]
                    S = np.eye(len(cls), dtype=bool)
                    S[np.ix_(ki, ki)] = shuffled_wiring(A[np.ix_(ki, ki)], self.seed)
                    A = S
                wired = [k for k in self.kernels if k[0] != k[1] and kn(k) and A[idx[k[1]], idx[k[0]]]]
                unwired = [k for k in self.kernels if k[0] != k[1] and kn(k) and not A[idx[k[1]], idx[k[0]]]]
                if base in ("wired", "shuffled"):
                    keep = wired
                elif base == "unwired":
                    keep = unwired
                elif base == "unwiredn":
                    rng = np.random.default_rng(self.seed)
                    n_w = sum(1 for k in self.kernels if k[0] != k[1] and kn(k) and class_wiring(cls)[idx[k[1]], idx[k[0]]])
                    keep = [unwired[i] for i in rng.choice(len(unwired), size=min(n_w, len(unwired)), replace=False)]
                else:
                    raise ValueError(f"unknown mask {self.mask}")
                keep = set(keep) | {k for k in self.kernels if k[0] == k[1] or not kn(k)}
                self.kernels = {k: v for k, v in self.kernels.items() if k in keep}
                self.info_mask = {"wired": len(wired), "unwired": len(unwired), "kept": len(self.kernels)}
            else:
                # links between classes that are both in the connectome but have no synapse or gap junction
                known = class_members_known(cls)
                wired = [k for k in self.kernels if k[0] != k[1] and known[idx[k[0]]] and known[idx[k[1]]] and A[idx[k[1]], idx[k[0]]]]
                unwired = [k for k in self.kernels if k[0] != k[1] and known[idx[k[0]]] and known[idx[k[1]]] and not A[idx[k[1]], idx[k[0]]]]
                if self.mask == "unwired":
                    keep = unwired
                elif self.mask == "unwiredn":            # as many unwired links as there are wired ones
                    rng = np.random.default_rng(self.seed)
                    keep = [unwired[i] for i in rng.choice(len(unwired), size=min(len(wired), len(unwired)), replace=False)]
                elif self.mask == "known":              # wired and unwired, both classes in the connectome
                    keep = wired + unwired
                else:
                    raise ValueError(f"unknown mask {self.mask}")
                # a class's own echo (its other members answering) is kept, as the wiring mask keeps it
                keep = set(keep) | {k for k in self.kernels if k[0] == k[1]}
                self.kernels = {k: v for k, v in self.kernels.items() if k in keep}
                self.info_mask = {"wired": len(wired), "unwired": len(unwired)}
        if self.no_kernels:                  # ablation: no causal knowledge from pokes
            self.kernels = {}
        self.info = {**self.var.info, "kernels": len(self.kernels), **getattr(self, "info_mask", {}), **(self.slow_model.info if self.slow_model is not None else {})}
        if self.individual and isinstance(self.var, ClassVAR):
            self.indiv = [self.var.individual(r, shock_only=self.indiv_shock)
                          for r in (self._hp_train if self.highpass else train)]
            self.info["individual_backgrounds"] = sum(m is not self.var for m in self.indiv)
        if self.class_quiet or self.quiet_fit or self.quiet_obs_fit:
            self.quiet_share = self._quiet_shares(list(train) + list(val), self.var.classes)
            self.info["median_quiet_share"] = round(float(np.median(self.quiet_share)), 3)
        if self.quiet_fit:
            self.calibrate_quiet(list(train))
        if self.quiet_obs_fit:
            self.calibrate_quiet(list(train), obs_grid=(0.0, 0.05, 0.1, 0.2))
        if self.regimes:
            self.calibrate_regimes(list(train))
        if self.obs_fit:
            self.calibrate_obs(list(train))
        return self

    def calibrate_quiet(self, train, n_worms: int = 6, seed: int = 0, obs_grid=(None,)):
        """Scale the per-class quiet shares and set how still a quiet class is, so that at
        random moments (no poke) the model matches the training worms on three things: the
        share of classes that cross 3 pre-window SDs in 30 s, the spread, and the PCI [L]."""
        from dataclasses import replace as _replace
        from ..bench.perturbational import event_matrices
        rng = np.random.default_rng(seed)
        npre, npost = window(train[0].dt)

        def at_random(rec):
            fr = rng.integers(npre, rec.n_frames - npost, len(rec.stims))
            return _replace(rec, stims=[(k, int(f)) for (k, _), f in zip(rec.stims, fr)])

        def triple(evs):
            B = [np.abs(np.nan_to_num(e["R"])) > 3 for e in evs]
            return np.array([np.median([b.any(axis=1).mean() for b in B]), np.median([e["spread"] for e in evs]),
                             np.median([e["pci"] for e in evs])])

        pick = [train[i] for i in rng.choice(len(train), size=min(n_worms, len(train)), replace=False)]
        target = triple([e for r in pick for e in event_matrices(at_random(r), keep=True)])
        base = self.quiet_share.copy()
        kernels, self.kernels = self.kernels, {}
        best = None
        for scale in (1.0, 1.5, 2.0, 2.5, 3.0):
            for qn in (0.03, 0.1):
                for ob in obs_grid:
                    self.quiet_share = np.clip(base * scale, 0, 0.95)
                    self.var.quiet_noise, self.var.quiet_decay = qn, 0.99
                    if ob is not None:
                        self.obs_noise = ob > 0
                        self.noise_frac = np.full(len(self.var.classes), ob)
                    got = triple([e for r in pick for e in event_matrices(at_random(self.simulate(r, np.random.default_rng(7))), keep=True)])
                    loss = float(np.sum(((got - target) / np.array([0.1, 0.05, 0.1])) ** 2))
                    if best is None or loss < best[0]:
                        best = (loss, scale, qn, ob, got)
        self.kernels = kernels
        self.quiet_share = np.clip(base * best[1], 0, 0.95)
        self.var.quiet_noise, self.var.quiet_decay = best[2], 0.99
        if best[3] is not None:
            self.obs_noise = best[3] > 0
            self.noise_frac = np.full(len(self.var.classes), best[3])
        self.info.update({"quiet_scale": best[1], "quiet_noise": best[2], "obs_share": best[3],
                          "quiet_target": np.round(target, 3).tolist(), "quiet_model": np.round(best[4], 3).tolist()})
        return self

    @staticmethod
    def _member_corrs(recs) -> dict:
        """Median correlation between two members of a class (e.g. left and right), per class."""
        from collections import defaultdict
        rho = defaultdict(list)
        for r in recs:
            by = defaultdict(list)
            for j, c in enumerate(r.classes):
                if c:
                    by[c].append(j)
            for c, js in by.items():
                if len(js) < 2:
                    continue
                a, b = r.x[js[0]], r.x[js[1]]
                ok = np.isfinite(a) & np.isfinite(b)
                if ok.sum() >= 500:
                    rho[c].append(float(np.corrcoef(a[ok], b[ok])[0, 1]))
        return {c: float(np.clip(np.median(v), 0.0, 0.95)) for c, v in rho.items() if len(v) >= 3}

    def _simulate_members(self, rec, bg, x, rng, phi: float = 0.95):
        """Observed like a real worm: one row per named neuron of the worm, members of a class
        sharing the class activity plus their own part (zero across members, so the class
        average is unchanged), sized to the training worms' member correlation; responses are
        then in each neuron's own fluctuation units, as for real neurons [A]."""
        npre, npost = window(rec.dt)
        T = x.shape[1]
        row = {c: i for i, c in enumerate(bg.classes)}
        nrn = [j for j, c in enumerate(rec.classes) if c in row]
        cls = [rec.classes[j] for j in nrn]
        y = np.vstack([x[row[c]] for c in cls])
        for c in set(cls):
            mem = [n for n, cc in enumerate(cls) if cc == c]
            m = len(mem)
            if m < 2:
                continue
            V = np.var(x[row[c]])
            rho = self.member_rho.get(c, self.member_rho_default)
            sig = np.sqrt(V * (1 - rho) / (rho * (1 - 1 / m) + 1 / m))
            w = rng.standard_normal((m, T + 200))
            for t in range(1, T + 200):
                w[:, t] = phi * w[:, t - 1] + np.sqrt(1 - phi ** 2) * w[:, t]
            w = w[:, 200:]
            y[mem] += sig * (w - w.mean(axis=0, keepdims=True)) * np.sqrt(m / (m - 1))
        pos = {j: n for n, j in enumerate(nrn)}
        stims = [(k, f) for k, f in rec.stims if k in pos and f - npre >= 0 and f + npost <= T]
        devs = [[] for _ in range(len(y))]
        for _, f in stims:
            pre = y[:, f - npre:f]
            d = pre - pre.mean(axis=1, keepdims=True)
            for n in range(len(y)):
                devs[n].append(d[n])
        fl = np.array([np.std(np.concatenate(d)) if d else 1.0 for d in devs])
        sd = np.nanstd(rec.x, axis=1)
        out_stims = []
        for k, f in stims:
            ci, i = rec.classes[k], pos[k]
            if not sd[k] > 0:
                continue
            own = (rec.x[k, f:f + npost] - np.nanmean(rec.x[k, f - npre:f])) / sd[k]
            y[i, f:f + npost] = y[i, f - 1] + np.nan_to_num(own) * np.std(y[i])
            for n, cj in enumerate(cls):
                h = self.kernels.get((ci, cj))
                if h is not None and n != i:
                    y[n, f:f + npost] += h[:npost] * fl[n]
            out_stims.append((i, f))
        return PumpProbe(uid=rec.uid, x=y, names=[rec.names[j] for j in nrn], classes=cls, stims=out_stims,
                         dt=rec.dt, all_stim_frames=list(rec.all_stim_frames))

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
        var = self.var
        if self.indiv:
            # a fixed training worm for each simulated worm (by uid), so repeats are the same individual
            var = self.indiv[int.from_bytes(rec.uid.encode(), "little") % len(self.indiv)]
        gain = self._gain(quiet.n_frames + 200, rng) if self.regime else None
        qmask = self._quiet_mask(quiet.n_frames + 200, rng) if self.quiet_share is not None else None
        kw = {"quiet": qmask} if qmask is not None else {}
        if self.obs_noise:
            # dynamics driven only by the non-measurement part of the residuals; the measurement
            # part is added afterwards as white noise of the same total size [A]
            keep = var.noise_sd.copy()
            var.noise_sd = keep * np.sqrt(1 - self.noise_frac)
            bg = var.simulate(quiet, rng, noise_gain=gain, **kw)
            var.noise_sd = keep
        else:
            bg = var.simulate(quiet, rng, noise_gain=gain, **kw)   # ongoing activity, no stimulation
        x = bg.x.copy()
        if self.slow_model is not None:
            # ongoing activity = fast part (the VAR) with variance share 1 - h, plus the slow
            # factors with share h, at each class's simulated size
            ci = {c: i for i, c in enumerate(self.var.classes)}
            rows = [ci[c] for c in bg.classes]
            sm = self.slow_model
            if self.slow_indiv:
                sm = self.slow_indiv[int.from_bytes(rec.uid.encode(), "little") % len(self.slow_indiv)]
            sl = sm.draw(x.shape[1] + 400, rng)[rows, 400:]
            h = sm.h[rows][:, None]
            sdb = x.std(axis=1, keepdims=True)
            x = x * np.sqrt(1 - h) + sl * sdb
        if self.obs_noise:
            ci = {c: i for i, c in enumerate(self.var.classes)}
            f = np.array([self.noise_frac[ci[c]] for c in bg.classes])
            sdx = x.std(axis=1, keepdims=True)
            w = rng.standard_normal(x.shape)
            if self.obs_smooth:                       # smooth in time, same variance
                phi = self.obs_smooth
                for t in range(1, w.shape[1]):
                    w[:, t] = phi * w[:, t - 1] + np.sqrt(1 - phi ** 2) * w[:, t]
            x = x + w * sdx * np.sqrt(f / np.clip(1 - f, 0.2, None))[:, None]
        if self.members:
            return self._simulate_members(rec, bg, x, rng)
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


class AtlasGRU:
    """A nonlinear background learned from the atlas worms (ingredient hunt, 'genuinely
    nonlinear dynamics'): a GRU reads the class activity of the last frame (and which classes
    are observed) and outputs the mean and the log-variance of the next frame, so the size of
    the fluctuations can depend on the brain's state (calm stretches can be calm). Trained on
    contiguous stimulation-free stretches of the training worms (at least 40 frames), Gaussian
    negative log-likelihood on observed classes, with input noise for stable free running [A].
    Same simulate() interface as ClassVAR. PyTorch is imported lazily."""

    def __init__(self, hidden: int = 64, steps: int = 1500, chunk: int = 40, batch: int = 32, lr: float = 2e-3,
                 input_noise: float = 0.1, min_fraction: float = 0.3, seed: int = 0, sampled: bool = False):
        self.hidden, self.steps, self.chunk, self.batch, self.lr = hidden, steps, chunk, batch, lr
        self.input_noise, self.min_fraction, self.seed = input_noise, min_fraction, seed
        self.sampled = sampled   # free-running training: inputs are partly the model's own samples
                                 # (scheduled sampling, rising to half by the end), so errors that
                                 # build up when it runs on its own are what it learns to avoid [A]
        self.name = f"gru{hidden}" + ("ss" if sampled else "")

    def _segments(self, recs):
        segs = []
        for r in recs:
            z = class_matrix(r, self.classes)
            m = spontaneous_mask(r)
            t = 0
            T = len(m)
            while t < T:
                if m[t]:
                    u = t
                    while u < T and m[u]:
                        u += 1
                    if u - t >= self.chunk + 1:
                        segs.append(z[:, t:u])
                    t = u
                else:
                    t += 1
        return segs

    def fit(self, train, val):
        import torch
        from collections import Counter
        torch.manual_seed(self.seed)
        cnt = Counter(c for r in train for c in set(r.classes) if c)
        self.classes = sorted(c for c, n in cnt.items() if n >= self.min_fraction * len(train))
        C = len(self.classes)
        segs = self._segments(list(train))
        vsegs = self._segments(list(val)) or segs[:2]
        nn = torch.nn

        class Net(nn.Module):
            def __init__(s):
                super().__init__()
                s.gru = nn.GRU(2 * C, self.hidden, batch_first=True)
                s.out = nn.Linear(self.hidden, 2 * C)

            def forward(s, x, obs, h=None):
                y, h = s.gru(torch.cat([x, obs], -1), h)
                o = s.out(y)
                return o[..., :C], o[..., C:].clamp(-6, 3), h

        self.net = Net()
        opt = torch.optim.Adam(self.net.parameters(), lr=self.lr)
        rng = np.random.default_rng(self.seed)

        def batch(pool, n):
            xs, os_ = [], []
            for _ in range(n):
                s = pool[rng.integers(len(pool))]
                a = rng.integers(0, s.shape[1] - self.chunk - 1 + 1)
                w = s[:, a:a + self.chunk + 1].T
                xs.append(np.nan_to_num(w))
                os_.append(np.isfinite(w).astype(np.float32))
            return torch.tensor(np.array(xs), dtype=torch.float32), torch.tensor(np.array(os_))

        def nll(x, o):
            inp = x[:, :-1] + self.input_noise * torch.randn_like(x[:, :-1])
            mu, lv, _ = self.net(inp, o[:, :-1])
            tgt, m = x[:, 1:], o[:, 1:]
            return (((tgt - mu) ** 2 / lv.exp() + lv) * m).sum() / m.sum().clamp(min=1)

        def nll_sampled(x, o, p_own):
            # step through the chunk; each input is the data or, with probability p_own, the
            # model's own sample from the previous step
            h, prev, loss, cnt = None, x[:, :1], 0.0, 0.0
            for t in range(x.shape[1] - 1):
                mu, lv, h = self.net(prev, o[:, t:t + 1], h)
                tgt, m = x[:, t + 1:t + 2], o[:, t + 1:t + 2]
                loss = loss + (((tgt - mu) ** 2 / lv.exp() + lv) * m).sum()
                cnt = cnt + m.sum()
                own = (mu + (0.5 * lv).exp() * torch.randn_like(mu)).detach()
                use = (torch.rand(x.shape[0], 1, 1) < p_own).float()
                prev = use * own + (1 - use) * (tgt + self.input_noise * torch.randn_like(tgt))
            return loss / cnt.clamp(min=1)

        for step in range(self.steps):
            x, o = batch(segs, self.batch)
            loss = nll_sampled(x, o, 0.5 * step / self.steps) if self.sampled else nll(x, o)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.0)
            opt.step()
        with torch.no_grad():
            x, o = batch(vsegs, 64)
            self.info = {"hidden": self.hidden, "segments": len(segs), "val_nll": round(float(nll(x, o)), 4),
                         "classes": C}
        self.noise_sd = np.ones(C)
        self.noise_sd0 = self.noise_sd.copy()
        return self

    def simulate(self, rec: PumpProbe, rng: np.random.Generator, burn: int = 200,
                 noise_gain: np.ndarray | None = None, quiet: np.ndarray | None = None) -> PumpProbe:
        import torch
        C = len(self.classes)
        idx = {c: i for i, c in enumerate(self.classes)}
        own = [c for c in sorted(set(rec.classes)) if c in idx]
        seen = np.zeros(C, bool)
        seen[[idx[c] for c in own]] = True
        obs = torch.tensor(seen.astype(np.float32)).view(1, 1, C)
        T = rec.n_frames
        z = np.zeros((C, T + burn), dtype=np.float32)
        h = None
        x = torch.zeros(1, 1, C)
        scale = self.noise_sd / np.where(self.noise_sd0 > 0, self.noise_sd0, 1.0)
        with torch.no_grad():
            for t in range(1, T + burn):
                mu, lv, h = self.net(x, obs, h)
                sd = np.exp(0.5 * lv.numpy().ravel())
                g = 1.0 if noise_gain is None else noise_gain[t]
                nxt = mu.numpy().ravel() + g * scale * sd * rng.standard_normal(C)
                nxt = np.clip(nxt, -8, 8)
                if quiet is not None and quiet[:, t].any():
                    q = quiet[:, t]
                    nxt[q] = (getattr(self, "quiet_decay", 0.97) * z[q, t - 1]
                              + getattr(self, "quiet_noise", 0.15) * rng.standard_normal(int(q.sum())))
                nxt[~seen] = 0.0
                z[:, t] = nxt
                x = torch.tensor(nxt, dtype=torch.float32).view(1, 1, C)
        out = z[[idx[c] for c in own], burn:].astype(float)
        return PumpProbe(uid=rec.uid, x=out, names=own, classes=own, stims=[], dt=rec.dt,
                         all_stim_frames=list(rec.all_stim_frames))
