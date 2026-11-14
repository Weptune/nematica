"""Amendment 27: the per-mouse comparison. Each AI (A1 random RNN; A1-slow random RNN with slow drives) is
recorded at every usable Allen mouse's OWN single-unit instrument numbers (samples per timescale, spikes per
bin, white share, rate spread), pooled in groups of 8, cut into one crop of 5,000 of that mouse's
timescales per recording (2 recordings per instance, 3 instances, no budget), and compared with that mouse.

Usage: python scripts/map_permouse.py record A1 | record A1-slow | analyse
Results: data/cache/map_ais/permouse/<ai>_<mouse>.pkl; docs/figures/map_permouse.json."""
import hashlib
import json
import pickle
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_ais as AIS  # noqa: E402
import map_ais_r4a as R4A  # noqa: E402
import map_step2_r4g as S2  # noqa: E402
from nematica.map import pipeline  # noqa: E402

OUT = AIS.CACHE / "permouse"
SHA = hashlib.sha256((ROOT / "scripts/map_permouse.py").read_bytes() + R4A.WRAPPER.encode()).hexdigest()[:16]
EQUIV = 0.5                     # ruler units: a smaller median difference is "no meaningful difference"


def mice():
    """The 35 mice usable on slow memory in the registered Allen analysis (finite value and finite SE)."""
    b = json.loads((ROOT / "docs/figures/map_brains.json").read_text())["preparations"]["R4a"]["individuals"]
    return [r for r in b if not r.get("error") and np.isfinite(r["values"].get("slow_fraction", np.nan))
            and np.isfinite(r["se"].get("slow_fraction", np.nan))]


def record(aid):
    R4A.setup()
    OUT.mkdir(parents=True, exist_ok=True)
    s1 = {r["id"]: r for r in json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"]["R4a"]["individuals"]}
    acts = None
    for m in mice():
        f = OUT / f"{aid}_{m['id']}.pkl"
        if f.exists() and pickle.loads(f.read_bytes()).get("sha") == SHA:
            continue
        if acts is None:
            inst = AIS.builder(aid, "R4a")[1]()
            acts, segs = [np.asarray(a, np.float32) for a, _ in inst], [g for _, g in inst]
        r1 = s1[m["id"]]
        prof = {k: r1[k] for k in ("bins_per_tau", "count_per_bin", "noise", "rate_log_sd")} | {"group": S2.GROUP}
        crop = int(round(S2.CROP_TAU * r1["bins_per_tau"]))
        try:
            r = pipeline.ai_at_prep(acts, "spikes", prof, segments=segs[0] or None, recs_per_instance=2, budget=False,
                                    crop_len=crop, n_draws=AIS.N_DRAWS, max_crops=1, cross_segments=True)
        except Exception as e:  # noqa: BLE001
            r = {"values": {}, "replicates": [], "reached": False, "error": f"{type(e).__name__}: {e}"}
        r.update(sha=SHA, code_sha256_16=AIS.code_hash(), mouse=m["id"], profile=prof, crop_len=crop, ai=aid)
        f.write_bytes(pickle.dumps(r))
        print(aid, m["id"], r.get("reached"), round(r.get("values", {}).get("slow_fraction", np.nan), 3), flush=True)


def ai_value(r):
    reps = [x.get("slow_fraction", np.nan) for x in r.get("replicates", [])]
    fin = [x for x in reps if np.isfinite(x)]
    return float(np.median(fin)) if reps and len(fin) >= 0.8 * len(reps) else np.nan


def analyse():
    M = mice()
    v = np.array([m["values"]["slow_fraction"] for m in M])
    sd = float(np.std(v, ddof=1))
    out = {"n_mice": len(M), "ruler_sd": sd, "equivalence_ruler_units": EQUIV, "tests": {}, "pairs": {}}
    for aid, test, pred in (("A1", "B' per-mouse slow memory", "below"), ("A1-slow", "D' per-mouse slow drives", "inside")):
        rows = []
        for m in M:
            f = OUT / f"{aid}_{m['id']}.pkl"
            r = pickle.loads(f.read_bytes()) if f.exists() else {}
            ok = r.get("sha") == SHA and r.get("reached")
            rows.append((m["id"], m["values"]["slow_fraction"], ai_value(r) if ok else np.nan))
        d = np.array([mv - av for _, mv, av in rows])     # mouse minus AI at that mouse's instrument
        fin = np.isfinite(d)
        out["pairs"][aid] = [{"mouse": i, "mouse_value": mv, "ai_value": av} for i, mv, av in rows]
        res = {"n_pairs": int(fin.sum()), "missing": int((~fin).sum())}
        if fin.sum() < 0.8 * len(d):
            res["result"] = "not testable (fewer than 80% of pairs)"
            out["tests"][test] = res
            continue
        dd = d[fin]
        rng = np.random.default_rng(0)
        boot = [np.median(rng.choice(dd, len(dd))) for _ in range(5000)]
        ci = [float(np.percentile(boot, 5)), float(np.percentile(boot, 95))]
        med = float(np.median(dd))
        p_pos = float(stats.wilcoxon(dd, alternative="greater").pvalue)
        p_neg = float(stats.wilcoxon(dd, alternative="less").pvalue)
        res.update(median_diff=med, median_diff_ruler=med / sd, ci90=ci, ci90_ruler=[c / sd for c in ci],
                   p_mouse_above=p_pos, p_mouse_below=p_neg, frac_mouse_above=float(np.mean(dd > 0)))
        equiv = ci[0] > -EQUIV * sd and ci[1] < EQUIV * sd
        if pred == "below":                               # AI below the mouse: d > 0
            res["result"] = ("confirmed" if p_pos < 0.05 and med > EQUIV * sd else
                             "refuted" if p_neg < 0.05 or equiv else "unclear")
        else:                                             # inside: no meaningful difference either way
            res["result"] = ("confirmed" if equiv else
                             "refuted" if (p_pos < 0.05 or p_neg < 0.05) and abs(med) > EQUIV * sd else "unclear")
        out["tests"][test] = res
    (ROOT / "docs/figures/map_permouse.json").write_text(json.dumps(out, indent=1, default=float))
    for k, t in out["tests"].items():
        print(k, t)


if __name__ == "__main__":
    if sys.argv[1] == "record":
        record(sys.argv[2])
    else:
        analyse()
