"""Study P (docs/OPTO_SECOND.md): the instruments of the Study V mice, and nothing else. For each mouse that
entered Study V this saves what a synthetic system needs to be recorded the way that mouse was (classes,
units per class, firing rates, spontaneous block lengths, the light schedule), and the class names. No
response to light is computed here beyond Study V's tagging rule, which decides which units are the driven
class. Output stays local: data/cache/opto_second/instruments.pkl.
python -I scripts/opto_second_instruments.py"""
import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from nematica.opto import real  # noqa: E402
from opto_run import named_profile  # noqa: E402

V = json.loads((ROOT / "docs/figures/opto/vbn_result.json").read_text())
OUT = ROOT / "data/cache/opto_second/instruments.pkl"


def main():
    inst = {}
    for m, v in V["mice"].items():
        d = real.load(m)
        t = real.tag(d)
        cls, names = named_profile(d, t, V["dropped_classes"])
        assert len(names) == v["classes"] and int(t.sum()) == v["tagged"], (m, len(names), int(t.sum()))
        i = real.instrument(d, cls, len(names))
        i["names"] = names; i["line"] = v["line"]
        inst[m] = i
        print(m, v["line"], len(names), int(t.sum()), flush=True)
    OUT.write_bytes(pickle.dumps(inst))
    for line in ("Sst", "Vip"):
        ms = [m for m in inst if inst[m]["line"] == line]
        sh = [len(set(inst[a]["names"]) & set(inst[b]["names"])) for i, a in enumerate(ms) for b in ms[i + 1:]]
        print(line, len(ms), "mice; classes per mouse", int(np.median([len(inst[m]["names"]) for m in ms])),
              "; shared classes per pair: min", min(sh), "quartiles", np.percentile(sh, [25, 50, 75]).tolist(), "max", max(sh))


if __name__ == "__main__":
    main()
