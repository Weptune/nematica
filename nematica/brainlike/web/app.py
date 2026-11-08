"""The brain-likeness website: upload a system, get its brain-likeness, see the leaderboard.

    uvicorn nematica.brainlike.web.app:app --host 0.0.0.0 --port 8000

Settings (environment):
  BRAINLIKE_DATA         folder for jobs and the database (default ./brainlike_data)
  BRAINLIKE_WORKERS      tests run at once (default 1)
  BRAINLIKE_TIMEOUT      seconds a test may take (default 1800)
  BRAINLIKE_MEMORY_MB    memory limit per test (default 4096)
  BRAINLIKE_ALLOW_CODE   "1" to accept Python code. Off by default. Only turn it on inside a sandbox with
                         no network and no secrets (see docs/BRAINLIKE.md).

Uploaded models and recordings are tested by a separate process with CPU, memory and time limits.
Rate-RNN weights (.npz, read without pickle) and ONNX graphs are data, not code.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from .. import report as REPORT
from ..protocol import make_schedule, schedule_json
from . import pages

DATA = Path(os.environ.get("BRAINLIKE_DATA", "brainlike_data")).resolve()
WORKERS = int(os.environ.get("BRAINLIKE_WORKERS", "1"))
TIMEOUT = int(os.environ.get("BRAINLIKE_TIMEOUT", "1800"))
MEMORY_MB = int(os.environ.get("BRAINLIKE_MEMORY_MB", "4096"))
ALLOW_CODE = os.environ.get("BRAINLIKE_ALLOW_CODE") == "1"
LIMITS = {"model": 100, "recordings": 400, "python": 1}          # MB per upload
SUFFIX = {"model": (".npz", ".onnx"), "recordings": (".npz",), "python": (".py",)}
MAX_WAITING_PER_IP = 3

DATA.mkdir(parents=True, exist_ok=True)
(DATA / "jobs").mkdir(exist_ok=True)
DB = DATA / "brainlike.sqlite"
_lock = threading.Lock()


def db():
    con = sqlite3.connect(DB, check_same_thread=False, timeout=30)
    con.row_factory = sqlite3.Row
    return con


with db() as _c:
    _c.execute("""create table if not exists jobs (id text primary key, created real, name text, author text,
                  description text, mode text, status text, score integer, out_of integer, distance real,
                  valid integer, public integer, reference integer default 0, ip text, error text)""")
    _cols = [r[1] for r in _c.execute("pragma table_info(jobs)")]
    for _col in ("tuned", "attempts"):
        if _col not in _cols:
            _c.execute(f"alter table jobs add column {_col} integer default 0")


@asynccontextmanager
async def _lifespan(_app):
    _start()
    yield


app = FastAPI(title="Brain-likeness test", docs_url=None, redoc_url=None, openapi_url=None, lifespan=_lifespan)


@app.middleware("http")
async def _upload_size(request: Request, call_next):
    """Refuse oversized uploads before their body is read (the form parser would otherwise spool it all)."""
    if request.method == "POST" and request.url.path == "/submit":
        n = request.headers.get("content-length")
        if n is None:
            return JSONResponse({"detail": "uploads need a Content-Length header"}, status_code=411)
        if not n.isdigit() or int(n) > max(LIMITS.values()) * 2 ** 20 + 2 ** 20:
            return JSONResponse({"detail": f"uploads are limited to {max(LIMITS.values())} MB"}, status_code=413)
    return await call_next(request)


def _clean(s: str, n: int) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()[:n]


# ---------------------------------------------------------------- the queue
MAX_QUEUE = int(os.environ.get("BRAINLIKE_MAX_QUEUE", "50"))
MAX_ATTEMPTS = 2


def _worker(d: Path, *extra: str) -> None:
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
           "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "HOME": str(d),
           "BRAINLIKE_MEMORY_MB": str(MEMORY_MB), "BRAINLIKE_TIMEOUT": str(TIMEOUT)}
    with (d / "worker.log").open("wb") as log:           # the worker caps its own output size
        subprocess.run([sys.executable, "-m", "nematica.brainlike.worker", str(d), *extra], cwd=d, env=env,
                       timeout=TIMEOUT, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)


def _checked(r: dict) -> dict:
    """result.json as the parent trusts it: typed fields only (the rendering escapes everything else)."""
    def num(v, kind):
        return None if v is None else kind(v)
    out = {"score": num(r.get("score"), int), "out_of": int(r["out_of"]), "valid": bool(r["valid"]),
           "mean_abs_distance": num(r.get("mean_abs_distance"), float)}
    if out["valid"] and (out["score"] is None or not 0 <= out["score"] <= out["out_of"] or out["mean_abs_distance"] is None):
        raise ValueError("inconsistent result")
    return out


def _run(job_id: str):
    d = DATA / "jobs" / job_id
    job = json.loads((d / "job.json").read_text())
    for f in ("result.json", "error.json", "activity.npz"):
        (d / f).unlink(missing_ok=True)
    try:
        _worker(d)
        if job["mode"] == "python" and (d / "activity.npz").exists():
            # anything the uploaded code wrote is discarded; a step that runs no uploaded code scores it
            for f in ("result.json", "error.json"):
                (d / f).unlink(missing_ok=True)
            _worker(d, "--score")
    except subprocess.TimeoutExpired:
        (d / "error.json").write_text(json.dumps({"error": f"the test took longer than {TIMEOUT // 60} minutes"}))
    upload = d / job["file"]
    upload.unlink(missing_ok=True)                        # results are kept, uploads are not
    (d / "activity.npz").unlink(missing_ok=True)
    with _lock, db() as c:
        try:
            r = _checked(json.loads((d / "result.json").read_text())) if (d / "result.json").exists() else None
        except Exception:                                 # noqa: BLE001
            (d / "result.json").unlink(missing_ok=True)
            r = None
            (d / "error.json").write_text(json.dumps({"error": "the test produced an unreadable result"}))
        if r is not None:
            c.execute("update jobs set status='done', score=?, out_of=?, distance=?, valid=? where id=?",
                      (r["score"], r["out_of"], r["mean_abs_distance"], int(r["valid"]), job_id))
        else:
            try:
                err = str(json.loads((d / "error.json").read_text())["error"])
            except Exception:                             # noqa: BLE001
                err = "the test stopped unexpectedly, probably at the memory or CPU limit"
            c.execute("update jobs set status='failed', error=? where id=?", (err[:1000], job_id))


def _loop():
    while True:
        with _lock, db() as c:
            row = c.execute("select id from jobs where status='queued' order by created limit 1").fetchone()
            if row:
                c.execute("update jobs set status='running', attempts=coalesce(attempts, 0) + 1 where id=?", (row["id"],))
        if row:
            try:
                _run(row["id"])
            except Exception as e:                   # never let the queue thread die
                with _lock, db() as c:
                    c.execute("update jobs set status='failed', error=? where id=?", (f"server error: {e}", row["id"]))
        else:
            time.sleep(2)


def _start():
    with db() as c:                                   # tests cut off by a restart go back in the queue, once
        c.execute("update jobs set status='failed', error='the server restarted twice during this test' "
                  "where status='running' and coalesce(attempts, 0) >= ?", (MAX_ATTEMPTS,))
        c.execute("update jobs set status='queued' where status='running'")
    if os.environ.get("BRAINLIKE_NO_QUEUE") != "1":
        for _ in range(max(1, WORKERS)):
            threading.Thread(target=_loop, daemon=True).start()


# ---------------------------------------------------------------- pages
def _board(limit: int | None = None):
    with db() as c:
        q = ("select id, name, author, score, out_of, distance, reference, mode, tuned, created from jobs "
             "where status='done' and valid=1 and public=1 and distance is not null "
             "order by distance asc, score desc, created asc")
        rows = c.execute(q + (f" limit {int(limit)}" if limit else "")).fetchall()
    return [dict(r) for r in rows]


EXAMPLES = (("real-worms-held-out-of-the-reference-group-3", "Real worms the test never saw", "#2e7d4f"),
            ("worm-emulator-minimal-recipe-group-3", "Worm emulator fitted to the atlas", "#2a4fb8"),
            ("random-tanh", "Random recurrent network", "#b8443f"))


def _examples():
    """Reference results shown on the front page, if they are on the board."""
    out = []
    with db() as c:
        for key, label, color in EXAMPLES:
            row = c.execute("select id from jobs where reference=1 and status='done' and id like ? order by id limit 1",
                            (f"ref-{key}%",)).fetchone()
            if row:
                res = json.loads((DATA / "jobs" / row["id"] / "result.json").read_text())
                out.append((label, res["signatures"], color))
    return out


@app.get("/", response_class=HTMLResponse)
def home():
    return pages.home(_board(10), ALLOW_CODE, LIMITS, _examples())


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/leaderboard", response_class=HTMLResponse)
def leaderboard():
    return pages.leaderboard(_board())


@app.get("/how", response_class=HTMLResponse)
def how():
    return pages.how(ALLOW_CODE)


@app.get("/schedule")
def schedule(n_units: int, step_seconds: float = 0.5):
    if not 10 <= n_units <= 1_000_000 or not 0.005 <= step_seconds <= 2:
        raise HTTPException(400, "n_units must be 10 to 1,000,000 and step_seconds 0.005 to 2")
    s = make_schedule(n_units, step_seconds)
    return Response(schedule_json(s), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="schedule_{n_units}u_{step_seconds:g}s.json"'})


@app.post("/submit")
async def submit(request: Request, mode: str = Form(...), name: str = Form(...), author: str = Form(""),
                 description: str = Form(""), public: str = Form(""), tuned: str = Form(""), class_name: str = Form("System"),
                 file: UploadFile = File(...)):
    if mode not in LIMITS or (mode == "python" and not ALLOW_CODE):
        raise HTTPException(400, "this kind of submission is not accepted on this server")
    fname = (file.filename or "").lower()
    if not fname.endswith(SUFFIX[mode]):
        raise HTTPException(400, f"for this kind of submission upload a {' or '.join(SUFFIX[mode])} file")
    name = _clean(name, 80)
    if not name:
        raise HTTPException(400, "give your system a name")
    ip = request.client.host if request.client else "?"
    with db() as c:
        n = c.execute("select count(*) from jobs where ip=? and status in ('queued','running')", (ip,)).fetchone()[0]
    if n >= MAX_WAITING_PER_IP:
        raise HTTPException(429, "you already have tests waiting; submit again when one finishes")
    job_id = secrets.token_urlsafe(9)
    d = DATA / "jobs" / job_id
    d.mkdir(parents=True)
    target = d / ("upload" + Path(fname).suffix)
    size, cap = 0, LIMITS[mode] * 2 ** 20
    with target.open("wb") as fh:
        while chunk := await file.read(2 ** 20):
            size += len(chunk)
            if size > cap:
                break
            fh.write(chunk)
    if size > cap or size == 0:
        target.unlink()
        d.rmdir()
        raise HTTPException(413 if size else 400,
                            f"files of this kind are limited to {LIMITS[mode]} MB" if size else "the file is empty")
    job = {"mode": mode, "file": target.name, "name": name,
           "class": re.sub(r"\W", "", class_name)[:60] or "System",
           # models the server runs get a secret schedule; recordings must follow the public one
           "schedule_seed": None if mode == "recordings" else secrets.randbits(31)}
    (d / "job.json").write_text(json.dumps(job))
    with _lock, db() as c:
        waiting = c.execute("select count(*) from jobs where ip=? and status in ('queued','running')", (ip,)).fetchone()[0]
        total = c.execute("select count(*) from jobs where status='queued'").fetchone()[0]
        if waiting >= MAX_WAITING_PER_IP or total >= MAX_QUEUE:
            target.unlink()
            (d / "job.json").unlink()
            d.rmdir()
            raise HTTPException(429, "you already have tests waiting; submit again when one finishes" if waiting >= MAX_WAITING_PER_IP
                                else "the queue is full; try again later")
        c.execute("insert into jobs (id, created, name, author, description, mode, status, public, ip, tuned) "
                  "values (?,?,?,?,?,?,?,?,?,?)",
                  (job_id, time.time(), name, _clean(author, 80), _clean(description, 600), mode, "queued",
                   1 if public else 0, ip, 1 if tuned else 0))
    return RedirectResponse(f"/r/{job_id}", status_code=303)


def _job(job_id: str):
    if not re.fullmatch(r"[\w-]{6,80}", job_id):
        raise HTTPException(404)
    with db() as c:
        row = c.execute("select * from jobs where id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no test with this address")
    return dict(row)


@app.get("/r/{job_id}", response_class=HTMLResponse)
def result(job_id: str):
    j = _job(job_id)
    if j["status"] == "done":
        res = json.loads((DATA / "jobs" / job_id / "result.json").read_text())
        meta = {"author": j["author"], "description": j["description"], "tuned": bool(j.get("tuned")), "mode": j["mode"]}
        return pages.with_nav(REPORT.render(res, j["name"], meta))
    with db() as c:
        ahead = c.execute("select count(*) from jobs where status='queued' and created < ?",
                          (j["created"],)).fetchone()[0]
    return pages.status(j, ahead)


@app.get("/api/r/{job_id}")
def result_json(job_id: str):
    from ..worker import clean
    j = _job(job_id)
    out = {"id": job_id, "name": j["name"], "status": j["status"], "error": j["error"]}
    if j["status"] == "done":
        out["result"] = clean(json.loads((DATA / "jobs" / job_id / "result.json").read_text()))
    return JSONResponse(out)


@app.get("/api/leaderboard")
def leaderboard_json():
    return JSONResponse([{k: r[k] for k in ("id", "name", "author", "score", "out_of", "distance", "reference", "mode", "tuned")}
                         for r in _board()])


def add_reference(name: str, result: dict, author: str = "NEMATICA reference", description: str = "") -> str:
    """Put a reference result (held-out worms, baseline networks) on the board."""
    job_id = "ref-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
    d = DATA / "jobs" / job_id
    d.mkdir(parents=True, exist_ok=True)
    from ..worker import clean
    (d / "result.json").write_text(json.dumps(clean(result)))
    with _lock, db() as c:
        c.execute("delete from jobs where id=?", (job_id,))
        c.execute("insert into jobs (id, created, name, author, description, mode, status, score, out_of, distance, "
                  "valid, public, reference) values (?,?,?,?,?,?,?,?,?,?,?,?,1)",
                  (job_id, time.time(), name, author, description, "reference", "done", result["score"],
                   result["out_of"], result.get("mean_abs_distance"), int(result["valid"]), 1))
    return job_id
