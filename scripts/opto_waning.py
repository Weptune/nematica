"""Study W (docs/OPTO_WANING.md): the registered run. Refuses to run before the registration is frozen, and
refuses to run twice. Nothing is printed until the result file is written.

python -I scripts/opto_waning.py        -> docs/figures/opto/waning_result.json   (run once)
python -I scripts/opto_waning.py --dry  -> /tmp/waning_dry.json: the same code on three synthetic mice that
                                           share only the real mice's trial tables, unit counts, areas and
                                           resting rates (no real spike is read); done before the freeze"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from nematica.opto import real, waning  # noqa: E402

WORM_TOP = 0.64       # top of the worm's interval for a second poke 0.6 to 2 minutes later (0.47, 0.34 to 0.64)
MIN_MICE = 20
CEILING = 0.9         # driven answer at the lowest light level over the highest: above this, the recorded driven units are called at their ceiling
DRY = "--dry" in sys.argv
OUT = Path("/tmp/waning_dry.json") if DRY else ROOT / "docs/figures/opto/waning_result.json"


def synthetic_mouse(d, rng):
    """For --dry only: Poisson spike trains at each unit's resting rate over the spontaneous and light
    blocks, with extra spikes after every light trial in the first 30 units and nothing else. Real spikes
    are thrown away."""
    spans = [(float(a), float(b)) for a, b in d["spont"]] + [(float(d["opto_start"].min()) - 5, float(d["opto_stop"].max()) + 5)]
    trains = []
    for i, r in enumerate(d["firing_rate"]):
        s = [rng.uniform(a, b, rng.poisson(max(float(r), 0.05) * (b - a))) for a, b in spans]
        if i < 30:
            for on, name, lv in zip(d["opto_start"], d["opto_name"], d["opto_level"]):
                s.append(on + (rng.uniform(0.002, 0.009, rng.poisson(1.0 * lv)) if name == "pulse" else rng.uniform(0, 1.0, rng.poisson(8.0 * lv))))
        trains.append(np.sort(np.concatenate(s)))
    return {**d, "trains": trains}


def summary(x):
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    return {"n": int(ok.sum()), "undefined": int((~ok).sum()), "median": float(np.nanmedian(x)) if ok.any() else None, "interval": waning.boot(x),
            "below_one": int((x[ok] < 1).sum()), "above_worm": int((x[ok] > WORM_TOP).sum()), "p_below_one": waning.sign_p(1 - x), "p_above_one": waning.sign_p(x - 1)}


def main():
    if not DRY:
        if "**Status: FROZEN**" not in (ROOT / "docs/OPTO_WANING.md").read_text():
            raise SystemExit("docs/OPTO_WANING.md is not frozen")
        if OUT.exists():
            raise SystemExit("already run: the registered run happens once")
    V = json.loads((ROOT / "docs/figures/opto/vbn_result.json").read_text())
    names = list(V["mice"])[:3] if DRY else list(V["mice"])
    rng = np.random.default_rng(1)
    mice = {}
    for m in names:
        d = real.load(m)
        if DRY:
            d = synthetic_mouse(d, rng)
        t = real.tag(d)
        rp, lp = waning.pulse_answers(d, t)
        rs, ls = waning.slow_answers(d, t)
        mice[m] = {"line": V["mice"][m]["line"], "driven_units": int(t.sum()), "pulse": waning.fade(rp, lp), "slow": waning.fade(rs, ls),
                   "pulse_by_level": [waning.fade(rp[:, lp == k], lp[lp == k])["ratio"] for k in np.unique(lp)],
                   "first": waning.first_pulses(rp, lp), "ceiling_pulse": waning.by_level(rp, lp), "ceiling_slow": waning.by_level(rs, ls),
                   "resting": waning.resting(d, t), "split": waning.split_mouse(d)}

    def col(f, line=None):
        return np.array([f(r) for r in mice.values() if line in (None, r["line"])], float)

    sp = lambda key: (lambda r: np.nan if r["split"] is None else r["split"][key])   # noqa: E731
    P = lambda r: r["pulse"]["ratio"]                                                # noqa: E731
    need = 2 if DRY else MIN_MICE
    pulse, by, bf, rest = summary(col(P)), summary(col(sp("beyond"))), summary(col(sp("beyond_frac"))), summary(col(sp("rest")))
    pulse["p_above_worm"] = waning.sign_p(col(P) - WORM_TOP)
    ceil_p, ceil_s = summary(col(lambda r: r["ceiling_pulse"]["answer"])), summary(col(lambda r: r["ceiling_slow"]["answer"]))
    inside = lambda iv, lo, hi: bool(iv[0] >= lo and iv[1] <= hi)                    # noqa: E731
    claims = {"W1a_fades": None, "W1b_late_third_above_0.64_of_early": None, "W2": None}
    if pulse["n"] >= need:
        claims["W1a_fades"] = bool(pulse["p_below_one"] < 0.05)
        claims["W1b_late_third_above_0.64_of_early"] = bool(pulse["p_above_worm"] < 0.05)
    if by["n"] >= need and bf["n"] >= need:
        a, f = by["p_below_one"] < 0.05, bf["p_below_one"] < 0.05
        if a and f:
            claims["W2"] = "fades faster than the recorded driven units' answer"
            if ceil_s["median"] is not None and ceil_s["median"] > CEILING:
                claims["W2"] += "; the driven units are at their ceiling, so a weakening of the light's effect that their spikes do not show cannot be excluded"
        elif a != f:
            claims["W2"] = "undecided: the two versions disagree, so a fade cannot be told from a drift in the neighbours' resting rate"
        elif inside(by["interval"], 0.8, 1.25) and inside(bf["interval"], 0.8, 1.25) and inside(rest["interval"], 0.9, 1.1):
            claims["W2"] = "no sign of it; follows the recorded driven units within a quarter"
        else:
            claims["W2"] = "no sign of it"
    first = np.array([r["first"] for r in mice.values()], float)
    brng = np.random.default_rng(0)
    fb = [(lambda ix: first[ix, 0].sum() / first[ix, 1].sum())(brng.integers(0, len(first), len(first))) for _ in range(4000)]
    res = {"dry": DRY, "pulse": pulse, "beyond": by, "beyond_frac": bf, "claims": claims,
           "described": {"slow_driven": summary(col(lambda r: r["slow"]["ratio"])), "split_driven": summary(col(sp("driven"))),
                         "net": summary(col(sp("net"))), "net_frac": summary(col(sp("net_frac"))), "neighbours_resting": rest,
                         "driven_resting": summary(col(lambda r: r["resting"])), "half": summary(col(sp("half"))),
                         "ceiling_pulse": ceil_p, "ceiling_slow": ceil_s, "light_low_over_high": summary(col(lambda r: r["ceiling_pulse"]["light"])),
                         "first_two_seen_over_expected": {"pooled": float(first[:, 0].sum() / first[:, 1].sum()), "interval": [float(np.percentile(fb, 2.5)), float(np.percentile(fb, 97.5))]},
                         "by_line": {ln: {"pulse": {**summary(col(P, ln)), "p_above_worm": waning.sign_p(col(P, ln) - WORM_TOP)}, "beyond": summary(col(sp("beyond"), ln)),
                                          "beyond_frac": summary(col(sp("beyond_frac"), ln)), "net": summary(col(sp("net"), ln)), "split_driven": summary(col(sp("driven"), ln))}
                                     for ln in sorted({r["line"] for r in mice.values()})},
                         "pulse_by_level_rank": {str(j): summary([r["pulse_by_level"][j] for r in mice.values()]) for j in range(3)}},
           "mice": mice}
    OUT.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("pulse", "beyond", "beyond_frac", "claims")}, indent=1))
    print(json.dumps(res["described"], indent=1))


if __name__ == "__main__":
    main()
