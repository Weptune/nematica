"""Study W calibration (docs/OPTO_WANING.md). Synthetic driven units with a known fade, on each real mouse's
own light schedule, levels, number of driven units and their resting rates; then the tagging rule and the
registered measure, unchanged. No real response to light is read: only schedules, levels, unit counts and
resting rates. The answer to a pulse is `gain` extra spikes at level 1, scaled by level, falling linearly
over the block to `f` times its starting size.
python -I scripts/opto_waning_cal.py -> docs/figures/opto/waning_cal.json"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from nematica.opto import real, waning  # noqa: E402

V = json.loads((ROOT / "docs/figures/opto/vbn_result.json").read_text())


def instruments():
    out = {}
    for m, v in V["mice"].items():
        d = real.load(m)
        t = real.tag(d)                      # which units are driven: Study V's rule, as already used
        out[m] = {"rates": d["firing_rate"][t], "opto_start": d["opto_start"], "opto_duration": d["opto_duration"], "opto_name": d["opto_name"],
                  "opto_level": d["opto_level"], "t0": float(d["opto_start"].min()) - 5, "t1": float(d["opto_stop"].max()) + 5}
    return out


def synth(rng, inst, f, gain):
    """Spike trains for the driven units: Poisson at the resting rate, plus Poisson extra spikes 2 to 9 ms
    after each square pulse and through each half-cosine, fading with the trial's place in the block."""
    order = np.argsort(inst["opto_start"]); place = np.empty(len(order)); place[order] = np.linspace(0, 1, len(order))
    size = (1 - (1 - f) * place) * inst["opto_level"]
    trains = []
    for r in inst["rates"]:
        s = [rng.uniform(inst["t0"], inst["t1"], rng.poisson(max(r, 0.05) * (inst["t1"] - inst["t0"])))]
        for on, dur, name, k in zip(inst["opto_start"], inst["opto_duration"], inst["opto_name"], size):
            if name == "pulse":
                s.append(on + rng.uniform(0.002, 0.009, rng.poisson(gain * k)))
            else:
                s.append(on + rng.uniform(0, 1.0, rng.poisson(8 * gain * k)))
        trains.append(np.sort(np.concatenate(s)))
    d = {**inst, "trains": trains}
    t = real.tag(d)
    return d, t


def main():
    INST = instruments()
    rng = np.random.default_rng(20261121)
    out = []
    for f in (1.0, 0.8, 0.5):
        for gain in (0.5, 1.0):
            for rep in range(20):
                rp, rs = [], []
                for m, inst in INST.items():
                    d, t = synth(rng, inst, f, gain)
                    if t.sum() < 3:
                        continue
                    rp.append(waning.fade(*waning.pulse_answers(d, t))["ratio"]); rs.append(waning.fade(*waning.slow_answers(d, t))["ratio"])
                rp, rs = np.array(rp), np.array(rs)
                out.append({"f": f, "gain": gain, "mice": len(rp), "pulse_median": float(np.nanmedian(rp)), "slow_median": float(np.nanmedian(rs)),
                            "pulse_above_worm": waning.sign_p(rp - 0.64), "pulse_below_one": waning.sign_p(1 - rp),
                            "slow_above_worm": waning.sign_p(rs - 0.64), "slow_below_one": waning.sign_p(1 - rs)})
            g = [o for o in out if o["f"] == f and o["gain"] == gain]
            print(f"f {f} gain {gain}: true late/early {(f + (1 - f) / 6) / (1 - (1 - f) / 6):.2f} | mice {g[0]['mice']} | pulse median {np.median([o['pulse_median'] for o in g]):.3f} slow {np.median([o['slow_median'] for o in g]):.3f}"
                  f" | 'above the worm' called: pulse {np.mean([o['pulse_above_worm'] < 0.05 for o in g]):.2f} slow {np.mean([o['slow_above_worm'] < 0.05 for o in g]):.2f}"
                  f" | 'a fade' called: pulse {np.mean([o['pulse_below_one'] < 0.05 for o in g]):.2f} slow {np.mean([o['slow_below_one'] < 0.05 for o in g]):.2f}", flush=True)
    (ROOT / "docs/figures/opto/waning_cal.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
