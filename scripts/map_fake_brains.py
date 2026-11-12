"""Test the frozen analysis (nematica/map/analysis.py) end to end on synthetic "fake brains" before any real
data (docs/MAP.md, amendment 3). Scenario "separated": five fake preparations from one region of parameter
space, standard fake AIs from another, one augmented AI near the brains; H1 should hold and the augmented AI
pass H2. Scenario "mixed": AIs drawn from the brains' region; H1 should fail.
Writes docs/figures/map_fake_brains.json."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.map import analysis, measures, recording, synthetic  # noqa: E402

DRAWS = 20
CAL = ["spectrum_steepness", "shared_fraction", "timescale_spread", "coupling_spread", "sparsity"]
BRAIN = dict(alpha=1.4, slow=0.3, coupling=0.6, private=0.7, tau_spread=0.3, T=5000)
AI = dict(alpha=0.7, slow=0.0, coupling=0.1, private=2.0, tau_spread=0.05, T=5000)


def jitter(base, rng, sd):
    out = dict(base)
    for k in ("alpha", "coupling", "private", "tau_spread"):
        out[k] = base[k] * float(np.exp(rng.normal(0, sd)))
    out["slow"] = float(np.clip(base["slow"] + rng.normal(0, sd * 0.2), 0, 0.7))
    return out


def meas(Y, seed):
    r = measures.measure_matched(Y, seed=seed, n_draws=DRAWS)
    return {m: r.get(m, np.nan) for m in measures.MEASURES}


def scenario(ai_region, seed=0):
    rng = np.random.default_rng(seed)
    preps, inst = [], []
    for pi in range(5):
        ptype = jitter(BRAIN, rng, 0.3)
        knobs = dict(decay=float(rng.uniform(0.5, 2)), frame=float(rng.uniform(1, 2)), snr=float(rng.uniform(2, 5)))
        inds, ses = [], []
        for ii in range(3):
            A = synthetic.population(np.random.default_rng(100 * pi + ii), **jitter(ptype, rng, 0.2))
            Y = recording.calcium(A, rng=np.random.default_rng(ii), **knobs)
            inds.append(meas(Y, ii))
            ses.append(measures.split_half_se(Y, seed=ii, n_draws=DRAWS))
            if ii == 0:
                t = measures.tau_med(Y)
                inst.append({"decay_over_tau": knobs["decay"] / knobs["frame"] / t, "frames_per_tau": t,
                             "noise": float(np.median(measures.noise_fraction(Y)))})
        se = {m: float(np.nanmean([s.get(m, np.nan) for s in ses])) for m in measures.MEASURES}
        preps.append({"id": f"P{pi}", "kind": "real", "group": "calcium", "dataset": f"d{pi}", "species_type": f"t{pi}",
                      "individuals": inds, "se": se})
    group_inst = {k: float(np.median([i[k] for i in inst])) for k in inst[0]}
    ais = []
    specs = [(f"F{j}", "standard", jitter(ai_region, rng, 0.25)) for j in range(4)] + [("AUG", "augmented", jitter(BRAIN, rng, 0.1))]
    for j, (name, role, par) in enumerate(specs):
        A = synthetic.population(np.random.default_rng(900 + j), **par)
        k = recording.match_calcium(A[:3000, :60], group_inst, rng=np.random.default_rng(j))
        reps = [meas(recording.record_matched(A, "calcium", k, rng=np.random.default_rng(50 + r)), 50 + r) for r in range(3)]
        val = {m: float(np.nanmean([r_[m] for r_ in reps])) for m in measures.MEASURES}
        budget = {m: 0.0 for m in measures.MEASURES}
        for knob in ("decay", "frame", "snr"):
            for f in (1 / 1.5, 1.5):
                kk = dict(k); kk[knob] = max(k[knob] * f, 1.0 if knob == "frame" else 1e-3)
                v2 = meas(recording.record_matched(A, "calcium", kk, rng=np.random.default_rng(j)), j)
                for m in measures.MEASURES:
                    budget[m] = max(budget[m], abs(v2[m] - val[m]) if np.isfinite(v2[m]) and np.isfinite(val[m]) else 0.0)
        ais.append({"id": name, "kind": "ai", "family": name, "role": role, "fitted_on": [],
                    "values": {"calcium": val}, "replicates": {"calcium": reps},
                    "reached": {"calcium": k["reached"]}, "budget": {"calcium": budget}})
    systems = analysis.mapped(preps + ais, "calcium")
    preps_m = [s for s in systems if s["kind"] == "real"]; ais_m = [s for s in systems if s["kind"] == "ai"]
    B = analysis.bvu(preps_m, CAL)
    use, why = analysis.usable_measures("calcium", systems, CAL, B)
    out = {"group_instrument": group_inst, "unreached": [a["id"] for a in ais if not a["reached"]["calcium"]],
           "measures": use, "dropped": why, "bvu": B}
    if len(use) >= analysis.MIN_MEASURES:
        out["H1"] = analysis.h1("calcium", preps_m, ais_m, use, B)
        out["H2"] = analysis.h2("calcium", preps_m, ais_m, use, B)
        out["gaps"] = analysis.gaps("calcium", preps_m, ais_m, use, B)
    # code-path check: the same decisions with the C3 and budget gates off (not a registered result)
    use0 = [m for m in CAL if all(np.isfinite(analysis.value(s_, m, "calcium")) for s_ in systems)]
    out["gates_off"] = {"measures": use0, "H1": analysis.h1("calcium", preps_m, ais_m, use0, B),
                        "H2": analysis.h2("calcium", preps_m, ais_m, use0, B),
                        "gaps": analysis.gaps("calcium", preps_m, ais_m, use0, B)}
    return out


if __name__ == "__main__":
    res = {"separated": scenario(AI, 0), "mixed": scenario(BRAIN, 1)}
    Path("docs/figures/map_fake_brains.json").write_text(json.dumps(res, indent=1, default=float))
    for k, v in res.items():
        print(k, "measures", v["measures"], "dropped", v["dropped"], "unreached", v["unreached"])
        print("  H1", v.get("H1")); print("  H2", v.get("H2")); print("  gaps", v.get("gaps"))
        print("  gates off:", v["gates_off"])
