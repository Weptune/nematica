"""The benchmark tool end to end on synthetic worms (no atlas needed): the rule, excess distance,
seeds, the HTML report and the file interface."""
from __future__ import annotations

import json

import numpy as np
import pytest
import yaml

from nematica.bench.verdicts import answers, excess, judge, level_passes
from nematica.data.pumpprobe import PumpProbe, neuron_class
from nematica.data.splits import folds_hash
from nematica.kit import score_files
from nematica.report_html import render
from nematica.score import BrainCopy, score, template_of, format_answers

NAMES = ["AVAL", "AVAR", "RIML", "RIMR", "ASHL", "ASHR", "AIBL", "AIBR", "SMDVL", "SMDVR", "RMDL", "RMDR",
         "URYDL", "URYDR", "OLQDL", "OLQDR", "IL2L", "AWBL", "AIYL", "RIAL", ""]


def synth_worm(i: int, T: int = 1400) -> PumpProbe:
    rng = np.random.default_rng(i)
    N = len(NAMES)
    slow = np.cumsum(rng.standard_normal((3, T)), axis=1) * 0.05
    load = rng.standard_normal((N, 3))
    x = load @ slow + 0.5 * rng.standard_normal((N, T))
    stims = []
    for k, f in enumerate(range(60, T - 80, 60)):
        j = k % (N - 1)
        x[j, f:f + 30] += 3.0
        x[(j + 1) % (N - 1), f + 2:f + 32] += 1.0
        stims.append((j, f))
    return PumpProbe(uid=f"w{i:02d}", x=x, names=list(NAMES), classes=[neuron_class(n) for n in NAMES],
                     stims=stims, all_stim_frames=[f for _, f in stims])


@pytest.fixture(scope="module")
def worms():
    return [synth_worm(i) for i in range(12)]


@pytest.fixture(scope="module")
def split_file(tmp_path_factory, worms):
    folds = [[w.uid for w in worms[k::3]] for k in range(3)]
    doc = {"dataset": "synthetic", "hash": folds_hash({"folds": folds}), "k": 3, "folds": folds}
    p = tmp_path_factory.mktemp("splits") / "synth.yaml"
    p.write_text(yaml.safe_dump(doc))
    return {"synth": p}


class Echo(BrainCopy):
    """Noise plus each poked neuron's drive and a small echo in the next neuron."""
    name = "echo"

    def run(self, w, rng):
        x = 0.7 * rng.standard_normal((len(w.names), w.n_frames))
        for p in w.pokes:
            n = min(len(p.drive), w.n_frames - p.frame)
            x[p.index, p.frame:p.frame + n] = np.nan_to_num(p.drive[:n])
        return x


def test_rule_and_excess():
    assert level_passes("IIO") and level_passes("III") and not level_passes("IOT") and not level_passes("II")
    j = judge({**{lv: "IIO" for lv in ("L1.distribution", "L1.timescale", "L2.correlation", "L2.dimension", "L4.leadlag")},
               "L4.dwell": "OOO", "C1.pattern": "III", "C2.magnitude": "IIT", "P2.spread": "IOI"})
    assert j["rest_levels_passing"] == 5 and j["rest_pass"] and j["poke_pass"] and not j["all_nine"]
    j2 = judge({"C1.pattern": "III", "C2.magnitude": "III"})        # spread not scored: cannot pass the pokes
    assert not j2["poke_pass"] and not j2["poke_scored"]
    e, lo, hi = excess({"system_median": 1.2, "bio_median": 1.0, "shift_lo": 0.1, "shift_hi": 0.3})
    assert e == pytest.approx(0.2) and lo == pytest.approx(0.1) and hi == pytest.approx(0.3)
    assert np.isnan(excess({"system_median": None, "bio_median": 1.0})[0])


@pytest.fixture(scope="module")
def scored(worms, split_file):
    return score(Echo, worms, split_files=split_file, seeds=2, log=lambda m: None)


def test_score_end_to_end(scored):
    levels = {r["metric"] for r in scored}
    assert {"L1.distribution", "L2.dimension", "C1.pattern", "C2.magnitude", "P2.spread"} <= levels
    assert {r["seed"] for r in scored} == {0, 1} and {r["fold"] for r in scored} == {0, 1, 2}
    a = answers(scored)["synth"]
    assert a["seeds"] == 2 and a["pools"] == 3
    assert all(len(v) == 3 for L in a["levels"].values() for v in L["letters"].values())
    assert "Split synth" in format_answers("echo", scored)


def test_seeds_are_different_noise_same_fit(worms, split_file):
    calls = []

    class Counting(Echo):
        name = "counting"

        def fit(self, ws):
            calls.append(len(ws))

    rows = score(Counting, worms, split_files=split_file, folds=[0], seeds=2, pci=False, log=lambda m: None)
    assert len(calls) == 1                                          # fitted once per fold
    d0 = [r["system_median"] for r in rows if r["seed"] == 0]
    d1 = [r["system_median"] for r in rows if r["seed"] == 1]
    assert d0 != d1                                                  # but simulated with fresh noise


def test_html_report(scored):
    html = render({"copy": "echo", "rows": scored, "meta": {"date": "2026-11-08"}},
                  {"other": {"copy": "other", "rows": scored}})
    assert html.startswith("<!DOCTYPE html>") and "<svg" in html and "nan" not in html.lower().replace("nan(", "")
    assert "Passes at rest" in html and "echo pattern" in html


def test_files_round_trip_matches_direct_scoring(worms, split_file, tmp_path):
    from nematica.data.splits import load_folds
    from nematica.bench.scorecard import fold_parts
    folds = load_folds(split_file["synth"])["folds"]
    recs = {w.uid: w for w in worms}
    copy = Echo()
    for fi in range(3):
        _, _, pool = fold_parts(recs, folds, fi)
        d = tmp_path / "synth" / f"fold{fi}" / "seed0"
        d.mkdir(parents=True)
        for i, r in enumerate(pool):
            x = copy.run(template_of(r), np.random.default_rng(1000 * fi + i))
            np.savez(d / f"{r.uid}.npz", x=x)
    via_files = score_files(tmp_path, worms, "echo", split_files=split_file, log=lambda m: None)
    direct = score(Echo, worms, split_files=split_file, log=lambda m: None)
    key = lambda r: (r["fold"], r["metric"])  # noqa: E731
    a = {key(r): r["system_median"] for r in via_files}
    b = {key(r): r["system_median"] for r in direct}
    assert a.keys() == b.keys()
    for k in a:
        assert a[k] == pytest.approx(b[k], nan_ok=True)


def test_files_missing_worm_is_an_error(worms, split_file, tmp_path):
    (tmp_path / "synth" / "fold0" / "seed0").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="missing"):
        score_files(tmp_path, worms, "x", split_files=split_file, log=lambda m: None)


def test_check_flags_a_copy_that_ignores_its_drive(worms):
    from nematica.score import check

    class Deaf(BrainCopy):
        def run(self, w, rng):
            return rng.standard_normal((len(w.names), w.n_frames))

    class Short(BrainCopy):
        def run(self, w, rng):
            return np.zeros((3, 3))

    assert check(Echo, worms, log=lambda m: None) == []
    assert any("drive" in p for p in check(Deaf, worms, log=lambda m: None))
    assert any("expected" in p for p in check(Short, worms, log=lambda m: None))


def test_leaderboard(scored):
    from nematica.report_html import render_leaderboard
    html = render_leaderboard({"a": {"rows": scored}, "b": {"rows": scored}})
    assert html.count("<tr>") >= 3 and "echo pattern" in html


def test_score_many_matches_score(worms, split_file):
    from nematica.score import score_many
    many = score_many({"echo": Echo}, worms, split_files=split_file, folds=[1], pci=False, log=lambda m: None)["echo"]
    one = score(Echo, worms, split_files=split_file, folds=[1], pci=False, log=lambda m: None)
    assert [(r["metric"], r["system_median"]) for r in many] == [(r["metric"], r["system_median"]) for r in one]
