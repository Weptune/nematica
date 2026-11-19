"""Study O calibration through real instruments (docs/OPTO.md, A6). For one mouse per Cre line: its QC units,
tagged units (registered tagging rule, square-pulse trials only), classes, firing rates, spontaneous blocks
and trial counts define the instrument; synthetic populations (13 individuals, shared network and coupling
jittered 30%) with links visible or silent at rest are recorded through it and scored with the same code
(nematica.opto.real.analyse) and claim rules as the real test. No test-condition response of a real mouse
is computed. python -I scripts/opto_instrument_cal.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from nematica.opto import real  # noqa: E402
from opto_calibrate import verdicts  # noqa: E402

MICE = [a for a in sys.argv[1:] if not a.startswith("--")] or ["sub-769360771"]


def main():
    rng = np.random.default_rng(int(next((a.split("=")[1] for a in sys.argv if a.startswith("--seed=")), 20261120)))
    out = {}
    for m in MICE:
        d = real.load(m)
        t = real.tag(d)
        cls, names = real.classes(d, t)
        inst = real.instrument(d, cls, len(names))
        K = len(names)
        out[m] = {"qc_units": int(len(t)), "tagged": int(t.sum()), "classes": K,
                  "units_in_classes": int((cls >= 0).sum()), "spont_s": round(sum(inst["spont_s"]), 1),
                  "n_train": inst["n_train"], "n_test": inst["n_test"]}
        for kind in ("visible", "silent"):
            c0 = rng.normal(0, 1, K); A0 = rng.normal(0, 1, (K, K)) / np.sqrt(K)
            pop = []
            for _ in range(13):
                rec = real.synthetic(rng, inst, kind == "silent", c0 * (1 + 0.3 * rng.normal(0, 1, K)),
                                     A0 * (1 + 0.3 * rng.normal(0, 1, (K, K))))
                pop.append(real.analyse(rec))
            v = verdicts(pop, rng)
            v["ceiling"] = round(float(np.median([r["ceiling"] for r in pop])), 3)
            out[m][kind] = v
            print(m, kind, {k: v[k] for k in ("ceiling", "between", "W", "P", "gap", "gap_lo", "O4", "O1", "O2", "O3")}, flush=True)
        out[m]["pass"] = bool(out[m]["silent"]["O4"] and not out[m]["visible"]["O4"])
    (ROOT / "docs/figures/opto/calibration_instruments_latest.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
