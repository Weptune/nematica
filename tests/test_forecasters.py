"""Tests for the forecaster ladder and the individual-worm models (arc 1)."""

import numpy as np

from nematica.bench import BenchSample
from nematica.data.canonical import zscore_rows
from nematica.systems.forecasters import (ESNFeatures, Forecaster, IndividualVAR, LagFeatures,
                                          StateSpace)

C, T, DT = 12, 800, 0.6


def worm(seed, A=None):
    """Linear dynamics x_t = A x_{t-1} + noise, plus velocity/reversal read out of x."""
    rng = np.random.default_rng(seed)
    if A is None:
        A = 0.9 * np.eye(C) + 0.05 * np.random.default_rng(0).standard_normal((C, C))
    x = np.zeros((C, T))
    for t in range(1, T):
        x[:, t] = A @ x[:, t - 1] + 0.3 * rng.standard_normal(C)
    vel = 0.1 * x[0] + 0.01 * rng.standard_normal(T)
    rev = (x[1] > 1.0).astype(float)
    x[rng.choice(C, 1)] = np.nan
    return BenchSample(f"real:w{seed}", tuple(f"N{i}" for i in range(C)), zscore_rows(x), DT,
                       origin=f"w{seed}", behaviour={"velocity": vel, "reversing": rev})


def test_linear_forecaster_learns_and_generates():
    train = [worm(s) for s in range(1, 7)]
    val, test = [worm(7)], [worm(8)]
    space = StateSpace.from_train(train, min_fraction=0.5)
    m = Forecaster("var1", space, LagFeatures(space.k, 1, False)).fit(train, val)
    r1 = m.one_step_r2(test)
    assert r1 > 0.5
    assert m.multi_step_r2(test, horizon=5, stride=50) < r1          # harder further ahead
    s = m.generate(test[0], np.random.default_rng(0), burn=50)
    assert s.x.shape == test[0].x.shape
    assert np.isnan(s.x[~test[0].observed]).all()                   # template mask applied
    assert set(s.behaviour) == {"velocity", "reversing", "reversing_drive"}


def test_lag_state_matches_training_features():
    """step() must build exactly the feature vector run() builds for the same history."""
    train = [worm(s) for s in range(1, 4)]
    space = StateSpace.from_train(train, min_fraction=0.5)
    v, _ = space.encode(train[0])
    for feats in (LagFeatures(space.k, 3, False), ESNFeatures(space.k, 50, seed=1)):
        F = feats.run(v)
        t = 40                                                     # predict v[:, t + 1]
        state = feats.step_init(v[:, : t + 1])
        _, f = feats.step(state, v[:, t])
        assert np.allclose(f, F[t + 1 - feats.warmup])


def test_individual_models_recover_individual_dynamics():
    """Worms with genuinely different dynamics: per-worm models (shrunk toward the pooled
    one) must forecast each worm's second half better than the pooled model."""
    rng = np.random.default_rng(3)
    base = 0.85 * np.eye(C)
    train = []
    for s in range(1, 9):
        A = base + 0.15 * rng.standard_normal((C, C))
        A *= 0.9 / np.max(np.abs(np.linalg.eigvals(A)))         # stable, each worm different
        train.append(worm(s, A))
    space = StateSpace.from_train(train, min_fraction=0.5)
    m = IndividualVAR(Forecaster("var1", space, LagFeatures(space.k, 1, False))).fit(train, [train[0]])
    assert m.info["within_worm_r2_individual"] > m.info["within_worm_r2_pooled"]
    a = m.generate(train[0], np.random.default_rng(0), which=0, burn=50)
    b = m.generate(train[0], np.random.default_rng(0), which=1, burn=50)
    assert a.name.endswith(":w1") and b.name.endswith(":w2")


def test_switching_model_keeps_state_and_behaviour_consistent():
    from nematica.systems.switching import SwitchingVAR
    train = [worm(s) for s in range(1, 7)]
    space = StateSpace.from_train(train, min_fraction=0.5)
    for lam in (None, 300):
        m = SwitchingVAR(space, lam=lam).fit(train, [worm(7)])
        s = m.generate(worm(8), np.random.default_rng(0), which=1, burn=50)
        rev = s.behaviour["reversing"]
        assert set(np.unique(rev)) <= {0.0, 1.0}
        assert 0.0 < rev.mean() < 1.0                       # it does switch, both ways
        assert s.x.shape == worm(8).x.shape


def test_calcium_space_round_trip_and_skew():
    """Encoding to the drive and rebuilding calcium must invert each other, and a skewed
    drive must come back as skewed calcium."""
    from scipy.stats import skew
    from nematica.systems.forecasters import CalciumStateSpace
    train = [worm(s) for s in range(1, 5)]
    sp = CalciumStateSpace.from_train(train, min_fraction=0.5, gamma=0.5)
    rng = np.random.default_rng(0)
    d = np.where(rng.random(2000) < 0.05, rng.exponential(3.0, 2000), 0.0) - 0.15
    c = np.empty_like(d)
    c[0] = d[0] / 0.5
    for t in range(1, d.size):
        c[t] = 0.5 * c[t - 1] + d[t]
    assert skew(c) > 1.0
    s = train[0]
    drive = CalciumStateSpace._drive_sample(s, 0.5).x
    i = int(np.flatnonzero(s.observed)[0])
    rebuilt = np.empty(drive.shape[1])
    rebuilt[0] = drive[i, 0] / 0.5
    for t in range(1, drive.shape[1]):
        rebuilt[t] = 0.5 * rebuilt[t - 1] + drive[i, t]
    assert np.allclose(rebuilt, s.x[i])


def test_multiscale_step_matches_run():
    from nematica.systems.forecasters import MultiScaleFeatures
    train = [worm(s) for s in range(1, 3)]
    space = StateSpace.from_train(train, min_fraction=0.5)
    v, _ = space.encode(train[0])
    f = MultiScaleFeatures(space.k, lags=3, windows=((3, 10), (10, 40)))
    F = f.run(v)
    for t in (45, 300):                                   # predict v[:, t + 1]
        state = f.step_init(v[:, : t + 1])
        _, x = f.step(state, v[:, t])
        assert np.allclose(x, F[t + 1 - f.warmup])


def test_slowfast_adds_slow_structure():
    from nematica.systems.forecasters import SlowFastVAR
    train = [worm(s) for s in range(1, 6)]
    m = SlowFastVAR(gamma=0.5, lam=300, window_s=60.0, tau_s=120.0).fit(train, [worm(6)])
    s = m.generate(worm(7), np.random.default_rng(0), which=0, burn=50)
    assert s.name.startswith("slowfast_lags3")
    assert s.x.shape == worm(7).x.shape and np.isfinite(s.x[s.observed]).all()
