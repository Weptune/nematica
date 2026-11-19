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
        r = real.analyse(real.recording(d, cls, len(names)))
        mice[m] = {"line": LINE[m], "tagged": int(t.sum()), "classes": len(names), "ceiling": r["ceiling"],
                   "W": r["W"], "P": r["P"], "profile": dict(zip(names, r["profile"]))}
    # between-mouse agreement within line, shared classes >= 4
    for m, v in mice.items():
        rs = []
        for o, u in mice.items():
            if o == m or u["line"] != v["line"]:
                continue
            sh = sorted(set(v["profile"]) & set(u["profile"]))
            if len(sh) >= 4:
                rs.append(core.agree(np.array([v["profile"][k] for k in sh]), np.array([u["profile"][k] for k in sh])))
        v["between"] = float(np.nanmedian(rs)) if rs else None
    ms = list(mice)
    rW = np.array([mice[m]["W"] for m in ms]); rP = np.array([mice[m]["P"] for m in ms])
    b = [m for m in ms if mice[m]["between"] is not None]
    dW = np.array([mice[m]["between"] - mice[m]["W"] for m in b]); dP = np.array([mice[m]["between"] - mice[m]["P"] for m in b])
    boots = [np.median(rng.choice(dP, len(dP))) for _ in range(2000)] if len(dP) else [np.nan]
    o4m = [m for m in ms if mice[m]["ceiling"] >= 0.5]
    out = {"dropped_classes": drop, "wt_class_medians": {k: round(x, 3) for k, x in wt_med.items()},
           "left_out": left_out,
           "O1": {"median_dW": float(np.median(dW)), "sign_p": sign_p(dW), "supported": bool(np.median(dW) > 0.1 and sign_p(dW) < 0.05), "n": len(dW)},
           "O2": {"upper90": float(np.percentile(boots, 95)), "supported": bool(np.percentile(boots, 95) < 0.1), "n": len(dP)},
           "O3": {"P_beats_W": int((rP > rW).sum()), "n": len(ms), "supported": bool((rP > rW).sum() >= 10)},
           "O4": ({**gap_claim([{"P": mice[m]["P"], "W": mice[m]["W"], "ceiling": mice[m]["ceiling"]} for m in o4m], rng), "n": len(o4m)}
                  if len(o4m) >= 8 else {"undecidable": True, "n": len(o4m)}),
           "mice": {m: {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v.items() if k != "profile"} for m, v in mice.items()}}
    (ROOT / "docs/figures/opto/result.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("dropped_classes", "left_out", "O1", "O2", "O3", "O4")}, indent=1, default=float))


if __name__ == "__main__":
    main()
