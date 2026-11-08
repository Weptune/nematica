"""Brain-likeness test: formats, schedule, uploads, the Python interface, the CLI and the website."""
import importlib
import io
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

from nematica.brainlike import BrainLike, load_network, make_schedule, run_python, run_test
from nematica.brainlike.networks import NetworkError, RateRNN
from nematica.brainlike.protocol import Protocol, schedule_json
from nematica.brainlike.signatures import SIGNATURES
from nematica.brainlike.test import recordings_from_upload

SMALL = Protocol(runs=4, minutes=6.0)


def _rnn(n=30, seed=0):
    r = np.random.default_rng(seed)
    return r.standard_normal((n, n)) * 1.2 / np.sqrt(n)


def _npz(**arrays) -> io.BytesIO:
    b = io.BytesIO()
    np.savez(b, **arrays)
    b.seek(0)
    return b


# ---------------------------------------------------------------- schedule
def test_schedule_is_deterministic_and_well_formed():
    a, b = make_schedule(300, 0.5), make_schedule(300, 0.5)
    assert schedule_json(a) == schedule_json(b) and a.digest() == b.digest()
    assert len(a.units) == 120 and len(a.runs) == 30 and a.steps == 4440 and a.push_steps == 4
    for run in a.runs:
        assert len(run["recorded"]) == 45
        assert all(p in run["recorded"] for _, p in run["pushes"])
        steps = [s for s, _ in run["pushes"]]
        assert steps == sorted(steps) and np.all(np.diff(steps) == 60)
    assert make_schedule(300, 0.1).steps == 22200 and make_schedule(300, 0.1).frames == 4440
    assert make_schedule(301, 0.5).digest() != a.digest()
    small = make_schedule(20, 0.5)
    assert small.units == list(range(20)) and all(len(r["recorded"]) == 20 for r in small.runs)


# ---------------------------------------------------------------- model formats
def test_rate_rnn_npz_and_errors(tmp_path):
    p = tmp_path / "net.npz"
    np.savez(p, W=_rnn(), leak=0.3, nonlinearity="relu", noise_sd=0.2, step_seconds=0.25)
    net = load_network(p)
    assert isinstance(net, RateRNN) and net.n == 30 and net.nl == "relu" and net.noise_sd == 0.2 and net.step_seconds == 0.25
    bad = [({"W": np.ones((3, 4))}, "square"), ({"W": np.ones((5, 5))}, "10 to"), ({"V": _rnn()}, "needs an array W"),
           ({"W": _rnn(), "leak": 2.0}, "leak"), ({"W": _rnn(), "nonlinearity": "cube"}, "nonlinearity"),
           ({"W": np.full((12, 12), np.nan)}, "NaN")]
    for arrays, msg in bad:
        np.savez(p, **arrays)
        with pytest.raises(NetworkError, match=msg):
            load_network(p)
    q = tmp_path / "x.txt"
    q.write_text("hi")
    with pytest.raises(NetworkError):
        load_network(q)


def test_npz_with_pickled_objects_is_refused(tmp_path):
    p = tmp_path / "evil.npz"
    np.savez(p, W=np.array([object()], dtype=object))
    with pytest.raises(NetworkError):
        load_network(p)


def _export_lstm(path, N=16, H=12, batch1=False):
    torch = pytest.importorskip("torch")

    class Step(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.H, self.cell, self.readout = H, torch.nn.LSTMCell(N, H), torch.nn.Linear(H, N)

        def forward(self, state, input):                                     # noqa: A002
            h, c = self.cell(input, (state[:, :self.H], state[:, self.H:]))
            return torch.cat([h, c], 1), torch.tanh(self.readout(h))
    torch.manual_seed(0)
    dyn = None if batch1 else {k: {0: "b"} for k in ("state", "input", "next_state", "activity")}
    torch.onnx.export(Step().eval(), (torch.zeros(1, 2 * H), torch.zeros(1, N)), str(path), input_names=["state", "input"],
                      output_names=["next_state", "activity"], dynamic_axes=dyn, opset_version=17, dynamo=False)
    return path


@pytest.mark.parametrize("batch1", [False, True])
def test_onnx_with_separate_state_and_activity(tmp_path, batch1):
    pytest.importorskip("onnxruntime")
    net = load_network(_export_lstm(tmp_path / "lstm.onnx", batch1=batch1))
    assert net.n == 16 and net.S == 24 and net.has_activity
    rng = np.random.default_rng(0)
    x = net.init_state(3, rng)
    x2 = net.step(x, rng.standard_normal((3, 16)))
    assert x2.shape == (3, 24) and net.activity(x2).shape == (3, 16)
    res = run_test(net, SMALL, log=lambda m: None)
    assert set(res["signatures"]) == set(SIGNATURES)


# ---------------------------------------------------------------- uploads of recordings
def test_recordings_upload_checks():
    s = make_schedule(40, 0.5)
    shape = (30, s.steps, len(s.units))
    a = np.random.default_rng(0).standard_normal(shape).astype(np.float32)
    act, sch = recordings_from_upload(np.load(_npz(activity=a, n_units=40)))
    assert act.shape == shape and not sch.framed
    with pytest.raises(NetworkError, match="needs"):
        recordings_from_upload(np.load(_npz(activity=a[:, :-1], n_units=40)))
    with pytest.raises(NetworkError, match="n_units"):
        recordings_from_upload(np.load(_npz(activity=a)))
    b = a.copy()
    b[3, 10, s.runs[3]["recorded"][0]] = np.nan
    with pytest.raises(NetworkError, match="run 3"):
        recordings_from_upload(np.load(_npz(activity=b, n_units=40)))
    c = a.copy()
    unrec = sorted(set(range(len(s.units))) - set(s.runs[0]["recorded"]))
    if unrec:
        c[0][:, unrec] = np.nan                                  # units a run does not record may be NaN
        recordings_from_upload(np.load(_npz(activity=c, n_units=40)))
    f = make_schedule(40, 0.1)
    framed = np.zeros((30, f.frames, len(f.units)), np.float32)
    _, sch = recordings_from_upload(np.load(_npz(activity=framed, n_units=40, step_seconds=0.1)))
    assert sch.framed
    with pytest.raises(NetworkError, match="step_seconds"):
        recordings_from_upload(np.load(_npz(activity=a, n_units=40, step_seconds=30.0)))


# ---------------------------------------------------------------- Python systems
class Toy(BrainLike):
    """A leaky noisy network, written by hand against the run() interface."""
    n_units, step_seconds, name = 30, 0.5, "toy"
    calibrate_push, push_strength = True, 1.0

    def __init__(self):
        self.W = _rnn(30, 1)

    def run(self, steps, record, pushes, push_steps, rng):
        x = np.zeros(self.n_units)
        drive = {}
        for t, u in pushes:
            for d in range(push_steps):
                drive[t + d] = u
        out = np.empty((steps, len(record)))
        for t in range(steps):
            u = 0.5 * rng.standard_normal(self.n_units)
            if t in drive:
                u[drive[t]] += self.push_strength
            x = 0.7 * x + 0.3 * (np.tanh(x) @ self.W.T + u)
            out[t] = np.tanh(x)[record]
        return out


def test_python_system_runs_and_calibrates():
    res = run_python(Toy(), SMALL, log=lambda m: None)
    assert res["push_strength"] > 0 and set(res["signatures"]) == set(SIGNATURES)
    assert not res["valid"] and any("pushes" in p for p in res["problems"])   # 4 short runs: too few pushes


def test_python_system_bad_output():
    class Bad(Toy):
        calibrate_push = False

        def run(self, steps, record, pushes, push_steps, rng):
            return np.zeros((steps, len(record) + 1))
    with pytest.raises(NetworkError, match="shape"):
        run_python(Bad(), SMALL, log=lambda m: None)


def test_full_test_on_a_random_network_is_valid_and_far_from_worms():
    res = run_test(RateRNN(_rnn(30), leak=0.3, noise_sd=0.5), log=lambda m: None)
    assert res["valid"] and res["measured"]["n_pushes"] >= 300
    assert res["score"] <= 2


# ---------------------------------------------------------------- command line
def test_cli_writes_report(tmp_path):
    from nematica.__main__ import main
    p = tmp_path / "net.npz"
    np.savez(p, W=_rnn(), leak=0.3, noise_sd=0.5)
    main(["brainlike", str(p), "--out", str(tmp_path / "out")])
    d = json.loads((tmp_path / "out" / "net.brainlike.json").read_text())
    assert d["name"] == "net" and d["out_of"] == 8
    assert "<svg" in (tmp_path / "out" / "net.brainlike.html").read_text()


# ---------------------------------------------------------------- website
@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAINLIKE_DATA", str(tmp_path / "site"))
    monkeypatch.setenv("BRAINLIKE_NO_QUEUE", "1")
    monkeypatch.setenv("BRAINLIKE_TIMEOUT", "600")
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1]) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    import nematica.brainlike.web.app as A
    A = importlib.reload(A)
    from fastapi.testclient import TestClient
    with TestClient(A.app) as c:
        yield A, c


def test_site_pages_and_schedule(site):
    A, c = site
    for url in ("/", "/how", "/leaderboard"):
        r = c.get(url)
        assert r.status_code == 200 and "Brain-likeness test" in r.text and "—" not in r.text
    r = c.get("/schedule", params={"n_units": 300, "step_seconds": 0.5})
    assert r.status_code == 200 and json.loads(r.text)["steps_per_run"] == 4440
    assert c.get("/schedule", params={"n_units": 3}).status_code == 400
    assert c.get("/r/nonexistent-id").status_code == 404
    assert c.get("/r/../../etc").status_code == 404


def test_site_refuses_bad_uploads(site):
    A, c = site
    f = {"file": ("x.txt", b"hello")}
    assert c.post("/submit", data={"mode": "model", "name": "x"}, files=f).status_code == 400
    assert c.post("/submit", data={"mode": "python", "name": "x"}, files={"file": ("s.py", b"x=1")}).status_code == 400
    assert c.post("/submit", data={"mode": "model", "name": " "}, files={"file": ("n.npz", b"PK")}).status_code == 400
    assert c.post("/submit", data={"mode": "model", "name": "e"}, files={"file": ("n.npz", b"")}).status_code == 400
    A.LIMITS["model"] = 0
    try:
        r = c.post("/submit", data={"mode": "model", "name": "big"}, files={"file": ("n.npz", b"x" * 10)})
        assert r.status_code == 413
    finally:
        A.LIMITS["model"] = 100
    assert not list((A.DATA / "jobs").iterdir())


def test_site_runs_a_model_end_to_end(site):
    A, c = site
    b = _npz(W=_rnn(), leak=0.3, noise_sd=0.5)
    r = c.post("/submit", data={"mode": "model", "name": "Random <b>RNN</b>", "author": "tester", "public": "1"},
               files={"file": ("rnn.npz", b.getvalue())}, follow_redirects=False)
    assert r.status_code == 303
    job = r.headers["location"].rsplit("/", 1)[1]
    page = c.get(f"/r/{job}").text
    assert "Next in line" in page and "<b>RNN</b>" not in page              # escaped
    A._run(job)
    j = c.get(f"/api/r/{job}").json()
    assert j["status"] == "done", j
    assert j["result"]["valid"] and j["result"]["out_of"] == 8
    page = c.get(f"/r/{job}").text
    assert "signatures inside the real-worm range" in page and "<nav" in page
    board = c.get("/api/leaderboard").json()
    assert [e["id"] for e in board] == [job]


def test_site_reports_a_broken_model(site):
    A, c = site
    r = c.post("/submit", data={"mode": "model", "name": "broken"},
               files={"file": ("bad.npz", _npz(W=np.ones((3, 4))).getvalue())}, follow_redirects=False)
    job = r.headers["location"].rsplit("/", 1)[1]
    A._run(job)
    j = c.get(f"/api/r/{job}").json()
    assert j["status"] == "failed" and "square" in j["error"]
    assert "could not run" in c.get(f"/r/{job}").text


def test_site_recordings_upload(site):
    A, c = site
    s = make_schedule(40, 0.5)
    rng = np.random.default_rng(0)
    a = np.cumsum(rng.standard_normal((30, s.steps, len(s.units))), axis=1).astype(np.float32) * 0.05
    r = c.post("/submit", data={"mode": "recordings", "name": "walks"},
               files={"file": ("rec.npz", _npz(activity=a, n_units=40).getvalue())}, follow_redirects=False)
    job = r.headers["location"].rsplit("/", 1)[1]
    A._run(job)
    j = c.get(f"/api/r/{job}").json()
    assert j["status"] == "done"
    assert not j["result"]["valid"]                  # no pushes were given: the test says so instead of scoring
    assert c.get("/api/leaderboard").json() == []    # not public, not valid


def test_reference_entries(site):
    A, c = site
    res = run_test(RateRNN(_rnn(30), leak=0.3, noise_sd=0.5), log=lambda m: None)
    job = A.add_reference("random tanh RNN", res, description="baseline")
    assert job == "ref-random-tanh-rnn"
    assert "Random recurrent network" in c.get("/").text      # shown in the front-page figure
    assert c.get("/api/leaderboard").json()[0]["reference"] == 1
