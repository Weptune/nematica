"""Pilot (docs/MAP.md phase 1): AI systems only, no brain data. Measures the cached Pythia-70M and
Mamba-130M recordings (data/derived/map/ai, from nematica.map.ai.record on the book sample) and a random
tanh RNN, natively and through the calcium and spike recording models. Writes docs/figures/map_pilot_ai.json."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.map import measures, recording  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REC = {"native": lambda A: recording.native(A),
       "calcium": lambda A: recording.calcium(A, decay=8.0, frame=2, snr=4.0, rng=np.random.default_rng(3)),
       "spikes": lambda A: recording.spikes(A, mean_count=0.5, bin_steps=4, rng=np.random.default_rng(3))}


def random_rnn(N=1000, T=49152, g=1.5, seed=0, slow=0.0):
    rng = np.random.default_rng(seed)
    W = rng.standard_normal((N, N)) * g / np.sqrt(N)
    x = np.zeros(N)
    out = np.empty((T, N), np.float32)
    drive = np.zeros(N)
    a = np.exp(-1 / 200.0)
    P = rng.standard_normal((N, 4)) / 2
    z = np.zeros(4)
    for t in range(T):
        if slow:
            z = a * z + np.sqrt(1 - a * a) * rng.standard_normal(4)
            drive = slow * (P @ z)
        x = 0.8 * x + 0.2 * (W @ np.tanh(x) + drive + 0.3 * rng.standard_normal(N))
        out[t] = np.tanh(x)
    return out


systems = {"pythia-70m": lambda: np.load(ROOT / "data/derived/map/ai/pythia-70m.npy").astype(np.float32),
           "mamba-130m": lambda: np.load(ROOT / "data/derived/map/ai/mamba-130m-hf.npy").astype(np.float32),
           "random-rnn": lambda: random_rnn(T=20000),
           "random-rnn+slow": lambda: random_rnn(T=20000, slow=1.0)}
out = {}
for name, make in systems.items():
    A = make()
    out[name] = {}
    for r, f in REC.items():
        res = measures.measure_matched(f(A), seed=0)
        out[name][r] = {k: v for k, v in res.items() if not k.endswith("_sd")}
        print(name, r, {k: round(v, 3) if isinstance(v, float) else v for k, v in out[name][r].items()}, flush=True)
(ROOT / "docs/figures/map_pilot_ai.json").write_text(json.dumps(out, indent=1))
