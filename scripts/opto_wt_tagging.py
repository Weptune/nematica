"""Study O, A10.11: the registered tagging rule run on the six wild-type (no ChR2) mice. Any unit tagged
there responds to the light without the opsin, so it is a false positive. Reads square-pulse spikes only.
python -I scripts/opto_wt_tagging.py -> docs/figures/opto/wt_tagging.json"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from nematica.opto import real  # noqa: E402
from opto_cache import CRE, WT  # noqa: E402

out = {}
for m in WT + CRE:
    d = real.load(m)
    t = real.tag(d)
    out[m] = {"group": "wild-type" if m in WT else "Cre", "qc_units": len(t), "tagged": int(t.sum()),
              "tagged_areas": sorted({str(a) for a in d["area"][t]})}
    print(m, out[m], flush=True)
(ROOT / "docs/figures/opto/wt_tagging.json").write_text(json.dumps(out, indent=1))
