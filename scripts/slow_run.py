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
GAINS = (0.05, 0.1, 0.25, 0.5, 0.86, 1.0, 2.0, 4.0)  # SLOW.md section 7; 0.86 = balanced (finding 20)
N_GROUPS = 4                                          # playback-speed groups (quartiles of bins per timescale)
KEYS = ("bins_per_tau", "count_per_bin", "noise", "rate_log_sd")
PRIMARY = ("M1", "M2", "ti", "tl", "int_ceiling", "lock_ceiling", "no_shared", "no_locked")
K0 = 2                                               # first lag used: 2 bins (40 ms), review S-R1 finding 1
MIN_UNITS = 30                                       # a mouse with fewer included units is excluded


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


def adaptation_trend(Y):
    """Reported (SLOW.md section 3): Spearman correlation, over repeats, between repeat number and how well
    that repeat's population response matches the mean of the other repeats."""
    from scipy.stats import spearmanr
    Y = np.asarray(Y, np.float32)
    R = Y.shape[0]
    if R < 4:
        return None
    tot = Y.sum(0)
    sim = [float(np.corrcoef(Y[r].ravel(), ((tot - Y[r]) / (R - 1)).ravel())[0, 1]) for r in range(R)]
    return float(spearmanr(np.arange(R), sim)[0])


def measures(Y):
    """Primary (review S-R1 fix): `lag_measures` from lag 2 with units centred within each repeat; also each
    half of the clip separately (finding 12), the adaptation trend and, for reference, the superseded
    measures."""
    r = M.lag_measures(Y, k0=K0)
    T = Y.shape[1]
    h1, h2 = M.lag_measures(Y[:, : T // 2], k0=K0), M.lag_measures(Y[:, T // 2:], k0=K0)
    old = M.internal_measures(Y)
    return {**{k: r[k] for k in PRIMARY}, "M1_first_half": h1["M1"], "M1_second_half": h2["M1"],
            "adapt_trend": adaptation_trend(Y),
            "superseded": {k: old.get(k) for k in ("M1_lag1", "M2_lag1", "M1", "M2_int")}}


def split_halves(Y):
    """C3 (SLOW.md section 6): the primary measures on odd and on even repeats."""
    a, b = M.lag_measures(Y[0::2], k0=K0), M.lag_measures(Y[1::2], k0=K0)
    return {"odd": {k: a[k] for k in PRIMARY}, "even": {k: b[k] for k in PRIMARY}}


# ------------------------------------------------------------------------------------------------ mice
def keep_units(X, per_repeat_bins=None):
    """The map study's inclusion rule for spikes, with review S-R1 finding 23 fixed: the rate threshold over
    all repeats, and the 200-spike minimum counted over the first 17 repeats only (17 is the fewest valid
    repeats seen), so 20- and 60-repeat sessions face the same rule."""
    n_all = X.sum(0)
    first = X[: 17 * per_repeat_bins] if per_repeat_bins else X
    return (X.std(0) > 1e-9) & (first.sum(0) >= INS.MIN_SPIKES) & \
        (n_all / (len(X) * INS.SPIKE_BIN_S) >= INS.MIN_RATE_HZ)


def stage_mice(dry=False):
    name = "mice_dry.jsonl" if dry else "mice.jsonl"
    have = {k[0] for k in done(name, ("id",))}
    for rank, (ds, a) in enumerate(D.sessions()):    # rank: the fixed session order (finding 15)
        uid = a["path"].split("/")[0]
        if uid in have:
            continue
        try:
            if dry:
                Y = _fake_mouse(uid)
                sel = np.ones(Y.shape[2], bool)
            else:
                z = D.movie_cache(a)
                Y = D.movie_counts(z)
                area, qc = D.unit_meta(a, z["units"])
                sel = D.visual_cortex(area) & qc          # review S-R1 finding 3: visual cortex, Allen QC
            R, nb, N = Y.shape
            X = Y.reshape(R * nb, N).astype(np.float32)
            keep = sel & keep_units(X, nb)
            if keep.sum() < MIN_UNITS:
                raise RuntimeError(f"only {int(keep.sum())} included visual-cortex units")
            seg = [r * nb for r in range(1, R)]
            prof = INS.instrument_numbers({"activity": X[:, keep], "dt": INS.SPIKE_BIN_S, "segments": seg},
                                          "spikes")
            del X
            row = {"id": uid, "rank": rank, "dandiset": ds, "repeats": R, "bins": nb, "units": int(keep.sum()), "units_cached": N,
                   "profile": {k: prof.get(k) for k in KEYS}, **measures(Y[:, :, keep]),
                   "split": split_halves(Y[:, :, keep]),
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
    for rank, exp in enumerate(D.twop_experiments()):
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
            row = {"id": uid, "rank": rank, "specimen": exp["specimen_id"], "area": exp["targeted_structure"]["acronym"],
                   "repeats": R, "bins": nb, "units": int(ok.sum()),
                   "profile": {k: prof.get(k) for k in INS.KEYS["calcium"]}, **measures(Y[:, :, ok]),
                   "split": split_halves(Y[:, :, ok]),
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
            r["instance"], r["group"], r["rtype"] = r.get("rank", i) % 3, 0, "calcium"
        return rows, {0: float(np.median([r["profile"]["bins_per_tau"] for r in npx]))}
    bpt = np.array([r["profile"]["bins_per_tau"] for r in rows])
    edges = np.quantile(bpt, np.linspace(0, 1, N_GROUPS + 1))
    for i, r in enumerate(rows):                       # instance from the fixed session order (finding 15)
        r["instance"] = r.get("rank", i) % 3
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
    knobs = {a: (float(v) if isinstance(v, (int, float, np.floating, np.integer)) and not isinstance(v, bool) else v)
             for a, v in k.items() if isinstance(v, (int, float, bool, np.floating, np.integer, dict))}
    return {**measures(Y), "recorded_bins": int(Y.shape[1]), "repeats_used": int(Y.shape[0]),
            "bin_steps": float(Rc.recording.per_sample(k, rtype)), "knobs": knobs,       # finding 10
            "reached": bool(k.get("reached", True)), "extras": M.unit_internal_shares(Yn)}


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


@functools.lru_cache(maxsize=3)
def a1_tau(inst):
    """Finding 16: the undriven A1 native timescale, measured per instance (8,000 steps)."""
    from nematica.map import zoo, measures as MM
    return float(MM.tau_med(zoo.random_rnn(n=480, steps=8000, seed=inst)[0]))


def families(rows, med, gains=GAINS):
    """Yields (family, run label, mice it serves, recorder, generator). Each generator is called once and its
    activity recorded at every mouse it serves, then discarded (disk, SLOW_LOG F4)."""
    feat = I.movie_features()
    Rmax = lambda ms: max(m["repeats"] for m in ms)
    for inst in range(3):
        for g in range(N_GROUPS):
            ms = [r for r in rows if r["instance"] == inst and r["group"] == g]
            if not ms:
                continue
            for gain in gains:
                yield ("A1", f"i{inst}-g{g}-gain{gain}", ms, record_for_mouse,
                       lambda ms=ms, gain=gain, g=g, inst=inst: I.driven_random_rnn(
                           feat, R=Rmax(ms), n=480, gain=gain, spf=I.steps_per_frame(a1_tau(inst), med[g]),
                           seed=inst)[:2])
        ms = [r for r in rows if r["instance"] == inst]
        for gain in gains:                             # A4: real-time playback, no speed groups
            yield ("A4", f"i{inst}-gain{gain}", ms, lif_for_mouse,
                   lambda ms=ms, gain=gain, inst=inst: I.driven_lif(feat, R=Rmax(ms), spf=(1000 / 30) / 5,
                                                                    gain=gain, seed=inst))
    # A2, A3, A5, A6, A7 (finding 12): one clip per instance, the same for every mouse, sized once so that it
    # records as about CFG["clip"] samples at the median instrument of all mice (`clip_units`)
    prof = group_profile(rows)
    for inst in range(3):
        ms = [r for r in rows if r["instance"] == inst]
        yield ("A2", f"i{inst}", ms, record_for_mouse, lambda ms=ms, inst=inst: gen_a2(inst, prof, Rmax(ms)))
        for kind, fam in (("gru", "A3"), ("cfc", "A5")):
            yield (fam, f"i{inst}", ms, record_for_mouse,
                   lambda ms=ms, inst=inst, kind=kind: gen_char(kind, inst, prof, Rmax(ms)))
        for fam, model in LMS:
            yield (fam, f"{model.format(s=inst + 1).split('/')[-1]}-i{inst}", ms, record_for_mouse,
                   lambda ms=ms, inst=inst, model=model: gen_lm(model, inst, prof, Rmax(ms)))


def sensitivity_families(rows, med):
    """Finding 5: playback sensitivity for the balanced-gain A1 (x0.5, x2, and playback from the driven
    timescale). Finding 7: H2's negative controls, tuned like the slow drive: a fast drive (time constant
    one frame) and more network noise."""
    feat = I.movie_features()
    for inst in range(3):
        for g in range(N_GROUPS):
            ms = [r for r in rows if r["instance"] == inst and r["group"] == g]
            if not ms:
                continue
            R = max(m["repeats"] for m in ms)
            spf = lambda inst=inst, g=g: I.steps_per_frame(a1_tau(inst), med[g])
            for mult in (0.5, 2.0):
                yield ("A1-play", f"i{inst}-g{g}-x{mult}", ms, record_for_mouse,
                       lambda R=R, spf=spf, mult=mult, inst=inst: I.driven_random_rnn(
                           feat, R=R, n=480, gain=BALANCED_GAIN, spf=spf() * mult, seed=inst)[:2])

            def driven_rule(R=R, inst=inst, g=g):
                from nematica.map import measures as MM
                A, _, _ = I.driven_random_rnn(feat, R=2, n=480, gain=BALANCED_GAIN,
                                              spf=I.steps_per_frame(a1_tau(inst), med[g]), seed=inst)
                return I.driven_random_rnn(feat, R=R, n=480, gain=BALANCED_GAIN,
                                           spf=I.steps_per_frame(float(MM.tau_med(A)), med[g]), seed=inst)[:2]
            yield ("A1-play", f"i{inst}-g{g}-driven", ms, record_for_mouse, driven_rule)
            for share in SLOW_SHARES:
                def fast(R=R, inst=inst, g=g, share=share):
                    A, st = _a1_base(inst, g, R, I.steps_per_frame(a1_tau(inst), med[g]))
                    return I.add_slow_drive(A, share, tau_steps=I.steps_per_frame(a1_tau(inst), med[g]),
                                            seed=inst), st
                yield ("A1-fast", f"i{inst}-g{g}-share{share}", ms, record_for_mouse, fast)
            for noise in (0.2, 0.4, 0.8, 1.6):
                yield ("A1-noise", f"i{inst}-g{g}-noise{noise}", ms, record_for_mouse,
                       lambda R=R, inst=inst, g=g, noise=noise: I.driven_random_rnn(
                           feat, R=R, n=480, gain=BALANCED_GAIN, noise=noise,
                           spf=I.steps_per_frame(a1_tau(inst), med[g]), seed=inst)[:2])


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
            spf = I.steps_per_frame(a1_tau(inst), med[g])
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
    f = NETS / f"a2_inst{inst}.pt"
    if not f.exists():
        for seed in (inst, inst + 3, inst + 6):       # SLOW.md section 4: accuracy at least 0.7, else next seed
            g = NETS / f"a2_seed{seed}.pt"
            if g.exists():
                net = I.load_task_rnn(g)
                break
            net, acc = I.trained_task_rnn(seed=seed)
            print("A2 seed", seed, "accuracy", round(acc, 3), flush=True)
            if acc >= 0.7:
                I.save_task_rnn(net, g)
                break
        else:
            raise RuntimeError(f"A2 instance {inst}: no seed reached accuracy 0.7")
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
    at = len(tok) * (inst + 2) // 6                    # finding 17: each instance its own clip
    mk = lambda c, r: I.lm_repeats(name, *I.text_clip_and_contexts(tok, c, 256, r, seed=inst, clip_at=at))[:2]
    n = clip_units(mk, prof, 300)
    return (*mk(n, R), n)


def stage_ais(only=None, dry=False):
    rows, med = mice_table(dry)
    name = CFG["prefix"] + ("ais_dry.jsonl" if dry else "ais.jsonl")
    have = done(name, ("family", "run", "id"))
    n_gen = 0
    fams = itertools.chain(families(rows, med, gains=(0.25,) if dry else GAINS), slow_families(rows, med),
                           sensitivity_families(rows, med))
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
            print(fam, run, m["id"], {k: row.get(k) for k in ("M1", "M2", "error")}, flush=True)
        del A


# ------------------------------------------------------------------------------------------------ tests
SPLIT_SEED = 2026
RUNS_PER_FAMILY = {"A1": len(GAINS), "A4": len(GAINS), "A2": 1, "A3": 1, "A5": 1, "A6": 4, "A7": 2}


def _wilcoxon(d, alt):
    from scipy.stats import wilcoxon
    d = np.asarray(d, float)
    d = d[np.isfinite(d)]
    if len(d) < 6 or np.all(d == 0):
        return np.nan
    return float(wilcoxon(d, alternative=alt).pvalue)


def _sign_test(x, alt):
    from scipy.stats import binomtest
    x = np.asarray(x, float)
    x = x[np.isfinite(x) & (x != 0)]
    if len(x) < 4:
        return np.nan
    return float(binomtest(int((x > 0).sum()), len(x), 0.5, alternative=alt).pvalue)


def _cluster_ci(d, cells, n=4000, seed=0):
    """Finding 6: bootstrap over generator cells (pairs sharing an AI run are resampled together)."""
    d, cells = np.asarray(d, float), np.asarray(cells)
    u = np.unique(cells)
    idx = {c: np.flatnonzero(cells == c) for c in u}
    rng = np.random.default_rng(seed)
    meds = [np.median(np.concatenate([d[idx[c]] for c in rng.choice(u, len(u))])) for _ in range(n)]
    return [float(np.quantile(meds, 0.05)), float(np.quantile(meds, 0.95))]


def _ruler(v):
    """Finding 19: a MAD-based SD (1.4826 x median absolute deviation)."""
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    return float(1.4826 * np.median(np.abs(v - np.median(v)))) if len(v) > 2 else np.nan


def _value(row, meas):
    """M1 as it is. M2 on a log scale, only where there is an internal part (M1 >= 0.05, positive shared
    covariance) and a locked part to time it against (finding 13: 'no_locked' is its own code).
    Returns (value or None, code)."""
    if meas == "M1":
        return row.get("M1"), "ok"
    if row.get("no_shared") or row.get("M1") is None or row["M1"] < 0.05:
        return None, "no internal part"
    if row.get("no_locked"):
        return None, "no locked part"
    m2 = row.get("M2")
    if m2 is None or not np.isfinite(m2) or m2 <= 0:
        return None, "no internal part"
    return float(np.log(m2)), "ok"


def _pair(mouse, ai_rows, meas):
    """Finding 2: the bracket rule. d = 0 if the mouse lies within the family's range over its gains or
    sizes, else mouse minus the nearer end. Finding 4: a mouse at ceiling against a family with a run at
    ceiling counts as a tie."""
    mv, _ = _value(mouse, meas)
    if mv is None:
        return None, "mouse absent"
    vals = [(_value(r, meas)[0], r) for r in ai_rows]
    ok = [(v, r) for v, r in vals if v is not None]
    if not ok:
        codes = {_value(r, meas)[1] for r in ai_rows}
        return None, ("no locked part" if codes == {"no locked part"} else "no internal part")
    if meas == "M2" and mouse.get("int_ceiling") and any(r.get("int_ceiling") for _, r in ok):
        return 0.0, "ceiling tie"
    lo, hi = min(v for v, _ in ok), max(v for v, _ in ok)
    return (0.0 if lo <= mv <= hi else mv - (hi if mv > hi else lo)), "ok"


def _verdict(d, cells, ruler):
    """Finding 6, as revised after a synthetic check of this code (SLOW_LOG): with only 3 instances for most
    families a sign test over cells can never reach p < 0.05, so the test is done within each instance
    (pairs within an instance share AI runs but differ in mice) and must hold in every instance."""
    du = np.asarray(d, float) / ruler
    cells = np.asarray(cells)
    inst = np.asarray([c.split("-")[0] for c in cells])
    per = {i: (_wilcoxon(du[inst == i], "greater"), _wilcoxon(du[inst == i], "less")) for i in np.unique(inst)}
    p_gap, p_rev = _wilcoxon(du, "greater"), _wilcoxon(du, "less")
    md = float(np.median(du))
    ci = _cluster_ci(du, cells)
    all_gap = all(np.isfinite(g) and g < 0.05 for g, _ in per.values())
    all_rev = all(np.isfinite(r) and r < 0.05 for _, r in per.values())
    if p_gap < 0.05 and all_gap and md > 0.5 and ci[0] > 0:
        v = "confirmed"
    elif p_rev < 0.05 and all_rev and md < -0.5 and ci[1] < 0:
        v = "refuted"
    else:
        v = "not decided"
    return {"verdict": v, "n_pairs": int(len(du)), "n_cells": int(len(np.unique(cells))), "median_d_ruler": md,
            "p_gap": p_gap, "p_reverse": p_rev, "per_instance_p": {k: list(v_) for k, v_ in per.items()},
            "cluster_ci90": ci}


def _family_test(mice, ais, fam, meas, ruler, need=None, min_ai_m1=None):
    d, cells, codes, missing = [], [], {}, 0
    for mid, m in mice.items():
        rows_m = [r for r in ais if r["family"] == fam and r["id"] == mid]
        if need and len(rows_m) < need:                # finding 11: every grid point or size must exist
            missing += 1
            continue
        if any(not r.get("reached", True) for r in rows_m):   # finding 10: unreached matches excluded
            missing += 1
            continue
        use_rows = [r for r in rows_m if r.get("M1", 0) >= min_ai_m1] if min_ai_m1 else rows_m
        if not use_rows:
            codes["AI M1 below the restriction"] = codes.get("AI M1 below the restriction", 0) + 1
            continue
        x, code = _pair(m, use_rows, meas)
        codes[code] = codes.get(code, 0) + 1
        if x is not None:
            d.append(x)
            cells.append(rows_m[0]["run"].split("-gain")[0].split("-share")[0])
    n = len(d) + sum(v for k, v in codes.items() if k in ("no internal part", "no locked part"))
    res = {"codes": codes, "missing": missing}
    if meas == "M2" and n and codes.get("no internal part", 0) > n / 2:
        return {**res, "verdict": "no internal part"}
    if meas == "M2" and n and codes.get("no locked part", 0) > n / 2:
        return {**res, "verdict": "no locked part"}
    if len(d) < 6:
        return {**res, "verdict": "too few pairs", "n_pairs": len(d)}
    return {**res, **_verdict(d, cells, ruler)}


def stage_tests(dry=False):
    pre = CFG["prefix"]
    mice = {r["id"]: r for r in map(json.loads, (OUT / (pre + ("mice_dry.jsonl" if dry else "mice.jsonl")))
                                    .read_text().splitlines()) if "error" not in r}
    ais = [r for r in map(json.loads, (OUT / (pre + ("ais_dry.jsonl" if dry else "ais.jsonl"))).read_text()
                          .splitlines()) if "error" not in r and r["id"] in mice]
    out = {"frozen": frozen(), "n_mice": len(mice), "H1": {}, "H2": {}, "H3": {}}
    rulers = {meas: _ruler([_value(m, meas)[0] for m in mice.values()]) for meas in ("M1", "M2")}
    out["rulers"] = rulers

    # validity check of M2 (finding 9): locked time falls, M2 rises, and the internal time moves less than
    # the locked time does
    sh = [m for m in mice.values() if "shuffled" in m]
    valid_m2 = True
    if sh:
        fin = lambda x: x is not None and np.isfinite(x) and x > 0
        pairs = [(m, m["shuffled"]) for m in sh if fin(m.get("tl")) and fin(m["shuffled"].get("tl"))]
        dl = [np.log(b["tl"]) - np.log(a["tl"]) for a, b in pairs]
        di = [np.log(b["ti"]) - np.log(a["ti"]) for a, b in pairs if fin(a.get("ti")) and fin(b.get("ti"))]
        d2 = [_value(b, "M2")[0] - _value(a, "M2")[0] for a, b in pairs
              if _value(a, "M2")[0] is not None and _value(b, "M2")[0] is not None]
        p_l, p_2 = _wilcoxon(dl, "less"), _wilcoxon(d2, "greater")
        stable = bool(di and dl and abs(np.median(di)) < abs(np.median(dl)))
        valid_m2 = bool(p_l < 0.05 and p_2 < 0.05 and stable)
        out["validity_shuffled"] = {"n_mice": len(pairs), "locked_time_falls_p": p_l, "M2_rises_p": p_2,
                                    "median_log_locked_change": float(np.median(dl)) if dl else None,
                                    "median_log_internal_change": float(np.median(di)) if di else None,
                                    "internal_moves_less": stable, "passes": valid_m2}

    # C3 (SLOW.md section 6): odd against even repeats, Spearman across mice
    from scipy.stats import spearmanr
    rel = {}
    for meas in ("M1", "M2"):
        xy = [(_value(m["split"]["odd"], meas)[0], _value(m["split"]["even"], meas)[0]) for m in mice.values()
              if "split" in m]
        xy = [(x, y) for x, y in xy if x is not None and y is not None]
        rho = float(spearmanr(*zip(*xy))[0]) if len(xy) >= 6 else np.nan
        rel[meas] = {"n_mice": len(xy), "rho": rho, "reliable": bool(rho >= 0.5)}
    out["C3"] = rel
    # nuisance: playback (SLOW.md section 6): the balanced-gain A1 against each playback variant
    nuis = {}
    for var in ("x0.5", "x2.0", "driven"):
        for meas in ("M1", "M2"):
            dd = []
            for mid in mice:
                base = [r for r in ais if r["id"] == mid and r["family"] == "A1" and r["run"].endswith("gain0.86")]
                alt = [r for r in ais if r["id"] == mid and r["family"] == "A1-play" and r["run"].endswith(var)]
                if base and alt and _value(base[0], meas)[0] is not None and _value(alt[0], meas)[0] is not None:
                    dd.append((_value(alt[0], meas)[0] - _value(base[0], meas)[0]) / rulers[meas])
            nuis[f"{var}|{meas}"] = {"n": len(dd), "median_shift_ruler": float(np.median(dd)) if dd else None}
    out["nuisance_playback"] = nuis
    playback_sensitive = any(v["median_shift_ruler"] is not None and abs(v["median_shift_ruler"]) >= 0.5
                             for k, v in nuis.items() if k.endswith("|M2"))
    out["nuisance_playback_M2_sensitive"] = playback_sensitive

    for fam, need in RUNS_PER_FAMILY.items():
        out["H1"][fam] = {meas: _family_test(mice, ais, fam, meas, rulers[meas], need) for meas in ("M1", "M2")}
        # reported, not counted: M2 with AI runs restricted to M1 at least 0.2 (C1 cross-talk, SLOW.md 7)
        out["H1"][fam]["M2_ai_m1_ge_0.2"] = {**_family_test(mice, ais, fam, "M2", rulers["M2"], need, 0.2),
                                             "counted": False}
    for fam in ("A1", "A4"):                           # movie-driven families: M2 set aside if playback-sensitive
        if playback_sensitive:
            out["H1"][fam]["M2"]["counted"] = False
    for fam in RUNS_PER_FAMILY:
        for meas in ("M1", "M2"):
            if not rel[meas]["reliable"]:                # C3 failure: the measure is not tested
                out["H1"][fam][meas]["counted"] = False
    use = ("M1", "M2") if valid_m2 else ("M1",)        # finding 9: if the check fails, the thesis uses M1 only
    fams = [f for f in RUNS_PER_FAMILY]
    cnt = lambda f, m: out["H1"][f][m].get("counted", True)
    conf = sum(any(out["H1"][f][m].get("verdict") == "confirmed" and cnt(f, m) for m in use) for f in fams)
    refut = any(out["H1"][f][m].get("verdict") == "refuted" and cnt(f, m) for f in fams for m in use)
    # (the restricted M2 entries are never in `use`, so they never count)
    out["H1"]["thesis"] = {"measures_used": list(use), "families_confirmed": conf, "any_refuted": refut,
                           "holds": conf >= 5 and not refut}

    # H2 with negative controls (finding 7): each candidate tuned on the seeded half, tested on the other
    ids = sorted(mice)
    half = set(np.random.default_rng(SPLIT_SEED).permutation(ids)[: len(ids) // 2])

    def tune_test(fam, key):
        rows = [r for r in ais if r["family"] == fam]
        grid = sorted({r["run"].split(key)[1] for r in rows})
        if not grid:
            return None

        def d_for(gp, train, meas):
            out_ = []
            for r in rows:
                if r["run"].endswith(key + gp) and (r["id"] in half) == train:
                    x, _ = _pair(mice[r["id"]], [r], meas)
                    if x is not None:
                        out_.append(x / rulers[meas])
            return out_
        score = {gp: sum(abs(np.median(d_for(gp, True, m))) if d_for(gp, True, m) else np.inf
                         for m in ("M1", "M2")) for gp in grid}
        best = min(score, key=score.get)
        res = {"chosen": best, "train_score": score[best]}
        for meas in ("M1", "M2"):
            dd = d_for(best, False, meas)
            cells = [r["run"].split(key)[0] for r in rows if r["run"].endswith(key + best) and r["id"] not in half
                     and _pair(mice[r["id"]], [r], meas)[0] is not None]
            ci = _cluster_ci(dd, cells) if len(dd) >= 6 else [np.nan, np.nan]
            res[meas] = {"n_pairs": len(dd), "median_d_ruler": float(np.median(dd)) if dd else None,
                         "cluster_ci90": ci, "equivalent": bool(-0.5 < ci[0] and ci[1] < 0.5)}
        res["equivalent_both"] = bool(res["M1"]["equivalent"] and res["M2"]["equivalent"])
        return res
    out["H2"] = {"slow": tune_test("A1-slow", "-share"), "control_fast": tune_test("A1-fast", "-share"),
                 "control_noise": tune_test("A1-noise", "-noise")}
    if out["H2"]["slow"]:
        ctrl_fail = all(c is not None and not c["equivalent_both"]
                        for c in (out["H2"]["control_fast"], out["H2"]["control_noise"]))
        out["H2"]["confirmed"] = bool(out["H2"]["slow"]["equivalent_both"] and ctrl_fail)

    # H3 (finding 18): on M1, the median over mice of how much closer Pythia 1B is than Pythia 14M
    diffs, cells = [], []
    for mid, m in mice.items():
        mv, _ = _value(m, "M1")
        a14 = [r for r in ais if r["id"] == mid and r["family"] == "A6" and "pythia-14m" in r["run"]]
        a1b = [r for r in ais if r["id"] == mid and r["family"] == "A6" and "pythia-1b" in r["run"]]
        if mv is None or not a14 or not a1b:
            continue
        diffs.append((abs(mv - a14[0]["M1"]) - abs(mv - a1b[0]["M1"])) / rulers["M1"])
        cells.append(a14[0]["run"].split("-i")[-1])
    if len(diffs) >= 6:
        ci = _cluster_ci(diffs, cells)
        out["H3"] = {"measure": "M1", "n_pairs": len(diffs), "median_closer_by_1b_ruler": float(np.median(diffs)),
                     "cluster_ci90": ci, "confirmed": bool(ci[1] < 0.5)}
    name = pre + ("tests_dry.json" if dry else "tests.json")
    (OUT / name).write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out["H1"]["thesis"]), flush=True)


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
