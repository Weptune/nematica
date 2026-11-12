"""Unit tests for the map study (docs/MAP.md, amendment 4, F17)."""
import numpy as np
import pytest

from nematica.map import analysis as An, instrument as I, measures as M, recording as R, synthetic
from nematica.map.data import bin_spikes


def _ar(T, N, tau, rng):
    a = 0.5 ** (1 / tau)
    x = np.zeros((T, N))
    e = rng.standard_normal((T, N))
    for t in range(1, T):
        x[t] = a * x[t - 1] + e[t]
    return x


# ---------------------------------------------------------------- estimators
@pytest.mark.parametrize("tau", [2.0, 8.0])
@pytest.mark.parametrize("share", [0.0, 0.5])
def test_timescale_and_noise_recovered_on_ar(tau, share):
    rng = np.random.default_rng(0)
    X = _ar(20000, 10, tau, rng)
    Y = X + rng.standard_normal(X.shape) * X.std(0) * np.sqrt(share / (1 - share)) if share else X
    assert abs(M.tau_med(Y) - tau) / tau < 0.1
    assert abs(np.median(M.noise_fraction(Y)) - share) < 0.04


def test_noise_share_on_poisson_counts():
    rng = np.random.default_rng(1)
    lam = np.exp(_ar(20000, 10, 6.0, rng) * 0.4) * 0.5
    C = rng.poisson(lam).astype(float)
    # true white share: Poisson variance (mean) over total variance
    true = np.median(lam.mean(0) / C.var(0))
    assert abs(np.median(M.noise_fraction(C)) - true) < 0.05


def test_segments_do_not_cross():
    rng = np.random.default_rng(2)
    a, b = _ar(5000, 6, 4.0, rng), _ar(5000, 6, 4.0, rng) + 50.0     # an offset between segments
    X = np.vstack([a, b])
    assert abs(M.tau_med(X, segments=[5000]) - 4.0) < 0.5
    assert M.tau_med(X) > 10                              # without segments the jump looks slow


def test_disattenuated_sparsity_is_noise_invariant():
    X = synthetic.population(np.random.default_rng(3), N=60, power=1.6)
    rng = np.random.default_rng(0)
    clean = M.sparsity(X)
    noisy = M.sparsity(X + rng.standard_normal(X.shape) * X.std(0) * 0.6)
    assert abs(noisy - clean) / abs(clean) < 0.2


def test_split_half_se_uses_time_halves_when_few_units():
    X = synthetic.population(np.random.default_rng(4), N=60, T=6000)
    se = M.split_half_se(X, n_splits=2, n_draws=4)
    assert set(se) == set(M.MEASURES)
    assert np.isfinite(se["shared_fraction"])


# ---------------------------------------------------------------- recording and matching
def test_segment_aware_recording_returns_starts():
    A = synthetic.population(np.random.default_rng(5), N=20, T=2000)
    Y, starts = R.record_matched(A, "calcium", dict(decay=4, frame=2, snr=5, hold=2), segments=[1000],
                                 rng=np.random.default_rng(0))
    assert len(starts) == 1 and 0 < starts[0] < len(Y)


@pytest.mark.parametrize("rt,prep", [
    ("calcium", dict(decay_over_tau=0.5, frames_per_tau=3, noise=0.6)),
    ("spikes", dict(bins_per_tau=10, count_per_bin=0.1, noise=0.97)),
])
def test_matching_reaches_realistic_targets_for_slow_networks(rt, prep):
    A = synthetic.population(np.random.default_rng(1), N=200, T=12000, tau_fast=30, tau_slow=300)
    f = R.match_calcium if rt == "calcium" else R.match_spikes
    assert f(A, prep)["reached"]


def test_hold_factor_is_target_aware():
    assert R.hold_factor(2.0, 10) == 10
    assert R.hold_factor(100.0, 10) == 1
    assert R.hold_factor(np.nan, 10) == 1


# ---------------------------------------------------------------- instrument numbers
def test_instrument_numbers_spikes_require_20ms_bins():
    X = (np.random.default_rng(0).random((3000, 20)) < 0.1).astype(float)
    assert "error" in I.instrument_numbers({"activity": X, "dt": 0.05}, "spikes")
    out = I.instrument_numbers({"activity": X, "dt": 0.02}, "spikes")
    assert set(out) >= {"bins_per_tau", "count_per_bin", "noise"}
    assert not any(k.startswith("tau_") and isinstance(v, (list, np.ndarray)) for k, v in out.items())


def test_bin_spikes():
    X = bin_spikes([[0.01, 0.03, 0.031], [0.5]], 1.0)
    assert X.shape == (50, 2) and X[0, 0] == 1 and X[1, 0] == 2 and X[25, 1] == 1


# ---------------------------------------------------------------- analysis
def _prep(i, sp, vals, rng, n=4):
    return {"id": f"p{i}", "kind": "real", "dataset": f"d{i}", "species_type": sp,
            "individuals": [{m: v + 0.1 * rng.standard_normal() for m, v in vals.items()} for _ in range(n)],
            "se": {m: 0.01 for m in vals}}


def _ai(i, vals, preps, rng, role="standard", fam=None, nrep=20):
    at = {}
    for p in preps:
        reps = [{m: v + 0.02 * rng.standard_normal() for m, v in vals.items()} for _ in range(nrep)]
        at[p["id"]] = {"values": {m: float(np.mean([r[m] for r in reps])) for m in vals}, "replicates": reps,
                       "reached": True, "budget": {m: 0.01 for m in vals}}
    return {"id": f"a{i}", "kind": "ai", "family": fam or f"f{i}", "role": role, "at": at}


@pytest.fixture
def world():
    rng = np.random.default_rng(0)
    ms = ["shared_fraction", "coupling_spread", "sparsity"]
    preps = [_prep(i, f"s{i}", {m: 0.3 * i for m in ms}, rng) for i in range(5)]
    ais = [_ai(i, {m: 5 + 0.3 * i for m in ms}, preps, rng) for i in range(4)]
    return preps, ais, ms


def test_h1_separated_world(world):
    preps, ais, ms = world
    B = An.bvu(preps, ms)
    use, why = An.usable_measures(preps, ais, ms, B)
    assert use == ms, why
    r = An.h1(preps, ais, use, B)
    assert r["powered"] and r["holds"]


def test_missing_se_or_budget_fails(world):
    preps, ais, ms = world
    B = An.bvu(preps, ms)
    del preps[0]["se"]["sparsity"]
    del ais[0]["at"]["p1"]["budget"]["coupling_spread"]
    use, why = An.usable_measures(preps, ais, ms, B)
    assert "sparsity" not in use and "coupling_spread" not in use


def test_augmented_is_not_sibling_of_base(world):
    preps, ais, ms = world
    aug = {**ais[0], "id": "aug", "role": "augmented"}
    assert not An.siblings(aug, ais[0])
    assert An.siblings({**ais[0], "id": "x"}, ais[0])


def test_h2_needs_distance_within_real_spread(world):
    preps, ais, ms = world
    rng = np.random.default_rng(1)
    near = _ai(9, {m: 0.6 for m in ms}, preps, rng, role="augmented", fam="f0")
    far = _ai(8, {m: 3.0 for m in ms}, preps, rng, role="augmented", fam="f1")
    B = An.bvu(preps, ms)
    r = An.h2(preps, ais + [near, far], ms, B)
    assert r["candidates"]["a9"]["passes"] and not r["candidates"]["a8"]["passes"]


def test_bootstrap_decides_and_needs_replicates(world):
    preps, ais, ms = world
    B = An.bvu(preps, ms)
    rng = np.random.default_rng(3)
    big, small = _ai(5, {m: 0.7 for m in ms}, preps, rng), _ai(6, {m: 1.2 for m in ms}, preps, rng)
    r = An.h4(preps, big, small, ms, B)           # big is about 5 BVU closer to the brains: H4 fails
    assert r["decided"] and r["holds"] is False
    few = _ai(7, {m: 5.0 for m in ms}, preps, np.random.default_rng(2), nrep=5)
    assert not An.h6(preps, few, ais[0], ms, B)["decided"]


def test_h8_and_robust(world):
    preps, ais, ms = world
    B = An.bvu(preps, ms)
    assert An.h8(preps, ais, ["p0", "missing"], ms, B) == {"p0": True, "missing": None}
    assert An.robust({"floor 2": True, "floor 4": True}) is True
    assert An.robust({"floor 2": True, "floor 4": False}) is None
    assert An.robust({"floor 2": True, "floor 4": None}) is None


# ---------------------------------------------------------------- amendment 5
def test_every_rest_stretch_counts():
    rng = np.random.default_rng(7)
    X = np.vstack([_ar(3000, 10, 8.0, rng)] + [_ar(2900, 10, 2.0, rng) for _ in range(9)])
    seg = [3000 + 2900 * i for i in range(9)]
    assert M.tau_med(X, segments=seg) < 3.5          # the nine short stretches dominate (longest alone: 8)


def test_noise_share_on_calcium_shaped_signals():
    A = synthetic.population(np.random.default_rng(1), N=40, T=20000)
    rng = np.random.default_rng(2)
    for decay in (0.3, 1.1, 3.0, 8.0):
        F = R.calcium(A, decay=decay, frame=1, snr=1e9)
        for share in (0.1, 0.3):
            Y = F + rng.standard_normal(F.shape) * F.std(0) * np.sqrt(share / (1 - share))
            assert abs(np.median(M.noise_fraction(Y)) - share) < 0.04


def test_detrend_removes_bleaching():
    rng = np.random.default_rng(3)
    X = _ar(5000, 10, 4.0, rng) + np.linspace(20, 0, 5000)[:, None]
    assert abs(M.tau_med(M.detrend(X)) - 4.0) < 0.5


def test_match_with_segments_reaches():
    A = synthetic.population(np.random.default_rng(4), N=100, T=8000)
    k = R.match(A, "calcium", dict(decay_over_tau=0.3, frames_per_tau=4, noise=0.3), segments=[2000, 4000, 6000])
    assert k["reached"]
