"""Tests for the benchmark ruler on synthetic data with known structure."""

import numpy as np
import pytest

from nematica.bench import BenchSample, build_reference, score_system
from nematica.bench.calib import frame_shuffle, independent_shift
from nematica.bench.levels import half_decay_time, l2_correlation, participation_ratio
from nematica.data.canonical import zscore_rows

C, T, DT = 20, 1600, 0.6


def synthetic_worm(seed, tau_s=8.0, n_modes=3):
    """Neurons driven by a few shared slow modes plus private noise."""
    rng = np.random.default_rng(seed)
    a = np.exp(-DT / tau_s)
    modes = np.zeros((n_modes, T))
    for t in range(1, T):
        modes[:, t] = a * modes[:, t - 1] + rng.standard_normal(n_modes) * np.sqrt(1 - a * a)
    mixing = np.random.default_rng(0).normal(size=(C, n_modes))   # same "wiring" in every worm
    x = mixing @ modes + 0.5 * rng.standard_normal((C, T))
    x = np.exp(0.6 * x)                                         # skewed, calcium-like
    x[rng.choice(C, 2, replace=False)] = np.nan                  # a couple of unlabelled classes
    return BenchSample(f"real:w{seed}", tuple(f"N{i}" for i in range(C)), zscore_rows(x), DT, origin=f"w{seed}")


def test_half_decay_time_matches_ar1():
    rng = np.random.default_rng(1)
    tau = 10.0
    a = np.exp(-DT / tau)
    x = np.zeros(20000)
    for t in range(1, x.size):
        x[t] = a * x[t - 1] + rng.standard_normal()
    # acf = a^k, falls to 0.5 at k = ln 0.5 / ln a -> time = tau * ln 2
    assert half_decay_time(x, DT, max_lag_s=200) == pytest.approx(tau * np.log(2), rel=0.1)


def test_participation_ratio_bounds():
    rng = np.random.default_rng(2)
    assert participation_ratio(rng.standard_normal((10, 5000))) == pytest.approx(10, rel=0.1)
    one = np.outer(np.ones(10), rng.standard_normal(5000))
    assert participation_ratio(one + 1e-6 * rng.standard_normal((10, 5000))) == pytest.approx(1, abs=0.05)


def test_same_wiring_gives_similar_correlations():
    a, b = synthetic_worm(1), synthetic_worm(2)
    assert l2_correlation(a, b) < 0.3


def test_ruler_separates_calibration_systems():
    real = [synthetic_worm(s) for s in range(1, 7)]
    ref = build_reference(real)
    held_out = [synthetic_worm(s) for s in range(10, 14)]
    rng = np.random.default_rng(5)
    rows = {r["metric"]: r for r in score_system("held_out", held_out, real, ref)}
    assert all(r["verdict"] in ("inside", "not scored") for r in rows.values())
    assert all(rows[m]["verdict"] == "inside" for m in ("L1.distribution", "L1.timescale", "L2.correlation"))
    shifted = {r["metric"]: r for r in score_system("shift", [independent_shift(s, rng) for s in real], real, ref)}
    assert shifted["L2.correlation"]["verdict"] == "outside"
    assert shifted["L1.distribution"]["verdict"] == "inside"
    shuffled = {r["metric"]: r for r in score_system("shuffle", [frame_shuffle(s, rng) for s in real], real, ref)}
    assert shuffled["L1.timescale"]["verdict"] == "outside"
    assert shuffled["L2.correlation"]["verdict"] == "inside"


def test_system_never_compared_with_its_own_source_worm():
    real = [synthetic_worm(s) for s in range(1, 5)]
    ref = build_reference(real)
    rows = score_system("copy", real, real, ref)
    assert rows[0]["n_pairs"] == 4 * 3


def test_population_average_is_flagged_too_typical():
    """A sample with no sampling noise of its own carries the population correlation structure
    exactly; it is closer to every real worm than real worms are to each other."""
    real = [synthetic_worm(s) for s in range(1, 9)]
    ref = build_reference(real)
    global T
    saved, T = T, 40 * T                # same model, 40x longer: correlations ~ exact mean
    try:
        avg = [synthetic_worm(s) for s in range(20, 23)]
    finally:
        T = saved
    rows = {r["metric"]: r for r in score_system("average", avg, real, ref)}
    assert rows["L2.correlation"]["verdict"] == "too typical"
    held_out = {r["metric"]: r for r in score_system("held_out", [synthetic_worm(s) for s in range(30, 34)], real, ref)}
    assert held_out["L2.correlation"]["verdict"] == "inside"


def test_discriminability_separates_shuffled_from_held_out():
    from nematica.bench.discriminability import core_classes, discriminability
    real = [synthetic_worm(s) for s in range(1, 13)]
    core = core_classes(real, n=8)
    held = [synthetic_worm(s) for s in range(40, 46)]
    rng = np.random.default_rng(3)
    ok = discriminability(real, held, core, n_perm=40, seed=1)
    bad = discriminability(real, [frame_shuffle(s, rng) for s in held], core, n_perm=40, seed=1)
    assert ok["verdict"] == "indistinguishable", ok
    assert bad["verdict"] == "distinguishable" and bad["auc"] > 0.9, bad


def arena_worm(seed, respond=True):
    """Synthetic worm that meets the boundary every ~2 min; classes N0-N3 respond after each
    encounter and reversals become likely, the rest follow the shared modes."""
    s = synthetic_worm(seed)
    rng = np.random.default_rng(100 + seed)
    t = np.arange(T) * DT
    d = 2.0 + 1.8 * np.sin(2 * np.pi * t / (110 + 20 * rng.random()) + rng.uniform(0, 6.3))
    d += 0.05 * rng.standard_normal(T)
    x = np.nan_to_num(s.x)
    rev = (rng.random(T) < 0.01).astype(float)
    from nematica.bench.environment import encounters
    probe = BenchSample("p", s.classes, s.x, DT, behaviour={"dist_to_boundary": d})
    w = int(8 / DT)
    for on in encounters(probe):
        if respond:
            x[:4, on:on + w] += np.linspace(2.5, 0, len(x[0, on:on + w]))
        if rng.random() < 0.8:
            rev[on + 3: on + 3 + int(5 / DT)] = 1
    x = np.where(s.observed[:, None], x, np.nan)
    return BenchSample(s.name, s.classes, zscore_rows(x), DT, origin=s.origin,
                       behaviour={"dist_to_boundary": d, "reversing": rev[:T]})



def test_environment_test_detects_broken_coupling():
    from nematica.bench.environment import encounters, environment_test
    real = [arena_worm(s) for s in range(1, 13)]
    assert all(len(encounters(r)) >= 4 for r in real)
    rows = lambda name, f: {r["metric"]: r for r in environment_test(real, f, name, n_partitions=80)}
    shift = rows("shift", lambda A, rng: [independent_shift(s, rng) for s in A])
    assert shift["L6.encounter"]["verdict"] == "outside", shift["L6.encounter"]
    assert shift["L6.approach"]["verdict"] == "inside"
    fresh = rows("fresh", lambda A, rng: [arena_worm(int(s.origin[1:]) + 500) for s in A])
    assert fresh["L6.encounter"]["verdict"] == "inside", fresh["L6.encounter"]
    deaf = rows("deaf", lambda A, rng: [arena_worm(int(s.origin[1:]) + 700, respond=False) for s in A])
    assert deaf["L6.encounter"]["verdict"] == "outside", deaf["L6.encounter"]


def test_folds_are_frozen_disjoint_and_date_spread(tmp_path):
    from nematica.data.splits import load_folds, make_worm_folds, save_folds
    uids = [f"2023-0{m}-1{d}-0{s}" for m in (1, 2, 3) for d in (0, 1, 2) for s in (1, 2)]
    doc = make_worm_folds(uids, 3, seed=0)
    assert sorted(u for f in doc["folds"] for u in f) == sorted(uids)
    assert all(len({u[:10] for u in f}) >= 4 for f in doc["folds"])     # dates spread
    p = tmp_path / "f.yaml"
    save_folds(doc, p, "x")
    assert load_folds(p)["folds"] == doc["folds"]
    import pytest
    with pytest.raises(FileExistsError):
        save_folds(doc, p, "x")


def test_combined_folds_separate_good_from_broken():
    from nematica.bench import combine_folds
    pools = [[synthetic_worm(s) for s in range(10 * f, 10 * f + 6)] for f in (1, 2, 3)]
    good, bad = [], []
    rng = np.random.default_rng(1)
    for f, pool in enumerate(pools):
        ref = build_reference(pool)
        good.append(score_system("held", [synthetic_worm(100 + 10 * f + i) for i in range(4)], pool, ref,
                                 return_boot=True))
        bad.append(score_system("shuffle", [frame_shuffle(s, rng) for s in pool], pool, ref, return_boot=True))
    g = {r["metric"]: r for r in combine_folds(good)}
    b = {r["metric"]: r for r in combine_folds(bad)}
    assert g["L2.correlation"]["verdict"] == "inside"
    assert b["L1.timescale"]["verdict"] == "outside"
    assert b["L1.timescale"]["folds"] == "outside/outside/outside"
