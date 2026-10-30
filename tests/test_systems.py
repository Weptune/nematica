"""Tests for the systems under test and the imaging model."""

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from nematica.bench import BenchSample
from nematica.data.canonical import zscore_rows
from nematica.forward.imaging import ImagingParams, first_order, image, sample_frames
from nematica.systems.baselines import IndependentAR, JointVAR
from nematica.systems.kunert import KunertModel


def test_kunert_matches_lsoda():
    m = KunertModel.load()
    n = m.n
    I = np.zeros(n)
    I[m.names.index("PLML")] = I[m.names.index("PLMR")] = 0.5
    rng = np.random.default_rng(0)
    v0, s0 = m.Vth + rng.uniform(-1, 1, n), rng.uniform(0, 0.1, n)

    def rhs(t, y):
        dV, dS = m.rhs(y[:n], y[n:], I)
        return np.concatenate([dV, dS])

    ts = np.arange(0, 10, 0.05)
    ref = solve_ivp(rhs, (0, 10), np.concatenate([v0, s0]), method="LSODA", t_eval=ts,
                    atol=1e-6, rtol=1e-7).y[:n] - m.Vth[:, None]
    _, V = m.simulate(10, dt=0.01, drive=lambda t: I, v0=v0, s0=s0)
    L = min(V.shape[1], ref.shape[1])
    err = np.abs(V[:, 20:L] - ref[:, 20:L])          # skip the first second of transient
    assert np.percentile(err, 99) < 0.01


def test_imaging_pipeline_shapes_and_mask():
    t_src = np.arange(0, 100, 0.05)
    drive = np.vstack([np.sin(t_src / 5) + 1.5, np.cos(t_src / 3) + 1.5, np.full_like(t_src, np.nan)])
    t_frames = np.arange(0, 96, 0.6)
    template = BenchSample("tpl", ("A", "B", "C"), np.vstack([np.ones(len(t_frames)), np.full(len(t_frames), np.nan),
                                                            np.ones(len(t_frames))]), 0.6)
    s = image("x", ("A", "B", "C"), drive, t_src, template, t_frames, ImagingParams(), np.random.default_rng(0))
    assert s.x.shape == (3, len(t_frames))
    assert s.observed.tolist() == [True, False, False]    # B masked by template, C not simulated


def test_first_order_and_sampling():
    x = np.zeros((1, 1000)); x[0, 100:] = 1.0
    y = first_order(x, 0.01, 0.5)
    assert y[0, 150] == pytest.approx(1 - np.exp(-0.5 / 0.5), rel=0.05)
    t = np.arange(1000) * 0.01
    f = sample_frames(np.vstack([t]), t, np.array([1.0, 5.0]), 0.6)
    assert f[0] == pytest.approx([1.0, 5.0], abs=0.02)


def _worm(seed, T=1200):
    rng = np.random.default_rng(seed)
    z = np.zeros((10, T))
    for t in range(1, T):
        z[:, t] = 0.9 * z[:, t - 1] + rng.standard_normal(10)
    vel = z[0] * 0.01 + 0.05
    rev = (z[1] > 1.5).astype(float)
    return BenchSample(f"w{seed}", tuple(f"N{i}" for i in range(10)), zscore_rows(z), 0.6, origin=f"w{seed}",
                       behaviour={"velocity": vel, "reversing": rev})


def test_baselines_generate_full_recordings():
    train = [_worm(s) for s in range(4)]
    ar, var = IndependentAR.fit(train), JointVAR.fit(train)
    rng = np.random.default_rng(1)
    a, v = ar.generate(train[0], rng), var.generate(train[0], rng)
    assert a.x.shape == v.x.shape == train[0].x.shape
    assert np.isfinite(a.x).all() and np.isfinite(v.x).all()
    assert set(v.behaviour) == {"velocity", "reversing"}
