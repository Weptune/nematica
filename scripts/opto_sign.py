"""Study S (docs/OPTO_SIGN.md): sign of the driven effect vs the watching copy's prediction, on the 15 Cre
mice Study O did not use. Refuses to run unless the registration is frozen.
python -I scripts/opto_sign.py -> docs/figures/opto/sign_result.json (summary numbers only)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from nematica.opto import core, real  # noqa: E402
from opto_calibrate import sign_p  # noqa: E402
from opto_run import LINE, named_profile  # noqa: E402

MICE = ["sub-699733573", "sub-703279277", "sub-734865729", "sub-735109599", "sub-738651046", "sub-744915196",
        "sub-763236006", "sub-763884096", "sub-707296975", "sub-726170927", "sub-739783158", "sub-757329617",
        "sub-730760263", "sub-732548371", "sub-745276220"]
DROP = ["VISmma|n", "VISp|n"]


def main():
    if "\n**Status: FROZEN" not in (ROOT / "docs/OPTO_SIGN.md").read_text():
        sys.exit("not frozen")
    studyO = "--studyO" in sys.argv          # Study O's 9 mice, descriptive only (the exploratory table)
    mice, left_out = {}, {}
    for m in (json.loads((ROOT / "docs/figures/opto/result.json").read_text())["mice"] if studyO else MICE):
        d = real.load(m)
        t = real.tag(d)
        if t.sum() < 3:
            left_out[m] = f"{int(t.sum())} tagged units"; continue
        cls, names = named_profile(d, t, DROP)
        if len(names) < 4:
            left_out[m] = f"{len(names)} classes"; continue
        n = len(names)
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
        mice[m] = {"line": LINE[m], "tagged": int(t.sum()), "classes": n, "real_up": float(np.mean(prof > 0)),
                   "w_up": float(np.mean(pw > 0)), "rest_r": rest_r, "W": r["W"], "P": r["P"], "c": r["c"],
                   "gap": (r["P"] - r["W"]) / r["ceiling"] if np.isfinite(r["ceiling"]) else None}
        print(m, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in mice[m].items()}, flush=True)
    if studyO:
        (ROOT / "docs/figures/opto/sign_studyO.json").write_text(json.dumps(
            {m: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in x.items()} for m, x in mice.items()}, indent=1, default=float))
        return
    ps = [m for m in mice if mice[m]["line"] in ("Pvalb", "Sst")]
    out = {"left_out": left_out, "n_pvalb_sst": len(ps)}
    if len(ps) < 8:
        out["undecided"] = True
    else:
        s1 = [0.5 - mice[m]["real_up"] for m in ps]
        s2 = [mice[m]["w_up"] - mice[m]["real_up"] for m in ps]
        s3 = [mice[m]["rest_r"] for m in ps]
        for k, x in (("S1", s1), ("S2", s2), ("S3", s3)):
            out[k] = {"positive": int(sum(v > 0 for v in x)), "nonzero": int(sum(v != 0 for v in x)),
                      "p": sign_p(x), "supported": bool(sign_p(x) < 0.05)}
    out["mice"] = {m: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in x.items()} for m, x in mice.items()}
    (ROOT / "docs/figures/opto/sign_result.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "mice"}, indent=1))


if __name__ == "__main__":
    main()
