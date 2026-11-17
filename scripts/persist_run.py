"""Study 3 pipeline (docs/PERSIST.md). Stages, each resumable, results appended row by row to JSONL files in
docs/figures/persist/ (summary numbers only; Allen data stays local):

  python scripts/persist_run.py mice      # NM3 mice: instrument numbers and measures (primary, held out)
  python scripts/persist_run.py other     # NM1 outside visual cortex (secondary, held out)
  python scripts/persist_run.py ais       # every system at every NM3 mouse's instrument
  python scripts/persist_run.py tests     # claims 1 to 5

`mice`, `other` and `ais` refuse to run on real data until PERSIST.md is frozen ("Frozen at commit <hash>").
`--dry` runs a stage on synthetic stand-ins (nothing real is read), for checking the code path.
Shared code from Study 2 is imported from scripts/slow_run.py and nematica/slow, unchanged.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.map import instrument as INS  # noqa: E402
from nematica.persist import data as PD, inputs as PI, measures as PM  # noqa: E402
from nematica.slow import data as D, inputs as I, measures as M, stream as ST  # noqa: E402

_spec = importlib.util.spec_from_file_location("slow_run", ROOT / "scripts/slow_run.py")
SR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SR)

OUT = ROOT / "docs/figures/persist"
CLIP_BINS = 6000                 # NM3: 120 s in 20 ms bins (registered clip length for the networks)
MAX_BINS = 4 * CLIP_BINS         # corrections never make a recording longer than this (PERSIST_LOG, bin cap)
W = 8                            # windows per repeat
K0 = 2
MIN_REPEATS = 8
MIN_UNITS = 30
MAX_UNITS = 480
FIRST_REPEATS = 8                # the spike minimum is counted over the first 8 repeats (the fewest valid)
MIN_SPIKES = int(round(200 * FIRST_REPEATS * 120.0 / (17 * 30.0)))   # Study 2's 200 per 510 s, same rate
N_GROUPS = 4
K_GAIN = 0.25                    # movie gain of the K controls (chaos survives it: PERSIST_LOG, chaos probe)
CONTROLS = {"K1": {"g": 3.0, "noise": 0.0}, "K2": {"g": 0.8, "noise": 0.0}, "K3": {"g": 1.5, "noise": 0.1}}
LMS = (("A6", "EleutherAI/pythia-14m-seed{s}"), ("A6", "EleutherAI/pythia-160m-seed{s}"),
       ("A6", "EleutherAI/pythia-410m-seed{s}"), ("A6", "EleutherAI/pythia-1b"),
       ("A7", "state-spaces/mamba-130m-hf"), ("A7", "state-spaces/mamba-370m-hf"))
NOISE_FILE = OUT / "noise_levels.json"   # N3 and N6 noise, set before freezing (PERSIST.md section 8)


def frozen():
    m = re.search(r"Frozen at commit ([0-9a-f]{7,40})", (ROOT / "docs/PERSIST.md").read_text())
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


def windowed(Y):
    return PM.windowed_from_counts(Y, W=W, k0=K0)


def mouse_measures(Y):
    r = M.lag_measures(Y, k0=K0)
    return {**{k: r[k] for k in SR.PRIMARY}, "windows": windowed(Y),
            "split": {"odd": windowed(Y[0::2]), "even": windowed(Y[1::2])}}


# ------------------------------------------------------------------------------------------------ mice
def nm3_sessions():
    feas = {r["session"]: r for r in json.loads((OUT / "feasibility.json").read_text())}
    for rank, (ds, a) in enumerate(D.sessions()):
        sess = a["path"].split("/")[0]
        if feas.get(sess, {}).get("nm3_complete"):
            yield rank, ds, a


def _fake_counts(uid, T=4000, R=10):
    from nematica.persist import synthetic as PS
    rng = np.random.default_rng(zlib.crc32(uid.encode()))
    A, st = PS.system(rng, "generated", T, R=R, N=200)
    prof = {"bins_per_tau": 40.0, "count_per_bin": 0.09, "noise": 0.94, "rate_log_sd": 1.1}
    out = ST.Recorder(A, st, T, {"hold": 1, "bin_steps": 0.67, "mean_count": 0.06, "gain": 1.0,
                                 "rate_log_sd": 1.1}, seed=1)
    return np.clip(out.counts(np.arange(len(out.cols))), 0, 255).astype(np.uint8), prof


def stage_mice(dry=False):
    name = "mice_dry.jsonl" if dry else "mice.jsonl"
    have = {k[0] for k in done(name, ("id",))}
    for rank, ds, a in nm3_sessions():
        uid = a["path"].split("/")[0]
        if uid in have:
            continue
        try:
            if dry:
                Y, _ = _fake_counts(uid)
                sel = np.ones(Y.shape[2], bool)
            else:
                z = PD.nm3_cache(a)
                z1 = D.movie_cache(a)
                assert np.array_equal(z["units"], z1["units"]), "NM3 and NM1 caches hold different units"
                Y = D.movie_counts(z)
                area, qc = D.unit_meta(a, z["units"])
                sel = D.visual_cortex(area) & qc
            R, nb, N = Y.shape
            X = Y.reshape(R * nb, N).astype(np.float32)
            keep = sel & SR.keep_units(X, per_repeat_bins=None, min_spikes=0) & \
                (X[: FIRST_REPEATS * nb].sum(0) >= MIN_SPIKES)
            if R < MIN_REPEATS:
                raise RuntimeError(f"only {R} valid repeats")
            if keep.sum() < MIN_UNITS:
                raise RuntimeError(f"only {int(keep.sum())} included visual-cortex units")
            if keep.sum() > MAX_UNITS:
                ki = np.sort(np.random.default_rng(zlib.crc32(uid.encode())).choice(np.flatnonzero(keep),
                                                                                   MAX_UNITS, replace=False))
                keep = np.zeros_like(keep)
                keep[ki] = True
            seg = [r * nb for r in range(1, R)]
            prof = INS.instrument_numbers({"activity": X[:, keep], "dt": INS.SPIKE_BIN_S, "segments": seg},
                                          "spikes")
            del X
            row = {"id": uid, "rank": rank, "dandiset": ds, "repeats": R, "bins": nb, "units": int(keep.sum()),
                   "profile": {k: prof.get(k) for k in SR.KEYS}, **mouse_measures(Y[:, :, keep]), "dry": dry,
                   "frozen": frozen()}
            if not dry:
                try:
                    Bh = PD.behaviour_nm3(a, z["starts"], nb)
                    Yr, r2 = D.regress_out(Y[:, :, keep], Bh)
                    row["behaviour_removed"] = {"windows": windowed(Yr), "median_r2": r2}
                except Exception as e:  # noqa: BLE001
                    row["behaviour_error"] = f"{type(e).__name__}: {e}"
        except Exception as e:  # noqa: BLE001
            row = {"id": uid, "error": f"{type(e).__name__}: {e}"}
        append(name, row)
        print(uid, {k: row.get(k) for k in ("repeats", "units", "error")}, flush=True)
        if dry and len(done(name, ("id",))) >= 6:
            break


REGIONS = {"thalamus": ("LGd", "LGv", "LP", "PO", "Eth", "TH", "POL", "SGN", "MGv", "MGd", "MGm", "LD", "VPM",
                        "VPL", "IntG", "PP", "PIL", "RT"),
           "hippocampus": ("CA1", "CA2", "CA3", "DG", "SUB", "ProS", "PoST", "PRE", "POST", "HPF")}


def region_group(area):
    if area.startswith("VIS"):
        return "visual_cortex"
    for g, names in REGIONS.items():
        if any(area == n or area.startswith(n + "-") for n in names):
            return g
    return "other" if area else "unknown"


def stage_other():
    """Secondary (PERSIST.md section 3): NM1 in units outside visual cortex, per region group."""
    name = "other.jsonl"
    have = {k[0] for k in done(name, ("id",))}
    for rank, (ds, a) in enumerate(D.sessions()):
        uid = a["path"].split("/")[0]
        if uid in have:
            continue
        rows = []
        try:
            z = D.movie_cache(a)
            Y = D.movie_counts(z)
            area, qc = D.unit_meta(a, z["units"])
            R, nb, N = Y.shape
            X = Y.reshape(R * nb, N).astype(np.float32)
            base = qc & SR.keep_units(X, nb)
            groups = np.array([region_group(str(x)) for x in area])
            for g in ("thalamus", "hippocampus", "other"):
                keep = base & (groups == g)
                if keep.sum() < MIN_UNITS:
                    continue
                if keep.sum() > MAX_UNITS:
                    ki = np.sort(np.random.default_rng(zlib.crc32((uid + g).encode())).choice(
                        np.flatnonzero(keep), MAX_UNITS, replace=False))
                    keep = np.zeros_like(keep)
                    keep[ki] = True
                r = M.lag_measures(Y[:, :, keep], k0=K0)
                rows.append({"id": uid, "region": g, "units": int(keep.sum()), "repeats": R,
                             **{k: r[k] for k in SR.PRIMARY}, "windows": windowed(Y[:, :, keep])})
            row = {"id": uid, "groups": rows}
        except Exception as e:  # noqa: BLE001
            row = {"id": uid, "error": f"{type(e).__name__}: {e}"}
        append(name, row)
        print(uid, [(x["region"], x["units"]) for x in row.get("groups", [])], row.get("error"), flush=True)


# ------------------------------------------------------------------------------------------------ AIs
def mice_table(dry=False):
    rows = [r for r in map(json.loads, (OUT / ("mice_dry.jsonl" if dry else "mice.jsonl")).read_text()
                           .splitlines()) if "error" not in r]
    rows = [r for r in rows if r["profile"].get("bins_per_tau") is not None
            and np.isfinite(r["profile"]["bins_per_tau"])]
    bpt = np.array([r["profile"]["bins_per_tau"] for r in rows])
    edges = np.quantile(bpt, np.linspace(0, 1, N_GROUPS + 1))
    for i, r in enumerate(rows):
        r["instance"] = r["rank"] % 3
        r["group"] = int(np.clip(np.searchsorted(edges, r["profile"]["bins_per_tau"], side="right") - 1, 0,
                                 N_GROUPS - 1))
    med = {g: float(np.median([r["profile"]["bins_per_tau"] for r in rows if r["group"] == g]))
           for g in range(N_GROUPS) if any(r["group"] == g for r in rows)}
    return rows, med


def record(A, starts, length, r, rng_seed):
    """One system at one mouse: Study 2's streamed recording (`record_stream`) at the mouse's NM3 instrument,
    with the windowed measures on the same recording and analysed units, and the bin cap."""
    R = r["repeats"]
    st = starts[:R]
    sil = M.silent_units(A)
    if sil.any():
        A = A[:, ~sil]
    out = ST.record_stream(A, st, length, r["profile"], nb_mouse=int(r["bins"]), R_mouse=R,
                           n_units_mouse=int(r["units"]), seed=rng_seed, halves=False,
                           extra=lambda rec, inc: PM.windowed_stream(rec, inc, W=W, k0=K0), max_bins=MAX_BINS)
    if "error" in out:
        raise RuntimeError(out["error"])
    out["windows"] = out.pop("extra")
    return out


def clip_units_stream(make, prof, guess, unit_steps=1):
    """Pilot (fixes Study 2's S9 deviation): 3 repeats of a clip of `guess` units recorded with the same
    streamed recorder as the real recordings; the clip is scaled to record as about CLIP_BINS bins."""
    A, st = make(guess, 3)
    out = ST.record_stream(A, st, guess * unit_steps, prof, nb_mouse=CLIP_BINS, R_mouse=3, n_units_mouse=100,
                           seed=0, halves=False, max_bins=MAX_BINS)
    nb = out.get("recorded_bins") or CLIP_BINS
    return max(int(round(guess * CLIP_BINS / nb)), 5)


def noise_level(key):
    lv = json.loads(NOISE_FILE.read_text()) if NOISE_FILE.exists() else {}
    if key not in lv:
        raise RuntimeError(f"noise level for {key} not set (PERSIST.md section 8)")
    return float(lv[key])


def gen_a2(inst, prof, R):
    net = I.load_task_rnn(SR.NETS / f"a2_inst{inst}.pt")
    n = clip_units_stream(lambda c, r: I.task_rnn_repeats(net, R=r, clip_trials=c, seed=inst), prof, 20,
                          unit_steps=60)
    return (*I.task_rnn_repeats(net, R=R, clip_trials=n, seed=inst), n * 60)


def gen_char(kind, inst, prof, R, noise_sd=0.0):
    from nematica.map import zoo
    model = I.load_char_net(SR.NETS / f"{kind}_seed{inst}.pt")
    data, _ = zoo.chars()
    split = len(data) - 200_000
    mk = lambda c, r: PI.char_repeats_noisy(model, data, split, clip_len=c, R=r, seed=inst, noise_sd=noise_sd,
                                            noise_seed=inst)
    n = clip_units_stream(mk, prof, 80)             # Study 2: about 80 bins per character at 1,500 bins
    return (*mk(n, R), n)


def gen_lm(model, inst, prof, R, noise_sd=0.0):
    import shutil
    name = model.format(s=inst + 1)
    tok = np.load(ROOT / "data/external/books/tokens.npy")
    at = len(tok) * (inst + 2) // 6
    if "mamba" in name:
        mk = lambda c, r: I.lm_repeats(name, *I.text_clip_and_contexts(tok, c, 256, r, seed=inst, clip_at=at))[:2]
    else:
        mk = lambda c, r: PI.lm_repeats_noisy(name, *I.text_clip_and_contexts(tok, c, 256, r, seed=inst,
                                                                              clip_at=at),
                                              noise_sd=noise_sd, noise_seed=inst)[:2]
    if shutil.disk_usage(ROOT).free / 1e9 < 3.0:
        raise RuntimeError("under 3 GB free; a language model needs up to about 3 GB")
    n = clip_units_stream(mk, prof, 80)             # about 80 bins per token (review S-R4)
    return (*mk(n, R), n)


@__import__("functools").lru_cache(maxsize=12)
def _k_tau(g, noise, inst):
    from nematica.map import measures as MM, zoo
    return float(MM.tau_med(zoo.random_rnn(n=480, steps=8000, seed=inst, g=g, noise=noise)[0]))


def k_tau(cfg, inst):
    """Undriven native timescale of a K control (as Study 2's a1_tau). A noise-free stable network decays to
    rest and has none, so it plays the movie at the K3 (Study 2 A1) timescale of the same instance."""
    if cfg["g"] < 1.0:
        return SR.a1_tau(inst)
    return _k_tau(cfg["g"], cfg["noise"], inst)


def gen_k(fam, inst, bpt, R, feat, other, mult=1.0):
    cfg = CONTROLS[fam]
    spf = I.steps_per_frame(k_tau(cfg, inst), bpt) * mult
    A, st, meta = PI.driven_rnn(feat, other, R=R, g=cfg["g"], noise=cfg["noise"], gain=K_GAIN, spf=spf, seed=inst,
                                keep_every=SR.keep_for(spf))
    return A, st, meta["clip_kept"]


def families(rows, med, dry=False):
    Rmax = lambda ms: max(m["repeats"] for m in ms)
    prof = SR.group_profile(rows)
    feat = PD.nm3_features() if not dry else np.random.default_rng(0).standard_normal((3600, 64)).astype(np.float32)
    other = I.movie_features() if not dry else np.random.default_rng(1).standard_normal((900, 64)).astype(np.float32)
    for inst in range(3):
        for g in sorted(med):
            ms = [r for r in rows if r["instance"] == inst and r["group"] == g]
            if not ms:
                continue
            for fam in CONTROLS:
                yield (fam, f"i{inst}-g{g}", ms, lambda ms=ms, g=g, inst=inst, fam=fam:
                       gen_k(fam, inst, med[g], Rmax(ms), feat, other))
            for mult in (0.5, 2.0):                   # playback sensitivity on K3
                yield ("K3-play", f"i{inst}-g{g}-x{mult}", ms, lambda ms=ms, g=g, inst=inst, mult=mult:
                       gen_k("K3", inst, med[g], Rmax(ms), feat, other, mult=mult))
    if dry:
        return
    for inst in range(3):
        ms = [r for r in rows if r["instance"] == inst]
        yield ("A2", f"i{inst}", ms, lambda ms=ms, inst=inst: gen_a2(inst, prof, Rmax(ms)))
        yield ("A3", f"i{inst}", ms, lambda ms=ms, inst=inst: gen_char("gru", inst, prof, Rmax(ms)))
        yield ("A5", f"i{inst}", ms, lambda ms=ms, inst=inst: gen_char("cfc", inst, prof, Rmax(ms)))
        yield ("N3", f"i{inst}", ms, lambda ms=ms, inst=inst: gen_char("gru", inst, prof, Rmax(ms),
                                                                       noise_sd=noise_level("N3")))
    for fam, model in LMS:
        for inst in range(3):
            ms = [r for r in rows if r["instance"] == inst]
            label = f"{model.format(s=inst + 1).split('/')[-1]}-i{inst}"
            yield (fam, label, ms, lambda ms=ms, inst=inst, model=model: gen_lm(model, inst, prof, Rmax(ms)))
            if "pythia-160m" in model:
                yield ("N6", label, ms, lambda ms=ms, inst=inst, model=model:
                       gen_lm(model, inst, prof, Rmax(ms), noise_sd=noise_level("N6")))


def stage_ais(only=None, dry=False):
    rows, med = mice_table(dry)
    name = "ais_dry.jsonl" if dry else "ais.jsonl"
    have = done(name, ("family", "run", "id"))
    for fam, run, ms, gen in families(rows, med, dry):
        if only and fam not in only:
            continue
        todo = [m for m in ms if (fam, run, m["id"]) not in have]
        if not todo:
            continue
        try:
            A, starts, length = gen()
        except Exception as e:  # noqa: BLE001
            append(name, {"family": fam, "run": run, "id": "*", "error": f"generation: {type(e).__name__}: {e}"})
            continue
        for m in todo:
            try:
                row = {"family": fam, "run": run, "id": m["id"], "instance": m["instance"], "group": m["group"],
                       **record(A, starts, length, m, rng_seed=zlib.crc32(run.encode()) % 2**31)}
            except Exception as e:  # noqa: BLE001
                row = {"family": fam, "run": run, "id": m["id"], "error": f"{type(e).__name__}: {e}"}
            append(name, row)
            w = row.get("windows") or {}
            print(fam, run, m["id"], row.get("reached"), w.get("c_time"), w.get("b_drive"), row.get("error"),
                  flush=True)
        del A


# ------------------------------------------------------------------------------------------------ tests
C_CLIP = 6.0


def value(row, meas, beh=False):
    w = (row.get("behaviour_removed") or {}).get("windows") if beh else row.get("windows")
    if not w:
        return np.nan
    if meas == "c":
        f = PM.drive_time_fit(np.array(w["int_amp_w"]), np.array(w["same_amp_w"]) - np.array(w["int_amp_w"]))
        return float(np.clip(f["c"], -C_CLIP, C_CLIP)) if np.isfinite(f["c"]) else np.nan
    f = PM.drive_time_fit(np.array(w["int_amp_w"]), np.array(w["same_amp_w"]) - np.array(w["int_amp_w"]))
    return float(f["b"]) if np.isfinite(f["b"]) else np.nan


def ruler(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


def family_test(mice, ai_rows, meas, margin, band, beh=False, n_boot=4000, seed=2026):
    """Paired d = mouse minus system (reached recordings only), with missing pairs counted; one-sided Wilcoxon
    overall and within each instance; cluster bootstrap over generator cells (instance, group)."""
    by = {r["id"]: r for r in ai_rows}
    d, cells, inst = [], [], []
    missing = 0
    for m in mice.values():
        r = by.get(m["id"])
        if r is None or not r.get("reached") or "error" in r:
            missing += 1
            continue
        x = value(m, meas, beh) - value(r, meas)
        if not np.isfinite(x):
            missing += 1
            continue
        d.append(x)
        cells.append(f"{r['instance']}|{r.get('group')}")
        inst.append(r["instance"])
    out = {"n_pairs": len(d), "missing": missing}
    if missing > 0.25 * len(mice):
        return {**out, "verdict": "not testable"}
    if len(d) < 6:
        return {**out, "verdict": "too few pairs"}
    d, cells, inst = np.array(d), np.array(cells), np.array(inst)
    p_gap, p_rev = SR._wilcoxon(d, "greater"), SR._wilcoxon(d, "less")
    per = {int(i): (SR._wilcoxon(d[inst == i], "greater"), SR._wilcoxon(d[inst == i], "less")) for i in range(3)}
    rng = np.random.default_rng(seed)
    uc = np.unique(cells)
    meds = []
    for _ in range(n_boot):
        pick = rng.choice(uc, len(uc), replace=True)
        meds.append(np.median(np.concatenate([d[cells == c] for c in pick])))
    ci = [float(np.quantile(meds, 0.05)), float(np.quantile(meds, 0.95))]
    med = float(np.median(d))
    conf = p_gap < 0.05 and all(per[i][0] < 0.05 for i in range(3)) and med > margin and ci[0] > 0
    ref = p_rev < 0.05 and all(per[i][1] < 0.05 for i in range(3)) and med < -margin and ci[1] < 0
    return {**out, "median_d": med, "ci90": ci, "p_gap": p_gap, "p_reverse": p_rev, "per_instance_p": per,
            "n_cells": len(uc), "equivalent": bool(-band <= ci[0] and ci[1] <= band),
            "verdict": "confirmed" if conf else "refuted" if ref else "not decided"}


def stage_tests(dry=False):
    mice = {r["id"]: r for r in map(json.loads, (OUT / ("mice_dry.jsonl" if dry else "mice.jsonl")).read_text()
                                    .splitlines()) if "error" not in r}
    rows, _ = mice_table(dry)
    mice = {r["id"]: {**mice[r["id"]], **r} for r in rows}
    ais = [r for r in map(json.loads, (OUT / ("ais_dry.jsonl" if dry else "ais.jsonl")).read_text().splitlines())
           if "error" not in r and r["id"] in mice]
    cal = json.loads((OUT / "calibration.json").read_text())
    out = {"frozen": frozen(), "n_mice": len(mice)}
    rul = {m: ruler([value(x, m) for x in mice.values()]) for m in ("c", "b")}
    bias = {"c": cal.get("bias_bound_c", 0.0), "b": cal.get("bias_bound_b", 0.0)}
    marg = {m: max(0.5 * rul[m], bias[m]) for m in rul}
    out.update({"rulers": rul, "bias_bounds": bias, "margins": marg})
    band = {m: 0.5 * rul[m] for m in rul}               # equivalence: the 90% interval within +-0.5 ruler units

    def by_run(fam):
        runs = {}
        for r in ais:
            if r["family"] == fam:
                runs.setdefault(r["run"].split("-i")[0] if fam in ("A6", "A7", "N6") else "all", []).append(r)
        return runs

    # claim 1: non-inferiority of the mice's c
    c = np.array([value(m, "c") for m in mice.values()])
    c = c[np.isfinite(c)]
    rng = np.random.default_rng(2026)
    boot = [np.median(rng.choice(c, len(c))) for _ in range(4000)]
    out["claim1"] = {"median_c": float(np.median(c)), "ci90": [float(np.quantile(boot, 0.05)),
                                                             float(np.quantile(boot, 0.95))],
                     "p": SR._wilcoxon(c + marg["c"], "greater")}
    out["claim1"]["holds"] = bool(out["claim1"]["ci90"][0] > -marg["c"] and out["claim1"]["p"] < 0.05)
    # claim 2: carriers
    res = {}
    for fam in ("A2", "A3", "A5", "A6", "A7"):
        res[fam] = {k: family_test(mice, v, "c", marg["c"], band["c"]) for k, v in by_run(fam).items()}
    def fam_ok(fam):
        v = [x["verdict"] for x in res[fam].values()]
        need = 3 if fam == "A6" else len(v)
        return sum(x == "confirmed" for x in v) >= need, any(x == "refuted" for x in v)
    ok = {f: fam_ok(f) for f in res}
    out["claim2"] = {"families": res, "holds": bool(sum(o[0] for o in ok.values()) >= 4 and
                                                    not any(o[1] for o in ok.values()))}
    # claim 3: generators close the gap
    eq = {}
    for fam, base, size in (("N3", "A3", "all"), ("N6", "A6", "pythia-160m")):
        t = {k: family_test(mice, v, "c", marg["c"], band["c"]) for k, v in by_run(fam).items()}
        eq[fam] = {"test": t, "equivalent": all(x.get("equivalent") for x in t.values()),
                   "noise_free_confirmed": res[base].get(size, {}).get("verdict") == "confirmed"}
    out["claim3"] = {**eq, "holds": all(v["equivalent"] and v["noise_free_confirmed"] for v in eq.values())}
    # claim 4: controls
    kt = {fam: family_test(mice, [r for r in ais if r["family"] == fam], "c", marg["c"], band["c"]) for fam in CONTROLS}
    out["claim4"] = {"tests": kt, "as_expected": kt["K2"]["verdict"] == "confirmed" and
                     kt["K1"]["verdict"] != "confirmed" and kt["K3"]["verdict"] != "confirmed"}
    # claim 5: kind of generator
    gt = {fam: family_test(mice, [r for r in ais if r["family"] == fam], "b", marg["b"], band["b"]) for fam in ("K1", "K3", "N3", "N6")}
    out["claim5"] = {"tests": gt, "holds": bool(sum(v["verdict"] == "confirmed" for v in gt.values()) >= 3 and
                                                 not any(v["verdict"] == "refuted" for v in gt.values()))}
    # behaviour removed (claims 1, 2, 5)
    out["behaviour_removed"] = {
        "claim2": {fam: {k: family_test(mice, v, "c", marg["c"], band["c"], beh=True)["verdict"] for k, v in by_run(fam).items()}
                   for fam in res},
        "claim5": {fam: family_test(mice, [r for r in ais if r["family"] == fam], "b", marg["b"], band["b"], beh=True)["verdict"]
                   for fam in gt}}
    # reliability (odd and even repeats)
    from scipy.stats import spearmanr
    rel = {}
    for meas in ("c", "b"):
        a = [value({"windows": m["split"]["odd"]}, meas) for m in mice.values()]
        b_ = [value({"windows": m["split"]["even"]}, meas) for m in mice.values()]
        ok_ = np.isfinite(a) & np.isfinite(b_)
        rel[meas] = float(spearmanr(np.array(a)[ok_], np.array(b_)[ok_])[0]) if ok_.sum() > 5 else np.nan
    out["reliability"] = rel
    # playback sensitivity (K3)
    pb = {}
    k3 = {r["id"]: r for r in ais if r["family"] == "K3"}
    for mult in ("x0.5", "x2.0"):
        sh = [value(r, "c") - value(k3[r["id"]], "c") for r in ais if r["family"] == "K3-play"
              and r["run"].endswith(mult) and r["id"] in k3 and r.get("reached") and k3[r["id"]].get("reached")]
        pb[mult] = float(np.nanmedian(sh) / rul["c"]) if sh else np.nan
    out["playback_shift_ruler"] = pb
    name = "tests_dry.json" if dry else "tests.json"
    (OUT / name).write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k].get("holds", out[k].get("as_expected")) for k in
                      ("claim1", "claim2", "claim3", "claim4", "claim5")}), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["mice", "other", "ais", "tests"])
    p.add_argument("--dry", action="store_true")
    p.add_argument("--only", nargs="*")
    a = p.parse_args()
    if a.stage in ("mice", "other", "ais") and not a.dry and not frozen():
        sys.exit("PERSIST.md is not frozen: no held-out activity is measured before the registration binds.")
    if a.stage == "mice":
        stage_mice(dry=a.dry)
    elif a.stage == "other":
        stage_other()
    elif a.stage == "ais":
        stage_ais(only=a.only, dry=a.dry)
    else:
        stage_tests(dry=a.dry)


if __name__ == "__main__":
    main()
