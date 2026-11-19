"""Visual Behavior Neuropixels: tagged-unit counts per cached mouse with Study O's A11 rule (pulse spikes
only; no response to the test condition is computed). -> docs/figures/opto/vbn_tagcount.json"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.opto import real  # noqa: E402

out = {}
f = ROOT / "docs/figures/opto/vbn_tagcount.json"
if f.exists():
    out = json.loads(f.read_text())
for l in (ROOT / "docs/figures/opto/feasibility_vbn.jsonl").read_text().splitlines():
    d = json.loads(l)
    if d["id"] in out or not d.get("opto_n") or not (real.CACHE / f"{d['id']}.npz").exists():
        continue
    x = real.load(d["id"])
    t = real.tag(x)
    cls, names = real.classes(x, t)
    out[d["id"]] = {"line": (d.get("genotype") or "").split("-")[0].split("/")[0], "qc": len(t), "tagged": int(t.sum()),
                    "classes": len(names), "tagged_areas": sorted({str(a) for a in x["area"][t]})}
    print(d["id"], out[d["id"]], flush=True)
    f.write_text(json.dumps(out, indent=1))
