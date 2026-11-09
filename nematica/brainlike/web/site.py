"""Serve the NEMATICA research site with the brain-likeness test inside it: the site at /, the test at /test/.

    python -m nematica.brainlike.web.site [port]        (default 8642, the research site's usual port)

Needs the packages in deploy/brainlike/requirements.txt. Test results are kept in ./brainlike_data (gitignored).
The calibration systems are put on the leaderboard at every start, so the board is never empty.
"""
from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("BRAINLIKE_BASE", "/test")
os.environ.setdefault("BRAINLIKE_DATA", str(ROOT / "brainlike_data"))
_path = os.environ.get("PYTHONPATH", "")                    # the test's worker process imports nematica too
if str(ROOT) not in _path.split(os.pathsep):
    os.environ["PYTHONPATH"] = os.pathsep.join(p for p in (str(ROOT), _path) if p)

import json  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import RedirectResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from . import app as test  # noqa: E402

CALIBRATION = ROOT / "nematica" / "brainlike" / "calibration"


def seed() -> int:
    n = 0
    for f in sorted(CALIBRATION.glob("*.json")):
        d = json.loads(f.read_text())
        test.add_reference(d["name"], d["result"], description=d.get("description", ""))
        n += 1
    return n


@asynccontextmanager
async def _lifespan(_app):
    seed()
    test._start()                                           # a mounted app's own startup does not run
    yield


site = FastAPI(title="NEMATICA", docs_url=None, redoc_url=None, openapi_url=None, lifespan=_lifespan)


@site.get("/test", include_in_schema=False)
def _test_slash():
    return RedirectResponse("/test/")


site.mount("/test", test.app)
site.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="research-site")


def main() -> None:
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8642
    print(f"NEMATICA site: http://localhost:{port}/   brain-likeness test: http://localhost:{port}/test/")
    uvicorn.run(site, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
