"""Study O calibration through real instruments (docs/OPTO.md, A6, A10.7, A10.12). Instruments: one mouse per
Cre line (QC units, tagged units by the registered rule on square-pulse trials only, classes, firing rates,
spontaneous blocks, the mouse's own trial schedule). Per seed, three synthetic populations of 13 individuals
(one shared network and coupling, jittered 30% per individual): links visible at rest, links silent at rest,
and links visible with W misspecified. Scored with the real test's code (nematica.opto.real.analyse) and
claim rules. No test-condition response of a real mouse is computed.

python -I scripts/opto_instrument_cal.py --seeds=0-19 [--out=name]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from nematica.opto import real  # noqa: E402
from opto_calibrate import verdicts  # noqa: E402

INSTRUMENTS = ["sub-769360771", "sub-776061236", "sub-763808588"]
SEED0 = int(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--seed0=")), 20261200))


def arg(name, default):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default)


def main():
    a, b = map(int, arg("seeds", "0-19").split("-"))
    insts = {}
    for m in INSTRUMENTS:
        d = real.load(m)
        t = real.tag(d)
        cls, names = real.classes(d, t)
        insts[m] = real.instrument(d, cls, len(names))
    out = {}
    for i in range(a, b + 1):
        rng = np.random.default_rng(SEED0 + i)
        m = INSTRUMENTS[i % 3]
        inst = insts[m]
        K = inst["n_classes"]
        res = {"instrument": m}
        for kind in ("visible", "silent", "misspecified"):
            c0 = rng.normal(0, 1, K); A0 = rng.normal(0, 1, (K, K)) / np.sqrt(K)
            pop = []
            for _ in range(int(arg("n", 13))):
                rec = real.synthetic(rng, inst, kind == "silent", c0 * (1 + 0.3 * rng.normal(0, 1, K)),
                                     A0 * (1 + 0.3 * rng.normal(0, 1, (K, K))), mis=kind == "misspecified")
                r = real.analyse(rec)
                r.update(real.rest_score(rec))
                pop.append(r)
            v = verdicts(pop, rng)
            v["c"] = round(float(np.median([r["c"] for r in pop])), 3)
            v["rest"] = round(float(np.nanmedian([r["rest_score"] for r in pop])), 3)
            v["train2_baseline"] = round(float(np.nanmedian([r.get("train2_baseline", np.nan) for r in pop])), 3)
            res[kind] = v
            print(i, m, kind, {k: v[k] for k in ("c", "W", "P", "gap", "gap_lo", "O4", "O1", "O2", "O3", "rest", "train2_baseline")}, flush=True)
        out[i] = res
        (ROOT / f"docs/figures/opto/calibration_A10_{arg('out', f'{a}-{b}')}.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
