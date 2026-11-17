"""Study 4 pipeline (docs/BARCODE.md). Resumable stages; summary numbers only in docs/figures/barcode/:

  python scripts/barcode_run.py mice     # per mouse and level: instrument numbers, M1, M2 (90 repeats)
  python scripts/barcode_run.py ais      # R0, the networks at 4 depths, the stacked RNN, at each mouse's levels
  python scripts/barcode_run.py tests    # H1 and H2

`mice` and `ais` refuse real data until BARCODE.md is frozen ("Frozen at commit <hash>"). `--dry` uses
synthetic stand-ins for the mice (nothing real is read) and small systems, to check the code path.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.barcode import data as BD, inputs as BI  # noqa: E402
from nematica.map import instrument as INS  # noqa: E402
from nematica.persist import synthetic as PS  # noqa: E402
from nematica.slow import data as D, inputs as I, measures as M, stream as ST  # noqa: E402

OUT = ROOT / "docs/figures/barcode"
K0 = 2
CLIP_BINS = 400
MAX_BINS = 4 * CLIP_BINS
MIN_UNITS = 30
MAX_UNITS = 480
MIN_SPIKES = int(round(200 * 720.0 / 510.0))     # Study 2's 200 spikes per 510 s, over 90 x 8 s
MIN_LEVELS = 3
LEVELS = ("visual_thalamus", "VISp", "VIS_higher", "hippocampus")
KEYS = ("bins_per_tau", "count_per_bin", "noise", "rate_log_sd")
PRIMARY = ("M1", "M2", "ti", "tl", "int_ceiling", "lock_ceiling", "no_shared", "no_locked")
NETWORKS = (("P160", "EleutherAI/pythia-160m-seed{s}"), ("P410", "EleutherAI/pythia-410m-seed{s}"),
            ("M370", "state-spaces/mamba-370m-hf"))
_PAT = re.compile(r"^(VIS[a-z]+?)(1|2/3|4|5|6a|6b)?$")


def frozen():
    m = re.search(r"Frozen at commit ([0-9a-f]{7,40})", (ROOT / "docs/BARCODE.md").read_text())
    return m.group(1) if m else None


def append(name, row):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "a") as f:
        f.write(json.dumps(row, default=float) + "\n")


def done(name, key):
    f = OUT / name
    if not f.exists():
        return set()
    return {tuple(r[k] for k in key) for r in map(json.loads, f.read_text().splitlines()) if "error" not in r}


def level_of(area):
    a = str(area)
    m = _PAT.match(a)
    b = m.group(1) if m else a
    if b.startswith(("LGd", "LGv", "LP")):
        return 0
    if b == "VISp":
        return 1
    if b.startswith("VIS"):
        return 2
    if b.startswith(("CA1", "CA2", "CA3", "DG", "SUB", "ProS", "PoST", "PRE", "POST")):
        return 3
    return -1


def include(X):
    """Study 2's inclusion rule over the 90 repeats: rate at least 0.05 Hz, at least MIN_SPIKES spikes."""
    n = X.sum(0)
    return (X.std(0) > 1e-9) & (n >= MIN_SPIKES) & (n / (len(X) * INS.SPIKE_BIN_S) >= INS.MIN_RATE_HZ)


def measures(Y):
    r = M.lag_measures(Y, k0=K0)
    a, b = M.lag_measures(Y[0::2], k0=K0), M.lag_measures(Y[1::2], k0=K0)
    return {**{k: r[k] for k in PRIMARY}, "M1_odd": a["M1"], "M1_even": b["M1"]}


def running(z, nb):
    t, x = z["run_t"], z["run_x"]
    if len(t) < 2:
        return None
    ok = np.isfinite(x)
    B = np.full((len(z["starts"]), nb, 1), np.nan)
    for r, s0 in enumerate(z["starts"]):
        B[r, :, 0] = np.interp(s0 + (np.arange(nb) + 0.5) * 0.02, t[ok], x[ok])
    return B


def _fake(uid):
    """Dry run: 4 synthetic 'levels' whose internal share rises (0.2, 0.3, 0.4, 0.5), recorded at one
    instrument; nothing real is read."""
    rng = np.random.default_rng(zlib.crc32(uid.encode()))
    out = []
    for k, share in enumerate((0.2, 0.3, 0.4, 0.5)):
        A, st = PS.system(rng, "generated", 120, R=30, N=60, share=share, env_kind="flat")
        rec = ST.Recorder(A, st, 120, {"hold": 1, "bin_steps": 0.3, "mean_count": 0.03, "gain": 1.0,
                                       "rate_log_sd": 1.0}, seed=k)
        out.append(np.clip(rec.counts(np.arange(len(rec.cols))), 0, 255).astype(np.uint8))
    return out


def stage_mice(dry=False):
    name = "mice_dry.jsonl" if dry else "mice.jsonl"
    have = {k[0] for k in done(name, ("id",))}
    for rank, a in enumerate(BD.sessions()):
        uid = a["path"].split("/")[0]
        if uid in have:
            continue
        try:
            levels = {}
            if dry:
                Ys = _fake(uid)
                z = None
            else:
                z = BD.cache(a)
                Yall = BD.counts(z)
                lv = np.array([level_of(x) for x in z["area"]])
            for k in range(4):
                if dry:
                    Y = Ys[k]
                    sel = np.ones(Y.shape[2], bool)
                else:
                    sel = z["qc"] & (lv == k)
                    Y = Yall[:, :, sel]
                R, nb, N = Y.shape
                X = Y.reshape(R * nb, N).astype(np.float32)
                keep = include(X) if not dry else np.ones(N, bool)
                if keep.sum() < MIN_UNITS:
                    levels[LEVELS[k]] = {"units": int(keep.sum()), "used": False}
                    continue
                if keep.sum() > MAX_UNITS:
                    ki = np.sort(np.random.default_rng(zlib.crc32(f"{uid}{k}".encode())).choice(
                        np.flatnonzero(keep), MAX_UNITS, replace=False))
                    keep = np.zeros_like(keep)
                    keep[ki] = True
                seg = [r * nb for r in range(1, R)]
                prof = INS.instrument_numbers({"activity": X[:, keep], "dt": INS.SPIKE_BIN_S, "segments": seg},
                                              "spikes")
                row = {"units": int(keep.sum()), "used": True, "repeats": R, "bins": nb,
                       "profile": {x: prof.get(x) for x in KEYS}, **measures(Y[:, :, keep])}
                if not dry:
                    try:
                        B = running(z, nb)
                        Yr, r2 = D.regress_out(Y[:, :, keep], B)
                        row["behaviour_removed"] = {"M1": M.lag_measures(Yr, k0=K0)["M1"], "median_r2": r2}
                    except Exception as e:  # noqa: BLE001
                        row["behaviour_error"] = f"{type(e).__name__}: {e}"
                levels[LEVELS[k]] = row
            res = {"id": uid, "rank": rank, "levels": levels, "dry": dry, "frozen": frozen(),
                   "n_levels": sum(v.get("used", False) for v in levels.values())}
        except Exception as e:  # noqa: BLE001
            res = {"id": uid, "error": f"{type(e).__name__}: {e}"}
        append(name, res)
        print(uid, res.get("n_levels"), res.get("error"), flush=True)
        if dry and len(done(name, ("id",))) >= 6:
            break


# ------------------------------------------------------------------------------------------------ systems
def mice_rows(dry=False):
    rows = [r for r in map(json.loads, (OUT / ("mice_dry.jsonl" if dry else "mice.jsonl")).read_text().splitlines())
            if "error" not in r and r["n_levels"] >= MIN_LEVELS]
    for r in rows:
        r["instance"] = r["rank"] % 3
    return rows


def vis_profile(rows):
    """Median instrument over the mice's visual-cortex levels (used to size every clip)."""
    profs = [v["profile"] for r in rows for k, v in r["levels"].items() if v.get("used") and k.startswith("VIS")]
    return {k: float(np.nanmedian([p[k] for p in profs])) for k in KEYS}


def record(A, starts, length, lvl, seed):
    sil = M.silent_units(A)
    if sil.any():
        A = A[:, ~sil]
    out = ST.record_stream(A, starts[:lvl["repeats"]], length, lvl["profile"], nb_mouse=int(lvl["bins"]),
                           R_mouse=int(lvl["repeats"]), n_units_mouse=int(lvl["units"]), seed=seed, halves=False,
                           max_bins=MAX_BINS)
    if "error" in out:
        raise RuntimeError(out["error"])
    return {k: out.get(k) for k in (*PRIMARY, "reached", "recorded_bins", "units_used", "numbers_on_repeats",
                                    "knobs")}


def clip_tokens(make, prof, guess=20):
    """Pilot (streamed recorder, as the real recordings): tokens so the clip records as about CLIP_BINS."""
    As, st, length = make(guess, 3)
    out = ST.record_stream(As[0], st, length, prof, nb_mouse=CLIP_BINS, R_mouse=3, n_units_mouse=100, seed=0,
                           halves=False, max_bins=MAX_BINS)
    return max(int(round(guess * CLIP_BINS / (out.get("recorded_bins") or CLIP_BINS))), 3)


def gen_lm(model, inst, prof, R):
    name = model.format(s=inst + 1)
    tok = np.load(ROOT / "data/external/books/tokens.npy")
    at = len(tok) * (inst + 2) // 6

    def make(c, r):
        clip, ctx = I.text_clip_and_contexts(tok, c, 256, r, seed=inst, clip_at=at)
        As, st, meta = BI.lm_depth_repeats(name, clip, ctx)
        return As, st, c
    n = clip_tokens(make, prof)
    return make(n, R)


def gen_r0(prof, R):
    T = int(np.clip(round(CLIP_BINS * 10.0 / prof["bins_per_tau"]), 60, 20000))
    A, st = PS.system(np.random.default_rng(0), "generated", T, R=R, N=300, share=0.4, tau_int=10.0,
                      env_kind="flat")
    return [A] * 4, st, T


def gen_stack(inst, prof, R, dry=False):
    from nematica.slow import inputs as SI
    flick = np.load(ROOT / "data/derived/barcode_flicker.npy") if not dry else np.sign(
        np.random.default_rng(0).standard_normal(480))
    import importlib.util
    spec = importlib.util.spec_from_file_location("slow_run", ROOT / "scripts/slow_run.py")
    SR = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(SR)
    # 60 Hz frames: steps per frame from the A1 timescale and the median visual-cortex timescale
    spf = SI.steps_per_frame(SR.a1_tau(inst), prof["bins_per_tau"]) * (1000 / 60) / (1000 / 30)
    As, st = BI.stacked_rnn(flick, R=R, n=480 if not dry else 60, spf=max(spf, 1.0), seed=inst,
                            burn=2000 if not dry else 100)
    return As, st, int(round(len(flick) * max(spf, 1.0)))


def systems(rows, dry=False):
    prof = vis_profile(rows)
    Rmax = max(r["levels"][k]["repeats"] for r in rows for k in LEVELS if r["levels"].get(k, {}).get("used"))
    yield "R0", "fixed", rows, lambda: gen_r0(prof, Rmax)
    for inst in range(3):
        ms = [r for r in rows if r["instance"] == inst]
        yield "STACK", f"i{inst}", ms, lambda inst=inst: gen_stack(inst, prof, Rmax, dry)
        if dry:
            continue
        for fam, model in NETWORKS:
            yield fam, f"{model.format(s=inst + 1).split('/')[-1]}-i{inst}", ms, \
                lambda inst=inst, model=model: gen_lm(model, inst, prof, Rmax)


def stage_ais(only=None, dry=False):
    rows = mice_rows(dry)
    name = "ais_dry.jsonl" if dry else "ais.jsonl"
    have = done(name, ("system", "run", "id", "level"))
    for fam, run, ms, gen in systems(rows, dry):
        if only and fam not in only:
            continue
        todo = [(m, k) for m in ms for k, lv in enumerate(LEVELS)
                if m["levels"].get(lv, {}).get("used") and (fam, run, m["id"], lv) not in have]
        if not todo:
            continue
        try:
            As, starts, length = gen()
        except Exception as e:  # noqa: BLE001
            append(name, {"system": fam, "run": run, "id": "*", "level": "*", "error": f"generation: {type(e).__name__}: {e}"})
            continue
        for m, k in todo:
            lv = LEVELS[k]
            try:
                row = {"system": fam, "run": run, "id": m["id"], "level": lv, "depth": k, "instance": m["instance"],
                       **record(As[k], starts, length, m["levels"][lv], seed=zlib.crc32(f"{run}{k}".encode()) % 2**31)}
            except Exception as e:  # noqa: BLE001
                row = {"system": fam, "run": run, "id": m["id"], "level": lv, "error": f"{type(e).__name__}: {e}"}
            append(name, row)
            print(fam, run, m["id"], lv, row.get("M1"), row.get("reached"), row.get("error"), flush=True)
        del As


# ------------------------------------------------------------------------------------------------ tests
def slope(points):
    """OLS slope of M1 on level index over the given {level index: M1} points (at least MIN_LEVELS)."""
    pts = [(k, v) for k, v in points.items() if v is not None and np.isfinite(v)]
    if len(pts) < MIN_LEVELS:
        return np.nan
    x, y = np.array(pts, float).T
    return float(np.polyfit(x, y, 1)[0])


def stage_tests(dry=False):
    import importlib.util

    from scipy.stats import spearmanr
    spec = importlib.util.spec_from_file_location("slow_run", ROOT / "scripts/slow_run.py")
    SR = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(SR)
    rows = mice_rows(dry)
    ais = [r for r in map(json.loads, (OUT / ("ais_dry.jsonl" if dry else "ais.jsonl")).read_text().splitlines())
           if "error" not in r]
    used = lambda m: {k: m["levels"][lv] for k, lv in enumerate(LEVELS) if m["levels"].get(lv, {}).get("used")}
    out = {"frozen": frozen(), "n_mice": len(rows)}
    ms = {m["id"]: slope({k: v["M1"] for k, v in used(m).items()}) for m in rows}
    msb = {m["id"]: slope({k: (v.get("behaviour_removed") or {}).get("M1") for k, v in used(m).items()}) for m in rows}
    odd = [slope({k: v["M1_odd"] for k, v in used(m).items()}) for m in rows]
    even = [slope({k: v["M1_even"] for k, v in used(m).items()}) for m in rows]
    ok = np.isfinite(odd) & np.isfinite(even)
    rho = float(spearmanr(np.array(odd)[ok], np.array(even)[ok])[0]) if ok.sum() > 4 else np.nan
    out["reliability"] = {"rho": rho, "reliable": bool(rho >= 0.5)}

    def sys_slopes(fam, levels_of, need_reach=True):
        res = {}
        for m in rows:
            pts = {}
            for r in ais:
                if r["system"] == fam and r["id"] == m["id"] and (r.get("reached") or not need_reach):
                    pts[LEVELS.index(r["level"])] = r["M1"]
            res[m["id"]] = slope({k: v for k, v in pts.items() if k in levels_of(m)}) \
                if len(pts) == len(levels_of(m)) else np.nan
        return res

    lv_of = lambda m: set(used(m))
    r0 = sys_slopes("R0", lv_of, need_reach=False)      # synthetic reference: reach not required (as calibration)
    for label, mouse in (("", ms), ("_behaviour_removed", msb)):
        d0 = np.array([mouse[i] - r0[i] for i in mouse if np.isfinite(mouse[i]) and np.isfinite(r0.get(i, np.nan))])
        h1 = {"n": len(d0), "median_d0": float(np.median(d0)) if len(d0) else np.nan,
              "p": SR._wilcoxon(d0 - 0.05, "greater") if len(d0) else np.nan}
        h1["holds"] = bool(len(d0) and h1["median_d0"] > 0.05 and h1["p"] < 0.05)
        out["H1" + label] = h1
        rul = SR._ruler(list(mouse.values())) if hasattr(SR, "_ruler") else float(
            1.4826 * np.nanmedian(np.abs(np.array(list(mouse.values())) - np.nanmedian(list(mouse.values())))))
        marg = max(0.5 * rul, 0.05)
        verdicts = {}
        for fam in ("P160", "P410", "M370", "STACK"):
            ss = sys_slopes(fam, lv_of)
            pairs = [(mouse[i] - ss[i], m["instance"]) for m in rows for i in [m["id"]]
                     if np.isfinite(mouse[i]) and np.isfinite(ss.get(i, np.nan))]
            missing = len(rows) - len(pairs)
            v = {"n_pairs": len(pairs), "missing": missing}
            if missing > 0.25 * len(rows) or len(pairs) < 6:
                v["verdict"] = "not testable"
            else:
                d = np.array([p[0] for p in pairs])
                inst = np.array([p[1] for p in pairs])
                rng = np.random.default_rng(2026)
                meds = [np.median(np.concatenate([d[inst == c] for c in rng.choice(3, 3)])) for _ in range(4000)]
                ci = [float(np.quantile(meds, 0.05)), float(np.quantile(meds, 0.95))]
                med = float(np.median(d))
                eq = -0.5 * rul <= ci[0] and ci[1] <= 0.5 * rul
                side = "greater" if med > 0 else "less"
                per = [SR._wilcoxon(d[inst == i], side) for i in range(3)]
                diff = abs(med) > marg and SR._wilcoxon(d, side) < 0.05 and all(p < 0.05 for p in per) and \
                    (ci[0] > 0 or ci[1] < 0)
                v.update({"median_d": med, "ci90": ci, "per_instance_p": per,
                          "verdict": "equivalent" if eq else ("differs, mouse rises more" if diff and med > 0 else
                                                              "differs, network rises more" if diff else "not decided")})
            verdicts[fam] = v
        counted = ("P160", "P410", "M370")
        n_eq = sum(verdicts[f]["verdict"] == "equivalent" for f in counted)
        n_diff = sum(verdicts[f]["verdict"].startswith("differs") for f in counted)
        out["H2" + label] = {"ruler": rul, "margin": marg, "systems": verdicts,
                             "holds": bool(n_eq >= 2 and n_diff == 0 and out["reliability"]["reliable"]),
                             "refuted": bool(n_diff >= 2)}
    name = "tests_dry.json" if dry else "tests.json"
    (OUT / name).write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({"H1": out["H1"]["holds"], "H2": out["H2"]["holds"], "H2_refuted": out["H2"]["refuted"],
                      "reliability": out["reliability"]}), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["mice", "ais", "tests"])
    p.add_argument("--dry", action="store_true")
    p.add_argument("--only", nargs="*")
    a = p.parse_args()
    if a.stage in ("mice", "ais") and not a.dry and not frozen():
        sys.exit("BARCODE.md is not frozen: no Barcoding activity is measured before the registration binds.")
    {"mice": lambda: stage_mice(a.dry), "ais": lambda: stage_ais(a.only, a.dry), "tests": lambda: stage_tests(a.dry)}[a.stage]()


if __name__ == "__main__":
    main()
