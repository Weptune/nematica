"""Study 2 pipeline (docs/SLOW.md). Stages, each resumable (results appended row by row to JSONL files in
docs/figures/slow_runs/, nothing third-party):

  python scripts/slow_run.py mice     # mouse instrument numbers and measures (Allen Neuropixels, movie one)
  python scripts/slow_run.py ais      # every AI family at every mouse's instrument
  python scripts/slow_run.py tests    # H1 to H3 verdicts

The `mice` and `ais` stages refuse to run until SLOW.md is frozen (a line "Frozen at commit <hash>"), so
no real activity is measured before the registration binds. `--dry` runs a stage on synthetic stand-ins
instead (for testing the code path; nothing real is read).
"""
from __future__ import annotations

import argparse
import functools
import itertools
import json
import re
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.map import instrument as INS  # noqa: E402
from nematica.slow import data as D, inputs as I, measures as M, record as Rc  # noqa: E402

OUT = ROOT / "docs/figures/slow_runs"
# per arm: file prefix, recording type, clip length in recorded samples (SLOW.md sections 4 and 5)
ARMS = {"npx": {"prefix": "", "rtype": "spikes", "clip": 1500},
        "2p": {"prefix": "2p_", "rtype": "calcium", "clip": 900}}
CFG = dict(ARMS["npx"])
GAINS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0)        # SLOW.md section 7
N_GROUPS = 4                                          # playback-speed groups (quartiles of bins per timescale)
KEYS = ("bins_per_tau", "count_per_bin", "noise", "rate_log_sd")
MEASURES = ("M1_lag1", "no_lag1_cov", "M2_lag1", "M2_ceiling", "M1", "M2_int", "M2", "ti_lag1", "tl_lag1", "noise_share")


def frozen():
    m = re.search(r"Frozen at commit ([0-9a-f]{7,40})", (ROOT / "docs/SLOW.md").read_text())
    return m.group(1) if m else None


def append(name, row):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "a") as f:
        f.write(json.dumps(row) + "\n")


def done(name, key):
    f = OUT / name
    if not f.exists():
        return set()
    return {tuple(r[k] for k in key) for r in map(json.loads, f.read_text().splitlines()) if "error" not in r}


def measures(Y):
    r = M.internal_measures(Y)
    return {k: r.get(k) for k in MEASURES}


# ------------------------------------------------------------------------------------------------ mice
def keep_units(X):
    """The map study's inclusion rule for spikes (nematica.map.instrument.include_units), as a mask."""
    n = X.sum(0)
    return (X.std(0) > 1e-9) & (n >= INS.MIN_SPIKES) & (n / (len(X) * INS.SPIKE_BIN_S) >= INS.MIN_RATE_HZ)


def stage_mice(dry=False):
    name = "mice_dry.jsonl" if dry else "mice.jsonl"
    have = {k[0] for k in done(name, ("id",))}
    for ds, a in D.sessions():
        uid = a["path"].split("/")[0]
        if uid in have:
            continue
        try:
            Y = D.movie_counts(D.movie_cache(a)) if not dry else _fake_mouse(uid)
            R, nb, N = Y.shape
            X = Y.reshape(R * nb, N).astype(np.float32)
            keep = keep_units(X)
            seg = [r * nb for r in range(1, R)]
            prof = INS.instrument_numbers({"activity": X[:, keep], "dt": INS.SPIKE_BIN_S, "segments": seg},
                                          "spikes")
            del X
            row = {"id": uid, "dandiset": ds, "repeats": R, "bins": nb, "units": int(keep.sum()), "units_cached": N,
                   "profile": {k: prof.get(k) for k in KEYS}, **measures(Y[:, :, keep]),
                   "extras": M.unit_internal_shares(Y[:, :, keep]), "dry": dry, "frozen": frozen()}
            if ds == "000022" and not dry:                # validity check: the shuffled movie (SLOW.md 7)
                Ys = D.movie_counts(D.movie_cache(a, shuffled=True))
                row["shuffled"] = {**measures(Ys[:, :, keep]), "repeats": int(Ys.shape[0])}
        except Exception as e:  # noqa: BLE001
            row = {"id": uid, "error": f"{type(e).__name__}: {e}"}
        append(name, row)
        print(uid, {k: row.get(k) for k in ("repeats", "units", "error")}, flush=True)
        if dry and len(done(name, ("id",))) >= 6:
            break


def _fake_mouse(uid):
    from nematica.slow import synthetic as S
    rng = np.random.default_rng(zlib.crc32(uid.encode()))
    A, st = S.continuous(rng, R=20, T=3000, N=300, share=0.5, tau_locked=6, tau_internal=24)
    prof = {"bins_per_tau": 2.6, "count_per_bin": 0.066, "noise": 0.9, "rate_log_sd": 1.2}
    Y, _ = Rc.record_repeats(A, st, 3000, prof, seed=1)
    return np.clip(np.round(Y), 0, 255).astype(np.uint8)


def stage_mice_2p():
    """Replication mice: dF/F on the 10 movie repeats; the map study's calcium instrument numbers (GCaMP6f's
    registered half-decay; repeats as segments); the measures."""
    name = "2p_mice.jsonl"
    have = {k[0] for k in done(name, ("id",))}
    for exp in D.twop_experiments():
        uid = str(exp["id"])
        if uid in have:
            continue
        try:
            Y = np.asarray(D.twop_movie(exp), np.float32)
            R, nb, N = Y.shape
            X = Y.reshape(R * nb, N)
            seg = [r * nb for r in range(1, R)]
            ok = X.std(0) > 1e-9
            prof = INS.instrument_numbers({"activity": X[:, ok], "dt": 1 / 30, "segments": seg,
                                           "indicator": "GCaMP6f"}, "calcium")
            row = {"id": uid, "specimen": exp["specimen_id"], "area": exp["targeted_structure"]["acronym"],
                   "repeats": R, "bins": nb, "units": int(ok.sum()),
                   "profile": {k: prof.get(k) for k in INS.KEYS["calcium"]}, **measures(Y[:, :, ok]),
                   "extras": M.unit_internal_shares(Y[:, :, ok]), "frozen": frozen()}
        except Exception as e:  # noqa: BLE001
            row = {"id": uid, "error": f"{type(e).__name__}: {e}"}
        append(name, row)
        print(uid, {k: row.get(k) for k in ("units", "error")}, flush=True)


# ------------------------------------------------------------------------------------------------ AIs
def mice_table(dry=False):
    rows = [r for r in map(json.loads, (OUT / (CFG["prefix"] + ("mice_dry.jsonl" if dry else "mice.jsonl")))
                           .read_text().splitlines()) if "error" not in r]
    if CFG["rtype"] == "calcium":
        # replication: one playback group at the Neuropixels mice's median timescale (calcium timescales are
        # set by the indicator, not the neurons; SLOW.md section 4)
        npx = [r for r in map(json.loads, (OUT / "mice.jsonl").read_text().splitlines()) if "error" not in r]
        for i, r in enumerate(rows):
            r["instance"], r["group"], r["rtype"] = i % 3, 0, "calcium"
        return rows, {0: float(np.median([r["profile"]["bins_per_tau"] for r in npx]))}
    bpt = np.array([r["profile"]["bins_per_tau"] for r in rows])
    edges = np.quantile(bpt, np.linspace(0, 1, N_GROUPS + 1))
    for i, r in enumerate(rows):                       # rank in the map study's (session) order
        r["instance"] = i % 3
        r["group"] = int(np.clip(np.searchsorted(edges, r["profile"]["bins_per_tau"], side="right") - 1, 0,
                                 N_GROUPS - 1))
    med = {g: float(np.median([r["profile"]["bins_per_tau"] for r in rows if r["group"] == g]))
           for g in range(N_GROUPS)}
    return rows, med


def record_for_mouse(A, starts, length, r, rng_seed):
    """One AI run at one mouse: the mouse's number of repeats, silent units excluded, its spike instrument."""
    R = r["repeats"]
    st = starts[:R]
    A = A[:, ~M.silent_units(A)]
    rtype = r.get("rtype", "spikes")
    Y, k = Rc.record_repeats(A, st, length, r["profile"], rtype=rtype, seed=rng_seed)
    Yn = np.stack([np.asarray(A[s:s + length]) for s in st])
    return {**measures(Y), "recorded_bins": int(Y.shape[1]), "bin_steps": float(Rc.recording.per_sample(k, rtype)),
            "extras": M.unit_internal_shares(Yn)}


def lif_for_mouse(A, starts, length, r, rng_seed):
    """A4: recorded like a mouse (SLOW.md section 5): 20 ms bins of its own spikes, thinned to the mouse's
    spikes per bin. In the replication it goes through the calcium model like every other AI."""
    if r.get("rtype") == "calcium":
        return record_for_mouse(A, starts, length, r, rng_seed)
    R = r["repeats"]
    nb = length // 4                                   # 4 native 5 ms steps per 20 ms bin
    Y = np.stack([A[s:s + nb * 4].reshape(nb, 4, -1).sum(1) for s in starts[:R]])
    p = min(1.0, r["profile"]["count_per_bin"] / max(float(np.median(Y.mean((0, 1)))), 1e-9))
    Y = np.random.default_rng(rng_seed).binomial(Y.astype(np.int64), p).astype(np.float32)
    keep = keep_units(Y.reshape(-1, Y.shape[2]))
    return {**measures(Y[:, :, keep]), "recorded_bins": int(nb), "thin_p": p,
            "extras": M.unit_internal_shares(Y[:, :, keep])}


def families(rows, med, gains=GAINS):
    """Yields (family, run label, generator, mice it serves, recorder). Each generator is called once and its
    activity recorded at every mouse it serves, then discarded (disk, SLOW_LOG F4)."""
    feat = I.movie_features()
    tau_a1 = 27.15                                     # undriven A1 native timescale (SLOW_LOG F2); per
    Rmax = lambda ms: max(m["repeats"] for m in ms)    # instance it is re-measured in generation (below)
    for inst in range(3):
        for g in range(N_GROUPS):
            ms = [r for r in rows if r["instance"] == inst and r["group"] == g]
            if not ms:
                continue
            spf = I.steps_per_frame(tau_a1, med[g])
            for gain in gains:
                yield ("A1", f"i{inst}-g{g}-gain{gain}", ms, record_for_mouse,
                       lambda ms=ms, gain=gain, spf=spf, inst=inst: I.driven_random_rnn(
                           feat, R=Rmax(ms), n=480, gain=gain, spf=spf, seed=inst)[:2])
        ms = [r for r in rows if r["instance"] == inst]
        for gain in gains:                             # A4: real-time playback, no speed groups
            yield ("A4", f"i{inst}-gain{gain}", ms, lif_for_mouse,
                   lambda ms=ms, gain=gain, inst=inst: I.driven_lif(feat, R=Rmax(ms), spf=(1000 / 30) / 5,
                                                                    gain=gain, seed=inst))
    # A2, A3, A5, A6, A7 (SLOW.md section 4): the clip is sized so that it records as about CLIP_BINS bins at
    # the group's median instrument, from a pilot of the same system (`clip_units`).
    for inst in range(3):
        for g in range(N_GROUPS):
            ms = [r for r in rows if r["instance"] == inst and r["group"] == g]
            if not ms:
                continue
            prof = group_profile(ms)
            yield ("A2", f"i{inst}-g{g}", ms, record_for_mouse,
                   lambda ms=ms, inst=inst, prof=prof: gen_a2(inst, prof, Rmax(ms)))
            for kind, fam in (("gru", "A3"), ("cfc", "A5")):
                yield (fam, f"i{inst}-g{g}", ms, record_for_mouse,
                       lambda ms=ms, inst=inst, prof=prof, kind=kind: gen_char(kind, inst, prof, Rmax(ms)))
            for fam, model in LMS:
                yield (fam, f"{model.format(s=inst + 1).split('/')[-1]}-i{inst}-g{g}", ms, record_for_mouse,
                       lambda ms=ms, inst=inst, prof=prof, model=model: gen_lm(model, inst, prof, Rmax(ms)))


BALANCED_GAIN = 0.86                                  # movie input as strong as recurrent input (SLOW_LOG F2)
SLOW_SHARES = (0.05, 0.1, 0.2, 0.3, 0.5)              # H2 grid (SLOW.md section 7)
SLOW_TAUS_S = (0.5, 1.0, 2.0, 5.0)


@functools.lru_cache(maxsize=1)
def _a1_base(inst, g, R, spf):
    return I.driven_random_rnn(I.movie_features(), R=R, n=480, gain=BALANCED_GAIN, spf=spf, seed=inst)[:2]


def slow_families(rows, med):
    """H2 candidate: the balanced-gain A1 with slow drives (share x time constant grid); the base network is
    generated once per (instance, group) and the drives added per grid point."""
    for inst in range(3):
        for g in range(N_GROUPS):
            ms = [r for r in rows if r["instance"] == inst and r["group"] == g]
            if not ms:
                continue
            spf = I.steps_per_frame(27.15, med[g])
            R = max(m["repeats"] for m in ms)
            for share in SLOW_SHARES:
                for tau_s in SLOW_TAUS_S:
                    def gen(inst=inst, g=g, R=R, spf=spf, share=share, tau_s=tau_s):
                        A, st = _a1_base(inst, g, R, spf)
                        return I.add_slow_drive(A, share, tau_steps=tau_s * 30 * spf, seed=inst), st
                    yield ("A1-slow", f"i{inst}-g{g}-share{share}-tau{tau_s}", ms, record_for_mouse, gen)


CLIP_BINS = 1500                                      # natural_movie_one in 20 ms bins
NETS = ROOT / "data/derived/slow_nets"
# instances: released seeds for Pythia 14M, 160M and 410M (as in the map study); for 1B and Mamba, instances
# differ in their text (the clip and contexts are drawn with the instance's seed)
LMS = (("A6", "EleutherAI/pythia-14m-seed{s}"), ("A6", "EleutherAI/pythia-160m-seed{s}"),
       ("A6", "EleutherAI/pythia-410m-seed{s}"), ("A6", "EleutherAI/pythia-1b"),
       ("A7", "state-spaces/mamba-130m-hf"), ("A7", "state-spaces/mamba-370m-hf"))


def group_profile(ms):
    return {k: float(np.median([m["profile"][k] for m in ms])) for k in ms[0]["profile"]}


def clip_units(make, prof, guess, unit_steps=1):
    """Pilot: generate 3 repeats of a clip of `guess` units, record at `prof`, and scale the clip so it
    records as about CLIP_BINS bins. `make(n_units, R)` returns (A, starts); `unit_steps` native steps per
    unit (60 for task trials)."""
    A, st = make(guess, 3)
    Y, _ = Rc.record_repeats(A, st, guess * unit_steps, prof, rtype=CFG["rtype"], seed=0)
    return max(int(round(guess * CFG["clip"] / Y.shape[1])), 5)


def gen_a2(inst, prof, R):
    f = NETS / f"a2_seed{inst}.pt"
    if not f.exists():
        net, acc = I.trained_task_rnn(seed=inst)
        if acc < 0.7:                                  # the map study's guard (amendment 22)
            raise RuntimeError(f"A2 seed {inst} did not learn the task (accuracy {acc:.2f})")
        I.save_task_rnn(net, f)
    net = I.load_task_rnn(f)
    n = clip_units(lambda c, r: I.task_rnn_repeats(net, R=r, clip_trials=c, seed=inst), prof, 20, unit_steps=60)
    return (*I.task_rnn_repeats(net, R=R, clip_trials=n, seed=inst), n * 60)


def gen_char(kind, inst, prof, R):
    from nematica.map import zoo
    f = NETS / f"{kind}_seed{inst}.pt"
    if not f.exists():
        model, data, split = I.trained_char_net(kind, seed=inst)
        I.save_char_net(model, f, kind)
    model = I.load_char_net(f)
    data, _ = zoo.chars()
    split = len(data) - 200_000
    n = clip_units(lambda c, r: I.char_repeats(model, data, split, clip_len=c, R=r, seed=inst), prof, 600)
    return (*I.char_repeats(model, data, split, clip_len=n, R=R, seed=inst), n)


def gen_lm(model, inst, prof, R):
    name = model.format(s=inst + 1)
    tok = np.load(ROOT / "data/external/books/tokens.npy")
    mk = lambda c, r: I.lm_repeats(name, *I.text_clip_and_contexts(tok, c, 256, r, seed=inst))[:2]
    n = clip_units(mk, prof, 300)
    return (*mk(n, R), n)


def stage_ais(only=None, dry=False):
    rows, med = mice_table(dry)
    name = CFG["prefix"] + ("ais_dry.jsonl" if dry else "ais.jsonl")
    have = done(name, ("family", "run", "id"))
    n_gen = 0
    fams = itertools.chain(families(rows, med, gains=(0.25,) if dry else GAINS), slow_families(rows, med))
    for fam, run, ms, rec, gen in fams:
        if dry and n_gen >= 2:
            break
        if only and fam not in only:
            continue
        todo = [m for m in ms if (fam, run, m["id"]) not in have]
        if not todo:
            continue
        try:
            res = gen()
            A, starts = res[0], res[1]
            length = res[2] if len(res) > 2 else starts[1] - starts[0]   # clip length in native steps
            n_gen += 1
        except Exception as e:  # noqa: BLE001
            append(name, {"family": fam, "run": run, "id": "*", "error": f"generation: {type(e).__name__}: {e}"})
            continue
        for m in todo:
            try:
                row = {"family": fam, "run": run, "id": m["id"], **rec(A, starts, length, m, rng_seed=zlib.crc32(run.encode()) % 2**31)}
            except Exception as e:  # noqa: BLE001
                row = {"family": fam, "run": run, "id": m["id"], "error": f"{type(e).__name__}: {e}"}
            append(name, row)
            print(fam, run, m["id"], {k: row.get(k) for k in ("M1_lag1", "M2_lag1", "error")}, flush=True)
        del A


# ------------------------------------------------------------------------------------------------ tests
SPLIT_SEED = 2026


def _wilcoxon(d, alt):
    from scipy.stats import wilcoxon
    d = np.asarray(d, float)
    d = d[np.isfinite(d)]
    if len(d) < 6 or np.all(d == 0):
        return np.nan
    return float(wilcoxon(d, alternative=alt).pvalue)


def _boot_ci(d, n=4000, seed=0):
    rng = np.random.default_rng(seed)
    d = np.asarray(d, float)
    d = d[np.isfinite(d)]
    med = np.median(rng.choice(d, (n, len(d))), 1)
    return [float(np.quantile(med, 0.05)), float(np.quantile(med, 0.95))]


def _value(row, measure):
    """M1 as it is; M2 on a log scale, only where the internal part exists (M1 >= 0.05)."""
    if measure == "M1":
        return row.get("M1_lag1")
    m2 = row.get("M2_lag1")
    if row.get("M1_lag1") is None or row["M1_lag1"] < 0.05 or m2 is None or not np.isfinite(m2) or m2 <= 0:
        return None
    return float(np.log(m2))


def _verdict(d, ruler):
    du = np.asarray(d, float) / ruler
    p_gap, p_rev = _wilcoxon(du, "greater"), _wilcoxon(du, "less")
    md = float(np.median(du))
    v = "confirmed" if p_gap < 0.05 and md > 0.5 else "refuted" if p_rev < 0.05 and md < -0.5 else "not decided"
    return {"verdict": v, "n_pairs": int(len(du)), "median_d_ruler": md, "p_gap": p_gap, "p_reverse": p_rev,
            "ci90_median_d": _boot_ci(du)}


def stage_tests(dry=False):
    pre = CFG["prefix"]
    mice = {r["id"]: r for r in map(json.loads, (OUT / (pre + ("mice_dry.jsonl" if dry else "mice.jsonl")))
                                    .read_text().splitlines()) if "error" not in r}
    ais = [r for r in map(json.loads, (OUT / (pre + ("ais_dry.jsonl" if dry else "ais.jsonl"))).read_text()
                          .splitlines()) if "error" not in r and r["id"] in mice]
    out = {"frozen": frozen(), "n_mice": len(mice), "H1": {}, "H2": {}, "H3": {}}
    rulers = {}
    for meas in ("M1", "M2"):
        mv = [_value(m, meas) for m in mice.values()]
        mv = [v for v in mv if v is not None]
        rulers[meas] = float(np.std(mv, ddof=1)) if len(mv) > 2 else np.nan
    out["rulers"] = rulers

    def closest(rows_m, meas, target):
        vals = [_value(r, meas) for r in rows_m]
        vals = [v for v in vals if v is not None]
        return None if not vals else min(vals, key=lambda v: abs(v - target))

    for fam in ("A1", "A2", "A3", "A4", "A5", "A6", "A7"):
        res = {}
        for meas in ("M1", "M2"):
            d, absent = [], 0
            for mid, m in mice.items():
                mv = _value(m, meas)
                rows_m = [r for r in ais if r["family"] == fam and r["id"] == mid]
                if mv is None or not rows_m:
                    continue
                av = closest(rows_m, meas, mv)       # gains and model sizes: the one closest to this mouse
                if av is None:
                    absent += 1
                    continue
                d.append(mv - av)
            n = len(d) + absent
            if meas == "M2" and n and absent > n / 2:
                res[meas] = {"verdict": "no internal part", "n_pairs": n, "absent": absent}
            elif d:
                res[meas] = {**_verdict(d, rulers[meas]), "absent": absent}
        out["H1"][fam] = res
    conf = sum(any(v.get("verdict") == "confirmed" for v in r.values()) for r in out["H1"].values())
    refut = any(v.get("verdict") == "refuted" for r in out["H1"].values() for v in r.values())
    out["H1"]["thesis"] = {"families_confirmed": conf, "any_refuted": refut, "holds": conf >= 5 and not refut}

    # H2: tune (share, tau) on a seeded half, test on the other half
    ids = sorted(mice)
    half = set(np.random.default_rng(SPLIT_SEED).permutation(ids)[: len(ids) // 2])
    slow = [r for r in ais if r["family"] == "A1-slow"]
    grid = sorted({r["run"].split("-share")[1] for r in slow})
    def d_for(gp, which, meas):
        return [_value(mice[r["id"]], meas) - _value(r, meas) for r in slow
                if r["run"].endswith("-share" + gp) and (r["id"] in half) == which
                and _value(mice[r["id"]], meas) is not None and _value(r, meas) is not None]
    if grid:
        score = {gp: sum(abs(np.median(d_for(gp, True, m))) / rulers[m] if d_for(gp, True, m) else np.inf
                         for m in ("M1", "M2")) for gp in grid}
        best = min(score, key=score.get)
        out["H2"] = {"chosen": best, "train_score": score[best]}
        for meas in ("M1", "M2"):
            d = np.asarray(d_for(best, False, meas)) / rulers[meas]
            ci = _boot_ci(d) if len(d) else [np.nan, np.nan]
            out["H2"][meas] = {"n_pairs": int(len(d)), "median_d_ruler": float(np.median(d)) if len(d) else None,
                               "ci90": ci, "equivalent": bool(len(d) and -0.5 < ci[0] and ci[1] < 0.5)}
        out["H2"]["confirmed"] = bool(out["H2"]["M1"]["equivalent"] and out["H2"]["M2"]["equivalent"])

    # H3: Pythia 1B not closer to the mice than Pythia 14M
    for meas in ("M1", "M2"):
        diffs = []
        for mid, m in mice.items():
            mv = _value(m, meas)
            a = {k: [_value(r, meas) for r in ais if r["id"] == mid and r["family"] == "A6" and k in r["run"]]
                 for k in ("pythia-14m", "pythia-1b")}
            if mv is None or not all(a.values()) or any(v is None for v in a["pythia-14m"] + a["pythia-1b"]):
                continue
            diffs.append((abs(mv - a["pythia-14m"][0]) - abs(mv - a["pythia-1b"][0])) / rulers[meas])
        if diffs:
            ci = _boot_ci(diffs)
            out["H3"][meas] = {"n_pairs": len(diffs), "median_closer_by_1b_ruler": float(np.median(diffs)),
                               "ci90": ci, "confirmed": bool(ci[1] < 0.5)}
    # validity check of M2: on the shuffled movie the locked part is faster, so the locked integral time
    # falls and M2 rises, if the internal part is the mouse's own (SLOW.md section 7)
    sh = [m for m in mice.values() if "shuffled" in m]
    if sh:
        dl = [np.log(m["shuffled"]["tl_lag1"]) - np.log(m["tl_lag1"]) for m in sh
              if m["shuffled"].get("tl_lag1") and m.get("tl_lag1")]
        d2 = [_value(m["shuffled"], "M2") - _value(m, "M2") for m in sh
              if _value(m["shuffled"], "M2") is not None and _value(m, "M2") is not None]
        out["validity_shuffled"] = {"n_mice": len(sh), "locked_time_falls_p": _wilcoxon(dl, "less"),
                                    "median_log_locked_change": float(np.median(dl)) if dl else None,
                                    "M2_rises_p": _wilcoxon(d2, "greater"),
                                    "median_log_M2_change": float(np.median(d2)) if d2 else None,
                                    "passes": bool(dl and d2 and _wilcoxon(dl, "less") < 0.05
                                                   and _wilcoxon(d2, "greater") < 0.05)}
    name = pre + ("tests_dry.json" if dry else "tests.json")
    (OUT / name).write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out["H1"]["thesis"]), json.dumps(out.get("H2", {}).get("confirmed")), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["mice", "ais", "tests"])
    p.add_argument("--arm", choices=list(ARMS), default="npx")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--only", nargs="*")
    a = p.parse_args()
    if a.stage in ("mice", "ais") and not a.dry and not frozen():
        sys.exit("SLOW.md is not frozen: no real activity is measured before the registration binds.")
    CFG.update(ARMS[a.arm])
    if a.stage == "mice":
        stage_mice_2p() if a.arm == "2p" else stage_mice(dry=a.dry)
    elif a.stage == "ais":
        stage_ais(only=a.only, dry=a.dry)
    else:
        stage_tests(dry=a.dry)


if __name__ == "__main__":
    main()
