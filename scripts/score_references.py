"""Score the reference copies on the benchmark (sharing each fold's real-worm ruler) and write their
reports to results/scores/reference/. The emulator's report comes from the research runs
(scripts/cache_to_report.py), which used the same procedure with five seeds.

    python scripts/score_references.py [--seeds 3]
"""
import argparse
import datetime
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.score import load_copy, score_many, write_report  # noqa: E402

COPIES = {"silent (independent noise)": "examples/copies/silent.py:Silent",
          "linear model from rest": "examples/copies/linear_rest.py:LinearRest",
          "VAR(3) from rest": "examples/copies/reference.py:Var3Rest",
          "first hybrid": "examples/copies/reference.py:FirstHybrid"}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=3)
    a = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    res = score_many({k: load_copy(v) for k, v in COPIES.items()}, "data/raw/randi2023_wt_npz", seeds=a.seeds,
                     log=lambda m: print(m, flush=True))
    for name, rows in res.items():
        slug = name.split(" (")[0].lower().replace(" ", "_").replace("(", "").replace(")", "")
        print(write_report(name, rows, f"results/scores/reference/{slug}.json",
                           meta={"date": datetime.date.today().isoformat(), "worms": 113, "command": f"scripts/score_references.py ({COPIES[name]})"}))
