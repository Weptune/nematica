"""Tests for the optogenetic atlas loader and the causal levels (arc 4)."""

from pathlib import Path

import numpy as np
import pytest

from nematica.bench.causal import (c_kinetics, c_magnitude, c_pattern, permuted_targets, response_set,
                                   score_sets, time_reversed)
from nematica.data.pumpprobe import load_pumpprobe, load_pumpprobe_dir, neuron_class

ATLAS = Path(__file__).resolve().parents[1] / "data" / "raw" / "2025_creamer_lds_npz"


def test_neuron_class_mapping():
    pairs = {"AVAL": "AVA", "RMDVR": "RMD", "RMED": "RME", "SMDDL": "SMD", "IL1VL": "IL1", "VA1": "VA01",
             "AVL": "AVL", "I1L": "I1", "M3R": "M3", "MCL": "MC", "OLQDR": "OLQ", "": ""}
    for name, cls in pairs.items():
        assert neuron_class(name) == cls


def _toy(tmp_path, seed=0, gain=1.0, uid="pumpprobe_20210101_000000"):
    """Six neurons; stimulating A (index 0) drives B up and C down after a short delay."""
    rng = np.random.default_rng(seed)
    T, N = 3000, 6
    x = 50 + rng.standard_normal((T, N)).astype(np.float32)
    # slow spontaneous fluctuations dominate each neuron's SD, as in real recordings
    x += (20 * np.sin(np.arange(T)[:, None] / 300.0 + rng.uniform(0, 6, N))).astype(np.float32)
    names = ["AVAL", "AVBL", "AIBL", "RIML", "SMDDL", "AVEL"]
    stims = np.arange(40, T - 70, 62)
    targets = np.array([0, 3] * (len(stims) // 2) + [0] * (len(stims) % 2))
    for f, k in zip(stims, targets):
        resp = np.exp(-np.arange(61) / 12.0)
        if k == 0:
            x[f + 2:f + 63, 1] += (8 * gain * resp)[:61]
            x[f + 2:f + 63, 2] -= (6 * gain * resp)[:61]
            x[f:f + 61, 5] += (3 * gain * resp)
        else:
            x[f:f + 61, 4] += (5 * gain * resp)
            x[f:f + 61, 1] -= (2 * gain * resp)
    for k in range(N):                       # more pairs: every neuron answers a little
        x[stims[0]:stims[0] + 61, k] += 0.5 * k
    p = tmp_path / f"{uid}.npz"
    np.savez(p, x=x, ids=np.array(names), stim_cell=np.r_[targets, -3], stim_frame=np.r_[stims, 10])
    return p


def test_loader_drops_untracked_targets(tmp_path):
    r = load_pumpprobe(_toy(tmp_path))
    assert r.x.shape == (6, 3000) and r.n_untracked_stims == 1
    assert r.classes[:2] == ["AVA", "AVB"] and all(k >= 0 for k, _ in r.stims)


def test_response_sets_and_levels(tmp_path, monkeypatch):
    import nematica.bench.causal as causal
    monkeypatch.setattr(causal, "MIN_SHARED", 4)
    a = response_set(load_pumpprobe(_toy(tmp_path, 0, uid="pumpprobe_a")))
    b = response_set(load_pumpprobe(_toy(tmp_path, 1, uid="pumpprobe_b")))
    big = response_set(load_pumpprobe(_toy(tmp_path, 2, gain=3.0, uid="pumpprobe_c")))
    assert a.amp(("AVA", "AVB")) > 0.1 and a.amp(("AVA", "AIB")) < -0.1
    assert c_pattern(a, b) < 0.2
    assert c_magnitude(a, big) > c_magnitude(a, b)
    rev = time_reversed(load_pumpprobe(_toy(tmp_path, 1, uid="pumpprobe_b")))
    assert c_kinetics(a, rev) > c_kinetics(a, b)
    perm = permuted_targets(load_pumpprobe(_toy(tmp_path, 1, uid="pumpprobe_b")), np.random.default_rng(0))
    assert c_pattern(a, perm) > c_pattern(a, b)


def test_score_sets_runs(tmp_path, monkeypatch):
    import nematica.bench.causal as causal
    monkeypatch.setattr(causal, "MIN_SHARED", 4)
    real = [response_set(load_pumpprobe(_toy(tmp_path, s, uid=f"pumpprobe_{s}"))) for s in range(5)]
    rows = score_sets("same", real, real, n_boot=50)
    assert {r["metric"] for r in rows} == {"C1.pattern", "C2.magnitude", "C3.kinetics"}
    assert all(r["verdict"] == "inside" for r in rows)


@pytest.mark.skipif(not ATLAS.is_dir() or not any(ATLAS.glob("*.npz")), reason="atlas not present")
def test_real_atlas_loads():
    recs = load_pumpprobe_dir(ATLAS)[:3]
    for r in recs:
        assert r.x.shape[0] == len(r.names) and r.stims
        rs = response_set(r)
        assert len(rs.traces) > 100


def test_lz76_and_pci():
    from nematica.bench.perturbational import lz76, lz76_reference, pci
    assert lz76(np.array([int(c) for c in "0001101001000101"])) == 6     # Kaspar and Schuster 1987
    rng = np.random.default_rng(0)
    for n in (2, 17, 300):
        for p in (0.05, 0.5):
            s = (rng.random(n) < p).astype(np.uint8)
            assert lz76(s) == lz76_reference(s)
    noisy = pci(rng.random((40, 61)) < 0.1)
    stereotyped = pci(np.tile(rng.random((40, 1)) < 0.3, (1, 61)))
    assert noisy > 0.8 and stereotyped < 0.2 and pci(np.zeros((5, 10), bool)) == 0.0


def test_event_matrices_on_toy(tmp_path):
    from nematica.bench.perturbational import pci_set
    names = ["AVAL", "AVBL", "AIBL", "RIML", "SMDDL", "AVEL", "RIAL", "RIBL", "RMDDL", "AIZL", "AIYL", "ASHL"]
    rng = np.random.default_rng(0)
    T, N = 2000, len(names)
    x = 50 + rng.standard_normal((T, N)).astype(np.float32)
    stims = np.arange(40, T - 70, 62)
    for f in stims:
        x[f:f + 30, 1:6] += 8
    p = tmp_path / "pumpprobe_toy.npz"
    np.savez(p, x=x, ids=np.array(names), stim_cell=np.zeros(len(stims), int), stim_frame=stims)
    s = pci_set(load_pumpprobe(p))
    assert len(s.pci) == len(stims) - 1 or len(s.pci) == len(stims)
    assert np.median(s.spread) > 0.1 and np.median(s.pci) > 0
