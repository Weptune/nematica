"""Study P (docs/OPTO_SECOND.md): does a copy taught by light pulses answer like a second mouse? Refuses to
run unless frozen. python -I scripts/opto_second.py -> docs/figures/opto/second_result.json (summary numbers)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from nematica.opto import core, real, second  # noqa: E402
from opto_run import named_profile  # noqa: E402

V = json.loads((ROOT / "docs/figures/opto/vbn_result.json").read_text())
FEAS = [json.loads(l) for l in (ROOT / "docs/figures/opto/feasibility_vbn.jsonl").read_text().splitlines()]
WT = [d["id"] for d in FEAS if d.get("opto_n") and d["genotype"].split("-")[0].split("/")[0] == "wt"]
AFFECTED = {"sub-556021", "sub-578257",      # a driven unit silent at rest (Study V's independent check)
            "sub-554013", "sub-563323", "sub-564012"}   # a class unit silent at rest (this study's review before the freeze)
LOW_LIGHT = 0.2                             # a class counts as little moved by light alone below this (SD units)


def light_alone():
    """Per class, the median over wild-type mice of the response to the slow light (as in Study V)."""
    wt = {}
    for m in WT:
        d = real.load(m)
        cls, names = real.classes(d, np.zeros(len(d["trains"]), bool))
        rec = real.recording(d, cls, len(names))
        sd = np.maximum(real.spont_sd(rec["spont"]), 1e-9)
        keep = rec["cls"] >= 0
        wt[m] = dict(zip(names, core.profile(real.unit_responses(rec["block"], rec["on_test"], sd)[:, keep], rec["cls"][keep], np.arange(len(names)))))
    return {k: float(np.median([v[k] for v in wt.values() if k in v])) for k in sorted({k for v in wt.values() for k in v})}


def main():
    if "\n**Status: FROZEN" not in (ROOT / "docs/OPTO_SECOND.md").read_text():
        sys.exit("not frozen")
    wt = light_alone()
    rules = {"primary": lambda k: True, "visual_only": lambda k: k.startswith("VIS"), "broad_only": lambda k: k.endswith("|b"),
             "low_light": lambda k: k in wt and abs(wt[k]) <= LOW_LIGHT}
    M = {r: {} for r in list(rules) + ["untouched"]}
    left = {}
    for m, v in V["mice"].items():
        d = real.load(m)
        t = real.tag(d)
        every = real.classes(d, t)[1]
        for r in M:
            keep = rules.get(r, rules["primary"])
            cls, names = named_profile(d, t, [k for k in every if k in V["dropped_classes"] or not keep(k)])
            if len(names) < 4:
                continue
            a = second.answers(real.recording(d, cls, len(names)), drop_silent=r != "untouched")
            if a is None:
                left[f"{m} ({r})"] = "fewer than 3 driven units or an empty class once silent units are dropped"; continue
            M[r][m] = {"line": v["line"], "names": names, **a}
        print(m, v["line"], {r: len(M[r][m]["names"]) for r in M if m in M[r]}, flush=True)
    M["untouched_without_affected"] = {m: x for m, x in M["untouched"].items() if m not in AFFECTED}
    out = {"left_out": left, "affected_mice": sorted(AFFECTED), "low_light_classes": sorted(k for k in wt if abs(wt[k]) <= LOW_LIGHT)}
    for r in ("primary", "untouched", "untouched_without_affected", "visual_only", "broad_only", "low_light"):
        pop = M[r]
        S = second.pairwise(pop, np.random.default_rng(20261121))
        out[r] = {}
        for line in ("Sst", "Vip"):
            o = second.claims(S, line)
            if not o.get("undecided"):
                o["verdict"] = {k: second.verdict(o, k) for k in ("P", "W", "X")}
                o["P_within_a_quarter_of_the_average_mouse"] = second.beats_average(o)
            out[r][line] = o
        if r == "primary":
            out["mice"] = {m: {k: (round(x, 3) if isinstance(x, float) else x) for k, x in s.items()} for m, s in S.items()}
    (ROOT / "docs/figures/opto/second_result.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "mice"}, indent=1, default=float))


if __name__ == "__main__":
    main()
