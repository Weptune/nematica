"""Amendment 28: tune the slow-drive strength on half the Allen mice, test it on the other half.

The random RNN (A1, 480 units, 3 seeds, 280,000 steps) gets slow drives (zoo.with_slow_drives, time constant
50 x its native timescale, k = 10) carrying a share s of each unit's variance. Each version is recorded at
each mouse's own instrument exactly as in amendment 27 (scripts/map_permouse.py), and compared with that
mouse on slow memory.

Usage: python scripts/map_slowdrive.py tune | choose | test | analyse
Results: data/cache/map_ais/slowdrive/s<share>_<mouse>.pkl; docs/figures/map_slowdrive.json."""
import json
import pickle
import shutil
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_ais as AIS  # noqa: E402
import map_permouse as PM  # noqa: E402
import map_step2_r4g as S2  # noqa: E402
from nematica.map import pipeline, zoo  # noqa: E402

OUT = AIS.CACHE / "slowdrive"
TMP = ROOT / "data/cache/slowdrive_acts"
GRID = (0.06, 0.12, 0.18)
SPLIT_SEED = 2026
RES = ROOT / "docs/figures/map_slowdrive.json"


def split():
    ids = sorted(m["id"] for m in PM.mice())
    p = np.random.default_rng(SPLIT_SEED).permutation(len(ids))
    h = len(ids) // 2
    return [ids[i] for i in p[:h]], [ids[i] for i in p[h:]]


def build(share):
    TMP.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        f = TMP / f"s{share}_{i}.npy"
        if not f.exists():
            A = zoo.random_rnn(n=480, seed=i, steps=280_000)[0]
            np.save(f, zoo.with_slow_drives(A, seed=i, share=share))
            del A
    return [np.load(TMP / f"s{share}_{i}.npy", mmap_mode="r") for i in range(3)]


def record(share, mice_ids):
    OUT.mkdir(parents=True, exist_ok=True)
    s1 = {r["id"]: r for r in json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"]["R4a"]["individuals"]}
    acts = None
    for mid in mice_ids:
        f = OUT / f"s{share}_{mid}.pkl"
        if f.exists():
            continue
        acts = acts or build(share)
        r1 = s1[mid]
        prof = {k: r1[k] for k in ("bins_per_tau", "count_per_bin", "noise", "rate_log_sd")} | {"group": S2.GROUP}
        crop = int(round(S2.CROP_TAU * r1["bins_per_tau"]))
        try:
            r = pipeline.ai_at_prep(acts, "spikes", prof, recs_per_instance=2, budget=False, crop_len=crop,
                                    n_draws=AIS.N_DRAWS, max_crops=1, cross_segments=True)
        except Exception as e:  # noqa: BLE001
            r = {"values": {}, "replicates": [], "reached": False, "error": f"{type(e).__name__}: {e}"}
        r.update(code_sha256_16=AIS.code_hash(), mouse=mid, share=share, profile=prof, crop_len=crop)
        f.write_bytes(pickle.dumps(r))
        print("share", share, mid, r.get("reached"), round(PM.ai_value(r) if r.get("reached") else np.nan, 3), flush=True)
    if TMP.exists():
        shutil.rmtree(TMP)                               # temporary activity this script wrote


def diffs(share, mice_ids):
    mv = {m["id"]: m["values"]["slow_fraction"] for m in PM.mice()}
    out = []
    for mid in mice_ids:
        if share == 0.0:
            f = PM.OUT / f"A1_{mid}.pkl"                  # amendment 27's recordings: share 0 and 0.4
        elif share == 0.4:
            f = PM.OUT / f"A1-slow_{mid}.pkl"
        else:
            f = OUT / f"s{share}_{mid}.pkl"
        r = pickle.loads(f.read_bytes()) if f.exists() else {}
        out.append(mv[mid] - PM.ai_value(r) if r.get("reached") else np.nan)
    return np.array(out)


def choose():
    tune, _ = split()
    rows = {}
    for s in (0.0,) + GRID + (0.4,):
        d = diffs(s, tune)
        rows[s] = {"median_diff": float(np.nanmedian(d)), "n": int(np.isfinite(d).sum())}
    best = min(GRID, key=lambda s: (abs(rows[s]["median_diff"]), s))
    return rows, best


def analyse():
    tune, held = split()
    rows, best = choose()
    sd = float(np.std([m["values"]["slow_fraction"] for m in PM.mice()], ddof=1))
    d = diffs(best, held)
    fin = np.isfinite(d)
    res = {"tuning_mice": tune, "held_out_mice": held, "tuning_curve": rows, "chosen_share": best,
           "ruler_sd": sd, "n_pairs": int(fin.sum()), "missing": int((~fin).sum())}
    if fin.sum() < 0.8 * len(d):
        res["result"] = "not testable (fewer than 80% of pairs)"
    else:
        dd = d[fin]
        rng = np.random.default_rng(0)
        boot = [np.median(rng.choice(dd, len(dd))) for _ in range(5000)]
        ci = [float(np.percentile(boot, 5)), float(np.percentile(boot, 95))]
        med = float(np.median(dd))
        pp = float(stats.wilcoxon(dd, alternative="greater").pvalue)
        pn = float(stats.wilcoxon(dd, alternative="less").pvalue)
        equiv = ci[0] > -PM.EQUIV * sd and ci[1] < PM.EQUIV * sd
        res.update(median_diff=med, median_diff_ruler=med / sd, ci90=ci, ci90_ruler=[c / sd for c in ci],
                   p_mouse_above=pp, p_mouse_below=pn,
                   result="confirmed" if equiv else
                   "refuted" if (pp < 0.05 or pn < 0.05) and abs(med) > PM.EQUIV * sd else "unclear")
    RES.write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: v for k, v in res.items() if "mice" not in k}, indent=1, default=float))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "tune":
        tune, _ = split()
        for s in GRID:
            record(s, tune)
    elif cmd == "choose":
        print(choose())
    elif cmd == "test":
        _, held = split()
        record(choose()[1], held)
    else:
        analyse()
