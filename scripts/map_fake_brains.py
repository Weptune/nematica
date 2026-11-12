"""Gated positive and negative controls for the frozen analysis (docs/MAP.md, amendment 4, F13), synthetic
"fake brains" only, run with every registered gate on.

Each scenario: five fake preparations of distinct types (four individuals each, 20% individual variation,
30% between preparations), each recorded with its own calcium instrument; instrument numbers come from the
frozen instrument_numbers; every fake AI is matched and recorded at each preparation's own instrument (F5);
C3 is the pooled split-half SE (5 splits); the budget uses common random numbers (F12).
  separated (positive control): standard AIs from another region of parameter space, one augmented AI
    near the brains. Expected: H1 holds, the augmented AI passes H2, and a paired bootstrap test decides.
  mixed (negative control): AIs drawn from the brains' region. Expected: H1 does not hold.
Writes docs/figures/map_fake_brains.json with a hash of the code.
"""
import hashlib
import json
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.map import analysis, instrument, measures, recording, synthetic  # noqa: E402

DRAWS = 20
N_SPLITS = 5
CAL = ["shared_fraction", "slow_fraction", "timescale_spread", "coupling_spread", "sparsity"]
BRAIN = dict(alpha=1.4, slow=0.3, coupling=0.6, private=0.7, tau_spread=0.3, T=6000)
AI = dict(alpha=0.7, slow=0.0, coupling=0.1, private=2.0, tau_spread=0.05, T=6000)
REPS = {"F0": 20, "F1": 20}                     # replicates for the paired bootstrap test; others 4
KNOBS = ("decay", "frame", "snr")
CODE = ["nematica/map/measures.py", "nematica/map/recording.py", "nematica/map/synthetic.py",
        "nematica/map/analysis.py", "nematica/map/instrument.py", "scripts/map_fake_brains.py"]


def jitter(base, rng, sd):
    out = dict(base)
    for k in ("alpha", "coupling", "private", "tau_spread"):
        out[k] = base[k] * float(np.exp(rng.normal(0, sd)))
    out["slow"] = float(np.clip(base["slow"] + rng.normal(0, sd * 0.2), 0, 0.7))
    return out


def meas(Y, seed, seg=None):
    r = measures.measure_matched(Y, seed=seed, n_draws=DRAWS, segments=seg)
    return {m: r.get(m, np.nan) for m in measures.MEASURES}


CACHE = ROOT / "data/cache/map_fake_brains"


def _run_cached(name, fn, job):
    """Results cached per job (keyed by the job and the code hash), so a restart resumes."""
    import pickle
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256((repr(job) + code_hash()).encode()).hexdigest()[:20]
    f = CACHE / f"{name}_{key}.pkl"
    if f.exists():
        return pickle.loads(f.read_bytes())
    r = fn(job)
    f.write_bytes(pickle.dumps(r))
    return r


def code_hash():
    h = hashlib.sha256()
    for f in CODE:
        h.update((ROOT / f).read_bytes())
    return h.hexdigest()[:16]


def _individual(job):
    pi, ii, par, knobs = job
    A = synthetic.population(np.random.default_rng(100 * pi + ii), **par)
    Y = recording.calcium(A, rng=np.random.default_rng(ii), **knobs)
    v = meas(Y, ii)
    se = measures.split_half_se(Y, seed=ii, n_splits=N_SPLITS, n_draws=DRAWS)
    num = instrument.instrument_numbers({"activity": Y, "dt": knobs["frame"],
                                         "half_decay_s": knobs["decay"] * np.log(2)}, "calcium")
    return pi, v, se, num


def _ai_at_prep(job):
    name, j, par, pid, inst, nrep = job
    A = synthetic.population(np.random.default_rng(900 + j), **par)
    k = recording.match(A, "calcium", inst, seed=j)
    rec = lambda kk, s: meas(recording.record_matched(A, "calcium", kk, rng=np.random.default_rng(s))[0], s)
    reps = [rec(k, 50 + r) for r in range(nrep)]
    budget = {m: [] for m in measures.MEASURES}
    for s in (50, 51):                           # common random numbers: same seed for base and swept knobs
        base = reps[s - 50]
        ch = {m: 0.0 for m in measures.MEASURES}
        for knob in KNOBS:
            for f in (1 / 1.5, 1.5):
                kk = dict(k); kk[knob] = max(k[knob] * f, 1.0 if knob == "frame" else 1e-3)
                v = rec(kk, s)
                for m in measures.MEASURES:
                    ch[m] = max(ch[m], abs(v[m] - base[m])) if np.isfinite(v[m]) and np.isfinite(base[m]) else np.nan
        for m in measures.MEASURES:
            budget[m].append(ch[m])
    vals = {m: float(np.nanmean([r[m] for r in reps])) if np.isfinite([r[m] for r in reps]).sum() >= 0.8 * nrep
            else np.nan for m in measures.MEASURES}
    return name, pid, {"values": vals, "replicates": reps, "reached": bool(k["reached"]),
                       "budget": {m: float(np.mean(v)) for m, v in budget.items()}, "achieved": k["achieved"]}


def individual(job):
    return _run_cached("individual", _individual, job)


def ai_at_prep(job):
    return _run_cached("ai", _ai_at_prep, job)


def scenario(ai_region, seed, pool):
    rng = np.random.default_rng(seed)
    jobs, ptypes = [], []
    for pi in range(5):
        ptype = jitter(BRAIN, rng, 0.3)
        knobs = dict(decay=float(rng.uniform(1.0, 3.0)), frame=float(rng.uniform(0.8, 1.6)),
                     snr=float(rng.uniform(1.5, 4.0)))
        for ii in range(4):
            jobs.append((pi, ii, jitter(ptype, rng, 0.2), knobs))
    preps = [{"id": f"P{pi}", "kind": "real", "dataset": f"d{pi}", "species_type": f"t{pi}", "individuals": [],
              "_se": [], "_num": []} for pi in range(5)]
    for pi, v, se, num in pool.imap(individual, jobs):
        preps[pi]["individuals"].append(v); preps[pi]["_se"].append(se); preps[pi]["_num"].append(num)
    for p in preps:
        ses = p.pop("_se")
        p["se"] = {m: float(np.sqrt(np.mean(np.square([s_[m] for s_ in ses])))) for m in measures.MEASURES}
        p["instrument"] = instrument.preparation_numbers(p.pop("_num"), "calcium")
    specs = [(f"F{j}", "standard", f"F{j}", jitter(ai_region, rng, 0.25)) for j in range(4)] + \
            [("AUG", "augmented", "F0", jitter(BRAIN, rng, 0.1))]
    ais = {n: {"id": n, "kind": "ai", "family": fam, "role": role, "fitted_on": [], "at": {}}
           for n, role, fam, _ in specs}
    jobs = [(n, j, par, p["id"], {k: p["instrument"][k] for k in instrument.KEYS["calcium"]}, REPS.get(n, 4))
            for j, (n, role, fam, par) in enumerate(specs) for p in preps]
    for n, pid, rec in pool.imap(ai_at_prep, jobs):
        ais[n]["at"][pid] = rec
    ais = list(ais.values())
    P, A = analysis.mapped(preps, ais)
    B = analysis.bvu(P, CAL)
    use, why = analysis.usable_measures(P, A, CAL, B)
    out = {"instruments": {p["id"]: p["instrument"] for p in preps},
           "unreached": [(a["id"], pid) for a in ais for pid, r in a["at"].items() if not r["reached"]],
           "mapped_ais": [a["id"] for a in A], "measures": use, "dropped": why, "bvu": B,
           "c3_over_bvu": {m: max(p["se"][m] for p in P) / B[m]["sd"] for m in CAL if B[m]["sd"] == B[m]["sd"]},
           "budget_over_bvu": {m: analysis.group_budget(P, A, m) / B[m]["sd"] for m in CAL if B[m]["sd"] == B[m]["sd"]}}
    if len(use) >= analysis.MIN_MEASURES:
        out["H1"] = analysis.h1(P, A, use, B)
        out["H2"] = analysis.h2(P, A, use, B)
        out["gaps"] = analysis.gaps(P, A, use, B)
        f0, f1 = next(a for a in A if a["id"] == "F0"), next(a for a in A if a["id"] == "F1")
        out["paired_F0_F1"] = {"h4_rule": analysis.h4(P, f0, f1, use, B), "h6_rule": analysis.h6(P, f0, f1, use, B),
                               "d_F0": analysis.distance(f0, analysis.brain_centroid(P, use), use, B, P),
                               "d_F1": analysis.distance(f1, analysis.brain_centroid(P, use), use, B, P)}
    return out


def main():
    t0 = time.time()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    with Pool(2) as pool:
        res = {"separated": scenario(AI, 0, pool)}
        print(f"separated {time.time() - t0:.0f}s", flush=True)
        res["mixed"] = scenario(BRAIN, 1, pool)
    res["provenance"] = {"code_sha256_16": code_hash(), "git_head_at_run": head, "files": CODE,
                         "seconds": round(time.time() - t0)}
    (ROOT / "docs/figures/map_fake_brains.json").write_text(json.dumps(res, indent=1, default=float))
    for k in ("separated", "mixed"):
        v = res[k]
        print(k, "measures", v["measures"], "dropped", v["dropped"], "unreached", v["unreached"])
        print("  C3/BVU", {m: round(x, 2) for m, x in v["c3_over_bvu"].items()},
              "budget/BVU", {m: round(x, 2) for m, x in v["budget_over_bvu"].items()})
        for h_ in ("H1", "H2", "gaps", "paired_F0_F1"):
            print(" ", h_, v.get(h_))


if __name__ == "__main__":
    main()
