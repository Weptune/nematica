"""The experiment, as the atlas ran it on worms, written as a schedule any system can follow.

A system enters the test in one of three ways (all produce the same recordings):
  1. the server runs an uploaded model (networks.py: rate-RNN weights or ONNX) with `run_network`;
  2. Python code with a `run(schedule_run, rng)` method, run with `run_python`;
  3. the owner runs the schedule on their own system, in any language or hardware, and uploads what was
     recorded (`recordings_from_upload`).

The schedule (`make_schedule`, exported as JSON by `schedule_json`):
  * 30 runs ("animals"), each 31.7 minutes long: 3,804 frames of 0.5 s, the atlas's median recording (or the
    same duration in the system's own steps).
  * Analysis units: up to 120 of the system's units, chosen at random once; in each run 45 of them are
    "recorded" (the atlas sees about 43 neuron types per worm).
  * A push every 31 s from 20 s on (the atlas's spacing), each to one recorded unit of that run, lasting 2 s:
    a brief extra drive to that unit, strong enough to move it clearly (the atlas's median pushed-neuron
    change is about 1.6 of its resting SD over the next 15 s; the test checks the recorded change itself).
    Two push slots per run are left empty, so a run has about as much undisturbed activity as an atlas worm.
  * Push times are fixed in seconds, so any step length gives the same experiment. Activity at steps shorter
    than 0.5 s is averaged into 0.5 s frames by time overlap; longer steps are interpolated.
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
    minutes: float = 31.7                    # 3,804 frames at 0.5 s: the atlas's median recording
    lead_s: float = 20.0                     # first push (atlas median: frame 43)
    empty_slots: int = 2                     # push slots left empty per run, so rest matches the atlas (324 frames; atlas 345)
    analysis_units: int = 120
    recorded_per_run: int = 45
    push_every_s: float = 31.0                # atlas: a median of 62 frames between pushes
    push_seconds: float = 2.0
    measurement_noise: float = 0.1          # SD of recording noise added by the test, in each unit's SD
    seed: int = 20261108
    version: int = 3


@dataclass
class Schedule:
    protocol: Protocol
    n_units: int
    step_seconds: float
    units: list                              # analysis units: indices into the system's units
    runs: list = field(default_factory=list)  # per run: {"recorded": [positions in units], "pushes": [[step, position]]}
    framed: bool = False                     # activity given already averaged into 0.5 s frames (uploads)

    seed: int = 0

    @property
    def frames(self) -> int:
        """Number of 0.5 s frames a run covers once resampled."""
        return int(np.floor(self.steps * self.step_seconds / FRAME_S + 1e-9))

    @property
    def steps(self) -> int:
        return int(round(self.protocol.minutes * 60 / self.step_seconds))

    @property
    def push_steps(self) -> int:
        return max(1, int(round(self.protocol.push_seconds / self.step_seconds)))

    def digest(self) -> str:
        return hashlib.sha256(schedule_json(self).encode()).hexdigest()[:16]


def make_schedule(n_units: int, step_seconds: float = FRAME_S, protocol: Protocol | None = None,
                  seed: int | None = None) -> Schedule:
    """The schedule for a system of n_units at step_seconds. The default seed is public (anyone can make the
    same schedule, as needed to follow it); the server gives models it runs a secret seed, so a model cannot
    know in advance which units are recorded or when pushes come."""
    p = protocol or Protocol()
    sd = p.seed if seed is None else int(seed)
    rng = np.random.default_rng(sd + n_units)
    units = sorted(rng.choice(n_units, size=min(n_units, p.analysis_units), replace=False).tolist())
    m = len(units)
    k = min(p.recorded_per_run, m)
    sch = Schedule(p, n_units, step_seconds, units, seed=sd)
    duration = sch.steps * step_seconds
    times = np.arange(p.lead_s, duration - 30.0 - p.push_seconds + 1e-9, p.push_every_s)
    slots = sorted({int(round(t / step_seconds)) for t in times})
    want = min(p.empty_slots, (len(slots) - 1) // 2)
    for _ in range(p.runs):
        rec = sorted(rng.choice(m, size=k, replace=False).tolist())
        for _attempt in range(100):
            empty: set[int] = set()
            for i in rng.permutation(np.arange(1, len(slots))):          # never the first slot
                if len(empty) == want:
                    break
                if i - 1 not in empty and i + 1 not in empty:
                    empty.add(int(i))
            if len(empty) == want:
                break
        else:
            raise ValueError("could not place the empty push slots; the protocol is too short")
        pushes = [[int(t), int(rng.choice(rec))] for i, t in enumerate(slots) if i not in empty]
        sch.runs.append({"recorded": rec, "pushes": pushes})
    return sch


def schedule_json(s: Schedule) -> str:
    return json.dumps({"version": s.protocol.version, "seed": s.seed, "n_units": s.n_units, "step_seconds": s.step_seconds,
                       "steps_per_run": s.steps, "frames_per_run": s.frames, "push_steps": s.push_steps, "units": s.units,
                       "runs": s.runs,
                       "about": "units: indices of your system's units the test analyses. In each run, record the "
                                "units listed (positions into `units`) for steps_per_run steps, and at each "
                                "[step, position] give that unit a brief extra drive lasting push_steps steps, strong "
                                "enough to move it clearly (the test checks the recorded change). Upload an npz with "
                                "array `activity` of shape (runs, steps_per_run, len(units)), or (runs, frames_per_run, "
                                "len(units)) averaged into 0.5 s frames, plus `n_units` and `step_seconds`. Units a "
                                "run does not record may be NaN."}, separators=(",", ":"))


def _frame_overlaps(steps: int, step_seconds: float):
    """For steps shorter than a frame: each step's first frame, the share of the step in it, and the next frame."""
    t0 = np.arange(steps) * step_seconds
    f0 = np.floor(t0 / FRAME_S + 1e-9).astype(int)
    edge = (f0 + 1) * FRAME_S
    w0 = np.clip((edge - t0) / step_seconds, 0.0, 1.0)
    return f0, w0


def _resample(a: np.ndarray, step_seconds: float) -> np.ndarray:
    """(steps, units) at step_seconds -> (frames, units) at 0.5 s: shorter steps are averaged by time overlap
    (each frame weighs every step by how much of it falls in the frame); longer steps are interpolated."""
    if abs(step_seconds - FRAME_S) < 1e-9:
        return a
    T = a.shape[0]
    frames = int(np.floor(T * step_seconds / FRAME_S + 1e-9))
    if step_seconds < FRAME_S:
        f0, w0 = _frame_overlaps(T, step_seconds)
        x = np.nan_to_num(np.asarray(a, float))
        out = np.zeros((frames + 1, a.shape[1]))
        wt = np.zeros(frames + 1)
        np.add.at(out, f0, x * w0[:, None])
        np.add.at(wt, f0, w0)
        f1 = np.minimum(f0 + 1, frames)
        np.add.at(out, f1, x * (1 - w0)[:, None])
        np.add.at(wt, f1, 1 - w0)
        return (out / np.maximum(wt, 1e-12)[:, None])[:frames]
    t_src = np.arange(T) * step_seconds
    t_dst = np.arange(frames) * FRAME_S
    return np.column_stack([np.interp(t_dst, t_src, a[:, j]) for j in range(a.shape[1])])


def push_frame(step: int, step_seconds: float) -> int:
    """The 0.5 s frame a push starts in: frames before it end before the push begins."""
    return int(np.floor(step * step_seconds / FRAME_S + 1e-9))


def to_recordings(activity: np.ndarray, sch: Schedule, rng: np.random.Generator) -> list[PumpProbe]:
    """(runs, steps, analysis units) -> one atlas-format recording per run: the run's recorded units,
    measurement noise added, pushes mapped to 0.5 s frames."""
    out = []
    names = [f"U{u:04d}" for u in sch.units]
    for i, run in enumerate(sch.runs):
        a = np.asarray(activity[i], float)[:, run["recorded"]]
        if not sch.framed:
            a = _resample(a, sch.step_seconds)
        sd = np.nanstd(a, axis=0)
        a = a + sch.protocol.measurement_noise * np.where(sd > 0, sd, 0) * rng.standard_normal(a.shape)
        pos = {p: r for r, p in enumerate(run["recorded"])}
        frames = [push_frame(s, sch.step_seconds) for s, _ in run["pushes"]]
        stims = [(pos[p], f) for (s, p), f in zip(run["pushes"], frames) if f < a.shape[0]]
        out.append(PumpProbe(uid=f"run{i:02d}", x=a.T.copy(), names=[names[p] for p in run["recorded"]],
                             classes=[names[p] for p in run["recorded"]], stims=stims, dt=FRAME_S,
                             all_stim_frames=frames))
    return out


def record_population(net, sch: Schedule, amplitude: float, rng: np.random.Generator, burn: int = 400) -> np.ndarray:
    """Run a model (networks.Network) through the schedule, all runs at once. Returns activity of the analysis
    units, (runs, steps, units), or (runs, frames, units) already averaged into 0.5 s frames when the steps are
    shorter than a frame (`sch.framed` is then set). Each run starts from its own random state and runs `burn`
    steps first."""
    R, T, n = len(sch.runs), sch.steps, net.n
    units = np.asarray(sch.units)
    x = net.init_state(R, rng)
    for _ in range(burn):
        x = net.step(x, net.noise_sd * rng.standard_normal((R, n)))
    push = np.zeros((T, R), int) - 1
    for i, run in enumerate(sch.runs):
        for s, p in run["pushes"]:
            push[s:s + sch.push_steps, i] = units[p]
    fine = sch.step_seconds < FRAME_S - 1e-9
    if fine:
        F = sch.frames
        f0, w0 = _frame_overlaps(T, sch.step_seconds)
        out = np.zeros((R, F + 1, len(units)))
        wt = np.zeros(F + 1)
    else:
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
        if fine:
            out[:, f0[t]] += w0[t] * a[:, units]
            wt[f0[t]] += w0[t]
            g = min(f0[t] + 1, F)
            out[:, g] += (1 - w0[t]) * a[:, units]
            wt[g] += 1 - w0[t]
        else:
            out[:, t] = a[:, units]
    if fine:
        sch.framed = True
        return (out / np.maximum(wt, 1e-12)[None, :, None])[:, :F].astype(np.float32)
    return out
