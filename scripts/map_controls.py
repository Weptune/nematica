"""Graded controls for the frozen analysis (docs/MAP.md, amendment 10; review 13 item 10), with every gate on,
in the spike group at realistic instrument numbers and the minimum powered size.

Each world: 4 preparation types x 3 individuals. Each preparation gets one of the real spike instruments from
step 1 (R4, R9, R10b, R10c); each fake individual is recorded to that instrument by the registered matching
call, and the preparation's instrument numbers are then measured from its individuals with the frozen
`instrument_numbers`. Four standard fake AI families lie at a separation s from the brains' region (s times
the between-preparation spread in every parameter; s = 0 means AIs come from the brains' own region) and one
augmented AI lies inside it. Every AI is recorded at every preparation's instrument through
`pipeline.ai_at_prep` (budget with common random numbers and seed floor). Two families carry 5 instances x 4
recordings for a paired bootstrap test. Reported per world: the measurements kept and why others dropped,
H1, H2 and a paired test; over worlds: the decision rate and, at s = 0, the false-positive rate of H1.
Writes docs/figures/map_controls.json. Results are cached per job.
"""
import hashlib
import json
import pickle
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.map import analysis, instrument, measures, pipeline, recording, synthetic  # noqa: E402

N, T = 150, 6000
DRAWS = 10
SEPARATIONS = (0.0, 1.0, 2.0, 3.0)
SEEDS = (0, 1)
PREP_SOURCES = ("R4", "R9", "R10b", "R10c")
CAL = ["shared_fraction", "slow_fraction", "timescale_spread", "coupling_spread", "drift", "spectrum_steepness"]
BRAIN = dict(alpha=1.4, slow=0.3, coupling=0.6, private=0.7, tau_spread=0.3)
LOGP = ("alpha", "coupling", "private", "tau_spread")
CODE = ["nematica/map/measures.py", "nematica/map/recording.py", "nematica/map/synthetic.py",
        "nematica/map/analysis.py", "nematica/map/instrument.py", "nematica/map/pipeline.py",
        "scripts/map_controls.py"]
CACHE = ROOT / "data/cache/map_controls"


def code_hash():
    h = hashlib.sha256()
    for f in CODE:
        h.update((ROOT / f).read_bytes())
    return h.hexdigest()[:16]


def jitter(base, rng, sd):
    out = dict(base)
    for k in LOGP:
        out[k] = base[k] * float(np.exp(rng.normal(0, sd)))
    out["slow"] = float(np.clip(base["slow"] + rng.normal(0, sd * 0.2), 0, 0.6))
    return out


def shifted(base, s):
    """The AI region: every log-parameter moved by s x 0.3 (the between-preparation spread), in the
    direction of 'less brain-like' (weaker spectrum, coupling and timescale spread, more private noise,
    less slow drive)."""
    out = dict(base)
    for k, sign in (("alpha", -1), ("coupling", -1), ("private", +1), ("tau_spread", -1)):
        out[k] = base[k] * float(np.exp(sign * s * 0.3))
    out["slow"] = float(np.clip(base["slow"] - s * 0.06, 0, 0.6))
    return out


def cached(name, fn, job):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{name}_{hashlib.sha256((repr(job) + code_hash()).encode()).hexdigest()[:20]}.pkl"
    if f.exists():
        return pickle.loads(f.read_bytes())
    r = fn(job)
    f.write_bytes(pickle.dumps(r))
    return r


def _individual(job):
    pid, ii, par, prof, gseed = job
    A = synthetic.population(np.random.default_rng(gseed), N=N, T=T, **par)
    k = recording.match(A, "spikes", prof, seed=ii)
    Y, seg = recording.record_matched(A, "spikes", k, rng=np.random.default_rng(ii))
    r = measures.measure_matched(Y, seed=ii, n_draws=DRAWS)
    v = {m: r.get(m, np.nan) for m in measures.MEASURES}
    se = measures.split_half_se(Y, seed=ii, n_splits=5, n_draws=DRAWS)
    num = instrument.instrument_numbers({"activity": Y, "dt": 0.02}, "spikes")
    return pid, v, se, num, bool(k["reached"])


def _ai(job):
    name, pid, inst, pars, nrep = job
    instances = [synthetic.population(np.random.default_rng(seed), N=N, T=T, **pars) for seed in nrep[0]]
    return name, pid, pipeline.ai_at_prep(instances, "spikes", inst, recs_per_instance=nrep[1], n_draws=DRAWS)


def individual(job):
    return cached("ind", _individual, job)


def ai(job):
    return cached("ai", _ai, job)


def world(s, seed, pool, real):
    rng = np.random.default_rng(100 + seed)
    jobs = []
    for pi, src in enumerate(PREP_SOURCES):
        ptype = jitter(BRAIN, rng, 0.3)
        prof = {k: real[src][k] for k in ("bins_per_tau", "count_per_bin", "noise", "rate_log_sd")}
        for ii in range(3):
            jobs.append((f"P{pi}", ii, jitter(ptype, rng, 0.2), prof, 10_000 * seed + 100 * pi + ii))
    preps = {f"P{pi}": {"id": f"P{pi}", "kind": "real", "dataset": f"d{pi}", "species_type": f"t{pi}",
                        "individuals": [], "_se": [], "_num": [], "_ok": []} for pi in range(len(PREP_SOURCES))}
    for pid, v, se, num, ok in pool.imap(individual, jobs):
        p = preps[pid]
        p["individuals"].append(v); p["_se"].append(se); p["_num"].append(num); p["_ok"].append(ok)
    for p in preps.values():
        ses = p.pop("_se")
        p["se"] = {m: float(np.sqrt(np.mean(np.square([x[m] for x in ses])))) for m in measures.MEASURES}
        p["instrument"] = instrument.preparation_numbers(p.pop("_num"), "spikes")
        p["recorded_reached"] = p.pop("_ok")
    preps = list(preps.values())
    ai_region = shifted(BRAIN, s)
    specs = [(f"F{j}", "standard", f"F{j}", jitter(ai_region, rng, 0.25)) for j in range(4)] + \
            [("AUG", "augmented", "F0", jitter(BRAIN, rng, 0.1))]
    ais = {n: {"id": n, "kind": "ai", "family": fam, "role": role, "fitted_on": [], "at": {}}
           for n, role, fam, _ in specs}
    jobs = []
    for j, (n, role, fam, par) in enumerate(specs):
        seeds = [9000 + 100 * j + 10_000 * seed + i for i in range(5 if n in ("F0", "F1") else 1)]
        nrep = (seeds, 4)
        for p in preps:
            inst = {k: p["instrument"][k] for k in instrument.KEYS["spikes"]}
            jobs.append((n, p["id"], inst, par, nrep))
    for n, pid, rec in pool.imap(ai, jobs):
        ais[n]["at"][pid] = rec
    ais = list(ais.values())
    P, A = analysis.mapped(preps, ais)
    B = analysis.bvu(P, CAL)
    use, why = analysis.usable_measures(P, A, CAL, B)
    out = {"separation": s, "seed": seed, "mapped_ais": [a["id"] for a in A],
           "unreached": [(a["id"], pid) for a in ais for pid, r in a["at"].items() if not r["reached"]],
           "measures": use, "dropped": why,
           "ratios_to_bvu": {m: {"c3": max(p["se"][m] for p in P) / B[m]["sd"],
                                 "budget": analysis.group_budget(P, A, m) / B[m]["sd"],
                                 "transfer": analysis.transfer_range(P, A, m) / B[m]["sd"]}
                             for m in CAL if B[m]["sd"] == B[m]["sd"] and B[m]["sd"] > 0}}
    if len(use) >= analysis.MIN_MEASURES:
        out["H1"] = analysis.h1(P, A, use, B)
        out["H2"] = analysis.h2(P, A, use, B)
        f0 = next((a for a in A if a["id"] == "F0"), None)
        f1 = next((a for a in A if a["id"] == "F1"), None)
        if f0 and f1:
            out["paired_F0_F1_h6_rule"] = analysis.h6(P, f0, f1, use, B)
    return out


def main():
    t0 = time.time()
    real = {p: v["median"] for p, v in json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"].items()}
    worlds = []
    with Pool(2) as pool:
        for s in SEPARATIONS:
            for seed in SEEDS:
                w = world(s, seed, pool, real)
                worlds.append(w)
                print(f"s={s} seed={seed} {time.time() - t0:.0f}s measures={w['measures']} H1={w.get('H1')}", flush=True)
    summary = {}
    for s in SEPARATIONS:
        ws = [w for w in worlds if w["separation"] == s]
        dec = [w for w in ws if w.get("H1", {}).get("holds") is not None]
        summary[str(s)] = {"worlds": len(ws), "H1_decided": len(dec),
                           "H1_holds": sum(bool(w["H1"]["holds"]) for w in dec)}
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    res = {"summary": summary, "worlds": worlds,
           "provenance": {"code_sha256_16": code_hash(), "git_head_at_run": head, "files": CODE,
                          "seconds": round(time.time() - t0)}}
    (ROOT / "docs/figures/map_controls.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
