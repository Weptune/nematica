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

    class Global(BrainCopy):
        def run(self, w, rng):
            return np.random.standard_normal((len(w.names), w.n_frames))

    class Patchy(Echo):
        def run(self, w, rng):
            x = super().run(w, rng)
            x[0, :10] = np.nan
            return x

    msgs = []
    assert check(Echo, worms, log=lambda m: None) == []
    assert check(Deaf, worms, log=msgs.append) == [] and any("drive" in m for m in msgs)    # a warning only
    assert any("expected" in p for p in check(Short, worms, log=lambda m: None))
    assert any("global" in p for p in check(Global, worms, log=lambda m: None))
    assert any("whole run" in p for p in check(Patchy, worms, log=lambda m: None))


def test_leaderboard(scored):
    from nematica.report_html import render_leaderboard
    html = render_leaderboard({"a": {"rows": scored}, "b": {"rows": scored}})
    assert html.count("<tr>") >= 3 and "echo pattern" in html


def test_score_many_matches_score(worms, split_file):
    from nematica.score import score_many
    many = score_many({"echo": Echo}, worms, split_files=split_file, folds=[1], pci=False, log=lambda m: None)["echo"]
    one = score(Echo, worms, split_files=split_file, folds=[1], pci=False, log=lambda m: None)
    assert [(r["metric"], r["system_median"]) for r in many] == [(r["metric"], r["system_median"]) for r in one]


def test_partial_runs_are_not_judged(scored):
    from nematica.report_html import render
    one_pool = [r for r in scored if r["fold"] == 0 and r["seed"] == 0]
    a = answers(one_pool)["synth"]
    assert not a["judged"] and "1 of 3 pools" in a["not_judged_because"][0]
    assert a["rest_pass_seeds"] is None and "NOT JUDGED" in format_answers("x", one_pool)
    assert "Not judged" in render({"copy": "x", "rows": one_pool})


def test_duplicated_rows_are_refused(scored):
    from nematica.bench.verdicts import RowsError
    with pytest.raises(RowsError, match="two rows"):
        answers(scored + [dict(scored[0])])


def test_poke_rule_needs_echo_spread(scored):
    no_p2 = [r for r in scored if r["metric"] != "P2.spread"]
    a = answers(no_p2)["synth"]
    assert not a["judged"] and any("spread" in p for p in a["not_judged_because"])


def test_low_coverage_is_not_judged(worms, split_file):
    class Few(Echo):
        name = "few"

        def run(self, w, rng):
            x = super().run(w, rng)
            x[4:] = np.nan                                   # models only four neurons
            return x

    rows = score(Few, worms, split_files=split_file, pci=False, log=lambda m: None)
    a = answers(rows)["synth"]
    assert a["coverage"] < 0.8 and any("classes" in p for p in a["not_judged_because"])


def test_bad_folds_and_seeds_are_errors(worms, split_file):
    with pytest.raises(ValueError, match="folds"):
        score(Echo, worms, split_files=split_file, folds=[7], log=lambda m: None)
    with pytest.raises(ValueError, match="seeds"):
        score(Echo, worms, split_files=split_file, seeds=0, log=lambda m: None)


def test_files_structure_errors(worms, split_file, tmp_path):
    (tmp_path / "synth" / "fold_0").mkdir(parents=True)
    with pytest.raises(ValueError, match="fold0"):
        score_files(tmp_path, worms, "x", split_files=split_file, log=lambda m: None)
    (tmp_path / "synth" / "fold_0").rmdir()
    (tmp_path / "synth" / "fold0" / "seed0").mkdir(parents=True)
    (tmp_path / "synth" / "fold1" / "seed1").mkdir(parents=True)
    with pytest.raises(ValueError, match="different seeds"):
        score_files(tmp_path, worms, "x", split_files=split_file, log=lambda m: None)


def test_low_level_models_cannot_be_mistaken_for_copies():
    from nematica.score import _as_model

    class Helper(BrainCopy):
        def simulate(self, *a):                               # a helper that happens to be called simulate
            raise AssertionError

        def run(self, w, rng):
            return np.zeros((len(w.names), w.n_frames))

    assert type(_as_model(Helper())).__name__ == "CopyAdapter"
    with pytest.raises(TypeError):
        _as_model(object())


def test_template_copy_passes_the_contract_check(worms):
    from nematica.score import check, load_copy
    from pathlib import Path
    tpl = Path(__file__).resolve().parents[1] / "examples" / "copies" / "template.py"
    assert check(load_copy(f"{tpl}:Template"), worms, log=lambda m: None) == []
