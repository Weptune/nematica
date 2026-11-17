"""Study 3 data (docs/PERSIST.md section 3). Natural movie three (NM3, 3,600 frames, about 120 s) spikes,
downloaded once per session and kept locally (data/cache/allen_nm3, git-ignored; third-party data stays
local, only summary numbers are committed). The same units as Study 2's NM1 cache (the map study's seeded
subset of Allen `good` units), so Study 2's area and QC metadata (`nematica.slow.data.unit_meta`) apply.

Differences from `nematica.slow.data.movie_cache`, which this mirrors: offsets are stored as uint32
milliseconds (NM3 repeats last 120 s, beyond uint16's 65,535 ms; feasibility F2), and the repeat finder
takes the frame count as a parameter."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..map import data as mdata

CACHE = Path(__file__).resolve().parents[2] / "data/cache/allen_nm3"
NM3 = ("natural_movie_three_presentations",)
NM3_FRAMES = 3600


def repeats(h, names=NM3, frames=NM3_FRAMES):
    """Start of every complete repeat (frame 0) and the end of its last frame, in session seconds, after
    removing repeats that overlap one of Allen's invalid intervals. Returns (starts, stops, dropped)."""
    key = next(k for k in names if k in h["intervals"])
    g = h[f"intervals/{key}"]
    st, en, fr = g["start_time"][:], g["stop_time"][:], np.asarray(g["frame"][:]).astype(int)
    o = np.argsort(st, kind="stable")
    st, en, fr = st[o], en[o], fr[o]
    starts, stops = [], []
    for i in np.flatnonzero(fr == 0):
        j = i + frames - 1
        if j < len(fr) and fr[j] == frames - 1:
            starts.append(float(st[i]))
            stops.append(float(en[j]))
    inv = []
    if "invalid_times" in h["intervals"]:
        it = h["intervals/invalid_times"]
        inv = list(zip(it["start_time"][:], it["stop_time"][:]))
    keep = [k for k, (a, b) in enumerate(zip(starts, stops)) if not any(x < b and y > a for x, y in inv)]
    return np.asarray(starts)[keep], np.asarray(stops)[keep], len(starts) - len(keep)


def nm3_cache(a, max_units=mdata.ALLEN_MAX_UNITS):
    """Download one session's spikes during NM3 once and keep them locally. Caching is not measuring: no
    statistic of the activity is computed here."""
    import h5py
    import requests
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (a["path"].split("/")[0] + ".npz")
    if f.exists():
        return np.load(f, allow_pickle=False)
    url = f"{mdata.DANDI}/assets/{a['asset_id']}/download/"
    with h5py.File(mdata.open_url(url), "r") as h:
        starts, stops, dropped = repeats(h)
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
            ms.append(np.floor((sel - a0) * 1000).astype(np.uint32))
            rep.append(np.full(len(sel), r, np.uint8))
        ptr.append(ptr[-1] + sum(len(x) for x in ms[-len(starts):]))
    del T
    np.savez_compressed(f, ms=np.concatenate(ms) if ms else np.zeros(0, np.uint32),
                        rep=np.concatenate(rep) if rep else np.zeros(0, np.uint8), ptr=np.asarray(ptr, np.int64),
                        starts=starts, stops=stops, dropped=dropped, units=good, n_good=n_good)
    return np.load(f, allow_pickle=False)
