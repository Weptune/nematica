"""Study 4 data: spikes during the repeated full-field flicker (RepeatFFF: 90 repeats of 8.007 s) and the
unique flicker (UniqueFFF), cached once per session (data/cache/barcode, git-ignored; third-party data stays
local, only summary numbers are committed). Caching computes no statistic of the activity.

Kept per unit: spike offsets in milliseconds (uint32) from each repeat's start, for the repeats, and from
each unique block's start. Units: all `good` units (no subset; at most a few thousand per session), with
area (peak channel location) and Allen's default QC stored alongside."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..map import data as mdata

DS = "000563"
CACHE = Path(__file__).resolve().parents[2] / "data/cache/barcode"
FRAMES = 480


def sessions():
    """The 14 sessions, sorted by path (fixed order; instance = rank mod 3)."""
    return sorted((x for x in mdata.dandi_assets(DS) if x["path"].endswith("_ogen.nwb")), key=lambda x: x["path"])


def _repeat_bounds(h):
    g = h["intervals/RepeatFFF_presentations"]
    st, sp = g["start_time"][:], g["stop_time"][:]
    ir = g["index_repeat"][:].astype(int)
    reps = np.unique(ir)
    starts = np.array([st[ir == k].min() for k in reps])
    stops = np.array([sp[ir == k].max() for k in reps])
    return starts, stops


def _unique_bounds(h):
    g = h["intervals/UniqueFFF_presentations"]
    st, sp, b = g["start_time"][:], g["stop_time"][:], g["stimulus_block"][:]
    return np.array([st[b == k].min() for k in np.unique(b)]), np.array([sp[b == k].max() for k in np.unique(b)])


def cache(a):
    import h5py
    import requests
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (a["path"].split("/")[0] + ".npz")
    if f.exists():
        return np.load(f, allow_pickle=False)
    url = f"{mdata.DANDI}/assets/{a['asset_id']}/download/"
    with h5py.File(mdata.open_url(url), "r") as h:
        starts, stops = _repeat_bounds(h)
        ustarts, ustops = _unique_bounds(h)
        idx = np.asarray(h["units/spike_times_index"][:], np.int64)
        q = h["units/quality"][:]
        isi, amp, pres = (np.asarray(h[f"units/{k}"][:]) for k in ("isi_violations", "amplitude_cutoff",
                                                                     "presence_ratio"))
        pk = np.asarray(h["units/peak_channel_id"][:])
        e = h["general/extracellular_ephys/electrodes"]
        lut = dict(zip(np.asarray(e["id"][:]).tolist(),
                       [x.decode() if isinstance(x, bytes) else str(x) for x in e["location"][:]]))
        stt = h["units/spike_times"]
        off, n = stt.id.get_offset(), stt.shape[0]
        assert stt.chunks is None and stt.compression is None and stt.dtype == np.float64
        rs = h["processing/running/running_speed"] if "processing/running/running_speed" in h else None
        run_t = np.asarray(rs["timestamps"][:]) if rs is not None else np.zeros(0)
        run_x = np.asarray(rs["data"][:], float) if rs is not None else np.zeros(0)
    good = np.flatnonzero(np.asarray([x in (b"good", "good") for x in q]))
    area = np.asarray([lut.get(int(c), "") for c in pk[good]])
    qc = (isi[good] < 0.5) & (amp[good] < 0.1) & (pres[good] > 0.9)
    s3 = requests.head(url, allow_redirects=True, timeout=60).url
    T = np.frombuffer(mdata._fetch_range(s3, off, n * 8), np.float64)
    first = np.concatenate([[0], idx[:-1]])
    blocks = list(zip(starts, stops)) + list(zip(ustarts, ustops))
    assert len(blocks) <= 255
    ms, rep, ptr = [], [], [0]
    for u in good:
        tt = T[first[u]:idx[u]]
        k = 0
        for r, (a0, b0) in enumerate(blocks):
            sel = tt[(tt >= a0) & (tt < b0)]
            ms.append(np.floor((sel - a0) * 1000).astype(np.uint32))
            rep.append(np.full(len(sel), r, np.uint8))
            k += len(sel)
        ptr.append(ptr[-1] + k)
    del T
    np.savez_compressed(f, ms=np.concatenate(ms), rep=np.concatenate(rep), ptr=np.asarray(ptr, np.int64),
                        starts=starts, stops=stops, ustarts=ustarts, ustops=ustops, units=good, area=area, qc=qc,
                        run_t=run_t, run_x=run_x)
    return np.load(f, allow_pickle=False)


def counts(z, which="repeat", bin_s=0.02):
    """(R, n_bins, units) spike counts in 20 ms bins: `which` = "repeat" (the 90 repeats) or "unique"."""
    if which == "repeat":
        ids, dur = range(len(z["starts"])), np.min(z["stops"] - z["starts"])
    else:
        ids, dur = range(len(z["starts"]), len(z["starts"]) + len(z["ustarts"])), np.min(z["ustops"] - z["ustarts"])
    ids = list(ids)
    nb = int(np.floor(dur / bin_s + 1e-9))
    N = len(z["ptr"]) - 1
    Y = np.zeros((len(ids), nb, N), np.uint8)
    ms, rep, ptr = z["ms"], z["rep"], z["ptr"]
    lo, hi = ids[0], ids[-1]                       # ids are contiguous
    for j in range(N):
        b = (ms[ptr[j]:ptr[j + 1]] // int(bin_s * 1000)).astype(np.int64)
        r = rep[ptr[j]:ptr[j + 1]].astype(np.int64)
        ok = (r >= lo) & (r <= hi) & (b < nb)
        np.add.at(Y[:, :, j], (r[ok] - lo, b[ok]), 1)
    return Y
