"""Study V (docs/OPTO_VBN.md), Allen Visual Behavior Neuropixels. Refuses to run unless frozen.
python -I scripts/opto_vbn.py -> docs/figures/opto/vbn_result.json (summary numbers only)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from scipy.stats import mannwhitneyu  # noqa: E402

from nematica.opto import core, real  # noqa: E402
from opto_calibrate import sign_p  # noqa: E402
from opto_run import named_profile  # noqa: E402

FEAS = [json.loads(l) for l in (ROOT / "docs/figures/opto/feasibility_vbn.jsonl").read_text().splitlines()]
LINE = {d["id"]: d["genotype"].split("-")[0].split("/")[0] for d in FEAS if d.get("opto_n")}


def per_mouse(d, t, drop, keep_name=lambda k: True):
    cls, names = named_profile(d, t, [k for k in real.classes(d, t)[1] if k in drop or not keep_name(k)])
    n = len(names)
    if n < 4:
        return None
    rec = real.recording(d, cls, n)
    c = rec["cls"]; keep = c >= 0
    sd = np.maximum(real.spont_sd(rec["spont"]), 1e-9)
    prof = core.profile(real.unit_responses(rec["block"], rec["on_test"], sd)[:, keep], c[keep], np.arange(n))
    sp = [x / sd for x in rec["spont"]]
    W = real.fit_watch(sp, c, n)
    te = real.courses(rec["block"] / sd, c, n, rec["on_test"], W[2])
    pw = core.predict_watch(W, te[:, 0], 0)[1:]
    X = np.concatenate([real.class_rates(x, c, n) for x in sp])
    rest_r = float(np.median([np.corrcoef(X[:, 0], X[:, k])[0, 1] for k in range(1, n + 1)]))
    r = real.analyse(rec)
    return {"classes": n, "real_up": float(np.mean(prof > 0)), "w_up": float(np.mean(pw > 0)), "rest_r": rest_r,
            "W": r["W"], "P": r["P"], "c": r["c"], "profile": dict(zip(names, prof))}


def sign(x):
    x = [v for v in x if np.isfinite(v)]
    return {"positive": int(sum(v > 0 for v in x)), "nonzero": int(sum(v != 0 for v in x)), "p": sign_p(x), "supported": bool(sign_p(x) < 0.05)}


def claims(M, tag=""):
    sst = [v for v in M.values() if v["line"] == "Sst"]; vip = [v for v in M.values() if v["line"] == "Vip"]
    o = {f"n_sst{tag}": len(sst), f"n_vip{tag}": len(vip)}
    if len(sst) >= 8:
        o["V1" + tag] = sign([0.5 - v["real_up"] for v in sst])
        o["V2" + tag] = sign([v["w_up"] - v["real_up"] for v in sst])
        if not tag:
            o["V3"] = sign([v["rest_r"] for v in sst])
    else:
        o["Sst_undecided" + tag] = True
    if not tag:
        if len(vip) >= 8:
            o["V4"] = sign([v["real_up"] - 0.5 for v in vip])
            if len(sst) >= 8:
                p = mannwhitneyu([v["w_up"] - v["real_up"] for v in sst], [v["w_up"] - v["real_up"] for v in vip], alternative="greater").pvalue
                o["V5"] = {"p": float(p), "supported": bool(p < 0.05)}
        else:
            o["Vip_undecided"] = True
    return o


def main():
    if "\n**Status: FROZEN" not in (ROOT / "docs/OPTO_VBN.md").read_text():
        sys.exit("not frozen")
    wt = {}
    for m, line in LINE.items():
        if line != "wt":
            continue
        d = real.load(m)
        cls, names = real.classes(d, np.zeros(len(d["trains"]), bool))
        rec = real.recording(d, cls, len(names))
        sd = np.maximum(real.spont_sd(rec["spont"]), 1e-9)
        keep = rec["cls"] >= 0
        wt[m] = dict(zip(names, core.profile(real.unit_responses(rec["block"], rec["on_test"], sd)[:, keep], rec["cls"][keep], np.arange(len(names)))))
    names = sorted({k for v in wt.values() for k in v})
    wt_med = {k: float(np.median([v[k] for v in wt.values() if k in v])) for k in names}
    drop = sorted(k for k, x in wt_med.items() if abs(x) > 0.5)
    print("dropped", drop, flush=True)
    M, Mvis, Mbroad, left = {}, {}, {}, {}
    for m, line in LINE.items():
        if line == "wt":
            continue
        d = real.load(m)
        t = real.tag(d)
        if t.sum() < 3:
            left[m] = f"{int(t.sum())} tagged"; continue
        r = per_mouse(d, t, drop)
        if r is None:
            left[m] = "fewer than 4 classes"; continue
        M[m] = {"line": line, "tagged": int(t.sum()), **r}
        rv = per_mouse(d, t, drop, lambda k: k.startswith("VIS"))
        if rv: Mvis[m] = {"line": line, **rv}
        rb = per_mouse(d, t, drop, lambda k: k.endswith("|b"))
        if rb: Mbroad[m] = {"line": line, **rb}
        print(m, line, {k: round(v, 3) for k, v in r.items() if isinstance(v, float)}, flush=True)
    out = {"dropped_classes": drop, "left_out": left, **claims(M), **claims(Mvis, "_visual_only"), **claims(Mbroad, "_broad_only")}
    for line in ("Sst", "Vip"):
        v = [x for x in M.values() if x["line"] == line]
        out[f"median_{line}"] = {k: float(np.nanmedian([x[k] for x in v])) for k in ("real_up", "w_up", "rest_r", "W", "P", "c")} if v else None
    out["mice"] = {m: {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v.items() if k != "profile"} for m, v in M.items()}
    (ROOT / "docs/figures/opto/vbn_result.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "mice"}, indent=1, default=float))


if __name__ == "__main__":
    main()
