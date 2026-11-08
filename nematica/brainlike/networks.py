"""Network formats the test accepts. Neither runs code from the uploader.

1. Rate RNN (.npz): arrays W (N x N, recurrent weights, W[i, j] = from unit j to unit i), optional b (N),
   optional `leak` (scalar in (0, 1], default 1), optional `nonlinearity` ("tanh", "relu", "sigmoid",
   "linear"; default "tanh"). One step:
       x <- (1 - leak) x + leak (W phi(x) + b + u),   activity = phi(x)
   where u is the test's input (noise and kicks), added to each unit's input.

2. ONNX (.onnx): any recurrent model exported with two inputs and one output,
       inputs  "state" (batch, N) float32 and "input" (batch, N) float32
       output  "next_state" (batch, N) float32
   The recorded activity of unit i is next_state[:, i]. The test's input (noise and kicks) is passed as
   "input", one value per unit: export your model so that input[:, i] adds to unit i's drive.

Optional metadata, in the npz (keys) or as ONNX metadata_props: `noise_sd` (SD of the independent input
noise per unit per step; default 0.1) and `step_seconds` (how many seconds one step stands for; default
0.5, the atlas frame). Both shape the test: a network with no noise has no ongoing activity, and the
slow-activity and timescale signatures are read in seconds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MAX_UNITS = 4096
NONLIN = {"tanh": np.tanh, "relu": lambda x: np.maximum(x, 0.0), "linear": lambda x: x,
          "sigmoid": lambda x: 1.0 / (1.0 + np.exp(-np.clip(x, -60, 60)))}


class NetworkError(ValueError):
    """A network the test cannot run, with a message meant for the person who uploaded it."""


@dataclass
class Network:
    n: int
    noise_sd: float = 0.1
    step_seconds: float = 0.5
    name: str = "network"
    meta: dict = field(default_factory=dict)

    def init_state(self, batch: int, rng: np.random.Generator) -> np.ndarray:
        return 0.1 * rng.standard_normal((batch, self.n))

    def step(self, state: np.ndarray, u: np.ndarray) -> np.ndarray:        # (batch, N) -> (batch, N)
        raise NotImplementedError

    def activity(self, state: np.ndarray) -> np.ndarray:                   # what a recording sees
        return state


class RateRNN(Network):
    def __init__(self, W, b=None, leak=1.0, nonlinearity="tanh", **kw):
        W = np.asarray(W, float)
        if W.ndim != 2 or W.shape[0] != W.shape[1]:
            raise NetworkError(f"W must be square (N x N); got shape {W.shape}")
        n = W.shape[0]
        if not 2 <= n <= MAX_UNITS:
            raise NetworkError(f"the network must have 2 to {MAX_UNITS} units; got {n}")
        if not np.isfinite(W).all():
            raise NetworkError("W contains NaN or infinite values")
        b = np.zeros(n) if b is None else np.asarray(b, float).reshape(-1)
        if b.shape != (n,) or not np.isfinite(b).all():
            raise NetworkError(f"b must be {n} finite numbers")
        if not 0 < float(leak) <= 1:
            raise NetworkError("leak must be in (0, 1]")
        if nonlinearity not in NONLIN:
            raise NetworkError(f"nonlinearity must be one of {sorted(NONLIN)}; got {nonlinearity!r}")
        super().__init__(n=n, **kw)
        self.W, self.b, self.leak, self.nl = W, b, float(leak), nonlinearity
        self.phi = NONLIN[nonlinearity]

    def step(self, x, u):
        return (1 - self.leak) * x + self.leak * (self.phi(x) @ self.W.T + self.b + u)

    def activity(self, x):
        return self.phi(x)


class OnnxNetwork(Network):
    def __init__(self, path, **kw):
        try:
            import onnxruntime as ort
        except ImportError as e:                                  # pragma: no cover
            raise NetworkError("ONNX support needs onnxruntime") from e
        so = ort.SessionOptions()
        so.intra_op_num_threads = 1
        so.inter_op_num_threads = 1
        try:
            self.sess = ort.InferenceSession(str(path), sess_options=so, providers=["CPUExecutionProvider"])
        except Exception as e:                                    # noqa: BLE001
            raise NetworkError(f"could not load the ONNX model: {e}") from e
        ins = {i.name: i for i in self.sess.get_inputs()}
        outs = [o.name for o in self.sess.get_outputs()]
        if set(ins) != {"state", "input"} or "next_state" not in outs:
            raise NetworkError(f"the ONNX model needs inputs 'state' and 'input' and an output 'next_state'; "
                               f"it has inputs {sorted(ins)} and outputs {outs}")
        n = ins["state"].shape[-1]
        if not isinstance(n, int) or not 2 <= n <= MAX_UNITS:
            raise NetworkError(f"'state' must have a fixed last dimension of 2 to {MAX_UNITS} units; got {n}")
        meta = self.sess.get_modelmeta().custom_metadata_map or {}
        for k in ("noise_sd", "step_seconds"):
            if k in meta and k not in kw:
                kw[k] = float(meta[k])
        super().__init__(n=n, **kw)

    def step(self, x, u):
        out = self.sess.run(["next_state"], {"state": x.astype(np.float32), "input": u.astype(np.float32)})[0]
        out = np.asarray(out, float)
        if out.shape != x.shape:
            raise NetworkError(f"next_state has shape {out.shape}; expected {x.shape}")
        return out


def load_network(path: str | Path, name: str | None = None) -> Network:
    path = Path(path)
    name = name or path.stem
    if path.suffix == ".npz":
        try:
            z = np.load(path, allow_pickle=False)
        except Exception as e:                                    # noqa: BLE001
            raise NetworkError(f"could not read the npz file: {e}") from e
        with z:
            if "W" not in z.files:
                raise NetworkError(f"the npz file needs an array W; it has {z.files}")
            kw = {"name": name}
            for k in ("noise_sd", "step_seconds"):
                if k in z.files:
                    kw[k] = float(z[k])
            nl = str(z["nonlinearity"]) if "nonlinearity" in z.files else "tanh"
            return RateRNN(z["W"], z["b"] if "b" in z.files else None,
                           float(z["leak"]) if "leak" in z.files else 1.0, nl, **kw)
    if path.suffix == ".onnx":
        return OnnxNetwork(path, name=name)
    raise NetworkError("upload a .npz (rate RNN weights) or an .onnx model")


def check_settings(net: Network) -> None:
    if not 0 < net.noise_sd <= 10:
        raise NetworkError("noise_sd must be in (0, 10]")
    if not 0.001 <= net.step_seconds <= 60:
        raise NetworkError("step_seconds must be between 0.001 and 60")
