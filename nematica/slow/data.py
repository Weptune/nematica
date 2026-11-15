"""Study 2 mouse data: Allen Visual Coding Neuropixels spikes during natural_movie_one (docs/SLOW.md, section 4).

Third-party data rule: everything downloaded stays in data/cache/allen_movie (git-ignored); only summary
numbers are committed. Units are the map study's (amendment 24): Allen `quality == good`, at most 2,400 per
session, the same seeded subset (nematica.map.data._allen_cache), so the QC mask of amendment 25 applies
unchanged. Spike times are stored per unit as uint16 milliseconds from the start of the repeat they fall in
(a repeat lasts about 30.0 s, under 65,535 ms), with a uint8 repeat number.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..map import data as mdata

CACHE = Path(__file__).resolve().parents[2] / "data/cache/allen_movie"
# natural_movie_one is named differently in the two dandisets (checked on the stimulus tables, SLOW_LOG
# 20:00); the shuffled version (functional_connectivity sessions only) is one fixed permutation of the same
# frames, identical on every repeat and in every session (Allen, community forum thread 1010)
MOVIE = ("natural_movie_one_presentations", "natural_movie_one_more_repeats_presentations")
SHUFFLED = ("natural_movie_one_shuffled_presentations",)
BIN_S = 0.02
FRAMES = 900


def _stim(h, names):
    for k in names:
        if k in h["intervals"]:
            return k
    raise KeyError(f"none of {names} in this session")


def _repeats(h, names=MOVIE):
    """Start time of every repeat (frame 0) and the end of its last frame, in session seconds, after removing
    any repeat that overlaps an invalid interval. Returns (starts, stops, dropped)."""
    g = h[f"intervals/{_stim(h, names)}"]
    st, en, fr = g["start_time"][:], g["stop_time"][:], np.asarray(g["frame"][:]).astype(int)
    o = np.argsort(st, kind="stable")
    st, en, fr = st[o], en[o], fr[o]
    first = np.flatnonzero(fr == 0)
    starts, stops = [], []
    for i in first:
        j = i + FRAMES - 1
        if j < len(fr) and fr[j] == FRAMES - 1:
            starts.append(float(st[i]))
            stops.append(float(en[j]))
    inv = []
    if "invalid_times" in h["intervals"]:
        it = h["intervals/invalid_times"]
        inv = list(zip(it["start_time"][:], it["stop_time"][:]))
    keep = [k for k, (a, b) in enumerate(zip(starts, stops)) if not any(x < b and y > a for x, y in inv)]
    return np.asarray(starts)[keep], np.asarray(stops)[keep], len(starts) - len(keep)


def movie_cache(a, max_units=mdata.ALLEN_MAX_UNITS, shuffled=False):
    """Download one session's spikes during natural_movie_one (or its shuffled version) once and keep them
    locally."""
    import h5py
    import requests
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (a["path"].split("/")[0] + ("_shuffled" if shuffled else "") + ".npz")
    if f.exists():
        return np.load(f, allow_pickle=False)
    url = f"{mdata.DANDI}/assets/{a['asset_id']}/download/"
    with h5py.File(mdata.open_url(url), "r") as h:
        starts, stops, dropped = _repeats(h, SHUFFLED if shuffled else MOVIE)
        idx = np.asarray(h["units/spike_times_index"][:], np.int64)
        q = h["units/quality"][:]
        st = h["units/spike_times"]
        off, n = st.id.get_offset(), st.shape[0]
        assert st.chunks is None and st.compression is None and st.dtype == np.float64
    good = np.flatnonzero(np.asarray([x in (b"good", "good") for x in q]))
    n_good = len(good)
    if len(good) > max_units:                          # the map study's subset (same seed and call)
        good = np.sort(np.random.default_rng(0).choice(good, max_units, replace=False))
    s3 = requests.head(url, allow_redirects=True, timeout=60).url
    T = np.frombuffer(mdata._fetch_range(s3, off, n * 8), np.float64)
    first = np.concatenate([[0], idx[:-1]])
    assert len(starts) <= 255
    ms, rep, ptr = [], [], [0]
    for u in good:
        tt = T[first[u]:idx[u]]
        for r, (a0, b0) in enumerate(zip(starts, stops)):
            sel = tt[(tt >= a0) & (tt < b0)]
            ms.append(np.floor((sel - a0) * 1000).astype(np.uint16))
            rep.append(np.full(len(sel), r, np.uint8))
        ptr.append(ptr[-1] + sum(len(x) for x in ms[-len(starts):]))
    np.savez_compressed(f, ms=np.concatenate(ms) if ms else np.zeros(0, np.uint16),
                        rep=np.concatenate(rep) if rep else np.zeros(0, np.uint8), ptr=np.asarray(ptr, np.int64),
                        starts=starts, stops=stops, dropped=dropped, units=good, n_good=n_good)
    return np.load(f, allow_pickle=False)


def movie_counts(z, n_bins=None):
    """(R, n_bins, units) spike counts in 20 ms bins from each repeat's start. n_bins defaults to the
    whole bins in the shortest repeat (1,500 for a 30.0 s clip)."""
    dur = np.min(z["stops"] - z["starts"])
    nb = n_bins or int(np.floor(dur / BIN_S + 1e-9))
    R, N = len(z["starts"]), len(z["ptr"]) - 1
    Y = np.zeros((R, nb, N), np.uint8)
    ms, rep, ptr = z["ms"], z["rep"], z["ptr"]
    for j in range(N):
        b = (ms[ptr[j]:ptr[j + 1]] // int(BIN_S * 1000)).astype(np.int64)
        r = rep[ptr[j]:ptr[j + 1]].astype(np.int64)
        ok = b < nb
        np.add.at(Y[:, :, j], (r[ok], b[ok]), 1)
    return Y


def sessions():
    """The 58 sessions (one per mouse), in the map study's order."""
    for ds in mdata.ALLEN_DANDISETS:
        for a in sorted((x for x in mdata.dandi_assets(ds) if "probe" not in x["path"]), key=lambda x: x["path"]):
            yield ds, a


# ---------------------------------------------------------------- replication: Allen Visual Coding two-photon
TWOP_MANIFEST = Path(__file__).resolve().parents[2] / "data/external/allen2p/ophys_experiments.json"
TWOP_URL = "https://allen-brain-observatory.s3.amazonaws.com/visual-coding-2p/ophys_experiment_data/{}.nwb"
TWOP_CACHE = Path(__file__).resolve().parents[2] / "data/cache/allen2p_movie"
TWOP_DFF = "processing/brain_observatory_pipeline/DfOverF/imaging_plane_1"


def twop_experiments():
    """One session-A experiment per mouse (SLOW.md section 4): the mouse's VISp experiment if it has one,
    else its lowest experiment id; in order of specimen id."""
    import json
    e = [x for x in json.loads(TWOP_MANIFEST.read_text()) if x["stimulus_name"] == "three_session_A"]
    by = {}
    for x in e:
        by.setdefault(x["specimen_id"], []).append(x)
    out = []
    for sid in sorted(by):
        xs = sorted(by[sid], key=lambda x: x["id"])
        visp = [x for x in xs if x["targeted_structure"]["acronym"] == "VISp"]
        out.append((visp or xs)[0])
    return out


def twop_movie(exp):
    """dF/F of every cell at each natural_movie_one frame of each of the 10 repeats: (R, 900, cells), float16,
    the imaging frame at or after each movie frame's onset. Cached locally (third-party data)."""
    import h5py
    TWOP_CACHE.mkdir(parents=True, exist_ok=True)
    f = TWOP_CACHE / f"{exp['id']}.npz"
    if f.exists():
        return np.load(f, allow_pickle=False)["dff"]
    with h5py.File(mdata.open_url(TWOP_URL.format(exp["id"])), "r") as h:
        g = h["stimulus/presentation/natural_movie_one_stimulus"]
        fr = np.asarray(g["data"][:]).astype(int)
        ts = np.asarray(g["timestamps"][:])
        img_t = np.asarray(h[f"{TWOP_DFF}/timestamps"][:])
        D_ = h[f"{TWOP_DFF}/data"]
        first = np.flatnonzero(fr == 0)
        reps = [i for i in first if i + FRAMES <= len(fr) and fr[i + FRAMES - 1] == FRAMES - 1]
        idx = np.stack([np.searchsorted(img_t, ts[i:i + FRAMES]) for i in reps])     # R x 900 imaging frames
        idx = np.clip(idx, 0, len(img_t) - 1)
        lo, hi = int(idx.min()), int(idx.max()) + 1
        X = np.asarray(D_[:, lo:hi], np.float32)                                     # cells x span
    out = np.transpose(X[:, idx - lo], (1, 2, 0)).astype(np.float16)                 # R x 900 x cells
    np.savez_compressed(f, dff=out, idx=idx)
    return out


def unit_meta(a, units):
    """Review S-R1 finding 3: per cached unit, its brain area (the location of its peak channel) and Allen's
    default QC (isi_violations < 0.5, amplitude_cutoff < 0.1, presence_ratio > 0.9, as amendment 25 of the
    map study). Metadata only; cached locally. Returns (areas as str array, qc bool array) in cache order."""
    import h5py
    f = CACHE / (a["path"].split("/")[0] + "_meta.npz")
    if f.exists():
        z = np.load(f, allow_pickle=False)
        return z["area"], z["qc"]
    CACHE.mkdir(parents=True, exist_ok=True)
    with h5py.File(mdata.open_url(f"{mdata.DANDI}/assets/{a['asset_id']}/download/"), "r") as h:
        pk = np.asarray(h["units/peak_channel_id"][:])
        isi, amp, pres = (np.asarray(h[f"units/{k}"][:]) for k in ("isi_violations", "amplitude_cutoff",
                                                                     "presence_ratio"))
        e = h["general/extracellular_ephys/electrodes"]
        eid = np.asarray(e["id"][:])
        loc = np.asarray([x.decode() if isinstance(x, bytes) else str(x) for x in e["location"][:]])
    lut = dict(zip(eid.tolist(), loc.tolist()))
    u = np.asarray(units)
    area = np.asarray([lut.get(int(c), "") for c in pk[u]])
    qc = (isi[u] < 0.5) & (amp[u] < 0.1) & (pres[u] > 0.9)
    np.savez(f, area=area, qc=qc)
    return area, qc


def visual_cortex(area):
    """Allen visual cortical areas: acronyms starting with VIS (VISp, VISl, VISal, VISrl, VISam, VISpm, ...)."""
    return np.char.startswith(np.asarray(area, str), "VIS")


def behaviour(a, starts, stops, n_bins):
    """S-R2 finding 11: running speed (all sessions) and pupil area (where tracked) in 20 ms bins aligned to
    each movie repeat: (R, n_bins, 1 or 2), NaN where not measured. Behaviour only, no neural data; cached."""
    import h5py
    f = CACHE / (a["path"].split("/")[0] + "_behaviour.npz")
    if f.exists():
        return np.load(f, allow_pickle=False)["B"]
    CACHE.mkdir(parents=True, exist_ok=True)
    with h5py.File(mdata.open_url(f"{mdata.DANDI}/assets/{a['asset_id']}/download/"), "r") as h:
        rs = h["processing/running/running_speed"]
        sig = [(np.asarray(rs["timestamps"][:]), np.asarray(rs["data"][:], float))]
        pp = "processing/filtered_gaze_mapping/pupil_area"
        if pp in h:
            sig.append((np.asarray(h[pp]["timestamps"][:]), np.asarray(h[pp]["data"][:], float)))
    B = np.full((len(starts), n_bins, len(sig)), np.nan)
    for j, (t, x) in enumerate(sig):
        ok = np.isfinite(x)
        t, x = t[ok], x[ok]
        for r, s0 in enumerate(starts):
            centres = s0 + (np.arange(n_bins) + 0.5) * BIN_S
            B[r, :, j] = np.interp(centres, t, x)
    np.savez(f, B=B)
    return B


def regress_out(Y, B):
    """Per unit, remove the part of its counts that a linear model of behaviour explains. Regressors: each
    behavioural signal and its 1 s running mean (additive effects), the same multiplied by the unit's mean
    response over repeats at that time (gain effects: behaviour scaling the stimulus response), and a constant
    per repeat; fitted on all repeats at once. Returns residuals (R, n_bins, units) and the median fraction
    of variance explained."""
    R, nb, N = Y.shape
    sigs = []
    for j in range(B.shape[2]):
        x = B[:, :, j]
        if not np.isfinite(x).all():
            continue
        k = np.ones(50) / 50
        sm = np.stack([np.convolve(xr, k, mode="same") for xr in x])
        for c in (x, sm):
            sigs.append(((c - c.mean()) / (c.std() + 1e-12)).reshape(-1))
    rep = np.repeat(np.eye(R), nb, axis=0)
    Yf = np.asarray(Y, float).reshape(R * nb, N)
    psth = np.asarray(Y, float).mean(0)                                  # nb x N
    res = np.empty_like(Yf)
    r2 = np.full(N, np.nan)
    for u in range(N):
        pu = np.tile(psth[:, u] - psth[:, u].mean(), R)
        cols = sigs + [x_ * pu for x_ in sigs]
        X = np.column_stack(cols + [rep]) if cols else rep
        beta, *_ = np.linalg.lstsq(X, Yf[:, u], rcond=None)
        fit = X @ beta
        res[:, u] = Yf[:, u] - fit + rep @ beta[-R:]
        v = Yf[:, u].var()
        if v > 0:
            r2[u] = 1 - (Yf[:, u] - fit).var() / v
    return res.reshape(R, nb, N), float(np.nanmedian(r2))
