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
- 30 runs of 31.7 minutes (the atlas's median recording). In each run 45 analysis units are recorded; from
  20 s on, every 31 seconds (the atlas's spacing), one recorded unit is pushed for 2 seconds, as the atlas
  probed real worms with light. Two push slots per run are left empty, so a run has about as much undisturbed
  activity as an atlas worm (324 frames against a median of 345). Push times are fixed in seconds, so any
  step length from 0.005 to 2 s gives the same experiment. This is protocol version 3 (9 Nov 2026).
- The test adds the same measurement noise to every recording (0.1 SD of each unit), resamples to 0.5 s frames
  (the atlas frame) and measures:

| Signature | What it is |
|---|---|
| Few patterns at rest | Share of resting variance in the 3 strongest patterns: how few patterns the activity uses. |
| Slow activity | Share of each unit's activity that is slow (still correlated 10 to 40 s later). |
| Units move together | Mean absolute correlation between units at rest. |
| Timescale | Median time for a unit's activity to become half-forgotten (autocorrelation 0.5), in seconds. |
| Push spread | Share of units that a single push moves by more than 1 SD, minus the same share at moments with no push. |
| Push stands out | How much of the change after a push is caused by the push, against moments with no push. |
| Tiring on a second push | Log change in a unit's own response when it is pushed a second time, against matched controls. Negative = it answers less. |
| Copyable by watching | How well a linear model fitted only to resting activity predicts the push responses, as a share of how well runs agree with each other. Real worms: poorly. |

(The exact definitions are in `nematica/brainlike/signatures.py`; they are the research code's, checked to give
identical numbers on the atlas.)

- **Reference.** For each signature, the range spanned by 60 random groups of 30 real worms, widened by the
  finite-population correction because the atlas has only 113 worms. Stored as summary numbers in
  `nematica/brainlike/reference.json`; no recordings are needed to run the test.
- **Distance and score.** The distance is the mean, over the signatures, of how far the system sits from the real-worm
  median in units of the real-worm range; the score is the number of signatures inside the range, out of 8.
- **Step-free score.** Slow activity and timescale are read in seconds, so they depend on the step length a
  system declares. Every result also gives the score on the other six signatures.
- **Noise check.** For models the server runs, the result also gives the score at half and double the declared
  noise, with the push recalibrated each time.
- **Validity.** A result is scored only if the pushes are visible and specific: at least 300 pushes, at least 10
  recorded units per run with resting activity, pushed units moving on average at least 0.75 SD (real worms: 1.6)
  and at least 0.5 SD more than the other recorded units (real worms: 1.54), and at least 6 of the 8 signatures
  measurable. A signature that cannot be measured counts as outside, at distance 10. When the test runs a model
  itself it chooses the push strength that moves a pushed unit about 1.6 SD, or, if none does, the smallest
  strength that reaches 90% of the best response.

## Calibration (registered before it ran; README "Brain-likeness test for any artificial system", amendments 1 and 3)

*Distance* is the mean, over the eight signatures, of how far a system sits from the real-worm median in units
of the real-worm range (each capped at 10; a signature that cannot be measured counts as 10). The leaderboard
ranks by it. The step-free distance leaves out the two signatures read in seconds.

| System | Inside, of 8 | Distance (step-free) |
|---|---|---|
| Real worms, held out of the reference (3 groups of 30, scored against the other 83) | 8, 6, 8 | 0.29 to 0.60 (0.26 to 0.29) |
| Worm emulator fitted to the atlas (3 groups; built on these worms, not independent) | 5, 4, 5 | 0.84 to 1.04 (0.86 to 1.20) |
| Artificial-lab network with hidden slow drives at the worm's timescale (40 s) | 1 | 2.32 (2.73) |
| Small transformer trained on a synthetic language | 3 | 3.25 (2.50) |
| RNNs trained on memory or integration tasks, and the same before training | 0 to 1 | 4.37 to 5.16 |
| Random tanh RNN, plain lab network, lab network with 5 s drives | 0 to 1 | 4.88 to 4.91 |
| Linear model fitted to the worms' resting activity (3 groups) | 0 to 1 | 5.21 to 5.34 |
| Untrained transformer, spiking networks, random GRU | 0 to 1 | 5.73 to 6.62 |

What this shows:

- **The distance grades; the count is coarse.** Untrained networks often reach 1 of 8 by chance, so counts below
  about 3 say little. By the rule registered beforehand the count does not grade (untrained controls scored above
  the resting-activity model), so ranking by distance is a choice made after seeing the calibration, and the
  first systems submitted are its first real test.
- **Slow state helps.** Hidden drives at the worm's timescale bring a network much closer (2.32) than the same
  drives at 5 s (4.91).
- **Training is not enough by itself.** Training a small transformer moved it much closer (3.25 against 5.73);
  training recurrent networks on a memory or an integration task moved them slightly further away.
- **Watching is not enough.** A linear model fitted to the worms' own resting activity is as far from them as
  random networks: it has no slow activity, its activity spreads over far too many patterns, and its runs barely
  agree with each other about push responses.
- **Most artificial systems' runs disagree.** Real worm groups agree with each other about push responses at
  0.07 to 0.13; most artificial systems tested agree less, so "copyable by watching" cannot be read for them and
  counts as outside.

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
| `steps_per_run` | 31.7 minutes at your step length |
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
output. The test feeds noise and pushes through `input`, one value per unit, and checks that a push to
unit i moves unit i more than the others, so route `input[:, i]` to unit i alone. A model exported with a fixed batch
of 1 works too (it is run one run at a time). Metadata `noise_sd` and `step_seconds` set those choices.

```python
import torch

class Step(torch.nn.Module):
    def __init__(self, H):
        super().__init__()
        self.H, self.cell = H, torch.nn.LSTMCell(1, H)
    def forward(self, state, input):
        h, c = self.cell(torch.zeros(len(state), 1), (state[:, :self.H], state[:, self.H:]))
        h = h + input                                          # input[:, i] reaches hidden unit i, and only it
        return torch.cat([h, c], 1), h                         # next_state, activity: the H hidden units

H = 64
names = ["state", "input", "next_state", "activity"]
torch.onnx.export(Step(H).eval(), (torch.zeros(1, 2 * H), torch.zeros(1, H)), "model.onnx",
                  input_names=names[:2], output_names=names[2:],
                  dynamic_axes={k: {0: "batch"} for k in names}, opset_version=17)

import onnx                                                          # optional: choose noise and step length
m = onnx.load("model.onnx")
for k, v in {"noise_sd": "0.3", "step_seconds": "0.1"}.items():
    m.metadata_props.add(key=k, value=v)
onnx.save(m, "model.onnx")
```

Up to 4,096 units and 100 MB. Neither format runs Python on the server: npz files are checked from their headers
and read without pickle; ONNX graphs are parsed by onnxruntime (native code that has had security bugs, so keep
it updated), loaded from memory so a model cannot point its weights at other files. Models the server runs get a
secret schedule, so a model cannot know which units are recorded or when pushes come.

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
- **Disclose tuning.** The submission form asks whether the system was tuned against this test; the answer is shown
  with the result. Results from uploaded recordings are marked as supplied by the owner.
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
| `BRAINLIKE_MAX_QUEUE` | 50 | tests waiting at once, across all visitors |

Put it behind a reverse proxy with HTTPS (Caddy, nginx) and set the proxy's upload limit to about 401 MB; the app
refuses larger uploads from their Content-Length before reading them. Set `FORWARDED_ALLOW_IPS` to the proxy's
address, or every visitor will share the proxy's address and its limit of 3 waiting tests. Uploads are deleted
once tested; results are kept. A test interrupted by two restarts is marked failed rather than retried forever.
With a bind-mounted data folder, make it writable by user id 10001 (the container's user).
A machine with 2 CPU cores and 8 GB of memory runs one test at a time comfortably; a 300-unit rate network takes
a few seconds, a 4,096-unit ONNX model up to about half an hour.

**Python uploads are off by default.** Accepting them means running strangers' code. The uploaded code only
produces activity; a separate step that runs no uploaded code scores it, and anything the code writes as a result
is discarded. That does not make it safe: the code runs as the server's user and can reach the database and other
jobs. Turn code uploads on only where that code cannot reach anything: a container or VM with no network access,
no secrets, a read-only file system apart from the job folder, and a separate user (gVisor or Firecracker are
good choices). The per-test limits on CPU, memory and time are not a sandbox.

JSON endpoints: `GET /api/r/<id>` (status and result of one test), `GET /api/leaderboard`.
