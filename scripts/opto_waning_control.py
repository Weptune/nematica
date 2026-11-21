"""Study W, controls added AFTER the registered run (docs/OPTO_WANING.md, "After the result"). Not registered.

1. The light alone. Study V found that in wild-type mice, which carry no channel, the light by itself moves
   most regions. If that response wears off with repetition, it could pass for a fade in the neighbours of
   driven cells. So: the same neighbours' measure in the wild-type mice (no driven units there).
2. The registered split left in the one class that Study V and P drop because the light alone moves it
   (VIS|n). Here it is dropped, as there.
3. In each mouse, the classes that fall and the classes that rise (by the middle third, which shares no
   trial with the thirds compared), each on their own.
4. The very first flash (found by the independent check, reproduced here). No registered measure holds the
   first answer to light: the first pulse is odd-numbered and was spent on choosing the units. Here the
   driven units' answer to the first, second and third pulse of the block is set against their mean answer
   to later odd-numbered pulses at the same light level (pulses 7 onward), separately for mice whose block
   opens with a pulse and mice whose block opens with a half-cosine. One trial per mouse.

python -I scripts/opto_waning_control.py -> docs/figures/opto/waning_control.json"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from nematica.opto import core, real, waning  # noqa: E402
from opto_run import named_profile  # noqa: E402

V = json.loads((ROOT / "docs/figures/opto/vbn_result.json").read_text())
FEAS = [json.loads(l) for l in (ROOT / "docs/figures/opto/feasibility_vbn.jsonl").read_text().splitlines()]
LINE = {d["id"]: d["genotype"].split("-")[0].split("/")[0] for d in FEAS if d.get("opto_n")}
DROP = V["dropped_classes"]


def rec_of(d, t, drop=()):
    cls, names = named_profile(d, t, [k for k in real.classes(d, t)[1] if k in drop]) if drop else real.classes(d, t)
    rec = real.recording(d, cls, len(names))
    ok = real.spont_sd(rec["spont"]) > 0
    rec = {**rec, "spont": [x[:, ok] for x in rec["spont"]], "block": rec["block"][:, ok], "cls": rec["cls"][ok]}
    if any((rec["cls"] == k).sum() == 0 for k in range(rec["n_classes"])) or rec["n_classes"] < 4:
        return None
    return rec


def measures(d, rec):
    hc = real.half_cosine(d)
    o = np.argsort(d["opto_start"][hc])
    on, level = rec["on_test"][o], d["opto_level"][hc][o]
    sd = real.spont_sd(rec["spont"])
    out = waning.split(rec["block"], on, level, rec["cls"], rec["n_classes"], sd)
    early, mid, late = waning.thirds3(level)
    resp = real.unit_responses(rec["block"], on, sd)
    keep, classes = rec["cls"] >= 0, np.arange(rec["n_classes"])
    prof = lambda ix: core.profile(resp[ix][:, keep], rec["cls"][keep], classes)   # noqa: E731
    T, E, L = prof(mid), prof(early), prof(late)
    out["size"] = float(np.sqrt(np.mean(T ** 2)))                      # how big the profile is, in SD units per class
    out["share_up"] = float(np.mean(T > 0))
    for name, sel in (("falling", T < 0), ("rising", T > 0)):
        tt = float(T[sel] @ T[sel]) if sel.sum() >= 3 else 0.0
        ne, nl = (float(E[sel] @ T[sel]) / tt, float(L[sel] @ T[sel]) / tt) if tt > 0 else (np.nan, np.nan)
        out[name] = nl / ne if ne > 0 else np.nan
        out[name + "_n"] = int(sel.sum())
    return out


def summary(x):
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    return {"n": int(ok.sum()), "median": float(np.nanmedian(x)) if ok.any() else None, "interval": waning.boot(x, n=20000), "below_one": int((x[ok] < 1).sum()), "p_below_one": waning.sign_p(1 - x)}


def first_flash(d, t):
    """(opens with a pulse?, [(answer, expected) for the 1st, 2nd, 3rd 10 ms pulse]): expected is the mean
    answer to odd-numbered pulses 7 onward at the same light level."""
    tr = real.square_pulses(d)
    tr = tr[np.isclose(d["opto_duration"][tr], 0.01)]
    tr = tr[np.argsort(d["opto_start"][tr])]
    on, lv = d["opto_start"][tr], d["opto_level"][tr]
    per = np.zeros(len(on))
    for i in np.flatnonzero(t):
        sp = d["trains"][i]
        per += (np.searchsorted(sp, on + 0.009) - np.searchsorted(sp, on + 0.002)) - (np.searchsorted(sp, on) - np.searchsorted(sp, on - 0.007))
    later = np.arange(len(on)) >= 6
    odd = np.arange(len(on)) % 2 == 0
    out = []
    for k in (0, 1, 2):
        same = per[later & odd & (lv == lv[k])]
        out.append((float(per[k]), float(same.mean()) if len(same) else float("nan")))
    return bool(on[0] == d["opto_start"].min()), out


def pooled(pairs, seed=0):
    """Sum of answers over sum of expected, over mice, with a 95% interval resampling mice."""
    a = np.array([p for p in pairs if np.isfinite(p[1])], float)
    if len(a) < 3:
        return None
    rng = np.random.default_rng(seed)
    b = [(lambda ix: a[ix, 0].sum() / a[ix, 1].sum())(rng.integers(0, len(a), len(a))) for _ in range(20000)]
    return {"n": int(len(a)), "ratio": float(a[:, 0].sum() / a[:, 1].sum()), "interval": [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))],
            "above_one": int((a[:, 0] > a[:, 1]).sum())}


def main():
    rows = {}
    for m, line in LINE.items():
        d = real.load(m)
        if line == "wt":
            t = np.zeros(len(d["trains"]), bool)
        elif m in V["mice"]:
            t = real.tag(d)
        else:
            continue
        r = {"line": line}
        if line != "wt":
            r["opens_with_pulse"], r["first"] = first_flash(d, t)
        for key, drop in (("all", ()), ("dropped", DROP)):
            rec = rec_of(d, t, drop)
            r[key] = None if rec is None else measures(d, rec)
        rows[m] = r
        print(m, line, {k: (None if r[k] is None else {q: round(r[k][q], 3) for q in ("net", "net_frac", "beyond", "size", "falling", "rising")}) for k in ("all", "dropped")}, flush=True)
    out = {"dropped_classes": DROP, "mice": rows, "by_line": {}}
    for line in ("wt", "Sst", "Vip"):
        g = [r for r in rows.values() if r["line"] == line]
        out["by_line"][line] = {key: {q: summary([np.nan if r[key] is None else r[key][q] for r in g]) for q in ("net", "net_frac", "beyond", "beyond_frac", "rest", "falling", "rising", "size", "share_up", "half")} for key in ("all", "dropped")}
    opsin = [r for r in rows.values() if r["line"] != "wt"]
    out["pooled_dropped"] = {q: summary([np.nan if r["dropped"] is None else r["dropped"][q] for r in opsin]) for q in ("beyond", "beyond_frac", "net", "net_frac", "falling", "rising")}
    out["pooled_all"] = {q: summary([np.nan if r["all"] is None else r["all"][q] for r in opsin]) for q in ("falling", "rising")}
    out["first_flash"] = {name: {str(k + 1): pooled([r["first"][k] for r in opsin if r["opens_with_pulse"] == flag]) for k in (0, 1, 2)}
                          for name, flag in (("opens_with_pulse", True), ("opens_with_half_cosine", False))}
    out["counted_with_undefined"] = {q: {"below_one": out["by_line"]["wt"]["all"][q]["below_one"], "of": len([r for r in rows.values() if r["line"] == "wt"]),
                                          "p": waning.sign_p([1 - (r["all"][q] if r["all"] and np.isfinite(r["all"][q]) else 2.0) for r in rows.values() if r["line"] == "wt"])} for q in ("net", "net_frac")}
    (ROOT / "docs/figures/opto/waning_control.json").write_text(json.dumps(out, indent=1))
    print("first flash:", json.dumps(out["first_flash"]))
    print("wild type, mice with no ratio counted as not below 1:", out["counted_with_undefined"])
    f = lambda s: f"{s['median']:.3f} [{s['interval'][0]:.2f}, {s['interval'][1]:.2f}] below 1 in {s['below_one']}/{s['n']} p {s['p_below_one']:.3f}" if s["median"] is not None else "none"   # noqa: E731
    for line, v in out["by_line"].items():
        for key in ("all", "dropped"):
            print(line, key, "| size", f"{v[key]['size']['median']:.3f}", "share up", f"{v[key]['share_up']['median']:.2f}", "half", f"{v[key]['half']['median']:.2f}", "| net", f(v[key]["net"]), "| net_frac", f(v[key]["net_frac"]),
                  "| beyond", f(v[key]["beyond"]), "| falling", f(v[key]["falling"]), "| rising", f(v[key]["rising"]), "| rest", f"{v[key]['rest']['median']:.3f}")
    print("pooled, class dropped:", {k: f(v) for k, v in out["pooled_dropped"].items()})
    print("pooled, all classes:", {k: f(v) for k, v in out["pooled_all"].items()})


if __name__ == "__main__":
    main()
