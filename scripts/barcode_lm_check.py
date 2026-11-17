"""Study 4 feasibility F3 (before freezing): time and peak memory of one language-model generation and one
recording, using Study 2's median NM1 instrument as a stand-in (no Barcoding activity is used)."""
import importlib.util
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("br", ROOT / "scripts/barcode_run.py")
BR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BR)

model = sys.argv[1] if len(sys.argv) > 1 else "EleutherAI/pythia-410m-seed{s}"
mice = [json.loads(l) for l in open(ROOT / "docs/figures/slow_runs/mice.jsonl")]
used = set(json.load(open(ROOT / "docs/figures/slow_runs/mice_table.json"))["rows"])
mice = [m for m in mice if m["id"] in used]
bpt = np.array([m["profile"]["bins_per_tau"] for m in mice])
prof = mice[int(np.argsort(bpt)[len(bpt) // 2])]["profile"]
t = time.time()
As, st, n = BR.gen_lm(model, 0, prof, 90)
t1 = time.time()
lvl = {"profile": prof, "bins": 400, "repeats": 90, "units": 200}
recs = [BR.record(As[k], st, n, lvl, seed=k) for k in range(4)]
t2 = time.time()
print(json.dumps({"model": model, "tokens": n, "A": [a.shape for a in As], "generate_s": round(t1 - t, 1),
                  "record_4_depths_s": round(t2 - t1, 1), "M1": [round(r["M1"], 3) for r in recs],
                  "reached": [r["reached"] for r in recs], "bins": [r["recorded_bins"] for r in recs],
                  "peak_rss_GB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6}))
