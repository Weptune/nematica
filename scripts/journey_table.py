"""Study J (docs/JOURNEY.md): activity tests passed per model and seed, from a run_same_worms cache.

python -I scripts/journey_table.py results/journey_dev2            development table: prints what is there
python -I scripts/journey_table.py results/journey_copper --claims the registered test: every registered model, seed
                                                                    and pool must be present, or it stops; then
                                                                    the claims are evaluated as registered
Writes docs/figures/journey_<cache name>.json. A test that is missing from a pool's file, or that the bench
could not score, counts as not inside (registered)."""
import glob
import json
import re
import sys
from pathlib import Path

import pandas as pd

REST = ["L1.distribution", "L1.timescale", "L2.correlation", "L2.dimension", "L4.leadlag", "L4.dwell"]
R0 = "hybrid_kernels_slow6d_indivslow1_hp_memfix_diag_hsd1"
R1 = "hybrid_kernels_slow6d_indivslow1_hp_memfix_hsd1_gcop"
C = "var3_spontaneous"
COUPLING = "hybrid_kernels_slow6d_indivslow1_hp_memfix_hsd1"
SHAPE = "hybrid_kernels_slow6d_indivslow1_hp_memfix_diag_hsd1_gcop"
PASS = 5
LETTER = {"inside": "I", "outside": "O", "too typical": "T"}


def table(cache):
    """model -> seed -> {"passed", "others" (passed among the five tests other than distribution), per-test
    letters over pools 0,1,2 ("-" where the pool's file lacks the test), "pools"}."""
    cells = {}
    for f in sorted(glob.glob(str(cache / "fluct_f*_*.csv"))):
        m = re.match(r"fluct_f(\d)_(.+?)(?:_s(\d+))?\.csv$", Path(f).name)
        d = pd.read_csv(f)
        got = {r.metric: LETTER.get(r.verdict, "?") for r in d.itertuples() if r.metric in REST}
        cells[(m.group(2), int(m.group(3) or 0), int(m.group(1)))] = got
    out = {}
    for model, seed in sorted({(a, b) for a, b, _ in cells}):
        pools = [k for k in (0, 1, 2) if (model, seed, k) in cells]
        per = {t: "".join(cells[(model, seed, k)].get(t, "-") if (model, seed, k) in cells else "-" for k in (0, 1, 2)) for t in REST}
        ok = {t: v.count("I") >= 2 for t, v in per.items()}
        out.setdefault(model, {})[seed] = {"passed": int(sum(ok.values())), "others": int(sum(v for t, v in ok.items() if t != "L1.distribution")),
                                           "pools": pools, **{t.split(".")[1]: v for t, v in per.items()}}
    return out


def need(out, model, seeds):
    for s in seeds:
        v = out.get(model, {}).get(s)
        if v is None or v["pools"] != [0, 1, 2]:
            raise SystemExit(f"incomplete: {model} seed {s} has pools {None if v is None else v['pools']}; the registered table needs all three")


def claims(out):
    five = range(5)
    for model in (R0, R1, C):
        need(out, model, five)
    for model in (COUPLING, SHAPE):
        need(out, model, range(3))
    c = [out[C][s]["passed"] for s in five]
    r0 = [out[R0][s]["passed"] for s in five]
    r1 = [out[R1][s]["passed"] for s in five]
    o0 = [out[R0][s]["others"] for s in five]
    o1 = [out[R1][s]["others"] for s in five]
    res = {"control_passed": c, "R0_passed": r0, "R1_passed": r1, "R0_others": o0, "R1_others": o1,
           "informative": sum(v < PASS for v in c) >= 4,
           "J1": sum(v <= 4 for v in r0) >= 4,
           "J2": sum(b > a for a, b in zip(o0, o1)) >= 4,
           "J3": sum(v >= PASS for v in r1) >= 4}
    if not res["informative"]:
        res.update({k: None for k in ("J1", "J2", "J3")})
    return res


def main():
    cache = Path(sys.argv[1])
    out = table(cache)
    for model, s in out.items():
        print(model)
        for seed, v in sorted(s.items()):
            gap = "" if v["pools"] == [0, 1, 2] else f"   INCOMPLETE: pools {v['pools']}"
            print("   seed", seed, "passed", v["passed"], "| other five", v["others"], "|", " ".join(f"{k[:6]}:{x}" for k, x in v.items() if k not in ("passed", "others", "pools")) + gap)
    res = {"table": out}
    if "--claims" in sys.argv:
        res["claims"] = claims(out)
        print(json.dumps(res["claims"], indent=1))
    (Path(__file__).resolve().parents[1] / f"docs/figures/journey_{cache.name}.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
