"""Runs one submission in its own process; the web app starts it with a timeout.

    python -m nematica.brainlike.worker <job folder> [--score]

The job folder holds job.json ({"mode": "model" | "recordings" | "python", "file": name, "name": ...,
"schedule_seed": secret}) and the uploaded file. Models and recordings are tested in one step. Python code is
run in a first step that only writes activity.npz (the code never sees the scoring); a second step, `--score`,
which runs no uploaded code, scores it. The result goes to result.json (non-finite numbers as null), or
error.json with a message for the person who uploaded it.

Resource limits come from the environment (BRAINLIKE_MEMORY_MB, BRAINLIKE_TIMEOUT) and are set here, first,
before anything else is loaded.
"""
from __future__ import annotations

import json
import math
import os
import sys
import traceback
import warnings
from pathlib import Path


def _limits():
    try:
        import resource
    except ImportError:                                            # pragma: no cover (not on Linux)
        return
    mem = int(os.environ.get("BRAINLIKE_MEMORY_MB", "4096")) * 2 ** 20
    cpu = int(os.environ.get("BRAINLIKE_TIMEOUT", "1800"))
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (300 * 2 ** 20, 300 * 2 ** 20))


def clean(o):
    """JSON-safe: non-finite floats become null, numpy scalars become Python numbers."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        o = o.item()
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def _write(d: Path, name: str, obj) -> None:
    (d / name).write_text(json.dumps(clean(obj), allow_nan=False), encoding="utf-8")


def main(folder: str, score_only: bool = False) -> int:
    _limits()
    d = Path(folder)
    job = json.loads((d / "job.json").read_text(encoding="utf-8"))
    warnings.filterwarnings("ignore")
    import numpy as np

    from .networks import NetworkError, check_npz, load_network
    from .protocol import make_schedule
    from .test import evaluate, python_activity, recordings_from_upload, run_test
    f = d / job["file"]
    seed = job.get("schedule_seed")
    try:
        if score_only:
            with np.load(d / "activity.npz", allow_pickle=False) as z:
                act = z["activity"]
                n, dt, framed = int(z["n_units"]), float(z["step_seconds"]), bool(z["framed"])
                extra = {"push_strength": float(z["push_strength"])} if "push_strength" in z.files else {}
            sch = make_schedule(n, dt, seed=seed)
            want = (len(sch.runs), sch.frames if framed else sch.steps, len(sch.units))
            if act.shape != want:
                raise NetworkError(f"activity has shape {act.shape}; expected {want}")
            sch.framed = framed
            res = evaluate(act, sch, "Python system run by the test", extra)
        elif job["mode"] == "model":
            res = run_test(load_network(f, job.get("name")), log=lambda m: None, noise_check=True, schedule_seed=seed)
        elif job["mode"] == "recordings":
            check_npz(f, {"activity": None, "n_units": 1, "step_seconds": 1}, max_bytes=2 * 2 ** 30)
            with np.load(f, allow_pickle=False) as z:
                act, sch = recordings_from_upload(z)
            res = evaluate(act, sch, "recordings supplied by the system's owner")
        elif job["mode"] == "python":
            import importlib.util
            spec = importlib.util.spec_from_file_location("submission", f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls = getattr(mod, job.get("class") or "System", None)
            if cls is None:
                raise NetworkError(f"the file has no class {job.get('class') or 'System'}")
            act, sch, extra = python_activity(cls(), schedule_seed=seed)
            np.savez(d / "activity.npz", activity=act, n_units=sch.n_units, step_seconds=sch.step_seconds,
                     framed=sch.framed, **extra)
            return 0
        else:
            raise NetworkError(f"unknown mode {job['mode']!r}")
        _write(d, "result.json", res)
        return 0
    except NetworkError as e:
        _write(d, "error.json", {"error": str(e)})
    except MemoryError:
        _write(d, "error.json", {"error": "the test ran out of memory (limit "
                                          f"{os.environ.get('BRAINLIKE_MEMORY_MB', '4096')} MB)"})
    except Exception as e:                                         # noqa: BLE001
        _write(d, "error.json", {"error": f"the test failed: {type(e).__name__}: {e}",
                                 "trace": traceback.format_exc()[-2000:]})
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], "--score" in sys.argv[2:]))
