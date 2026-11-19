"""Study O calibration (docs/OPTO.md). Synthetic systems with known coupling: links active at rest (W should
succeed), links silent at rest (W should fail, P succeed), and jittered individuals. Usage:
python -I scripts/opto_calibrate.py [--pilot]   (--pilot: a generic instrument, before any mouse is cached)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from nematica.opto import core  # noqa: E402


def score(rng, silent, coupling=None, A=None):
    counts, cls, T_sp, on_tr, on_te, c = core.synthetic(rng, silent=silent, coupling=coupling, A=A)
    classes = np.arange(cls.max() + 1)
    sp = counts[:T_sp]
    win = sp[: (T_sp // 50) * 50].reshape(-1, 50, sp.shape[1]).sum(1)
    sd = win.std(0)
    resp = core.unit_responses(counts, on_te, sd)
    prof = core.profile(resp, cls, classes)
    ceil = core.agree(core.profile(resp[0::2], cls, classes), core.profile(resp[1::2], cls, classes))
    allc = np.concatenate([[-1], classes])
    X = core.class_rates(counts, cls, allc)
    W = core.fit_watch(X[:T_sp])
    mu, s = W[1], W[2]
    def course(onsets, n=core.TEST_BINS):
        tr = np.stack([X[o:o + n] - X[o - core.PRE_BINS:o].mean(0) for o in onsets]).mean(0)
        return tr / s
    te = course(on_te)
    pw = core.predict_watch(W, te[:, 0], 0)[1:]
    tr = course(on_tr)
    H = core.fit_poke(tr[:, 1:], tr[:, 0])
    pp = core.predict_poke(H, te[:, 0])
    return {"ceiling": ceil, "W": core.agree(pw, prof), "P": core.agree(pp, prof), "profile": prof, "c": c}


def sign_p(x):
    from math import comb
    x = [v for v in x if v != 0]; n = len(x); k = sum(v > 0 for v in x)
    return sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n


def verdicts(pop, rng):
    """Claim rules O1 to O3 on a population: between-individual agreement from the measured profiles."""
    P = np.array([r["profile"] for r in pop])
    between = np.array([np.median([core.agree(P[i], P[j]) for j in range(len(P)) if j != i]) for i in range(len(P))])
    rW = np.array([r["W"] for r in pop]); rP = np.array([r["P"] for r in pop])
    dW, dP = between - rW, between - rP
    boots = [np.median(rng.choice(dP, len(dP))) for _ in range(2000)]
    return {"between": round(float(np.median(between)), 3), "W": round(float(np.median(rW)), 3), "P": round(float(np.median(rP)), 3),
            "O1": bool(np.median(dW) > 0.1 and sign_p(dW) < 0.05), "O1_d": round(float(np.median(dW)), 3), "O1_p": round(sign_p(dW), 4),
            "O2": bool(np.percentile(boots, 95) < 0.1), "O2_hi": round(float(np.percentile(boots, 95)), 3),
            "O3": int((rP > rW).sum()), "O3_ok": bool((rP > rW).sum() >= 10)}


def main():
    rng = np.random.default_rng(20261119)
    jit = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--jitter=")), 0.3))
    kinds = ("silent",) if "--silent-only" in sys.argv else ("visible", "silent")
    out = {"jitter": jit}
    for kind in kinds:
        base = rng.normal(0, 1, 12); A0 = rng.normal(0, 1, (12, 12)) / np.sqrt(12)
        pop = [score(rng, kind == "silent", base * (1 + jit * rng.normal(0, 1, 12)), A0 * (1 + jit * rng.normal(0, 1, (12, 12)))) for _ in range(13)]
        out[kind] = verdicts(pop, rng)
        out[kind]["ceiling"] = round(float(np.median([r["ceiling"] for r in pop])), 3)
        print(kind, out[kind], flush=True)
    if len(kinds) == 1:
        (ROOT / "docs/figures/opto" / f"calibration_A2_j{jit}.json").write_text(json.dumps(out, indent=1)); return
    ok = {"silent": out["silent"]["O1"] and out["silent"]["O2"] and out["silent"]["O3_ok"], "visible": not out["visible"]["O1"],
          "c": out["visible"]["between"] < out["visible"]["ceiling"]}
    print("A1 checks:", ok)
    name = "calibration_A1_pilot.json" if "--pilot" in sys.argv else "calibration_A1.json"
    (ROOT / "docs/figures/opto" / name).write_text(json.dumps({**out, "checks": ok}, indent=1))


if __name__ == "__main__":
    main()
