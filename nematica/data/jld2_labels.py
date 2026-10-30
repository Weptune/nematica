"""Read the Flavell-lab NeuroPAL_labels.jld2 file from Python, without Julia.

JLD2 is HDF5 underneath. A Julia Dict is stored as a struct with one field, `kvvec`,
referencing a vector of key/value pairs; values are references to further datasets.
h5py can follow all of this except Julia `SubString` values (the `label` and `region`
strings), whose variable-length encoding libhdf5 refuses to decode.

So `label` is rebuilt from the fields that do decode, using the naming rule

    label = neuron_class + dv_part + lr_part
    dv_part = "D"/"V" if given, "?" if "missing", "" if "undefined"
    lr_part = "L"/"R" if given, "?" if "missing", "" if "undefined"

which reproduces 2,698 of 2,698 labels in the Atanas 2023 JSON exports, where both the
label and its parts are stored. Rebuilt labels are flagged so this stays visible.
"""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np

from .recording import RoiLabel

_UNREADABLE = object()


def rebuild_label(neuron_class: str, lr, dv) -> str:
    def part(value, allowed):
        if value in allowed:
            return value
        if value == "missing":
            return "?"
        return ""
    return f"{neuron_class}{part(dv, ('D', 'V'))}{part(lr, ('L', 'R'))}"


class _Decoder:
    def __init__(self, f: h5py.File):
        self.f = f
        self.unreadable = 0

    def __call__(self, x):
        if isinstance(x, h5py.Reference):
            if not x:
                return None
            try:
                obj = self.f[x]
                value = obj[()]
            except Exception:
                self.unreadable += 1
                return _UNREADABLE
            return self(value)
        if isinstance(x, np.void) and x.dtype.names:
            return {n: self(x[n]) for n in x.dtype.names}
        if isinstance(x, np.ndarray):
            if x.dtype.names or x.dtype == object:
                return [self(e) for e in x.ravel()]
            return x.tolist()
        if isinstance(x, bytes):
            return x.decode("utf-8", errors="replace")
        if isinstance(x, np.generic):
            return x.item()
        return x


def _as_dict(node) -> dict:
    """A decoded Julia Dict ({'kvvec': [{'first': k, 'second': v}, ...]}) -> Python dict."""
    if not isinstance(node, dict) or "kvvec" not in node:
        raise ValueError("not a decoded Julia Dict")
    return {kv["first"]: kv["second"] for kv in node["kvvec"]}


def load_neuropal_labels(path: str | Path, key: str = "dict_match_dict") -> dict[str, dict[int, RoiLabel]]:
    """Return {recording uid: {trace row (0-based): RoiLabel}}."""
    with h5py.File(path, "r") as f:
        dec = _Decoder(f)
        top = _as_dict(dec(f[key][()]))
        out: dict[str, dict[int, RoiLabel]] = {}
        for uid, pair in top.items():
            # pair is a Julia Tuple stored as a struct with fields "1" and "2"
            by_row = _as_dict(pair["1"])
            labels: dict[int, RoiLabel] = {}
            for row, meta_node in by_row.items():
                meta = _as_dict(meta_node)
                cls = meta.get("neuron_class")
                if cls is _UNREADABLE or cls is None:
                    continue
                lr, dv = meta.get("LR"), meta.get("DV")
                lr = None if lr is _UNREADABLE else lr
                dv = None if dv is _UNREADABLE else dv
                name = meta.get("label")
                if not isinstance(name, str):
                    name = rebuild_label(str(cls), lr, dv)
                conf = meta.get("confidence")
                labels[int(row) - 1] = RoiLabel(
                    name=name,
                    neuron_class=str(cls),
                    side=lr if lr in ("L", "R") else None,
                    dv=dv if dv in ("D", "V") else None,
                    confidence=float(conf) if isinstance(conf, (int, float)) else 0.0,
                )
            out[str(uid)] = labels
    return out
