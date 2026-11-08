"""The experiment, as the atlas ran it on worms, written as a schedule any system can follow.

A system enters the test in one of three ways (all produce the same recordings):
  1. the server runs an uploaded model (networks.py: rate-RNN weights or ONNX) with `run_network`;
  2. Python code with a `run(schedule_run, rng)` method, run with `run_python`;
  3. the owner runs the schedule on their own system, in any language or hardware, and uploads what was
     recorded (`recordings_from_upload`).

The schedule (`make_schedule`, exported as JSON by `schedule_json`):
  * 30 runs ("animals"), each 37 minutes long: 4,440 frames of 0.5 s (or the same duration in the
    system's own steps).
  * Analysis units: up to 120 of the system's units, chosen at random once; in each run 45 of them are
    "recorded" (the atlas sees about 43 neuron types per worm).
  * A push every 30 s from 30 s on, each to one recorded unit of that run, lasting 2 s: a brief extra
    drive to that unit, strong enough to move it clearly (the atlas's median pushed-neuron change is about
    1.6 of its resting SD over the next 15 s; the test checks the recorded change itself).
  * Between pushes the system runs on its own, with whatever ongoing input or noise it normally has.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

import numpy as np

from ..data.pumpprobe import PumpProbe

FRAME_S = 0.5


@dataclass
class Protocol:
    runs: int = 30
    minutes: float = 37.0
    analysis_units: int = 120
    recorded_per_run: int = 45
    push_every_s: float = 30.0
    push_seconds: float = 2.0
    measurement_noise: float = 0.1          # SD of recording noise added by the test, in each unit's SD
    seed: int = 20261108
    version: int = 1


@dataclass
class Schedule:
    protocol: Protocol
    n_units: int
    step_seconds: float
    units: list                              # analysis units: indices into the system's units
    runs: list = field(default_factory=list)  # per run: {"recorded": [positions in units], "pushes": [[step, position]]}

    @property
    def steps(self) -> int:
        return int(round(self.protocol.minutes * 60 / self.step_seconds))

    @property
    def push_steps(self) -> int:
        return max(1, int(round(self.protocol.push_seconds / self.step_seconds)))

    def digest(self) -> str:
        return hashlib.sha256(schedule_json(self).encode()).hexdigest()[:16]


def make_schedule(n_units: int, step_seconds: float = FRAME_S, protocol: Protocol | None = None) -> Schedule:
    p = protocol or Protocol()
    rng = np.random.default_rng(p.seed + n_units)
    units = sorted(rng.choice(n_units, size=min(n_units, p.analysis_units), replace=False).tolist())
    m = len(units)
    k = min(p.recorded_per_run, m)
    sch = Schedule(p, n_units, step_seconds, units)
    every = int(round(p.push_every_s / step_seconds))
    tail = int(round(30.0 / step_seconds))
    for _ in range(p.runs):
        rec = sorted(rng.choice(m, size=k, replace=False).tolist())
        pushes = [[int(t), int(rng.choice(rec))] for t in range(every, sch.steps - tail, every)]
        sch.runs.append({"recorded": rec, "pushes": pushes})
    return sch


def schedule_json(s: Schedule) -> str:
    return json.dumps({"version": s.protocol.version, "n_units": s.n_units, "step_seconds": s.step_seconds,
                       "steps_per_run": s.steps, "push_steps": s.push_steps, "units": s.units,
                       "runs": s.runs,
                       "about": "units: indices of your system's units the test analyses. In each run, record the "
                                "units listed (positions into `units`) for steps_per_run steps, and at each "
                                "[step, position] give that unit a brief extra drive lasting push_steps steps, strong "
                                "enough to move it clearly (the test checks the recorded change). Upload an npz with "
                                "array `activity` of shape (runs, steps_per_run, len(units)): all analysis units, NaN "
                                "where not recorded is fine."}, separators=(",", ":"))


def _resample(a: np.ndarray, step_seconds: float) -> np.ndarray:
    """(steps, units) at step_seconds -> (frames, units) at 0.5 s, by averaging (finer steps) or linear
    interpolation (coarser steps)."""
    if abs(step_seconds - FRAME_S) < 1e-9:
        return a
    T = a.shape[0]
    t_src = np.arange(T) * step_seconds
    frames = int(np.floor(t_src[-1] / FRAME_S)) + 1
    if step_seconds < FRAME_S:
        idx = np.minimum((t_src / FRAME_S).astype(int), frames - 1)
        out = np.zeros((frames, a.shape[1]))
        cnt = np.zeros(frames)
        np.add.at(out, idx, np.nan_to_num(a))
        np.add.at(cnt, idx, 1)
        return out / np.maximum(cnt, 1)[:, None]
    t_dst = np.arange(frames) * FRAME_S
    return np.column_stack([np.interp(t_dst, t_src, a[:, j]) for j in range(a.shape[1])])


def to_recordings(activity: np.ndarray, sch: Schedule, rng: np.random.Generator) -> list[PumpProbe]:
    """(runs, steps, analysis units) -> one atlas-format recording per run: the run's recorded units,
    measurement noise added, pushes mapped to 0.5 s frames."""
    out = []
    names = [f"U{u:04d}" for u in sch.units]
    for i, run in enumerate(sch.runs):
        a = np.asarray(activity[i], float)[:, run["recorded"]]
        a = _resample(a, sch.step_seconds)
        sd = np.nanstd(a, axis=0)
        a = a + sch.protocol.measurement_noise * np.where(sd > 0, sd, 0) * rng.standard_normal(a.shape)
        pos = {p: r for r, p in enumerate(run["recorded"])}
        frames = [int(round(s * sch.step_seconds / FRAME_S)) for s, _ in run["pushes"]]
        stims = [(pos[p], f) for (s, p), f in zip(run["pushes"], frames) if f < a.shape[0]]
        out.append(PumpProbe(uid=f"run{i:02d}", x=a.T.copy(), names=[names[p] for p in run["recorded"]],
                             classes=[names[p] for p in run["recorded"]], stims=stims, dt=FRAME_S,
                             all_stim_frames=frames))
    return out


def record_population(net, sch: Schedule, amplitude: float, rng: np.random.Generator, burn: int = 400) -> np.ndarray:
    """Run a model (networks.Network) through the schedule, all runs at once: returns (runs, steps,
    analysis units) of activity. Each run starts from its own random state and runs `burn` steps first."""
    R, T, n = len(sch.runs), sch.steps, net.n
    units = np.asarray(sch.units)
    x = net.init_state(R, rng)
    for _ in range(burn):
        x = net.step(x, net.noise_sd * rng.standard_normal((R, n)))
    push = np.zeros((T, R), int) - 1
    for i, run in enumerate(sch.runs):
        for s, p in run["pushes"]:
            push[s:s + sch.push_steps, i] = units[p]
    out = np.empty((R, T, len(units)), np.float32)
    for t in range(T):
        u = net.noise_sd * rng.standard_normal((R, n))
        on = push[t] >= 0
        if on.any():
            u[np.flatnonzero(on), push[t][on]] += amplitude
        x = net.step(x, u)
        a = net.activity(x)
        if not np.isfinite(a).all():
            from .networks import NetworkError
            raise NetworkError(f"the network's activity became NaN or infinite at step {t}")
        out[:, t] = a[:, units]
    return out
