import numpy as np

from nematica.data.pumpprobe import PumpProbe, neuron_class
from nematica.gallery import LinearRest, RandomNet
from nematica.score import CopyAdapter


def worms(n=6, T=500):
    rng = np.random.default_rng(0)
    names = ["AVAL", "AVBL", "ASHL", "RIML", "AIBL"]
    out = []
    for k in range(n):
        x = np.cumsum(rng.standard_normal((len(names), T)), axis=1) * 0.1 + rng.standard_normal((len(names), T))
        out.append(PumpProbe(uid=f"w{k}", x=x, names=names, classes=[neuron_class(m) for m in names],
                             stims=[(2, 100), (0, 300)], all_stim_frames=[100, 300]))
    return out


def test_random_net_keeps_statistics_and_shuffles_wiring():
    ws = worms()
    a, r = LinearRest(), RandomNet(seed=1)
    a.fit(ws)
    r.fit(ws)
    off = ~np.eye(len(a.A), dtype=bool)
    np.testing.assert_allclose(np.diag(r.A) / np.diag(a.A), np.diag(r.A)[0] / np.diag(a.A)[0])   # one rescale
    assert np.isclose(np.abs(np.linalg.eigvals(r.A)).max(), np.abs(np.linalg.eigvals(a.A)).max())
    assert not np.allclose(r.A[off], a.A[off])
    np.testing.assert_allclose(np.sort(np.abs(r.A[off])) / np.sort(np.abs(a.A[off])),
                               (np.abs(r.A[off]).sum() / np.abs(a.A[off]).sum()), rtol=1e-6)


def test_gallery_copy_runs_through_adapter():
    ws = worms()
    m = CopyAdapter(RandomNet()).fit(ws[:4], ws[4:5])
    sim = m.simulate(ws[5], np.random.default_rng(0))
    assert sim.x.shape == (5, 500) and sim.stims == [(2, 100), (0, 300)]
