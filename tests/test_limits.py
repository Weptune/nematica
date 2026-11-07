import numpy as np

from nematica import limits as L


def _expected_loss(net0, net, ws, wts):
    S0 = L.spectrum(net0, ws)
    S = L.spectrum(net, ws)
    tot = 0.0
    for a, b, w in zip(S, S0, wts):
        sign, ld = np.linalg.slogdet(a)
        tot += w * (ld + np.trace(np.linalg.solve(a, b)).real)
    return tot


def test_fisher_matches_hessian():
    net = L.random_net(n=4, k=1, seed=1)
    m = 64
    I, (fidx, qidx) = L.fisher(net, T=2.0, m=m)          # T=2 gives T/2 = 1: per-unit Hessian scale
    ws = np.pi * np.arange(m + 1) / m
    wts = np.full(m + 1, 2.0)
    wts[0] = wts[-1] = 1.0
    wts /= 2 * m

    def setp(theta):
        F = net.F.copy()
        F[fidx[:, 0], fidx[:, 1]] = theta[:len(fidx)]
        q = net.q.copy()
        q[qidx] = theta[len(fidx):len(fidx) + len(qidx)]
        r = theta[len(fidx) + len(qidx):]
        return L.LGNet(F=F, q=q, r=r, n=net.n)

    th0 = np.concatenate([net.F[fidx[:, 0], fidx[:, 1]], net.q[qidx], net.r])
    rng = np.random.default_rng(0)
    for _ in range(6):
        a, b = rng.integers(len(th0), size=2)
        h = 1e-4
        def f(da, db):
            t = th0.copy()
            t[a] += da
            t[b] += db
            return _expected_loss(net, setp(t), ws, wts)
        hess = (f(h, h) - f(h, -h) - f(-h, h) + f(-h, -h)) / (4 * h * h)
        # at T = 2 the Fisher information equals the Hessian of the expected Whittle loss
        assert np.isclose(hess, I[a, b], rtol=1e-2, atol=1e-7), (a, b, hess, I[a, b])


def test_shared_noise_twin_same_spectrum_different_poke():
    net = L.random_net(n=6, k=2, seed=3)
    rng = np.random.default_rng(1)
    M = 0.5 * rng.standard_normal((2, 6))
    tw = L.shared_noise_twin(net, M)
    ws = np.linspace(0, np.pi, 50)
    assert np.allclose(L.spectrum(net, ws), L.spectrum(tw, ws), atol=1e-9)
    G1 = L.poke_response(net.F, 6)
    G2 = L.poke_response(tw.F, 6)
    Gh = L.poke_response_hidden(net.F, 6)
    assert np.allclose(G2, G1 - Gh @ M, atol=1e-9)
    assert np.abs(G2 - G1).max() > 0.1


def test_private_noise_identifiable_up_to_hidden_rotation():
    for k in (1, 2, 3):
        net = L.random_net(n=6, k=k, seed=2)
        I, lay = L.fisher(net, T=1000, m=128)
        ev = np.linalg.eigvalsh(I)
        nnull = int((ev < 1e-10 * ev[-1]).sum())
        assert nnull == k * (k - 1) // 2
        N = L.gauge_tangents(net, lay)
        if len(N):
            assert np.abs(I @ N.T).max() < 1e-8 * ev[-1]       # the gauge is the null space
        cov, info = L.crb_G(net, T=1000, m=128)
        assert info["leak"] < 1e-8 and info["cond"] > 1e-9


def test_silent_link_information_scales_with_activity():
    lo = L.silent_link_demo(theta=1.0, T=2000, reps=60, seed=1)
    hi = L.silent_link_demo(theta=4.0, T=2000, reps=60, seed=2)
    # the error follows the Fisher prediction (within sampling noise of 60 replicates)
    assert 0.7 < lo["emp_sd"] / lo["pred_sd"] < 1.4
    # a link active on fewer frames carries less information, so a larger error
    assert hi["active"] < lo["active"] and hi["pred_sd"] > 3 * lo["pred_sd"]
    # a link that never fires at rest: no information at any length
    never = L.silent_link_demo(theta=50.0, T=2000, reps=5, seed=3)
    assert never["info"] == 0 and never["estimable"] == 0
