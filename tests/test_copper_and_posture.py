"""Tests for label rebuilding, posture reconstruction and (if present) the real copper files."""

import json
import os
from pathlib import Path

import numpy as np
import pytest

from nematica.data import load_copper_dir, rebuild_label
from nematica.data.posture import body_length_mm, centreline, valid_segments


@pytest.mark.parametrize("cls,lr,dv,expected", [
    ("AVA", "L", "undefined", "AVAL"),
    ("SMB", "R", "V", "SMBVR"),
    ("CEP", "L", "D", "CEPDL"),
    ("AQR", "undefined", "undefined", "AQR"),
    ("SIA", "L", "missing", "SIA?L"),
    ("SIA", "missing", "missing", "SIA??"),
    ("AIA", "missing", "undefined", "AIA?"),
])
def test_rebuild_label(cls, lr, dv, expected):
    assert rebuild_label(cls, lr, dv) == expected


ATANAS = Path(os.environ.get("NEMATICA_ATANAS_DIR", "data/raw/atanas2023_wwweb"))


@pytest.mark.skipif(not any(ATANAS.glob("*.json")), reason="Atanas JSON not present")
def test_rebuild_rule_matches_every_atanas_label():
    total = mismatches = 0
    for f in ATANAS.glob("*.json"):
        for v in json.loads(f.read_text())["labeled"].values():
            total += 1
            mismatches += rebuild_label(v["neuron_class"], v["LR"], v["DV"]) != v["label"]
    assert total > 2000 and mismatches == 0


def test_centreline_straight_and_curved():
    seg = np.full(62, np.nan)
    seg[:50] = 0.0
    pts = centreline(seg, 0.0177)
    assert valid_segments(seg) == 50
    assert pts.shape == (51, 2)
    assert pts[-1, 0] == pytest.approx(50 * 0.0177) and abs(pts[-1, 1]) < 1e-12
    assert body_length_mm(seg, 0.0177) == pytest.approx(0.885)
    seg[:50] = np.linspace(0, np.pi, 50)          # half circle
    end = centreline(seg, 0.0177)[-1]
    assert np.hypot(*end) < 50 * 0.0177           # curling shortens end-to-end distance


COPPER = Path(os.environ.get("NEMATICA_COPPER_DIR", "data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415"))


@pytest.mark.skipif(not any(COPPER.glob("*-cudata.h5")), reason="copper files not present")
def test_real_copper_files_load():
    recs = load_copper_dir(COPPER)
    assert len(recs) == 27
    for r in recs:
        assert r.n_frames == 1600
        assert 0.55 < r.frame_interval < 0.65
        assert np.all(np.diff(r.t) > 0)
        seg = r.posture["segment_angle"]
        assert seg.shape[0] == 1600                      # width = longest tracked body, NaN-padded
        typical = np.median([valid_segments(seg[t]) for t in range(r.n_frames)])
        assert 35 <= typical <= 60, (r.uid, typical)     # about 0.6 to 1.1 mm at 17.7 um
        assert len(r.labelled()) > 40, r.uid
        assert all(0 <= a <= b < r.n_frames for a, b in r.reversals)


@pytest.mark.skipif(not any(COPPER.glob("*-cudata.h5")), reason="copper files not present")
def test_motion_matched_body_follows_generated_behaviour():
    """A body assembled from real postures must move at the generated velocity, mostly
    continue real clips, and not spin: whole-body turning per frame like a real worm's."""
    from nematica.export.virtual_worm import MotionLibrary
    recs = load_copper_dir(COPPER)[:6]
    lib = MotionLibrary.from_recordings(recs[:5])
    r = recs[5]
    v, rev, t = r.behaviour["velocity"][:400], r.behaviour["reversing"][:400], r.t[:400]
    ang, path, cont = lib.synthesize(v, rev, t, seed=0)
    assert ang.shape == (400, lib.shapes.shape[1]) and np.isfinite(ang).all()
    step = np.hypot(*np.diff(path, axis=0).T)
    assert np.allclose(step, np.abs(v[:-1]) * np.diff(t), atol=1e-9)
    assert cont > 0.5
    orient = np.angle(np.mean(np.exp(1j * ang), axis=1))
    turn = np.abs(np.angle(np.exp(1j * np.diff(orient))))
    assert np.percentile(turn, 95) < 0.6                      # no spinning with head sweeps


@pytest.mark.skipif(not any(COPPER.glob("*-cudata.h5")), reason="copper files not present")
def test_closed_loop_worm_runs_in_its_arena():
    from nematica.bench import from_recording
    from nematica.data.canonical import canonical_classes
    from nematica.export.virtual_worm import MotionLibrary
    from nematica.systems.closed_loop import SensoryVAR
    recs = load_copper_dir(COPPER)[:7]
    classes = tuple(canonical_classes(recs, 0.25))
    S = [from_recording(r, classes) for r in recs]
    lib = MotionLibrary.from_recordings(recs[:5])
    m = SensoryVAR(senses=True, hazard_from="none").fit(S[:5], S[5:6])
    r = recs[6]
    smp, ang, path, cont = m.simulate(S[6], r.meta["arena"]["radius_mm"], 2.0, lib,
                                      np.random.default_rng(0), 0, r.t, burn=50)
    d = smp.behaviour["dist_to_boundary"]
    assert len(d) == S[6].x.shape[1] and np.isfinite(d).all()
    assert np.allclose(d, r.meta["arena"]["radius_mm"] - np.hypot(*path.T))
    assert set(np.unique(smp.behaviour["reversing"])) <= {0.0, 1.0}
