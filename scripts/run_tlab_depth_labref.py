"""Phase 2 reference: the lab's recurrent base network (round 1 base, brain 0, no individuals'
variation) scored on its own truth with the time-lagged linear watcher (annlab.K_linear) against true
kick responses (annlab.true_K), every unit seen or a random half seen, 10 hours of recording.
Output appended to docs/figures/tlab_depth.csv."""
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica import annlab as L  # noqa: E402

OUT = ROOT / "docs" / "figures" / "tlab_depth.csv"
br = L.make_brain(rho=1.3, share=0.0, seed=0, q=0.2)
K = L.true_K(br, np.random.default_rng(1))
mask = ~np.eye(br.n, dtype=bool)
none = np.zeros(br.n, bool)
res = {}
for name, seen in (("all", 1.0), ("half", 0.5)):
    recs = L.recordings(br, 10, np.random.default_rng(2), none, poke=False, seen=seen)
    res[name] = L.score(L.K_linear(recs, br.n), K, mask)
rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
row = {"condition": "lab recurrent base (time-lagged watcher)", "width": br.n, "layers": "", "basis": "units",
       "base_loss": "", "watch_all": round(res["all"], 3), "watch_half": round(res["half"], 3), "individuals": "", "n_ind": 1}
rows.append(row)
fields = list(rows[0]) if rows else list(row)
with OUT.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print(row)
