"""Network formats the test accepts. Neither runs code from the uploader.

1. Rate RNN (.npz): arrays W (N x N, recurrent weights, W[i, j] = from unit j to unit i), optional b (N),
   optional `leak` (scalar in (0, 1], default 1), optional `nonlinearity` ("tanh", "relu", "sigmoid",
   "linear"; default "tanh"). One step:
       x <- (1 - leak) x + leak (W phi(x) + b + u),   activity = phi(x)
   where u is the test's input (noise and kicks), added to each unit's input.

2. ONNX (.onnx): any recurrent model exported as one step,
       inputs  "state" (batch, S) float32 and "input" (batch, N) float32
       outputs "next_state" (batch, S) float32 and, optionally, "activity" (batch, N) float32
   The state can hold anything (an LSTM's h and c, synaptic variables, spike traces...). The units are
   what "activity" reports; without that output the units are the state itself (N = S). The test's input
   (noise and pushes) is passed as "input", one value per unit: export your model so that input[:, i]
   adds to unit i's drive. A model exported with a fixed batch of 1 is run one run at a time.

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
        if not 10 <= n <= MAX_UNITS:
            raise NetworkError(f"the network must have 10 to {MAX_UNITS} units; got {n}")
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
            # loaded from bytes, so a model cannot point its weights at files outside the upload
            self.sess = ort.InferenceSession(Path(path).read_bytes(), sess_options=so, providers=["CPUExecutionProvider"])
        except Exception as e:                                    # noqa: BLE001
            raise NetworkError(f"could not load the ONNX model: {e}") from e
        ins = {i.name: i for i in self.sess.get_inputs()}
        outs = {o.name: o for o in self.sess.get_outputs()}
        if set(ins) != {"state", "input"} or "next_state" not in outs:
            raise NetworkError(f"the ONNX model needs inputs 'state' and 'input' and an output 'next_state' "
                               f"(optionally 'activity'); it has inputs {sorted(ins)} and outputs {sorted(outs)}")
        S, n = ins["state"].shape[-1], ins["input"].shape[-1]
        for what, v in (("state", S), ("input", n)):
            if not isinstance(v, int) or v < 1:
                raise NetworkError(f"'{what}' must have a fixed last dimension; got {v}")
        if not 10 <= n <= MAX_UNITS:
            raise NetworkError(f"the model must have 10 to {MAX_UNITS} units ('input' last dimension); got {n}")
        if S > 4 * MAX_UNITS:
            raise NetworkError(f"'state' may hold at most {4 * MAX_UNITS} numbers; got {S}")
        self.has_activity = "activity" in outs
        if not self.has_activity and S != n:
            raise NetworkError(f"without an 'activity' output, 'state' and 'input' must have the same size; "
                               f"got {S} and {n}")
        b = ins["state"].shape[0]
        self.batch1 = isinstance(b, int) and b == 1
        self.S = S
        self._outs = ["next_state"] + (["activity"] if self.has_activity else [])
        self._last = None
        meta = self.sess.get_modelmeta().custom_metadata_map or {}
        for k in ("noise_sd", "step_seconds"):
            if k in meta and k not in kw:
                try:
                    kw[k] = float(meta[k])
                except ValueError:
                    raise NetworkError(f"metadata {k} must be a number; got {meta[k]!r}") from None
        super().__init__(n=n, **kw)

    def init_state(self, batch, rng):
        return 0.1 * rng.standard_normal((batch, self.S))

    def _call(self, x, u):
        feed = {"state": x.astype(np.float32), "input": u.astype(np.float32)}
        if self.batch1 and x.shape[0] != 1:
            parts = [self._call(x[i:i + 1], u[i:i + 1]) for i in range(x.shape[0])]
            return [np.concatenate([p[k] for p in parts]) for k in range(len(self._outs))]
        return [np.asarray(o, float) for o in self.sess.run(self._outs, feed)]

    def step(self, x, u):
        out = self._call(x, u)
        nxt = out[0]
        if nxt.shape != x.shape:
            raise NetworkError(f"next_state has shape {nxt.shape}; expected {x.shape}")
        if self.has_activity:
            a = out[1].reshape(x.shape[0], -1)
            if a.shape[1] != self.n:
                raise NetworkError(f"activity has {a.shape[1]} units; 'input' has {self.n}")
            self._last = (nxt, a)
        return nxt

    def activity(self, x):
        if not self.has_activity:
            return x
        if self._last is not None and self._last[0] is x:
            return self._last[1]
        raise NetworkError("activity was requested for a state the model did not just produce")


def check_npz(path, allowed: dict, max_bytes: int) -> None:
    """Check an uploaded npz before loading anything: only the expected arrays, plain numbers, sizes read from
    the headers (allowed: name -> maximum number of elements, None for no limit beyond max_bytes)."""
    import zipfile
    try:
        zf = zipfile.ZipFile(path)
    except Exception as e:                                        # noqa: BLE001
        raise NetworkError(f"not a valid npz file: {e}") from e
    with zf:
        infos = zf.infolist()
        if sum(i.file_size for i in infos) > max_bytes:
            raise NetworkError(f"the arrays add up to more than {max_bytes // 2 ** 20} MB once unpacked")
        for info in infos:
            key = info.filename[:-4] if info.filename.endswith(".npy") else info.filename
            if key not in allowed:
                raise NetworkError(f"unexpected array {key!r}; allowed: {', '.join(sorted(allowed))}")
            with zf.open(info) as fh:
                try:
                    version = np.lib.format.read_magic(fh)
                    shape, _, dtype = (np.lib.format.read_array_header_1_0(fh) if version == (1, 0)
                                       else np.lib.format.read_array_header_2_0(fh))
                except Exception as e:                            # noqa: BLE001
                    raise NetworkError(f"array {key!r} could not be read: {e}") from e
            if dtype.hasobject:
                raise NetworkError(f"array {key!r} holds Python objects; numbers only")
            cap = allowed[key]
            if cap is not None and int(np.prod(shape)) > cap:
                raise NetworkError(f"array {key!r} has {int(np.prod(shape))} elements; at most {cap}")


MODEL_KEYS = {"W": MAX_UNITS * MAX_UNITS, "b": MAX_UNITS, "leak": 1, "nonlinearity": 1, "noise_sd": 1, "step_seconds": 1}


def load_network(path: str | Path, name: str | None = None) -> Network:
    path = Path(path)
    name = name or path.stem
    if path.suffix == ".npz":
        check_npz(path, MODEL_KEYS, max_bytes=8 * MAX_UNITS * MAX_UNITS + 2 ** 20)
        try:
            with np.load(path, allow_pickle=False) as z:
                arrays = {k: z[k] for k in z.files}
        except Exception as e:                                    # noqa: BLE001  (object arrays are refused here)
            raise NetworkError(f"could not read the npz file (numbers only, no Python objects): {e}") from e
        if "W" not in arrays:
            raise NetworkError(f"the npz file needs an array W; it has {sorted(arrays)}")
        kw = {"name": name}
        try:
            for k in ("noise_sd", "step_seconds"):
                if k in arrays:
                    kw[k] = float(np.asarray(arrays[k]).item())
            leak = float(np.asarray(arrays["leak"]).item()) if "leak" in arrays else 1.0
        except (TypeError, ValueError):
            raise NetworkError("noise_sd, step_seconds and leak must be single numbers") from None
        nl = str(np.asarray(arrays["nonlinearity"]).item()) if "nonlinearity" in arrays else "tanh"
        if arrays["W"].dtype.kind not in "fiu":
            raise NetworkError("W must hold numbers")
        return RateRNN(arrays["W"], arrays.get("b"), leak, nl, **kw)
    if path.suffix == ".onnx":
        return OnnxNetwork(path, name=name)
    raise NetworkError("upload a .npz (rate RNN weights) or an .onnx model")


def check_settings(net: Network) -> None:
    if not 0 < net.noise_sd <= 10:
        raise NetworkError("noise_sd must be in (0, 10]")
    if not 0.005 <= net.step_seconds <= 2.0:
        raise NetworkError("step_seconds must be between 0.005 and 2")
    if net.n < 10:
        raise NetworkError("the network needs at least 10 units")
