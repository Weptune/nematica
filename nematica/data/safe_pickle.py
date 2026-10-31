"""Read third-party pickles as plain data.

Only numpy array reconstruction and builtin containers are allowed; any other class in the
pickle becomes an inert attribute holder, so nothing from the pickle's own code base is
imported or executed. Used to read published model parameters (e.g. Creamer et al. 2024).
"""

from __future__ import annotations

import pickle

ALLOWED = {("numpy.core.multiarray", "_reconstruct"), ("numpy._core.multiarray", "_reconstruct"),
           ("numpy", "ndarray"), ("numpy", "dtype"), ("numpy.core.multiarray", "scalar"),
           ("numpy._core.multiarray", "scalar"), ("builtins", "slice"), ("collections", "OrderedDict")}


class Stub:
    """Holds the attributes of an object whose class is not trusted."""

    def __init__(self, *args, **kwargs):
        self._args = args

    def __setstate__(self, state):
        if isinstance(state, tuple) and len(state) == 2:
            state = {**(state[0] or {}), **(state[1] or {})}
        self.__dict__.update(state if isinstance(state, dict) else {"_state": state})


class SafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) in ALLOWED:
            return getattr(__import__(module, fromlist=[name]), name)
        return type(name, (Stub,), {"_origin": f"{module}.{name}"})


def load(path):
    with open(path, "rb") as fh:
        return SafeUnpickler(fh).load()
