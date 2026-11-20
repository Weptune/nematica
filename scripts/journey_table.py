"""Study J (docs/JOURNEY.md): activity tests passed per model and seed, from a run_same_worms cache.
python -I scripts/journey_table.py results/journey_copper -> prints the table and writes docs/figures/journey_<name>.json"""
import glob
import json
import re
import sys
from pathlib import Path

import pandas as pd

REST = ["L1.distribution", "L1.timescale", "L2.correlation", "L2.dimension", "L4.leadlag", "L4.dwell"]
cache = Path(sys.argv[1])
rows = []
for f in sorted(glob.glob(str(cache / "fluct_f*_*.csv"))):
    m = re.match(r"fluct_f(\d)_(.+?)(?:_s(\d))?\.csv$", Path(f).name)
    d = pd.read_csv(f)
    d = d[d.metric.isin(REST)]
    for _, r in d.iterrows():
        rows.append({"model": m.group(2), "seed": int(m.group(3) or 0), "fold": int(m.group(1)), "metric": r.metric, "inside": r.verdict == "inside", "v": {"inside": "I", "outside": "O", "too typical": "T"}.get(r.verdict, "?")})
d = pd.DataFrame(rows)
out = {}
for (model, seed), g in d.groupby(["model", "seed"]):
    if g.fold.nunique() < 3:
        continue
    per = {k: "".join(g[g.metric == k].sort_values("fold").v) for k in REST}
    out.setdefault(model, {})[int(seed)] = {"passed": int(sum(v.count("I") >= 2 for v in per.values())), **{k.split(".")[1]: v for k, v in per.items()}}
for model, s in out.items():
    print(model)
    for seed, v in sorted(s.items()):
        print("   seed", seed, "passed", v["passed"], " ".join(f"{k[:6]}:{x}" for k, x in v.items() if k != "passed"))
(Path(__file__).resolve().parents[1] / f"docs/figures/journey_{cache.name}.json").write_text(json.dumps(out, indent=1))
