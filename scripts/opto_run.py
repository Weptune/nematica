"""Study O, the real test (docs/OPTO.md). Refuses to run unless the registration is frozen.
python -I scripts/opto_run.py   -> docs/figures/opto/result.json (summary numbers only)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from nematica.opto import core, real  # noqa: E402
from opto_cache import CRE, WT  # noqa: E402
from opto_calibrate import gap_claim, sign_p  # noqa: E402

LINE = {}
for l in (ROOT / "docs/figures/opto/feasibility.jsonl").read_text().splitlines():
    d = json.loads(l)
    LINE[d["id"]] = d["genotype"].split("-")[0]


def named_profile(d, tagged, drop=()):
    cls, names = real.classes(d, tagged)
    keep = [j for j, k in enumerate(names) if k not in drop]
    remap = np.full(len(names), -2); remap[keep] = np.arange(len(keep))
    cls = np.where(cls >= 0, remap[np.clip(cls, 0, None)], cls)
    names = [names[j] for j in keep]
    return cls, names


def main():
    if "\n**Status: FROZEN" not in (ROOT / "docs/OPTO.md").read_text():
        sys.exit("not frozen")
    rng = np.random.default_rng(20261122)
    # light-only check
    wt = {}
    for m in WT:
        d = real.load(m)
        cls, names = named_profile(d, np.zeros(len(d["trains"]), bool))
        rec = real.recording(d, cls, len(names))
        sd = real.spont_sd(rec["spont"])
        resp = real.unit_responses(rec["block"], rec["on_test"], sd)
        keep = rec["cls"] >= 0
        wt[m] = dict(zip(names, core.profile(resp[:, keep], rec["cls"][keep], np.arange(len(names)))))
    allnames = sorted({k for v in wt.values() for k in v})
    wt_med = {k: float(np.median([v[k] for v in wt.values() if k in v])) for k in allnames}
    drop = sorted(k for k, x in wt_med.items() if abs(x) > 0.5)
    # Cre mice
    mice, left_out = {}, {}
    for m in CRE:
        d = real.load(m)
        t = real.tag(d)
        if t.sum() < 3:
            left_out[m] = f"{int(t.sum())} tagged units"; continue
        cls, names = named_profile(d, t, drop)
        if len(names) < 4:
            left_out[m] = f"{len(names)} classes after the light-only check"; continue
        rec = real.recording(d, cls, len(names))
        r = real.analyse(rec)
        r.update(real.rest_score(rec))
        v = {"line": LINE[m], "tagged": int(t.sum()), "classes": len(names), "unchecked": [k for k in names if k not in wt_med],
             "profile": dict(zip(names, r.pop("profile")))}
        v.update(r)
        if LINE[m] == "Pvalb":                                    # A10.9 robustness: no narrow classes
            cls2, names2 = named_profile(d, t, list(drop) + [k for k in names if k.endswith("|n")])
            if len(names2) >= 4:
                r2 = real.analyse(real.recording(d, cls2, len(names2)))
                v["no_narrow"] = {"W": r2["W"], "P": r2["P"], "c": r2["c"], "ceiling": r2["ceiling"]}
        mice[m] = v
    # between-mouse agreement within line, shared classes >= 4
    for m, v in mice.items():
        rs = []
        for o, u in mice.items():
            if o == m or u["line"] != v["line"]:
                continue
            sh = sorted(set(v["profile"]) & set(u["profile"]))
            if len(sh) >= 4:
                rs.append(core.agree(np.array([v["profile"][k] for k in sh]), np.array([u["profile"][k] for k in sh])))
        rs = [x for x in rs if np.isfinite(x)]
        v["between"] = float(np.median(rs)) if rs else None
    fin = lambda *k: [m for m in mice if all(mice[m].get(x) is not None and np.isfinite(mice[m][x]) for x in k)]  # noqa: E731
    m3 = fin("W", "P")
    rW = np.array([mice[m]["W"] for m in m3]); rP = np.array([mice[m]["P"] for m in m3])
    b12 = fin("W", "P", "between")
    dW = np.array([mice[m]["between"] - mice[m]["W"] for m in b12]); dP = np.array([mice[m]["between"] - mice[m]["P"] for m in b12])
    boots = [np.median(rng.choice(dP, len(dP))) for _ in range(2000)] if len(dP) else [np.nan]
    o4m = [m for m in fin("W", "P", "c", "ceiling") if mice[m]["c"] >= 0.5]
    def o4(sel, get):
        return ({**gap_claim([get(m) for m in sel], rng), "n": len(sel)} if len(sel) >= 8 else {"undecidable": True, "n": len(sel)})
    nn = [m for m in o4m if mice[m]["line"] != "Pvalb" or ("no_narrow" in mice[m] and mice[m]["no_narrow"]["c"] >= 0.5)]
    out = {"dropped_classes": drop, "wt_class_medians": {k: round(x, 3) for k, x in wt_med.items()},
           "left_out": left_out,
           "O1": {"median_dW": float(np.median(dW)) if len(dW) else None, "sign_p": sign_p(dW) if len(dW) else None,
                  "supported": bool(len(dW) and np.median(dW) > 0.1 and sign_p(dW) < 0.05), "n": len(dW)},
           "O2": {"upper90": float(np.percentile(boots, 95)), "supported": bool(len(dP) and np.percentile(boots, 95) < 0.1), "n": len(dP)},
           "O3": {"P_beats_W": int((rP > rW).sum()), "n": len(m3), "needed": int(np.ceil(10 / 13 * len(m3))),
                  "supported": bool((rP > rW).sum() >= np.ceil(10 / 13 * len(m3)))},
           "O4": o4(o4m, lambda m: mice[m]),
           "O4_no_narrow_pvalb": o4(nn, lambda m: mice[m]["no_narrow"] if mice[m]["line"] == "Pvalb" else mice[m]),
           "rest_score_median": float(np.nanmedian([mice[m].get("rest_score", np.nan) for m in mice])),
           "train2_baseline_median": float(np.nanmedian([mice[m].get("train2_baseline", np.nan) for m in mice])),
           "mice": {m: {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v.items() if k != "profile"} for m, v in mice.items()}}
    (ROOT / "docs/figures/opto/result.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("dropped_classes", "left_out", "O1", "O2", "O3", "O4", "O4_no_narrow_pvalb", "rest_score_median", "train2_baseline_median")}, indent=1, default=float))


if __name__ == "__main__":
    main()
