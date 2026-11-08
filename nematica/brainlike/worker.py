"""Runs one submission in its own process (the web app starts it with resource limits and a timeout).

    python -m nematica.brainlike.worker <job folder>

The job folder holds job.json ({"mode": "model" | "recordings" | "python", "file": name, "name": ...})
and the uploaded file. The result is written to result.json, or error.json with a message for the person
who uploaded it.
"""
from __future__ import annotations

import json
import sys
import traceback
import warnings
from pathlib import Path


def main(folder: str) -> int:
    d = Path(folder)
    job = json.loads((d / "job.json").read_text(encoding="utf-8"))
    warnings.filterwarnings("ignore")
    from .networks import NetworkError, load_network
    from .test import evaluate, recordings_from_upload, run_python, run_test
    f = d / job["file"]
    try:
        if job["mode"] == "model":
            res = run_test(load_network(f, job.get("name")), log=lambda m: None)
        elif job["mode"] == "recordings":
            import numpy as np
            with np.load(f, allow_pickle=False) as z:
                act, sch = recordings_from_upload(z)
            res = evaluate(act, sch, "recordings uploaded by the system's owner")
        elif job["mode"] == "python":
            import importlib.util
            spec = importlib.util.spec_from_file_location("submission", f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls = getattr(mod, job.get("class") or "System")
            res = run_python(cls(), log=lambda m: None)
        else:
            raise NetworkError(f"unknown mode {job['mode']!r}")
        (d / "result.json").write_text(json.dumps(res, default=float), encoding="utf-8")
        return 0
    except NetworkError as e:
        (d / "error.json").write_text(json.dumps({"error": str(e)}), encoding="utf-8")
    except Exception as e:                                         # noqa: BLE001
        (d / "error.json").write_text(json.dumps({"error": f"the test failed: {type(e).__name__}: {e}",
                                                  "trace": traceback.format_exc()[-2000:]}), encoding="utf-8")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
