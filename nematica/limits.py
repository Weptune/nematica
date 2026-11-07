"""The watching limit: how well could ANY method recover poke responses from rest alone?

Model (linear Gaussian latent network). State z = [x; h]: x are the n units a recording can
see, h are k hidden units or drives that no recording sees.
    z[t+1] = F z[t] + w[t],   w ~ N(0, Q)       Q diagonal: every unit has private noise
    y[t]   = x[t] + v[t],     v ~ N(0, R)       R diagonal: measurement noise
Poke response of seen unit i to a kick of seen unit j, summed over `win` frames:
    G[i, j] = sum_{t<win} (F^t)[i, j]

Three results, each checked numerically in tests/test_limits.py and scripts/run_limit_theory.py:

1. Shared-noise lemma (exact, global). If the hidden units' noise may correlate with the seen
   units' noise, the poke response is NOT identifiable from rest: for any matrix M, the
   transform T = [[I, 0], [M, I]] gives F' = T F T^-1, Q' = T Q T^T with the identical
   observed spectrum but G' = G - Gh M, where Gh is the seen units' response to kicks of the
   hidden units. Watching cannot tell a direct link from shared noise routed through hidden
   units. With private (diagonal) noise, Q' diagonal forces M Q_x = 0, so M = 0: this
   family is ruled out.

2. Information limit (local). With private noise the parameters are locally identifiable
   (the Fisher information, gauge fixed by Q_h = 1, has full rank), so watching is limited
   only by data. The Cramer-Rao bound gives the smallest covariance any unbiased watcher can
   reach from T frames: Cov(G_hat) >= J_G I(theta)^-1 J_G^T, with I from the Whittle
   (frequency-domain) likelihood:
       I_ab = T/2 * mean_w tr(S^-1 dS/da S^-1 dS/db),
       S(w) = C H Q H^* C^T + R,  H = (I - e^{-iw} F)^-1.
   The bound shrinks as 1/T. `agreement_from_cov` turns it into the best expected
   agreement (correlation with the true G), the number our ruler reports.

3. Silent-link lemma (nonlinear). A link that only carries signal when its source is above a
   threshold contributes to the rest likelihood only on frames where the source is above
   threshold. Its Fisher information is proportional to T times the fraction of rest frames
   it is active; if the source never crosses at rest, the link is invisible to watching at
   any T, and a poke that drives the source over threshold reveals it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


# ------------------------------------------------------------------ the model
@dataclass
class LGNet:
    F: np.ndarray            # (d, d)
    q: np.ndarray            # (d,) private noise variances
    r: np.ndarray            # (n,) measurement noise variances
    n: int                   # number of seen units (the first n states)
    Qfull: np.ndarray | None = field(default=None)   # optional full noise covariance

    @property
    def d(self):
        return self.F.shape[0]

    @property
    def k(self):
        return self.d - self.n

    @property
    def Q(self):
        return np.diag(self.q) if self.Qfull is None else self.Qfull

    def stable(self):
        return np.abs(np.linalg.eigvals(self.F)).max() < 1


def random_net(n=12, k=2, rho=0.8, density=0.3, drive_rho=0.98, drive_load=0.5,
               hidden_kind="drive", q_obs=1.0, r=0.1, seed=0) -> LGNet:
    """A random stable latent network.

    hidden_kind "drive": hidden units are slow AR(1) drives (timescale set by drive_rho)
    that feed the seen units and receive nothing. "unit": hidden units are ordinary units,
    wired in both directions like the seen ones.
    drive_load scales the hidden-to-seen loadings.
    """
    rng = np.random.default_rng(seed)
    d = n + k
    A = rng.standard_normal((n, n)) * (rng.random((n, n)) < density)
    np.fill_diagonal(A, 0)
    ev = np.abs(np.linalg.eigvals(A)).max()
    A *= (rho / ev) if ev > 0 else 1.0
    A += 0.3 * np.eye(n)                     # a little self-memory (leak), as in rate units
    ev = np.abs(np.linalg.eigvals(A)).max()
    if ev > rho:
        A *= rho / ev
    F = np.zeros((d, d))
    F[:n, :n] = A
    if k:
        if hidden_kind == "drive":
            F[n:, n:] = np.diag(np.full(k, drive_rho))
            F[:n, n:] = drive_load * rng.standard_normal((n, k)) * np.sqrt(1 - drive_rho ** 2)
        else:
            F[:n, n:] = rng.standard_normal((n, k)) * (rng.random((n, k)) < density)
            F[n:, :n] = rng.standard_normal((k, n)) * (rng.random((k, n)) < density)
            F[n:, n:] = 0.3 * np.eye(k)
            ev = np.abs(np.linalg.eigvals(F)).max()
            if ev > rho:
                F *= rho / ev
    q = np.concatenate([np.full(n, q_obs), np.ones(k)])
    return LGNet(F=F, q=q, r=np.full(n, r), n=n)


def poke_response(F, n, win=30):
    """G[i, j] = sum_{t<win} (F^t)[i, j] over seen units."""
    d = F.shape[0]
    P, G = np.eye(d), np.zeros((d, d))
    for _ in range(win):
        G += P
        P = F @ P
    return G[:n, :n]


def poke_response_hidden(F, n, win=30):
    d = F.shape[0]
    P, G = np.eye(d), np.zeros((d, d))
    for _ in range(win):
        G += P
        P = F @ P
    return G[:n, n:]


def spectrum(net: LGNet, omegas):
    """S(w) for each w: (m, n, n) complex."""
    d, n = net.d, net.n
    out = np.empty((len(omegas), n, n), complex)
    Q = net.Q
    for i, w in enumerate(omegas):
        H = np.linalg.inv(np.eye(d) - np.exp(-1j * w) * net.F)
        U = H[:n]
        out[i] = U @ Q @ U.conj().T + np.diag(net.r)
    return out


def simulate(net: LGNet, T, rng, burn=500):
    d, n = net.d, net.n
    L = np.linalg.cholesky(net.Q + 1e-15 * np.eye(d))
    z = np.zeros(d)
    y = np.empty((T, n))
    for t in range(-burn, T):
        z = net.F @ z + L @ rng.standard_normal(d)
        if t >= 0:
            y[t] = z[:n] + np.sqrt(net.r) * rng.standard_normal(n)
    return y


# ------------------------------------------------------------------ Fisher information
def param_layout(net: LGNet, fix_hidden_q=True, F_mask=None):
    """Which parameters are free: entries of F (optionally masked), seen q, (hidden q), r."""
    d, n = net.d, net.n
    if F_mask is None:
        F_mask = np.ones((d, d), bool)
    fidx = np.argwhere(F_mask)
    qidx = np.arange(n) if fix_hidden_q else np.arange(d)
    return fidx, qidx


def fisher(net: LGNet, T, m=256, fix_hidden_q=True, F_mask=None):
    """Whittle Fisher information for T frames, private-noise model. Returns (I, layout)."""
    d, n = net.d, net.n
    fidx, qidx = param_layout(net, fix_hidden_q, F_mask)
    P = len(fidx) + len(qidx) + n
    I = np.zeros((P, P))
    Q = net.Q
    # S(-w) = conj S(w): use w in (0, pi) with weight 2, plus w = 0 and w = pi once
    ws = np.pi * np.arange(m + 1) / m
    wts = np.full(m + 1, 2.0)
    wts[0] = wts[-1] = 1.0
    wts /= 2 * m                                  # mean over the full circle
    a_idx, b_idx = fidx[:, 0], fidx[:, 1]
    for w, wt in zip(ws, wts):
        e = np.exp(-1j * w)
        H = np.linalg.inv(np.eye(d) - e * net.F)
        U = H[:n]                                 # C H
        S = U @ Q @ U.conj().T + np.diag(net.r)
        L = np.linalg.cholesky(S)
        Li = np.linalg.inv(L)
        Ut = Li @ U                               # whitened (n, d)
        V = H @ Q @ U.conj().T                    # (d, n)
        Vt = V @ Li.conj().T                      # (d, n)
        # dS/dF_ab = e U[:, a] V[b, :] + h.c.   (whitened)
        X = e * Ut[:, a_idx].T[:, :, None] * Vt[b_idx][:, None, :]      # (Pf, n, n)
        AF = X + np.conj(np.transpose(X, (0, 2, 1)))
        AQ = Ut[:, qidx].T[:, :, None] * Ut[:, qidx].conj().T[:, None, :]
        AR = Li.T[:, :, None] * Li.conj().T[:, None, :]                 # l_i l_i^H, l_i = Li[:, i]
        J = np.concatenate([AF, AQ, AR]).reshape(P, n * n)
        # tr(A_a A_b) = sum_ij A_a[i,j] A_b[j,i] = vec(A_a) . vec(A_b^T)
        Jt = np.concatenate([AF, AQ, AR]).transpose(0, 2, 1).reshape(P, n * n)
        I += wt * np.real(J @ Jt.T)
    return T / 2 * I, (fidx, qidx)


def G_jacobian(net: LGNet, layout, win=30, pairs="offdiag"):
    """Jacobian of the seen-unit poke response (selected pairs) w.r.t. the free parameters."""
    import torch
    fidx, qidx = layout
    d, n = net.d, net.n
    F0 = torch.tensor(net.F, dtype=torch.float64)
    fi = torch.tensor(fidx[:, 0]), torch.tensor(fidx[:, 1])

    def G_of(theta_f):
        F = F0.clone()
        F[fi] = theta_f
        P, G = torch.eye(d, dtype=torch.float64), torch.zeros(d, d, dtype=torch.float64)
        for _ in range(win):
            G = G + P
            P = F @ P
        g = G[:n, :n]
        if pairs == "offdiag":
            g = g[~torch.eye(n, dtype=torch.bool)]
        return g.reshape(-1)

    th = F0[fi].clone()
    Jf = torch.autograd.functional.jacobian(G_of, th).numpy()
    P = len(fidx) + len(qidx) + n
    J = np.zeros((Jf.shape[0], P))
    J[:, :len(fidx)] = Jf
    return J


def gauge_tangents(net: LGNet, layout):
    """Directions that change nothing observable: rotations among hidden units.

    With hidden noise fixed at 1, T = blockdiag(I, O) with O orthogonal keeps Q diagonal and
    C = [I 0] unchanged, so the k(k-1)/2 rotation generators are exact symmetries.
    """
    fidx, qidx = layout
    d, n, k = net.d, net.n, net.k
    P = len(fidx) + len(qidx) + n
    out = []
    for a in range(k):
        for b in range(a + 1, k):
            B = np.zeros((d, d))
            B[n + a, n + b], B[n + b, n + a] = 1.0, -1.0
            dF = B @ net.F - net.F @ B
            v = np.zeros(P)
            v[:len(fidx)] = dF[fidx[:, 0], fidx[:, 1]]
            out.append(v / np.linalg.norm(v))
    return np.array(out).reshape(len(out), P)


def crb_G(net: LGNet, T, win=30, m=256, F_mask=None):
    """Cramer-Rao covariance of the off-diagonal poke response, gauge handled.

    Returns (cov, info). info["leak"] is how much of the poke-response gradient lies along
    the gauge (must be ~0: the poke response is gauge invariant), info["cond"] the smallest
    non-gauge eigenvalue relative to the largest.
    """
    I, lay = fisher(net, T, m=m, F_mask=F_mask)
    J = G_jacobian(net, lay, win=win)
    N = gauge_tangents(net, lay)
    scale = np.trace(I) / len(I)
    if len(N):
        Nq, _ = np.linalg.qr(N.T)
        leak = np.linalg.norm(J @ Nq) / max(np.linalg.norm(J), 1e-300)
        Ireg = I + scale * Nq @ Nq.T
    else:
        leak, Ireg = 0.0, I
    ev = np.linalg.eigvalsh(Ireg)
    cov = J @ np.linalg.solve(Ireg, J.T)
    return cov, {"leak": float(leak), "cond": float(ev[0] / ev[-1]), "P": I.shape[0]}


def agreement_from_cov(G_true_off, cov, draws=400, rng=None):
    """Expected correlation between the truth and an efficient estimate with error cov."""
    rng = rng or np.random.default_rng(0)
    w, V = np.linalg.eigh((cov + cov.T) / 2)
    Lc = V * np.sqrt(np.clip(w, 0, None))
    rs = []
    for _ in range(draws):
        e = Lc @ rng.standard_normal(len(w))
        rs.append(np.corrcoef(G_true_off + e, G_true_off)[0, 1])
    return float(np.mean(rs)), float(np.percentile(rs, 5)), float(np.percentile(rs, 95))


def offdiag(G):
    n = G.shape[0]
    return G[~np.eye(n, dtype=bool)]


# ------------------------------------------------------------------ the shared-noise lemma
def shared_noise_twin(net: LGNet, M):
    """The exact twin: same observed spectrum, different poke response (lemma 1)."""
    d, n, k = net.d, net.n, net.k
    Tm = np.eye(d)
    Tm[n:, :n] = M
    Ti = np.linalg.inv(Tm)
    F2 = Tm @ net.F @ Ti
    Q2 = Tm @ net.Q @ Tm.T
    return LGNet(F=F2, q=np.diag(Q2).copy(), r=net.r.copy(), n=n, Qfull=Q2)


# ------------------------------------------------------------------ watchers
def var_watcher(ys, n, win=30, ridge=1e-3):
    """The project's watching copy: VAR(1) on what is seen, kicked in silico."""
    X = np.concatenate([y[:-1] for y in ys])
    Y = np.concatenate([y[1:] for y in ys])
    X = X - X.mean(0)
    Y = Y - Y.mean(0)
    W = np.linalg.solve(X.T @ X + ridge * len(X) * np.eye(n), X.T @ Y).T
    r = np.abs(np.linalg.eigvals(W)).max()
    if r > 0.999:
        W *= 0.999 / r
    return poke_response(W, n, win)


def periodogram_bands(y, band=8):
    """Banded periodogram of one recording: (centres, weights, P) with P (b, n, n) complex."""
    T = len(y)
    yc = y - y.mean(0)
    f = np.fft.fft(yc, axis=0)[1:T // 2]          # w in (0, pi), conj pairs counted once
    ws = 2 * np.pi * np.arange(1, T // 2) / T
    nb = len(ws) // band
    f = f[:nb * band].reshape(nb, band, -1)
    P = np.einsum("bti,btj->bij", f, f.conj()) / (band * T)
    return ws[:nb * band].reshape(nb, band).mean(1), np.full(nb, float(band)), P


def whittle_fit(ys, n, k, win=30, band=8, steps=1500, init=None, seed=0, lr=0.02, obs_sets=None,
                hidden_kind="free", verbose=False, polish=300):
    """Best watcher: maximum (Whittle) likelihood fit of the correct model class
    (latent linear network, private noise), then kicked in silico.

    ys: list of (T, n) arrays; with obs_sets, each recording contributes the spectrum of the
    units it saw.
    """
    groups = []
    for idx, y in enumerate(ys):
        obs = np.arange(n) if obs_sets is None else np.flatnonzero(obs_sets[idx])
        w, wt, P = periodogram_bands(y[:, obs], band)
        groups.append((obs, w, wt, P))
    F, lq, lr_, loss = whittle_fit_groups(groups, n, k, steps=steps, init=init, seed=seed, lr=lr,
                                         hidden_kind=hidden_kind, verbose=verbose, polish=polish)
    return poke_response(F, n, win), (F, lq, lr_), loss


def whittle_loss(groups, F, q, r, n):
    """Mean Whittle negative log likelihood per frequency weight (numpy, for held-out scoring)."""
    d = F.shape[0]
    tot, wsum = 0.0, 0.0
    for obs, w, wt, P in groups:
        for wi, wti, Pi in zip(w, wt, P):
            H = np.linalg.inv(np.eye(d) - np.exp(-1j * wi) * F)
            U = H[obs]
            S = (U * q) @ U.conj().T + np.diag(r[obs])
            sign, ld = np.linalg.slogdet(S)
            tot += wti * (ld + np.trace(np.linalg.solve(S, Pi)).real)
            wsum += wti
    return tot / wsum


def whittle_fit_groups(groups, n, k, steps=1500, init=None, seed=0, lr=0.02, hidden_kind="free",
                       verbose=False, polish=300, ridge=0.0):
    """Whittle MLE from grouped periodograms. groups: list of (obs index array, freqs (b,),
    weights (b,), P (b, |obs|, |obs|) complex). Hidden noise is fixed at 1 (gauge).
    ridge: optional L2 penalty on the seen-to-seen couplings (per unit weight).
    Returns F, log q (seen), log r, final loss."""
    import torch
    torch.manual_seed(seed)
    d = n + k
    rng = np.random.default_rng(seed)
    # frequencies shared across groups are computed once
    allw = np.unique(np.concatenate([g[1] for g in groups]))
    wpos = {float(x): i for i, x in enumerate(allw)}
    data = []
    for obs, w, wt, P in groups:
        data.append((torch.tensor(np.asarray(obs)), torch.tensor([wpos[float(x)] for x in w]),
                     torch.tensor(wt, dtype=torch.float64), torch.tensor(P, dtype=torch.complex128)))
    Wt = torch.tensor(allw)
    if init is None:
        F0 = np.zeros((d, d))
        F0[:n, :n] = 0.5 * np.eye(n)
        if k:
            F0[n:, n:] = np.diag(0.9 - 0.03 * np.arange(k))
            F0[:n, n:] = 0.1 * rng.standard_normal((n, k))
        lq0 = np.zeros(n)
        lr0 = np.log(0.1) * np.ones(n)
    else:
        F0, lq0, lr0 = init
        F0 = np.array(F0, float)
        if F0.shape[0] < d:                      # grow a smaller fit by k hidden units
            G0 = np.zeros((d, d))
            m0 = F0.shape[0]
            G0[:m0, :m0] = F0
            for h in range(m0, d):
                G0[h, h] = 0.9 - 0.03 * (h - m0)      # distinct timescales
            G0[:n, m0:] = 0.05 * rng.standard_normal((n, d - m0))
            F0 = G0
    F = torch.tensor(F0, requires_grad=True)
    lq = torch.tensor(np.asarray(lq0, float), requires_grad=True)
    lrr = torch.tensor(np.asarray(lr0, float), requires_grad=True)
    mask = torch.ones(d, d, dtype=torch.float64)
    if hidden_kind == "drive" and k:
        mask[n:, :n] = 0
        mask[n:, n:] = torch.eye(k, dtype=torch.float64)
    eye = torch.eye(d, dtype=torch.complex128)
    totw = float(sum(float(g[2].sum()) for g in data))

    def objective():
        Fm = F * mask
        q = torch.cat([torch.exp(lq), torch.ones(k, dtype=torch.float64)]).to(torch.complex128)
        e = torch.exp(-1j * Wt)[:, None, None]
        H = torch.linalg.inv(eye[None] - e * Fm.to(torch.complex128)[None])
        loss = 0.0
        for obs, wi, wt, P in data:
            U = H[wi][:, obs, :]
            S = (U * q[None, None, :]) @ U.conj().transpose(1, 2)
            S = S + torch.diag_embed(torch.exp(lrr[obs]).to(torch.complex128))[None]
            L = torch.linalg.cholesky(S)
            ld = 2 * torch.log(torch.diagonal(L, dim1=1, dim2=2).real).sum(1)
            tr = torch.diagonal(torch.cholesky_solve(P, L), dim1=1, dim2=2).real.sum(1)
            loss = loss + (wt * (ld + tr)).sum()
        # stability penalty only when it bites: differentiating eigenvalues is unsafe when two
        # coincide (NaN gradients even where the penalty is zero)
        with torch.no_grad():
            rad0 = float(torch.linalg.eigvals(Fm).abs().max())
        pen = 0.0
        if rad0 > 0.995:
            rad = torch.linalg.matrix_norm(torch.linalg.matrix_power(Fm, 8), ord=2) ** (1 / 8)
            pen = 100 * torch.relu(rad - 0.995) ** 2
        if ridge:
            pen = pen + ridge * (Fm[:n, :n] ** 2).sum() / n
        return loss / totw + pen

    best = [np.inf, None]

    def keep(loss):
        with torch.no_grad():
            Fm = (F * mask).numpy()
            sr = np.abs(np.linalg.eigvals(Fm)).max()
            if np.isfinite(loss) and sr < 0.999 and loss < best[0]:
                best[0] = loss
                best[1] = (Fm.copy(), lq.detach().numpy().copy(), lrr.detach().numpy().copy())

    with torch.no_grad():
        keep(float(objective()))                 # the starting point is always a fallback
    opt = torch.optim.Adam([F, lq, lrr], lr=lr)
    for it in range(steps):
        opt.zero_grad()
        try:
            loss = objective()
            if not torch.isfinite(loss):
                raise FloatingPointError
        except Exception:                       # a non-positive-definite S: step back
            with torch.no_grad():
                if best[1] is not None:
                    F.copy_(torch.tensor(best[1][0]))
                    lq.copy_(torch.tensor(best[1][1]))
                    lrr.copy_(torch.tensor(best[1][2]))
            continue
        loss.backward()
        if not all(torch.isfinite(p.grad).all() for p in (F, lq, lrr)):
            continue
        opt.step()
        if it % 25 == 0 or it == steps - 1:
            keep(float(loss.detach()))
            if verbose and it % 100 == 0:
                print(it, round(float(loss.detach()), 5), flush=True)
    if best[1] is not None:
        with torch.no_grad():
            F.copy_(torch.tensor(best[1][0]))
            lq.copy_(torch.tensor(best[1][1]))
            lrr.copy_(torch.tensor(best[1][2]))
    if polish:
        lb = torch.optim.LBFGS([F, lq, lrr], lr=1, max_iter=polish, history_size=50,
                               tolerance_grad=1e-10, tolerance_change=1e-13, line_search_fn="strong_wolfe")

        calls = [0]

        def closure():
            calls[0] += 1
            if calls[0] > 4 * polish:
                raise RuntimeError("polish budget")
            lb.zero_grad()
            l = objective()
            if not torch.isfinite(l):
                raise FloatingPointError("non-finite loss")
            l.backward()
            return l
        try:
            lb.step(closure)
            keep(float(objective().detach()))
        except Exception:
            pass
        if verbose:
            print("polished", best[0], flush=True)
    Fh, lqh, lrh = best[1]
    return Fh, lqh, lrh, best[0]


# ------------------------------------------------------------------ the silent-link lemma
def silent_link_demo(theta, T, w=1.0, a=0.9, sigma=1.0, reps=200, seed=0):
    """Lemma 3, numerically. Source x[t+1] = a x[t] + N(0, 1); target
    y[t+1] = 0.5 y[t] + w * relu(x[t] - theta) + N(0, sigma^2). The best watcher knows the
    form and estimates w by least squares (the MLE). Returns the efficient Fisher information
    for w per recording (averaged), the predicted SD 1 / sqrt(info), the
    empirical SD of the estimates, and the fraction of frames the link is active."""
    rng = np.random.default_rng(seed)
    est, info, act = [], [], []
    for _ in range(reps):
        x = np.zeros(T + 1)
        e = rng.standard_normal(T + 1)
        for t in range(T):
            x[t + 1] = a * x[t] + e[t]
        g = np.maximum(x[:-1] - theta, 0)
        y = np.zeros(T + 1)
        n = sigma * rng.standard_normal(T + 1)
        for t in range(T):
            y[t + 1] = 0.5 * y[t] + w * g[t] + n[t]
        X = np.column_stack([y[:-1], g])
        # efficient information for w: the target's own memory is estimated too, and its
        # regressor is correlated with the link's input
        XtX = X.T @ X
        I = 0.0 if (g ** 2).sum() == 0 else 1.0 / (np.linalg.inv(XtX)[1, 1] * sigma ** 2)
        info.append(I)
        act.append(float((g > 0).mean()))
        if I > 0:
            est.append(np.linalg.lstsq(X, y[1:], rcond=None)[0][1])
    info = float(np.mean(info))
    return {"info": info, "pred_sd": 1 / np.sqrt(info) if info > 0 else np.inf,
            "emp_sd": float(np.std(est)) if len(est) > 2 else np.inf,
            "active": float(np.mean(act)), "estimable": len(est) / reps}
