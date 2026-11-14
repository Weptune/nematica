"""A4 and A5 through scripts/map_ais_fast.py with shorter truncation (memory only: the 25,000-step truncation
ran out of memory on this 8 GB machine). A4 keeps 8,000 native steps (2 recordings of one 5,000-timescale
crop need about 6,000 at the x16 hold), A5 12,000 (7 recordings would need about 21,000, so its stretches
overlap and the result carries the overlap flag). Everything else is map_ais_fast.run unchanged."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_ais_fast as F  # noqa: E402

LEN = {"A4": 8000, "A5": 12000}

if __name__ == "__main__":
    for aid in sys.argv[1:] or ["A4", "A5"]:
        F.TRUNC = {"R2": LEN[aid], "R4g": LEN[aid]}
        F.run(aid, ("R2", "R4g"))
