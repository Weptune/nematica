# Brain-likeness test

How close is an artificial network's activity to a living nervous system's? The test records a system at rest
and while briefly pushing single units, measures eight signatures of its activity, and checks each against
recordings of 113 real *C. elegans* nervous systems probed the same way (the signal propagation atlas,
Randi et al. 2023, Nature 623, 406-414, CC BY 4.0).

It asks only two things of a system: that its units can be recorded over time, and that one unit can be given
a brief push. A rate RNN, an LSTM or transformer run step by step, a spiking simulation, neuromorphic hardware,
an organoid on a multi-electrode array or a whole-brain emulation can all take it.

## The test

- Up to 120 of the system's units are chosen as analysis units (fixed by the system's size).
- 30 runs of 37 minutes. In each run 45 analysis units are recorded and, every 30 seconds, one recorded unit is
  pushed for 2 seconds, as the atlas probed real worms with light.
- The test adds the same measurement noise to every recording (0.1 SD of each unit), resamples to 0.5 s frames
  (the atlas frame) and measures:

| Signature | What it is |
|---|---|
| Ongoing dimension | How many independent patterns ongoing activity spreads over |
| Slow activity | Share of ongoing variance in slow fluctuations |
| Correlation | Average absolute correlation between units at rest |
| Timescale | How long ongoing activity remembers itself |
| Echo breadth | How widely one push spreads to the other recorded units |
| Evoked share | How much of the response to a push is explained by the push |
| Tiring | Whether responses to repeated pushes weaken |
| Watch share | How much the response to a push is predictable from activity before it |

(The exact definitions are in `nematica/brainlike/signatures.py`; they are the research code's, checked to give
identical numbers on the atlas.)

- **Reference.** For each signature, the range spanned by 60 random groups of 30 real worms, widened by the
  finite-population correction because the atlas has only 113 worms. Stored as summary numbers in
  `nematica/brainlike/reference.json`; no recordings are needed to run the test.
- **Score.** The number of signatures inside the real-worm range, out of 8. The result page also shows how far
  each signature is from the real-worm median, in units of that range.
- **Validity.** A result is scored only if the pushes are visible: at least 300 pushes, at least 10 recorded
  units per run, and pushed units moving on average at least 0.75 SD (real worms: 1.6). When the test runs a
  model itself it chooses the push strength that moves a pushed unit about 1.6 SD; a model that still responds
  weakly is scored with a note, since that is a property of the model.

## Calibration (registered before it ran, README "Brain-likeness test for any artificial system")

| System | Score |
|---|---|
| Real worms, held out of the reference (3 groups of 30, scored against the other 83) | 7, 6, 7 of 8 |
| Random tanh RNN, 120 units (npz) | 0 of 8 |
| Artificial-lab network, plain | 0 of 8 |
| Artificial-lab network with slow hidden drives | 0 of 8 |
| Random GRU, 120 units (ONNX) | 0 of 8 |

Real nervous systems land around 6 to 8; the baselines miss on every signature. The registered expectation that
slow hidden drives would raise the lab network's score failed: their 5 s time constant is too fast to count as
slow activity at the atlas's scale.

## Three ways in

### 1. Recordings (any system, run anywhere)

Get the schedule for your system's size and step length:

```
python -m nematica brainlike-schedule --n-units 300 --step-seconds 0.5 > schedule.json
```

or from the website (`/schedule?n_units=300&step_seconds=0.5`). It is deterministic: the same size and step
always give the same schedule. Fields:

| Field | Meaning |
|---|---|
| `units` | indices of your units the test analyses |
| `runs[i].recorded` | positions in `units` to record in run i |
| `runs[i].pushes` | `[step, position]`: at that step push that unit |
| `push_steps` | how many steps a push lasts (2 seconds) |
| `steps_per_run` | 37 minutes at your step length |
| `frames_per_run` | the same run in 0.5 s frames |

```python
import json, numpy as np
s = json.load(open("schedule.json"))
units = np.array(s["units"])
activity = np.full((len(s["runs"]), s["steps_per_run"], len(units)), np.nan, np.float32)
for i, run in enumerate(s["runs"]):
    rec = units[run["recorded"]]
    pushes = [(step, units[p]) for step, p in run["pushes"]]
    a = my_system_run(s["steps_per_run"], rec, pushes, s["push_steps"])   # (steps, len(rec))
    activity[i][:, run["recorded"]] = a
np.savez_compressed("recordings.npz", activity=activity, n_units=300, step_seconds=0.5)
```

- Start each run from a different state, with whatever ongoing input or noise the system normally has.
- Units a run does not record may be NaN; recorded units need a value at every step.
- Fast systems may average each run into 0.5 s frames and upload `(runs, frames_per_run, units)` instead.
- The push strength is yours. Pick one that clearly moves the pushed unit; the test checks this from the data,
  and does not score recordings where pushes are not visible.
- For spiking systems, record a rate (spike counts per step, or a smoothed rate); for imaging, the fluorescence
  trace.

Score locally with `python -m nematica brainlike recordings.npz`, or upload it (limit 400 MB).

### 2. A model the test runs

**Rate network (.npz):** arrays `W` (N by N, `W[i, j]` from unit j to unit i), optional `b`, `leak` (0 to 1,
default 1), `nonlinearity` (`tanh`, `relu`, `sigmoid` or `linear`), `noise_sd` (default 0.1) and
`step_seconds` (default 0.5). One step is `x = (1 - leak) x + leak (W phi(x) + b + u)`, the recorded activity
`phi(x)`, and `u` the test's input: independent noise of SD `noise_sd` plus pushes.

**Any recurrent model (.onnx):** one step, with inputs `state` (batch, S) and `input` (batch, N), outputs
`next_state` (batch, S) and optionally `activity` (batch, N). The state can hold anything (an LSTM's h and c,
synaptic variables, adaptation); the N units are what `activity` reports, or the state itself without that
output. The test feeds noise and pushes through `input`, one value per unit. A model exported with a fixed batch
of 1 works too (it is run one run at a time). Metadata `noise_sd` and `step_seconds` set those choices.

```python
import torch

class Step(torch.nn.Module):
    def __init__(self, N, H):
        super().__init__()
        self.H, self.cell, self.readout = H, torch.nn.LSTMCell(N, H), torch.nn.Linear(H, N)
    def forward(self, state, input):
        h, c = self.cell(input, (state[:, :self.H], state[:, self.H:]))
        return torch.cat([h, c], 1), torch.tanh(self.readout(h))       # next_state, activity

N, H = 100, 64
names = ["state", "input", "next_state", "activity"]
torch.onnx.export(Step(N, H).eval(), (torch.zeros(1, 2 * H), torch.zeros(1, N)), "model.onnx",
                  input_names=names[:2], output_names=names[2:],
                  dynamic_axes={k: {0: "batch"} for k in names}, opset_version=17)

import onnx                                                          # optional: choose noise and step length
m = onnx.load("model.onnx")
for k, v in {"noise_sd": "0.3", "step_seconds": "0.1"}.items():
    m.metadata_props.add(key=k, value=v)
onnx.save(m, "model.onnx")
```

Up to 4,096 units and 100 MB. Neither format runs uploaded code: npz files are read without pickle, ONNX graphs
by onnxruntime.

### 3. Python

```python
import numpy as np
from nematica.brainlike import BrainLike, run_python

class System(BrainLike):
    n_units, step_seconds = 300, 0.5
    calibrate_push, push_strength = True, 1.0      # optional: let the test choose the push strength

    def run(self, steps, record, pushes, push_steps, rng):
        """Simulate `steps` steps from a fresh state. At each (step, unit) in `pushes` drive that unit for
        `push_steps` steps (with self.push_strength). Return the activity of the units in `record`,
        shape (steps, len(record)). Use `rng` for all randomness."""
        ...

print(run_python(System())["score"])
```

`python -m nematica brainlike my_system.py --class System` writes the JSON result and the HTML report.

## Reading a result

- **One animal.** The reference is immobilised *C. elegans* probed with light every 30 seconds. A system inside
  on all eight signatures behaves like a worm nervous system under these conditions; that is not a claim about
  brains in general.
- **Inside means not distinguishable with 30 runs**, not identical.
- **Your choices count.** Noise level and step length shape ongoing activity and the time-based signatures.
  Report them with your score; the result records them.
- **Not a training target by accident.** If you tune a system against this test, say so: a tuned system's score
  measures the tuning as much as the system. The reference ranges come from all 113 atlas worms.

## Running the website

The site is a FastAPI app with a SQLite job store and a queue that runs each test in a separate process with
CPU, memory and time limits.

```
docker build -f deploy/brainlike/Dockerfile -t brainlike .
docker run -d --restart unless-stopped -p 8000:8000 -v brainlike-data:/data --name brainlike brainlike
```

On first start the calibration systems (held-out worm groups and baseline networks, summary numbers from
`nematica/brainlike/calibration/`) are put on the leaderboard as references. Without Docker:

```
pip install -r deploy/brainlike/requirements.txt
BRAINLIKE_DATA=/srv/brainlike python scripts/seed_brainlike_board.py
BRAINLIKE_DATA=/srv/brainlike uvicorn nematica.brainlike.web.app:app --host 0.0.0.0 --port 8000
```

| Setting | Default | Meaning |
|---|---|---|
| `BRAINLIKE_DATA` | `./brainlike_data` | jobs and the database |
| `BRAINLIKE_WORKERS` | 1 | tests run at once (each uses one CPU core) |
| `BRAINLIKE_TIMEOUT` | 1800 | seconds one test may take |
| `BRAINLIKE_MEMORY_MB` | 4096 | memory limit per test |
| `BRAINLIKE_ALLOW_CODE` | off | `1` accepts Python uploads (see below) |
| `FORWARDED_ALLOW_IPS` | 127.0.0.1 | addresses of your reverse proxy, so per-visitor limits see real addresses |

Put it behind a reverse proxy with HTTPS (Caddy, nginx) and set the proxy's upload limit to at least 400 MB.
A machine with 2 CPU cores and 8 GB of memory runs one test at a time comfortably; a 300-unit rate network takes
a few seconds, a 4,096-unit ONNX model up to about half an hour.

**Python uploads are off by default.** Accepting them means running strangers' code. Turn them on only where
that code cannot reach anything: a container or VM with no network access, no secrets, a read-only file system
apart from the job folder, and a separate user (gVisor or Firecracker are good choices). The per-test limits
on CPU, memory and time are not a sandbox.

JSON endpoints: `GET /api/r/<id>` (status and result of one test), `GET /api/leaderboard`.
