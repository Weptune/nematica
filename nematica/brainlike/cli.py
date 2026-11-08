"""Brain-likeness test on your own machine.

    python -m nematica brainlike my_rnn.npz                 (rate RNN weights)
    python -m nematica brainlike model.onnx                 (any recurrent model, one step)
    python -m nematica brainlike recordings.npz             (recordings that followed the schedule)
    python -m nematica brainlike my_system.py --class System
    python -m nematica brainlike-schedule --n-units 300 --step-seconds 0.5 > schedule.json

Writes <name>.brainlike.json and <name>.brainlike.html next to --out (default results/brainlike/).
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path


def run_file(path: str | Path, class_name: str = "System", name: str | None = None, log=print,
             noise_check: bool = True) -> tuple[str, dict]:
    import numpy as np

    from .networks import NetworkError, load_network
    from .test import evaluate, recordings_from_upload, run_python, run_test
    path = Path(path)
    if path.suffix == ".py":
        import importlib.util
        spec = importlib.util.spec_from_file_location("submission", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, class_name):
            raise NetworkError(f"{path.name} has no class {class_name}; pass --class")
        system = getattr(mod, class_name)()
        own = getattr(system, "name", "system")
        return name or (own if own != "system" else path.stem), run_python(system, log=log)
    name = name or path.stem
    if path.suffix == ".npz":
        with np.load(path, allow_pickle=False) as z:
            if "activity" in z.files:
                act, sch = recordings_from_upload(z)
                return name, evaluate(act, sch, "recordings made by the system's owner")
    return name, run_test(load_network(path, name), log=log, noise_check=noise_check)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m nematica brainlike", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help=".npz weights, .onnx model, .npz recordings, or .py with a BrainLike class")
    ap.add_argument("--class", dest="cls", default="System", help="class name in a .py file (default System)")
    ap.add_argument("--name", default=None)
    ap.add_argument("--out", default="results/brainlike")
    ap.add_argument("--no-noise-check", action="store_true", help="models: skip the runs at half and double noise")
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    from .networks import NetworkError
    from .report import render
    try:
        name, res = run_file(a.file, a.cls, a.name, log=lambda m: print(m, file=sys.stderr, flush=True),
                             noise_check=not a.no_noise_check)
    except NetworkError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() or c in "-_." else "_" for c in name).strip("._") or "system"
    (out / f"{slug}.brainlike.json").write_text(json.dumps({"name": name, **res}, indent=1, default=float))
    (out / f"{slug}.brainlike.html").write_text(render(res, name), encoding="utf-8")
    if res["valid"]:
        print(f"{name}: {res['score']} of {res['out_of']} signatures inside the real-worm range "
              f"({res['score_step_free']} of {res['out_of_step_free']} that do not depend on the step length)")
        for c in res.get("noise_check", []):
            print(f"  at {c['factor']:g}x noise: {c['score']} of {res['out_of']}" if c["valid"] else f"  at {c['factor']:g}x noise: not scored")
    else:
        print(f"{name}: not scored ({'; '.join(res['problems'])})")
    for k, v in res["signatures"].items():
        d = v.get("distance")
        print(f"  {k:13s} {'inside ' if v.get('inside') else 'outside'} "
              f"{'' if d is None else f'{d:+.2f}'}")
    print(f"Report: {out / (slug + '.brainlike.html')}")
    return 0 if res["valid"] else 1


def schedule_main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m nematica brainlike-schedule")
    ap.add_argument("--n-units", type=int, required=True)
    ap.add_argument("--step-seconds", type=float, default=0.5)
    a = ap.parse_args(argv)
    from .protocol import make_schedule, schedule_json
    from .test import MAX_STEP, MIN_STEP, MIN_UNITS
    if not MIN_UNITS <= a.n_units <= 1_000_000 or not MIN_STEP <= a.step_seconds <= MAX_STEP:
        ap.error(f"--n-units must be {MIN_UNITS} to 1,000,000 and --step-seconds {MIN_STEP} to {MAX_STEP}")
    print(schedule_json(make_schedule(a.n_units, a.step_seconds)))
    return 0
