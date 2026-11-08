"""Put the calibration results (held-out real worm groups and baseline networks) on a brain-likeness
website's leaderboard as references.

    BRAINLIKE_DATA=/srv/brainlike python scripts/seed_brainlike_board.py [nematica/brainlike/calibration]

The results hold summary numbers only (eight signature values and ranges per system), no recordings.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("BRAINLIKE_NO_QUEUE", "1")
from nematica.brainlike.web.app import DATA, add_reference  # noqa: E402

src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "nematica" / "brainlike" / "calibration"
files = sorted(src.glob("*.json"))
if not files:
    raise SystemExit(f"no calibration results in {src}; run scripts/calibrate_brainlike.py worms and systems first")
for f in files:
    d = json.loads(f.read_text())
    job = add_reference(d["name"], d["result"], description=d.get("description", ""))
    print(f"{job}: {d['name']} ({d['result']['score']} of {d['result']['out_of']})")
print(f"board: {DATA}")
