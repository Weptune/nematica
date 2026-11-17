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
MOVIE_FAMS = {"A1", "A4", "A1-slow", "A1-fast", "A1-noise", "A1-play"}
PLAYBACK_FAMS = MOVIE_FAMS - {"A4"}                 # amendment S1 (S-R3 N1): A4 plays in real time, no groups


def _code_state():
    """S-R2 finding 13: the repository commit and whether the working tree differs from it."""
    import subprocess
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "nematica", "scripts"],
                                    capture_output=True, text=True).stdout.strip())
        fz = frozen()                                  # amendment S1 (S-R3 N12): code compared with the freeze
        since = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", fz, "--", "nematica", "scripts"],
                               capture_output=True, text=True).stdout.split() if fz else None
        return {"head": head, "dirty": dirty, "frozen": fz, "code_files_changed_since_freeze": since}
    except Exception:  # noqa: BLE001
        return {"head": None, "dirty": None}


PRIMARY = ("M1", "M2", "ti", "tl", "int_ceiling", "lock_ceiling", "no_shared", "no_locked")
K0 = 2                                               # first lag used: 2 bins (40 ms), review S-R1 finding 1
MIN_UNITS = 30                                       # a mouse with fewer included units is excluded
MIN_REPEATS = 10                                     # amendment S1: a mouse with fewer valid repeats is excluded
MAX_UNITS = 480                                      # and one with more keeps a seeded subset of 480


def frozen():
    m = re.search(r"Frozen at commit ([0-9a-f]{7,40})", (ROOT / "docs/SLOW.md").read_text())
    return m.group(1) if m else None


CODE_STATE = _code_state()                           # after frozen(): defined before it, every stamp was empty


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
def keep_units(X, per_repeat_bins=None, min_spikes=None):
    """The map study's inclusion rule for spikes, with review S-R1 finding 23 fixed: the rate threshold over
    all repeats, and the 200-spike minimum counted over the first 17 repeats only (17 is the fewest valid
    repeats seen), so 20- and 60-repeat sessions face the same rule."""
    n_all = X.sum(0)
    first = X[: 17 * per_repeat_bins] if per_repeat_bins else X
    ms = INS.MIN_SPIKES if min_spikes is None else min_spikes   # amendment S1: scaled for AI clips
    return (X.std(0) > 1e-9) & (first.sum(0) >= ms) & \
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
            if R < MIN_REPEATS:                           # amendment S1 (S-R3 N14)
                raise RuntimeError(f"only {R} valid repeats")
            if keep.sum() < MIN_UNITS:
                raise RuntimeError(f"only {int(keep.sum())} included visual-cortex units")
            if keep.sum() > MAX_UNITS:                    # S-R2 finding 10: at most as many units as the AIs
                ki = np.sort(np.random.default_rng(zlib.crc32(uid.encode())).choice(np.flatnonzero(keep),
                                                                                   MAX_UNITS, replace=False))
                keep = np.zeros_like(keep)
                keep[ki] = True
            seg = [r * nb for r in range(1, R)]
            prof = INS.instrument_numbers({"activity": X[:, keep], "dt": INS.SPIKE_BIN_S, "segments": seg},
                                          "spikes")
            del X
            row = {"id": uid, "rank": rank, "code": CODE_STATE, "dandiset": ds, "repeats": R, "bins": nb, "units": int(keep.sum()), "units_cached": N,
                   "profile": {k: prof.get(k) for k in KEYS}, **measures(Y[:, :, keep]),
                   "split": split_halves(Y[:, :, keep]),
                   "extras": M.unit_internal_shares(Y[:, :, keep]), "dry": dry, "frozen": frozen()}
        except Exception as e:  # noqa: BLE001
            row = {"id": uid, "error": f"{type(e).__name__}: {e}"}
        if "error" not in row and not dry:                # amendment S1 (S-R3 N5): sensitivities fail alone
            try:                                          # S-R2 finding 11: behaviour regressed out
                Bh = D.behaviour(a, z["starts"], z["stops"], nb)
                Yr_, r2 = D.regress_out(Y[:, :, keep], Bh)
                row["behaviour_removed"] = {**{k_: v_ for k_, v_ in M.lag_measures(Yr_, k0=K0).items()
                                               if k_ in PRIMARY}, "median_r2": r2,
                                            "signals": int(np.isfinite(Bh).all((0, 1)).sum())}
            except Exception as e:  # noqa: BLE001
                row["behaviour_error"] = f"{type(e).__name__}: {e}"
            if ds == "000022":                            # validity check: the shuffled movie (SLOW.md 7)
                try:
                    Ys = D.movie_counts(D.movie_cache(a, shuffled=True))
                    row["shuffled"] = {**measures(Ys[:, :, keep]), "repeats": int(Ys.shape[0])}
                except Exception as e:  # noqa: BLE001
                    row["shuffled_error"] = f"{type(e).__name__}: {e}"
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
    # amendment S6: a mouse whose timescale on the movie cannot be measured (the map study's instrument
    # function returns NaN bins per timescale, with a white share of 0.97 to 1.0) has no instrument to match
    # an AI to; it is left out of every AI comparison and reported
    rows = [r for r in rows if r["profile"].get("bins_per_tau") is not None
            and np.isfinite(r["profile"]["bins_per_tau"])]
    bpt = np.array([r["profile"]["bins_per_tau"] for r in rows])
    edges = np.quantile(bpt, np.linspace(0, 1, N_GROUPS + 1))
    for i, r in enumerate(rows):                       # instance from the fixed session order (finding 15)
        r["instance"] = r.get("rank", i) % 3
        r["group"] = int(np.clip(np.searchsorted(edges, r["profile"]["bins_per_tau"], side="right") - 1, 0,
                                 N_GROUPS - 1))
    med = {g: float(np.median([r["profile"]["bins_per_tau"] for r in rows if r["group"] == g]))
           for g in range(N_GROUPS)}
    return rows, med


def _subsample(keep_idx, n, seed):
    """S-R2 finding 10: the AI recording is cut to the mouse's number of included units (seeded)."""
    if n < len(keep_idx):
        keep_idx = np.sort(np.random.default_rng(seed).choice(keep_idx, n, replace=False))
    return keep_idx


def record_for_mouse_lite(A, starts, length, r, rng_seed):
    """As record_for_mouse, without the half-clip M1 (operational, SLOW_LOG "Speed"): for the H2 controls and
    the playback sensitivity, where the half-clip values are not reported."""
    return record_for_mouse(A, starts, length, r, rng_seed, halves=False)


def record_for_mouse(A, starts, length, r, rng_seed, halves=True):
    """One AI run at one mouse (amendment S4: streamed, `nematica.slow.stream.record_stream`): the mouse's
    number of repeats; silent units excluded; the spike model started from knobs set by the timescales and
    corrected on the recorded repeats until the instrument numbers are within tolerance of the mouse's; the
    mouse's inclusion rule scaled to the clip; then the mouse's number of units."""
    from nematica.slow import stream as ST
    R = r["repeats"]
    st = starts[:R]
    sil = M.silent_units(A)
    if sil.any():                                      # memory: copy only when something is removed
        A = A[:, ~sil]
    out = ST.record_stream(A, st, length, r["profile"], nb_mouse=int(r.get("bins", 1501)), R_mouse=R,
                           n_units_mouse=int(r.get("units", A.shape[1])), seed=rng_seed, halves=halves)
    if "error" in out:
        raise RuntimeError(out["error"])
    Yn = np.stack([np.asarray(A[s:s + length, :100]) for s in st])     # extras on 100 units (memory)
    return {**out, "extras": M.unit_internal_shares(Yn), "method": "stream"}


def lif_for_mouse(A, starts, length, r, rng_seed):
    """A4: recorded like a mouse (SLOW.md section 5): 20 ms bins of its own spikes, thinned to the mouse's
    spikes per bin (thinning probability from the included neurons), the mouse's inclusion rule, then the
    mouse's number of units (S-R2 findings 10, 15)."""
    if r.get("rtype") == "calcium":
        return record_for_mouse(A, starts, length, r, rng_seed)
    R = r["repeats"]
    nb = length // 4                                   # 4 native 5 ms steps per 20 ms bin
    Y = np.stack([A[s:s + nb * 4].reshape(nb, 4, -1).sum(1) for s in starts[:R]])
    msp = Rc.scaled_min_spikes(nb, int(r.get("bins", 1501)))
    inc0 = keep_units(Y.reshape(-1, Y.shape[2]), nb, msp)
    med = float(np.median(Y[:, :, inc0].mean((0, 1)))) if inc0.any() else 1.0
    p = min(1.0, r["profile"]["count_per_bin"] / max(med, 1e-9))
    Y = np.random.default_rng(rng_seed).binomial(Y.astype(np.int64), p).astype(np.float32)
    idx = _subsample(np.flatnonzero(keep_units(Y.reshape(-1, Y.shape[2]), nb, msp)),
                     int(r.get("units", Y.shape[2])), rng_seed)
    Y = Y[:, :, idx]
    got = Rc.recorded_numbers(Y, min_spikes=msp)
    return {**measures(Y), "recorded_bins": int(nb), "repeats_used": int(Y.shape[0]), "units_used": int(len(idx)),
            "thin_p": p, "numbers_on_repeats": {x: got.get(x) for x in r["profile"]},
            "reached": bool(len(idx) >= int(r.get("units", 0))),   # not matched; units must suffice (S1)
            "extras": M.unit_internal_shares(Y)}


def keep_for(spf):
    """Memory (S-R1 finding 11) and S-R2 finding 18: A1 activity is kept as block means so that every playback
    group has about 5 kept samples per 20 ms bin (0.6 frames per bin). Block means are not a pure clock change
    (the spike model's nonlinearity acts on the means): at the median group, M1 read 0.212 at 10 samples per
    bin, 0.201 at 5 and 0.171 at 2.6; holding the samples per bin equal keeps the family the same system in
    every group (SLOW_LOG, "Block means")."""
    return max(1, int(round(spf * 0.6 / 5)))


@functools.lru_cache(maxsize=3)
def a1_tau(inst):
    """Finding 16: the undriven A1 native timescale, measured per instance (8,000 steps)."""
    from nematica.map import zoo, measures as MM
    return float(MM.tau_med(zoo.random_rnn(n=480, steps=8000, seed=inst)[0]))


def a1_run(feat, R, inst, bpt, gain=None, mult=1.0, tau=None, **kw):
    """One movie-driven A1 run at the playback for a mouse timescale `bpt` (times `mult`), block-mean kept."""
    spf = I.steps_per_frame(tau or a1_tau(inst), bpt) * mult
    return I.driven_random_rnn(feat, R=R, n=480, gain=BALANCED_GAIN if gain is None else gain, spf=spf, seed=inst,
                               keep_every=keep_for(spf), **kw)[:2]


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
                       lambda ms=ms, gain=gain, g=g, inst=inst: a1_run(feat, Rmax(ms), inst, med[g], gain=gain))
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
    # language models last, model by model, so each large model is downloaded, used for its instances and
    # removed before the next (amendment S1, review S-R3 B2: disk)
    for fam, model in LMS:
        for inst in range(3):
            ms = [r for r in rows if r["instance"] == inst]
            yield (fam, f"{model.format(s=inst + 1).split('/')[-1]}-i{inst}", ms, record_for_mouse,
                   lambda ms=ms, inst=inst, model=model: gen_lm(model, inst, prof, Rmax(ms)))


PLAY_GAIN = 0.25          # S-R2 finding 4: the playback check needs an A1 with an internal part (M1 about 0.35)


def sensitivity_families(rows, med):
    """S-R1 finding 5 / S-R2 finding 4: playback sensitivity for A1 at gain 0.25 (x0.5, x2, and playback from
    the driven timescale). S-R1 finding 7 / S-R2 finding 8: H2's negative controls, each with 8 grid points
    like the slow drive: a fast drive (share x 1 or 2 frames) and more network noise (noise x gain)."""
    feat = I.movie_features()
    for inst in range(3):
        for g in range(N_GROUPS):
            ms = [r for r in rows if r["instance"] == inst and r["group"] == g]
            if not ms:
                continue
            R = max(m["repeats"] for m in ms)
            for mult in (0.5, 2.0):
                yield ("A1-play", f"i{inst}-g{g}-x{mult}", ms, record_for_mouse_lite,
                       lambda R=R, mult=mult, inst=inst, g=g: a1_run(feat, R, inst, med[g], gain=PLAY_GAIN, mult=mult))

            def driven_rule(R=R, inst=inst, g=g):
                from nematica.map import measures as MM
                A, _, _ = I.driven_random_rnn(feat, R=2, n=480, gain=PLAY_GAIN,
                                              spf=I.steps_per_frame(a1_tau(inst), med[g]), seed=inst)
                return a1_run(feat, R, inst, med[g], gain=PLAY_GAIN, tau=float(MM.tau_med(A)))
            yield ("A1-play", f"i{inst}-g{g}-driven", ms, record_for_mouse_lite, driven_rule)
            for share in SLOW_SHARES:
                for frames in FAST_FRAMES:
                    def fast(R=R, inst=inst, g=g, share=share, frames=frames):
                        spf_ = I.steps_per_frame(a1_tau(inst), med[g])
                        A, st = _a1_base(inst, g, R, spf_)
                        return I.add_slow_drive(A, share, tau_steps=frames * spf_ / keep_for(spf_), seed=inst), st
                    yield ("A1-fast", f"i{inst}-g{g}-share{share}-tau{frames}f", ms, record_for_mouse_lite, fast)
            for gain in NOISE_GAINS:
                for noise in NOISES:
                    yield ("A1-noise", f"i{inst}-g{g}-share{noise}-tau{gain}g", ms, record_for_mouse_lite,
                           lambda R=R, inst=inst, g=g, noise=noise, gain=gain: a1_run(feat, R, inst, med[g],
                                                                                     gain=gain, noise=noise))


BALANCED_GAIN = 0.86                                  # movie input as strong as recurrent input (SLOW_LOG F2)
SLOW_SHARES = (0.1, 0.2, 0.3, 0.5)                    # H2 grids, 8 points each (SLOW.md section 7)
SLOW_TAUS_S = (1.0, 3.0)
FAST_FRAMES = (1, 2)
NOISES = (0.2, 0.4, 0.8, 1.6)
NOISE_GAINS = (0.25, 0.86)


@functools.lru_cache(maxsize=1)
def _a1_base(inst, g, R, spf):
    return I.driven_random_rnn(I.movie_features(), R=R, n=480, gain=BALANCED_GAIN, spf=spf, seed=inst,
                               keep_every=keep_for(spf))[:2]


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
                        return I.add_slow_drive(A, share, tau_steps=tau_s * 30 * spf / keep_for(spf), seed=inst), st
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
    import shutil
    free = shutil.disk_usage(ROOT).free / 1e9
    if free < 3.0:
        raise RuntimeError(f"only {free:.1f} GB free; a language model needs up to about 3 GB")
    n = clip_units(mk, prof, 300)
    out = (*mk(n, R), n)
    if "{s}" in model or inst == 2:                    # last use of this download
        drop_model_cache(name)
    return out


DROP_AFTER_USE = ("pythia-160m", "pythia-410m", "pythia-1b", "mamba-130m", "mamba-370m")


def drop_model_cache(name):
    """Remove a downloaded model from the local Hugging Face cache after its last use (amendment S1: disk).
    Only the large models this study downloads; the small Pythia-14m files stay."""
    import os
    import shutil
    if not any(x in name for x in DROP_AFTER_USE):
        return
    d = Path.home() / ".cache/huggingface/hub" / ("models--" + name.replace("/", "--"))
    if not d.exists():
        return
    for snap in d.glob("snapshots/*/*"):
        tgt = Path(os.path.realpath(snap))
        if tgt.exists() and tgt.is_file():
            tgt.unlink()
    shutil.rmtree(d)


def fixed_mice_table(dry=False):
    """Amendment S1 (S-R3 N11): the mouse table (instance, playback group, group medians) is written once,
    after the mice stage has covered every session, and every later AI or test run must agree with it."""
    rows, med = mice_table(dry)
    f = OUT / (CFG["prefix"] + ("mice_table_dry.json" if dry else "mice_table.json"))
    tab = {"rows": {r["id"]: [r["instance"], r["group"]] for r in rows}, "med": {str(k): v for k, v in med.items()}}
    if not dry and CFG["prefix"] == "":
        seen = {k[0] for k in done("mice.jsonl", ("id",))} | {
            r["id"] for r in map(json.loads, (OUT / "mice.jsonl").read_text().splitlines()) if "error" in r}
        if len(seen) < 58:
            sys.exit(f"the mice stage has covered {len(seen)} of 58 sessions; finish it first")
    if f.exists():
        old = json.loads(f.read_text())
        if old != json.loads(json.dumps(tab)):
            sys.exit(f"{f.name} differs from the current mouse table; the mice stage changed after AI runs began")
    else:
        f.write_text(json.dumps(tab, indent=1))
    return rows, med


RETRY_ROUNDS = 10


def stage_retry(only=None):
    """Amendment S7: every AI recording that missed the instrument tolerance is recorded once more, starting
    from its own best knobs, with up to RETRY_ROUNDS corrections and a new spike seed. The retry row replaces
    the original in the tests (whatever its outcome); both are kept on disk."""
    import os
    from nematica.slow import stream as ST
    rows, med = fixed_mice_table()
    mice = {r["id"]: r for r in rows}
    ais = [r for f in sorted(OUT.glob("ais*.jsonl")) if "_dry" not in f.name and "retry" not in f.name
           for r in map(json.loads, f.read_text().splitlines()) if "error" not in r and r["id"] in mice]
    have = done("ais_retry.jsonl", ("family", "run", "id"))
    todo = {}
    for r in ais:
        if not r.get("reached") and (r["family"], r["run"], r["id"]) not in have:
            todo.setdefault((r["family"], r["run"]), []).append(r)
    shard = os.environ.get("SLOW_SHARD")
    si, sn = (int(x) for x in shard.split("/")) if shard else (0, 1)
    fams = itertools.chain(families(rows, med), slow_families(rows, med), sensitivity_families(rows, med))
    for fam, run, ms, rec, gen in fams:
        if (fam, run) not in todo or (only and fam not in only):
            continue
        if shard and zlib.crc32(f"{fam}|{run}".encode()) % sn != si:
            continue
        res = gen()
        A, starts = res[0], res[1]
        length = res[2] if len(res) > 2 else starts[1] - starts[0]
        del res
        for old in todo[(fam, run)]:
            m = mice[old["id"]]
            try:
                Ax = A[:, ~M.silent_units(A)] if M.silent_units(A).any() else A
                k0 = {x: v for x, v in old["knobs"].items() if x in ("hold", "bin_steps", "mean_count", "gain",
                                                                      "rate_log_sd")}
                out = ST.record_stream(Ax, starts[:m["repeats"]], length, m["profile"], nb_mouse=int(m.get("bins", 1501)),
                                       R_mouse=m["repeats"], n_units_mouse=int(m["units"]),
                                       seed=zlib.crc32(("retry" + run).encode()) % 2**31, rounds=RETRY_ROUNDS,
                                       k_start=k0)
                if "error" in out:
                    raise RuntimeError(out["error"])
                Yn = np.stack([np.asarray(Ax[s:s + length, :100]) for s in starts[:m["repeats"]]])
                row = {"family": fam, "run": run, "id": m["id"], "instance": m["instance"],
                       "group": m["group"] if fam in PLAYBACK_FAMS else None, "code": CODE_STATE, "retry": True,
                       **out, "extras": M.unit_internal_shares(Yn), "method": "stream"}
            except Exception as e:  # noqa: BLE001
                row = {"family": fam, "run": run, "id": m["id"], "retry": True, "error": f"{type(e).__name__}: {e}"}
            append("ais_retry.jsonl", row)
            print("retry", fam, run, m["id"], row.get("reached"), row.get("error"), flush=True)
        del A


def stage_ais(only=None, dry=False):
    rows, med = fixed_mice_table(dry)
    # sharding (operational, results unchanged): SLOW_SHARD="i/n" runs only generator runs whose label
    # hashes to i mod n, writing to its own file; every ais*.jsonl file is read back together
    import os
    shard = os.environ.get("SLOW_SHARD")
    si, sn = (int(x) for x in shard.split("/")) if shard else (0, 1)
    base = CFG["prefix"] + ("ais_dry" if dry else "ais")
    name = base + (f"_shard{si}of{sn}.jsonl" if shard else ".jsonl")
    have = set()
    for f in OUT.glob(base + "*.jsonl"):
        if dry or "_dry" not in f.name:
            have |= done(f.name, ("family", "run", "id"))
    n_gen = 0
    fams = itertools.chain(families(rows, med, gains=(0.25,) if dry else GAINS), slow_families(rows, med),
                           sensitivity_families(rows, med))
    for fam, run, ms, rec, gen in fams:
        if dry and n_gen >= 2:
            break
        if only and fam not in only:
            continue
        if shard and zlib.crc32(f"{fam}|{run}".encode()) % sn != si:
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
        del res
        for m in todo:
            try:
                row = {"family": fam, "run": run, "id": m["id"], "instance": m["instance"],
                       "group": m["group"] if fam in PLAYBACK_FAMS else None, "code": CODE_STATE,
                       **rec(A, starts, length, m, rng_seed=zlib.crc32(run.encode()) % 2**31)}
            except Exception as e:  # noqa: BLE001
                row = {"family": fam, "run": run, "id": m["id"], "error": f"{type(e).__name__}: {e}"}
            append(name, row)
            print(fam, run, m["id"], {k: row.get(k) for k in ("M1", "M2", "error")}, flush=True)
        del A


# ------------------------------------------------------------------------------------------------ tests
SPLIT_SEED = 2026
MAX_MISSING = 0.25
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
    """M1 as it is, unless there is no shared covariance at lag k0 at all ('no shared part', S-R2 finding 19:
    excluded rather than counted as 0). M2 on a log scale, only where there is an internal part (M1 >= 0.05)
    and a locked part to time it against ('no locked part', S-R1 finding 13). Returns (value or None, code)."""
    if row.get("no_shared"):
        return None, "no shared part"
    if meas == "M1":
        return row.get("M1"), "ok"
    if row.get("M1") is None or row["M1"] < 0.05:
        return None, "no internal part"
    if row.get("no_locked"):
        return None, "no locked part"
    m2 = row.get("M2")
    if m2 is None or not np.isfinite(m2) or m2 <= 0:
        return None, "no internal part"
    return float(np.log(m2)), "ok"


def _pair(mouse, ai_rows, meas):
    """S-R1 finding 2: the bracket rule over the family's runs that have a value. d = 0 if the mouse lies
    within their range, else mouse minus the nearer end. Ceilings on M2 (S-R1 finding 4, S-R2 finding 12): a
    mouse at internal ceiling against a family with a run at ceiling is a tie; a pair whose nearer AI run is
    at internal ceiling while the mouse lies above it, or where either side's locked time is at ceiling, is
    censored (excluded and counted)."""
    mv, mcode = _value(mouse, meas)
    if mv is None:
        return None, "mouse " + mcode
    ok = [(v, r) for v, r in ((_value(r, meas)[0], r) for r in ai_rows) if v is not None]
    if not ok:
        codes = {_value(r, meas)[1] for r in ai_rows}
        for c in ("no shared part", "no locked part"):
            if codes == {c}:
                return None, c
        return None, "no internal part"
    if meas == "M2":
        if mouse.get("int_ceiling") and any(r.get("int_ceiling") for _, r in ok):
            return 0.0, "ceiling tie"
        if mouse.get("lock_ceiling") or any(r.get("lock_ceiling") for _, r in ok):
            return None, "censored"
    lo, hi = min(v for v, _ in ok), max(v for v, _ in ok)
    if lo <= mv <= hi:
        return 0.0, "ok"
    end_v, end_r = max(ok, key=lambda x: x[0]) if mv > hi else min(ok, key=lambda x: x[0])
    if meas == "M2" and mv > hi and end_r.get("int_ceiling"):
        return None, "censored"
    return mv - end_v, "ok"


# S-R2 findings 6 and 9: known mouse-AI biases from the pre-freeze calibration, in measure units (M1; log M2):
# spike type (up to 0.075 in M1 at share 0.3; up to 0.5 in log M2), short recorded clips (M1 -0.03 to -0.04 at
# about 570 bins; log M2 -0.33 at 218 bins). A gap must exceed both 0.5 ruler units and this bound.
BIAS_BOUND = {"M1": 0.10, "M2": 0.5}


def _verdict(d, cells, ruler, bound=0.0):
    """Finding 6, as revised after a synthetic check of this code (SLOW_LOG): with only 3 instances for most
    families a sign test over cells can never reach p < 0.05, so the test is done within each instance
    (pairs within an instance share AI runs but differ in mice) and must hold in every instance."""
    du = np.asarray(d, float) / ruler
    cells = np.asarray(cells)
    inst = np.asarray([str(c).split("|")[0] for c in cells])
    per = {i: (_wilcoxon(du[inst == i], "greater"), _wilcoxon(du[inst == i], "less")) for i in np.unique(inst)}
    p_gap, p_rev = _wilcoxon(du, "greater"), _wilcoxon(du, "less")
    md = float(np.median(du))
    ci = _cluster_ci(du, cells)
    margin = max(0.5, bound / ruler) if ruler and np.isfinite(ruler) else 0.5
    full = len(per) == 3                               # amendment S1 (S-R3 N9): all 3 instances must be present
    all_gap = full and all(np.isfinite(g) and g < 0.05 for g, _ in per.values())
    all_rev = full and all(np.isfinite(r) and r < 0.05 for _, r in per.values())
    if p_gap < 0.05 and all_gap and md > margin and ci[0] > 0:
        v = "confirmed"
    elif p_rev < 0.05 and all_rev and md < -margin and ci[1] < 0:
        v = "refuted"
    else:
        v = "not decided"
    return {"verdict": v, "n_pairs": int(len(du)), "n_cells": int(len(np.unique(cells))), "median_d_ruler": md,
            "p_gap": p_gap, "p_reverse": p_rev, "per_instance_p": {k: list(v_) for k, v_ in per.items()},
            "cluster_ci90": ci, "margin_ruler": margin}


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
            cells.append(f"{rows_m[0].get('instance')}|{rows_m[0].get('group')}")    # S-R2 finding 3
    n = len(d) + sum(v for k, v in codes.items() if k in ("no internal part", "no locked part", "no shared part"))
    res = {"codes": codes, "missing": missing}
    n_all = len(mice)
    if n_all and missing > MAX_MISSING * n_all:        # S-R2 finding 14
        return {**res, "verdict": "not testable (missing pairs)"}
    if n and codes.get("no shared part", 0) > n / 2:
        return {**res, "verdict": "no shared part"}
    if meas == "M2" and n and codes.get("no internal part", 0) > n / 2:
        return {**res, "verdict": "no internal part"}
    if meas == "M2" and n and codes.get("no locked part", 0) > n / 2:
        return {**res, "verdict": "no locked part"}
    if len(d) < 6:
        return {**res, "verdict": "too few pairs", "n_pairs": len(d)}
    return {**res, **_verdict(d, cells, ruler, BIAS_BOUND[meas])}


def stage_tests(dry=False):
    pre = CFG["prefix"]
    mice = {r["id"]: r for r in fixed_mice_table(dry)[0]}   # with instance and playback group
    ais = [r for f in sorted(OUT.glob(pre + ("ais_dry" if dry else "ais") + "*.jsonl"))
           if (dry or "_dry" not in f.name) and "retry" not in f.name
           for r in map(json.loads, f.read_text().splitlines()) if "error" not in r and r["id"] in mice]
    rf = OUT / (pre + "ais_retry.jsonl")                # amendment S7: a retry replaces its original
    if rf.exists() and not dry:
        rt = {(r["family"], r["run"], r["id"]): r for r in map(json.loads, rf.read_text().splitlines())}
        ais = [rt.get((r["family"], r["run"], r["id"]), r) for r in ais]
        ais = [r for r in ais if "error" not in r]
    ok_ais = [r for r in ais if r.get("reached", True)]  # amendment S1 (S-R3 N7): reached instruments only
    out = {"frozen": frozen(), "code": CODE_STATE, "n_mice": len(mice), "H1": {}, "H2": {}, "H3": {}}
    rulers = {meas: _ruler([_value(m, meas)[0] for m in mice.values()]) for meas in ("M1", "M2")}
    out["rulers"] = rulers

    # validity check of M2 (finding 9): locked time falls, M2 rises, and the internal time moves less than
    # the locked time does
    sh = [m for m in mice.values() if "shuffled" in m]
    valid_m2 = False                                   # amendment S1 (S-R3 N4): no shuffled data, no check
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
                base = [r for r in ok_ais if r["id"] == mid and r["family"] == "A1" and r["run"].endswith(f"gain{PLAY_GAIN}")]
                alt = [r for r in ok_ais if r["id"] == mid and r["family"] == "A1-play" and r["run"].endswith(var)]
                if base and alt and _value(base[0], meas)[0] is not None and _value(alt[0], meas)[0] is not None:
                    dd.append((_value(alt[0], meas)[0] - _value(base[0], meas)[0]) / rulers[meas])
            nuis[f"{var}|{meas}"] = {"n": len(dd), "median_shift_ruler": float(np.median(dd)) if dd else None}
    out["nuisance_playback"] = nuis
    playback_sensitive = {meas: any(v["median_shift_ruler"] is not None and abs(v["median_shift_ruler"]) >= 0.5
                                    for k, v in nuis.items() if k.endswith("|" + meas)) for meas in ("M1", "M2")}
    out["nuisance_playback_M2_sensitive"] = playback_sensitive

    for fam, need in RUNS_PER_FAMILY.items():
        out["H1"][fam] = {meas: _family_test(mice, ais, fam, meas, rulers[meas], need) for meas in ("M1", "M2")}
        # reported, not counted: M2 with AI runs restricted to M1 at least 0.2 (C1 cross-talk, SLOW.md 7)
        out["H1"][fam]["M2_ai_m1_ge_0.2"] = {**_family_test(mice, ais, fam, "M2", rulers["M2"], need, 0.2),
                                             "counted": False}
    for fam in ("A1", "A4"):                           # movie-driven families: a measure is set aside if
        for meas in ("M1", "M2"):                      # playback moves it by 0.5 ruler units or more
            if playback_sensitive[meas]:
                out["H1"][fam][meas]["counted"] = False
    for fam in RUNS_PER_FAMILY:
        for meas in ("M1", "M2"):
            if not rel[meas]["reliable"]:                # C3 failure: the measure is not tested
                out["H1"][fam][meas]["counted"] = False
    # S-R2 finding 7: one verdict per claim item (SLOW.md section 7)
    fams = list(RUNS_PER_FAMILY)
    noisy, deterministic = ["A1", "A4"], ["A2", "A3", "A5", "A6", "A7"]
    cnt = lambda f, m: out["H1"][f][m].get("counted", True)
    v = lambda f, m: out["H1"][f][m].get("verdict")
    c1 = {"confirmed": [f for f in fams if v(f, "M1") == "confirmed" and cnt(f, "M1")],
          "refuted": [f for f in fams if v(f, "M1") == "refuted" and cnt(f, "M1")]}
    c1["holds"] = len(c1["confirmed"]) >= 5 and not c1["refuted"]
    c1["noisy_confirmed"] = [f for f in noisy if f in c1["confirmed"]]
    c1["deterministic_confirmed"] = [f for f in deterministic if f in c1["confirmed"]]
    testable = [f for f in fams if v(f, "M2") in ("confirmed", "refuted", "not decided") and cnt(f, "M2")]
    c2 = {"testable": testable, "confirmed": [f for f in testable if v(f, "M2") == "confirmed"],
          "refuted": [f for f in testable if v(f, "M2") == "refuted"], "validity_check_passed": valid_m2}
    c2["holds"] = bool(valid_m2 and len(testable) >= 3 and len(c2["confirmed"]) * 3 >= len(testable) * 2
                       and not c2["refuted"])
    if not valid_m2:
        c2["status"] = "not assessable: the shuffled-movie check failed"
    out["claims"] = {"1_more_internal_state": c1, "2_slower_relative_to_input": c2}
    # S-R2 finding 11: the same family tests with each mouse's values after behaviour is regressed out
    mice_b = {mid: {**m, **m["behaviour_removed"]} for mid, m in mice.items() if "behaviour_removed" in m}
    if len(mice_b) >= 6:                               # amendment S1 (S-R3 N6): the same rules and flags
        rb = {meas: _ruler([_value(m, meas)[0] for m in mice_b.values()]) for meas in ("M1", "M2")}
        hb = {f: {meas: {**_family_test(mice_b, ais, f, meas, rb[meas], need),
                         "counted": out["H1"][f][meas].get("counted", True)} for meas in ("M1", "M2")}
              for f, need in RUNS_PER_FAMILY.items()}
        out["H1_behaviour_removed"] = hb
        vb = lambda f, m: hb[f][m].get("verdict")
        cb = lambda f, m: hb[f][m].get("counted", True)
        conf_b = [f for f in fams if vb(f, "M1") == "confirmed" and cb(f, "M1")]
        ref_b = [f for f in fams if vb(f, "M1") == "refuted" and cb(f, "M1")]
        c1["holds_with_behaviour_removed"] = bool(len(conf_b) >= 5 and not ref_b)
        tb = [f for f in fams if vb(f, "M2") in ("confirmed", "refuted", "not decided") and cb(f, "M2")]
        cfb = [f for f in tb if vb(f, "M2") == "confirmed"]
        c2["holds_with_behaviour_removed"] = bool(valid_m2 and len(tb) >= 3 and len(cfb) * 3 >= len(tb) * 2
                                                  and not any(vb(f, "M2") == "refuted" for f in tb))

    # H2 with negative controls (finding 7): each candidate tuned on the seeded half, tested on the other
    # S-R2 finding 8: hold out by generator cell, so tuning and test halves share no AI run
    cells_all = sorted({f"{m['instance']}|{m['group']}" for m in mice.values()})
    train_cells = set(np.random.default_rng(SPLIT_SEED).permutation(cells_all)[: len(cells_all) // 2])
    half = {mid for mid, m in mice.items() if f"{m['instance']}|{m['group']}" in train_cells}

    def tune_test(fam, key):
        rows = [r for r in ok_ais if r["family"] == fam]
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
                 "control_noise": tune_test("A1-noise", "-share"), "split": "by generator cell",
                 "train_cells": sorted(train_cells)}
    if out["H2"]["slow"]:
        ctrl_fail = all(c is not None and not c["equivalent_both"]
                        for c in (out["H2"]["control_fast"], out["H2"]["control_noise"]))
        out["H2"]["confirmed"] = bool(out["H2"]["slow"]["equivalent_both"] and ctrl_fail)

    # H3 (finding 18): on M1, the median over mice of how much closer Pythia 1B is than Pythia 14M
    diffs, cells = [], []
    for mid, m in mice.items():
        mv, _ = _value(m, "M1")
        a14 = [r for r in ok_ais if r["id"] == mid and r["family"] == "A6" and "pythia-14m" in r["run"]]
        a1b = [r for r in ok_ais if r["id"] == mid and r["family"] == "A6" and "pythia-1b" in r["run"]]
        if mv is None or not a14 or not a1b:
            continue
        v14, v1b = _value(a14[0], "M1")[0], _value(a1b[0], "M1")[0]   # S-R3 N7: codes as in H1
        if v14 is None or v1b is None:
            continue
        diffs.append((abs(mv - v14) - abs(mv - v1b)) / rulers["M1"])
        cells.append(a14[0]["run"].split("-i")[-1])
    if len(diffs) >= 6:
        ci = _cluster_ci(diffs, cells)
        out["H3"] = {"measure": "M1", "n_pairs": len(diffs), "median_closer_by_1b_ruler": float(np.median(diffs)),
                     "cluster_ci90": ci, "confirmed": bool(ci[1] < 0.5)}
    out["claims"]["3_slow_drive_closes_gap_controls_do_not"] = {"holds": bool(out["H2"].get("confirmed"))}
    out["claims"]["4_scale_does_not"] = {"holds": bool(out["H3"].get("confirmed"))}
    name = pre + ("tests_dry.json" if dry else "tests.json")
    (OUT / name).write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v_.get("holds") for k, v_ in out["claims"].items()}), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["mice", "ais", "retry", "tests"])
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
    elif a.stage == "retry":
        stage_retry(only=a.only)
    else:
        stage_tests(dry=a.dry)


if __name__ == "__main__":
    main()
