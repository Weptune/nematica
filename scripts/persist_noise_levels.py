"""Study 3, before freezing (docs/PERSIST.md section 8): the noise levels of N3 (GRU + noise) and N6
(Pythia-160M + noise). Each level is the one whose recording at the median Study 2 mouse's NM1 instrument
(a 6,000-bin clip, 10 repeats) gives whole-clip M1 equal to the median mouse's NM1 M1 (Study 2, 49 mice).
Instance 0 only; the level is then fixed for all instances. Bisection on log noise, 8 steps.
Writes docs/figures/persist/noise_levels.json (with every evaluation)."""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("persist_run", ROOT / "scripts/persist_run.py")
PR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PR)
from nematica.slow import stream as ST  # noqa: E402

OUT = ROOT / "docs/figures/persist/noise_levels.json"


def target_and_instrument():
    mice = [json.loads(l) for l in open(ROOT / "docs/figures/slow_runs/mice.jsonl")]
    used = set(json.load(open(ROOT / "docs/figures/slow_runs/mice_table.json"))["rows"])
    mice = [m for m in mice if m["id"] in used]
    target = float(np.median([m["M1"] for m in mice]))
    bpt = np.array([m["profile"]["bins_per_tau"] for m in mice])
    med = mice[int(np.argsort(bpt)[len(bpt) // 2])]
    return target, {"id": med["id"], "profile": med["profile"], "units": 200, "repeats": 10, "bins": PR.CLIP_BINS}


def m1_at(gen, mouse):
    A, st, length = gen()
    out = ST.record_stream(A, st, length, mouse["profile"], nb_mouse=PR.CLIP_BINS, R_mouse=10, n_units_mouse=200,
                           seed=7, halves=False, max_bins=PR.MAX_BINS)
    return out.get("M1", np.nan), bool(out.get("reached")), int(out.get("recorded_bins", 0))


def bisect(key, make, lo, hi, target, mouse, log):
    for step in range(8):
        mid = float(np.sqrt(lo * hi))
        m1, reached, nb = m1_at(lambda: make(mid), mouse)
        log.append({"system": key, "noise": mid, "M1": m1, "reached": reached, "bins": nb})
        print(key, step, round(mid, 4), round(m1, 3), reached, nb, flush=True)
        if m1 < target:
            lo = mid
        else:
            hi = mid
    return float(np.sqrt(lo * hi))


def main():
    target, mouse = target_and_instrument()
    prof = mouse["profile"]
    log = []
    res = json.loads(OUT.read_text()) if OUT.exists() else {}
    if "N3" not in res:
        base = m1_at(lambda: PR.gen_char("gru", 0, prof, 10, noise_sd=0.0), mouse)
        log.append({"system": "N3", "noise": 0.0, "M1": base[0], "reached": base[1], "bins": base[2]})
        res["N3"] = bisect("N3", lambda s: PR.gen_char("gru", 0, prof, 10, noise_sd=s), 1e-3, 1.0, target, mouse, log)
    if "N6" not in res:
        model = "EleutherAI/pythia-160m-seed{s}"
        base = m1_at(lambda: PR.gen_lm(model, 0, prof, 10, noise_sd=0.0), mouse)
        log.append({"system": "N6", "noise": 0.0, "M1": base[0], "reached": base[1], "bins": base[2]})
        res["N6"] = bisect("N6", lambda s: PR.gen_lm(model, 0, prof, 10, noise_sd=s), 1e-3, 2.0, target, mouse, log)
    res["target_M1"] = target
    res["instrument_mouse"] = mouse["id"]
    res["evaluations"] = res.get("evaluations", []) + log
    OUT.write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: res[k] for k in ("N3", "N6", "target_M1")}))


if __name__ == "__main__":
    main()
