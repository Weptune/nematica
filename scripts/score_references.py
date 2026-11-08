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

NOTES = {"VAR(3) from rest": "Reads out one row per neuron class, which inflates echo size and spread (README, emulator step 5).",
         "first hybrid": "Reads out one row per neuron class, which inflates echo size and spread (README, emulator step 5)."}
COPIES = {"silent (independent noise)": "examples/copies/silent.py:Silent",
          "linear model from rest": "examples/copies/linear_rest.py:LinearRest",
          "VAR(3) from rest": "examples/copies/reference.py:Var3Rest",
          "first hybrid": "examples/copies/reference.py:FirstHybrid"}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--split", choices=("cv3", "blocks1"), action="append", help="score only this split (repeatable); "
                    "reports from separate runs are merged by scripts/merge_reports.py")
    a = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    splits = tuple(a.split) if a.split else ("cv3", "blocks1")
    res = score_many({k: load_copy(v) for k, v in COPIES.items()}, "data/raw/randi2023_wt_npz", seeds=a.seeds,
                     splits=splits, log=lambda m: print(m, flush=True))
    tag = "" if len(splits) == 2 else "." + splits[0]
    for name, rows in res.items():
        slug = name.split(" (")[0].lower().replace(" ", "_").replace("(", "").replace(")", "")
        print(write_report(name, rows, f"results/scores/reference/{slug}{tag}.json",
                           meta={"date": datetime.date.today().isoformat(), "command": f"scripts/score_references.py ({COPIES[name]})",
                                 "note": NOTES.get(name)}))
