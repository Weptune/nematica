"""Tests for the swarm engine (arc 6)."""

from pathlib import Path

import numpy as np
import pytest

from nematica.swarm.engine import SwarmRun, _body_links, _min_dist_to_others, start_positions
from nematica.swarm.metrics import _components, _onsets, rate_by_density, swarm_summary

COPPER = Path(__file__).resolve().parents[1] / "data" / "raw" / "doi_10_5061_dryad_w9ghx3g4v__v20260415"


def _line(x0, y0, n=5, step=0.2):
    return np.array([[x0 + i * step, y0] for i in range(n)])


def test_min_distance_ignores_own_body():
    bodies = np.vstack([_line(0, 0), _line(0, 1)])
    owner = np.repeat([0, 1], 5)
    heads = np.array([[0.0, 0.0], [0.0, 1.0]])
    d = _min_dist_to_others(heads, bodies, owner, 2)
    assert np.allclose(d, [1.0, 1.0])


def test_body_links_and_components():
    bodies = np.vstack([_line(0, 0), _line(0, 0.05), _line(0, 3), _line(0, 3.05)])
    links = _body_links(bodies, 4, 0.1)
    assert sorted(links) == [(0, 1), (2, 3)]
    assert sorted(_components(5, links)) == [1, 2, 2]


def test_start_positions_are_inside_and_apart():
    p = start_positions(30, 4.0, np.random.default_rng(0))
    assert np.all(np.hypot(*p.T) <= 3.0 + 1e-9)
    d = np.hypot(p[:, None, 0] - p[None, :, 0], p[:, None, 1] - p[None, :, 1]) + np.eye(30) * 9
    assert d.min() >= 0.5


def _toy_run(states, density):
    n, T = states.shape
    return SwarmRun(heads=np.zeros((n, T, 2)) + np.arange(n)[:, None, None], states=states,
                    touched=np.zeros((n, T), bool), blocked=np.zeros((n, T), bool), density=density,
                    links=[[] for _ in range(T)], dist=np.ones((n, T)), origins=["a"] * n, dt=0.6,
                    radius_mm=4.0)


def test_onsets_and_rate_by_density():
    states = np.zeros((2, 200))
    states[0, 50:55] = 1
    states[0, 100:103] = 1
    assert _onsets(states).sum() == 2
    density = np.zeros((2, 200), int)
    density[0, 80:140] = 2
    r = rate_by_density(_toy_run(states, density))
    assert r["rev_per_min_density_2+"] > r["rev_per_min_density_0"]
    s = swarm_summary(_toy_run(states, density))
    assert s["frac_in_cluster"] == 0 and s["nn_dist_mm"] > 0


@pytest.mark.skipif(not any(COPPER.glob("*-cudata.h5")), reason="copper files not present")
def test_swarm_runs_and_interactions_act():
    from nematica.bench import from_recording
    from nematica.data import load_copper_dir
    from nematica.data.canonical import canonical_classes
    from nematica.export.virtual_worm import MotionLibrary
    from nematica.swarm import average_worm, run_swarm
    from nematica.systems.closed_loop import SensoryVAR
    recs = load_copper_dir(COPPER)[:7]
    classes = tuple(canonical_classes(recs, 0.25))
    S = [from_recording(r, classes) for r in recs]
    lib = MotionLibrary.from_recordings(recs[:5])
    m = SensoryVAR(senses=True, hazard_from="none").fit(S[:5], S[5:6])
    avg = average_worm(m)
    r = recs[6]
    # one worm alone, no interactions: the agent path matches the single-worm simulation API
    smp, ang, path, _ = m.simulate(S[6], 4.0, 2.0, lib, np.random.default_rng(3), 0, r.t, burn=20)
    a = m.agent(S[6], 4.0, 2.0, lib, np.random.default_rng(3), 0, burn=20)
    for i in range(50):
        a.think()
        a.move(float(r.t[i + 1] - r.t[i]))
    assert np.allclose(a.path[:50], path[:50]) and np.allclose(a.angles[:50], ang[:50])
    # a crowded swarm: interactions on refuse moves into other bodies, off never refuse
    origins = [m.names[j % 5] for j in range(14)] + [avg, avg]
    on = run_swarm(m, origins, S[6], lib, 2.0, r.t, np.random.default_rng(1), interact=True, burn=20, n_frames=120)
    off = run_swarm(m, origins, S[6], lib, 2.0, r.t, np.random.default_rng(1), interact=False, burn=20, n_frames=120)
    assert on.heads.shape == (16, 120, 2) and np.isfinite(on.heads).all()
    assert on.blocked.any() and not off.blocked.any()
    assert off.touched.any()
