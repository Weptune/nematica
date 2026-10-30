"""Tests for the data layer. Synthetic fixtures only, so they run without any dataset."""

import json
import os
from pathlib import Path

import numpy as np
import pytest

from nematica.data import (Recording, RoiLabel, load_split, load_wormwideweb_dir,
                           load_wormwideweb_json, make_worm_split, save_split)

T, N = 40, 5


def fake_json(uid="2023-01-10-14", heat=True):
    rng = np.random.default_rng(0)
    ts = 1000.0 + 0.6 * np.arange(T)
    traces = rng.normal(1.0, 0.1, size=(N, T))
    d = {
        "uid": uid,
        "trace_original": traces.tolist(),
        "trace_array": ((traces - traces.mean(1, keepdims=True))
                        / traces.std(1, keepdims=True)).tolist(),
        "timestamp_confocal": ts.tolist(),
        "labeled": {
            "1": {"label": "AVAL", "neuron_class": "AVA", "LR": "L", "DV": "undefined", "confidence": 5.0},
            "2": {"label": "AVAR", "neuron_class": "AVA", "LR": "R", "DV": "undefined", "confidence": 4.0},
            "4": {"label": "AIA?", "neuron_class": "AIA", "LR": "?", "DV": "undefined", "confidence": 2.0},
            "5": {"label": "AQR", "neuron_class": "AQR", "LR": "undefined", "DV": "undefined", "confidence": 1.0},
        },
        "velocity": np.linspace(-0.1, 0.1, T).tolist(),
        "head_curvature": np.zeros(T).tolist(),
        "reversal_events": [[2, 5], [20, 22]],
        "ranges": [[1, 18], [23, T]] if heat else [[1, 20], [21, T]],
        "dataset_type": ["heat", "neuropal"] if heat else ["baseline", "neuropal"],
    }
    if heat:
        d["events"] = {"heat": [20]}
    return d


@pytest.fixture
def json_dir(tmp_path):
    for i, heat in enumerate([True, True, True, False, False, False, True, False]):
        uid = f"2023-01-{10 + i:02d}-0{i}"
        (tmp_path / f"{uid}.json").write_text(json.dumps(fake_json(uid, heat)))
    return tmp_path


def test_loader_uses_original_traces_and_converts_to_zero_based(tmp_path):
    p = tmp_path / "w.json"
    p.write_text(json.dumps(fake_json()))
    r = load_wormwideweb_json(p)
    raw = np.array(fake_json()["trace_original"])
    np.testing.assert_allclose(r.traces, raw)          # not the whole-recording z-score
    assert r.t[0] == 0 and r.frame_interval == pytest.approx(0.6)
    assert r.reversals == [(1, 4), (19, 21)]           # 1-based inclusive -> 0-based
    assert r.events == {"heat": [19]}
    assert r.valid.sum() == 18 + (T - 22) and not r.valid[18:22].any()
    assert set(r.labels) == {0, 1, 3, 4}               # "1","2","4","5" -> rows 0,1,3,4
    assert r.conditions == ("heat", "neuropal")


def test_identity_helpers(tmp_path):
    p = tmp_path / "w.json"
    p.write_text(json.dumps(fake_json()))
    r = load_wormwideweb_json(p)
    assert r.classes(2.0) == ["AIA", "AVA"]            # AQR has confidence 1, dropped
    names, ct = r.class_traces(2.0)
    np.testing.assert_allclose(ct[names.index("AVA")], r.traces[[0, 1]].mean(0))
    neuron_names, _ = r.neuron_traces(2.0)
    assert neuron_names == ["AVAL", "AVAR"]            # "AIA?" is side-unresolved
    assert r.find("AVAL") is not None and r.find("RIM") is None
    assert r.summary()["labelled"] == 3


def test_recording_validates_shapes():
    with pytest.raises(ValueError):
        Recording(uid="x", dataset="d", t=np.arange(3), traces=np.zeros((2, 4)),
                  traces_kind="k", labels={})
    with pytest.raises(ValueError):
        Recording(uid="x", dataset="d", t=np.arange(4), traces=np.zeros((2, 4)),
                  traces_kind="k", labels={5: RoiLabel("AVAL", "AVA", "L", None, 5)})


def test_split_is_disjoint_balanced_and_frozen(json_dir, tmp_path):
    recs = load_wormwideweb_dir(json_dir)
    conds = ["heat" if "heat" in r.conditions else "baseline" for r in recs]
    split = make_worm_split([r.uid for r in recs], conds, n_test=2, n_val=2, seed=1)
    assert not set(split["train"]) & set(split["test"])
    assert not set(split["val"]) & set(split["test"])
    assert len(split["train"]) + len(split["val"]) + len(split["test"]) == len(recs)
    by_uid = dict(zip([r.uid for r in recs], conds))
    assert {by_uid[u] for u in split["test"]} == {"heat", "baseline"}

    path = tmp_path / "split.yaml"
    save_split(split, path, "fake")
    assert load_split(path)["test"] == split["test"]
    with pytest.raises(FileExistsError):
        save_split(split, path, "fake")
    text = path.read_text().replace(split["test"][0], "tampered")
    path.write_text(text)
    with pytest.raises(ValueError):
        load_split(path)


REAL = os.environ.get("NEMATICA_ATANAS_DIR", "data/raw/atanas2023_wwweb")


@pytest.mark.skipif(not Path(REAL).is_dir() or not any(Path(REAL).glob("*.json")),
                    reason="real Atanas JSON files not present")
def test_real_atanas_files_load():
    recs = load_wormwideweb_dir(REAL)
    assert len(recs) >= 30
    for r in recs:
        assert 1590 <= r.n_frames <= 1620
        assert 0.55 < r.frame_interval < 0.65
        assert np.all(np.diff(r.t) > 0)
        assert len(r.labelled()) >= 50
