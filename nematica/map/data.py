"""Loaders for the map's real preparations (docs/MAP.md). Each returns a list of individuals, each a dict
with `activity` (time, units), `dt` (seconds per sample), `recording` ('calcium' | 'spikes' | 'field'),
and identifiers. Data is downloaded or streamed by script into data/external/map (gitignored) and never
redistributed. Rule: a loader is checked on shapes only before the measurement code is frozen.
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/external/map"
DANDI = "https://api.dandiarchive.org/api"


def dandi_assets(dandiset, version="draft"):
    out, url = [], f"{DANDI}/dandisets/{dandiset}/versions/{version}/assets/?page_size=400"
    while url:
        d = json.loads(subprocess.run(["curl", "-sSfL", url], capture_output=True, check=True).stdout)
        out += d["results"]
        url = d.get("next")
    return out


def dandi_get(asset, dest):
    dest = Path(dest)
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-sSfL", "-o", str(dest), f"{DANDI}/assets/{asset['asset_id']}/download/"], check=True)
    return dest


def bin_spikes(times_by_unit, duration_s, bin_s=None):
    """Spike times (s) per unit -> counts per bin (time x units). Amendment 4 (F3): every spiking preparation
    is binned at instrument.SPIKE_BIN_S (20 ms)."""
    from .instrument import SPIKE_BIN_S
    bin_s = bin_s or SPIKE_BIN_S
    nb = int(duration_s / bin_s)
    X = np.zeros((nb, len(times_by_unit)), np.float32)
    for i, tt in enumerate(times_by_unit):
        b = (np.asarray(tt) / bin_s).astype(int)
        b = b[(b >= 0) & (b < nb)]
        np.add.at(X[:, i], b, 1)
    return X


def culture_session(path, bin_s=None, min_spikes=200):
    """Rat cortical culture on an HD-MEA (DANDI 002020): detected spikes per electrode (the registered unit for
    R9 is the electrode, amendment 4) -> counts per 20 ms bin."""
    import h5py
    with h5py.File(path, "r") as f:
        g = f["processing/ecephys/detected_spikes"]
        ch = g["source_channel"][:]
        t = g["time_from_first_spike_seconds"][:]
        dur = float(f["processing/ecephys/conversion_provenance/duration_s"][0])
    from .instrument import SPIKE_BIN_S
    bin_s = bin_s or SPIKE_BIN_S
    chans, counts = np.unique(ch, return_counts=True)
    keep = chans[counts >= min_spikes]
    X = bin_spikes([t[ch == c] for c in keep], dur, bin_s)
    return {"activity": X, "dt": bin_s, "recording": "spikes", "duration_s": dur, "units_total": len(chans)}


# ---------------------------------------------------------------- step 1 loaders (amendments 5 and 6)
RAW = ROOT / "data/raw"


def atanas_worms(folder=RAW / "atanas2023_wwweb"):
    """R2 (amendment 6): Atanas et al. 2023, freely moving worms. Activity = `trace_original` (fluorescence),
    dt = median confocal frame interval. Rest: 'baseline' recordings whole, their two ranges as segments;
    'heat' recordings only the first range (before the heat pulse). Amendment 13: a baseline recording is one
    continuous stretch (its two ranges have no time gap). Indicator NLS-GCaMP7f."""
    out = []
    for f in sorted(Path(folder).glob("*.json")):
        d = json.loads(f.read_text())
        X = np.asarray(d["trace_original"], float).T                 # (time, neurons)
        dt = float(np.median(np.diff(d["timestamp_confocal"])))
        r = [(int(a[0]) - 1, int(a[-1])) for a in d["ranges"]]       # 1-indexed inclusive -> python
        heat = "heat" in d["dataset_type"]
        # amendment 13: a baseline recording is one continuous stretch (no time gap between its two ranges)
        rest = r[:1] if heat else [(r[0][0], r[-1][1])]
        out.append({"id": d["uid"], "activity": X, "dt": dt, "rest": rest, "indicator": "jGCaMP7f",
                    "kind": "heat (pre-pulse only)" if heat else "baseline"})
    return out


class RangeFile(io.RawIOBase):
    """Seekable, read-only file over HTTP range requests. Each request goes through the original URL, so
    short-lived signed redirects (figshare to S3) are re-resolved. Lets zip members and HDF5 files be read
    without downloading whole archives to disk."""

    def __init__(self, url, chunk=4 << 20):
        import requests
        self._rq = requests
        self.orig = url
        r = requests.get(url, headers={"Range": "bytes=0-0"}, stream=True, timeout=60)
        self.size = int(r.headers["Content-Range"].split("/")[1])
        r.close()
        self.pos, self.chunk, self.cache = 0, chunk, {}

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, o, w=0):
        self.pos = o if w == 0 else (self.pos + o if w == 1 else self.size + o)
        return self.pos

    def _get(self, i):
        if i not in self.cache:
            a = i * self.chunk
            b = min(a + self.chunk, self.size) - 1
            for k in range(6):
                try:
                    r = self._rq.get(self.orig, headers={"Range": f"bytes={a}-{b}"}, timeout=120)
                    r.raise_for_status()
                    if len(r.content) == b - a + 1:
                        break
                except Exception:  # noqa: BLE001
                    if k == 5:
                        raise
            if len(self.cache) > 8:
                self.cache.pop(next(iter(self.cache)))
            self.cache[i] = r.content
        return self.cache[i]

    def readinto(self, buf):
        n = min(len(buf), self.size - self.pos)
        out = 0
        while out < n:
            i, off = divmod(self.pos, self.chunk)
            c = self._get(i)
            k = min(n - out, len(c) - off)
            buf[out:out + k] = c[off:off + k]
            out += k
            self.pos += k
        return max(n, 0)


def open_url(url):
    return io.BufferedReader(RangeFile(url), buffer_size=8 << 20)


def figshare_files(article):
    d = json.loads(subprocess.run(["curl", "-sSfL", f"https://api.figshare.com/v2/articles/{article}"],
                                  capture_output=True, check=True).stdout)
    return {f["name"]: f for f in d["files"]}


def chen_fish(skip=()):
    """R3 (amendment 7): Chen et al. 2018 zebrafish, figshare 7272617, streamed. Yields one individual at a
    time: the 'Spontaneous' block of `CellResp` (dF/F), segments at gaps, dt = 1 / stated frame rate.
    Fish without a Spontaneous block, or with a stated rate outside 1 to 5 Hz, are yielded with `error`."""
    import zipfile

    import h5py
    import scipy.io as sio
    files = figshare_files(7272617)
    subs = sorted([n for n in files if n.startswith("subject_")], key=lambda n: int(n[8:-4]))
    for name in subs:
        sid = name[:-4]
        if sid in skip:
            yield {"id": sid, "cached": True}
            continue
        try:
            fp = open_url(files[name]["download_url"])
            z = zipfile.ZipFile(fp)
            for zi in z.infolist():                       # three archives over 4 GB store member offsets
                fp.seek(zi.header_offset)                 # 2^32 too large; use the offset whose local
                if fp.read(4) != b"PK\x03\x04" and zi.header_offset >= 1 << 32:   # header magic matches
                    fp.seek(zi.header_offset - (1 << 32))
                    if fp.read(4) == b"PK\x03\x04":
                        zi.header_offset -= 1 << 32
            meta = [n for n in z.namelist() if n.endswith("data_full.mat") and "MACOSX" not in n][0]
            v = sio.loadmat(io.BytesIO(z.read(meta)), squeeze_me=True, struct_as_record=False)["data"]
        except Exception as e:  # noqa: BLE001
            yield {"id": sid, "error": f"unreadable by streaming: {type(e).__name__}"}
            continue
        names = list(np.atleast_1d(v.timelists_names))
        fps = float(v.fpsec)
        if "Spontaneous" not in names:
            yield {"id": sid, "error": "no Spontaneous block"}
            continue
        if not 1 <= fps <= 5:
            yield {"id": sid, "error": f"stated frame rate {fps} Hz outside 1 to 5"}
            continue
        frames = np.atleast_1d(np.asarray(v.timelists, dtype=object)[names.index("Spontaneous")]).astype(int) - 1
        ts = [n for n in z.namelist() if n.endswith("TimeSeries.h5") and "MACOSX" not in n and "half" not in n][0]
        note = ""
        tmp = CACHE / "_stream_tmp.h5"                    # the member is decompressed to a scratch file
        tmp.parent.mkdir(parents=True, exist_ok=True)     # (it can be 4 GB) and removed after reading
        crc = zipfile.ZipExtFile._update_crc
        for attempt in (0, 1):
            try:
                if attempt:                               # archives with shifted offsets also carry a wrong
                    zipfile.ZipExtFile._update_crc = lambda self, data: None   # CRC: let HDF5 judge
                    note = ", archive CRC mismatch ignored"
                with z.open(ts) as src, open(tmp, "wb") as dst:
                    shutil.copyfileobj(src, dst, 16 << 20)
                break
            except zipfile.BadZipFile:
                if attempt:
                    raise
            finally:
                zipfile.ZipExtFile._update_crc = crc
        try:
            with h5py.File(tmp, "r") as h:
                X = np.asarray(h["CellResp"][np.sort(frames), :], np.float32)
        except Exception as e:  # noqa: BLE001
            yield {"id": sid, "error": f"TimeSeries unreadable: {type(e).__name__}"}
            continue
        finally:
            tmp.unlink(missing_ok=True)
        fr = np.sort(frames)
        seg = [i for i in range(1, len(fr)) if fr[i] != fr[i - 1] + 1]
        yield {"id": sid, "activity": X, "dt": 1.0 / fps, "segments": seg, "indicator": "GCaMP6f",
               "kind": f"Spontaneous block, {len(fr)} frames{note}"}


CAP_S = 1200.0          # amendment 8: instrument numbers use at most the first 20 minutes of rest


def _nwb_units(h):
    st = h["units/spike_times"][:]
    idx = h["units/spike_times_index"][:]
    return [st[a:b] for a, b in zip(np.r_[0, idx[:-1]], idx)]


def spikes_individual(uid, trains, kind="", cap_s=CAP_S):
    """Spike trains (s) -> 20 ms counts over [t0, t0 + cap) where t0 is the first spike of any unit."""
    t0 = min(float(t.min()) for t in trains if len(t))
    t1 = max(float(t.max()) for t in trains if len(t))
    dur = min(t1 - t0, cap_s)
    X = bin_spikes([np.asarray(t) - t0 for t in trains], dur)
    return {"id": uid, "activity": X, "dt": 0.02, "kind": kind, "duration_total_s": t1 - t0}


def stringer_neuropixels(skip=()):
    """R4 (amendment 8): Stringer et al. 2019, figshare 7739750; individual = mouse; units = clusters of all
    eight probes; whole recording spontaneous."""
    import zipfile

    import scipy.io as sio
    z = zipfile.ZipFile(open_url(figshare_files(7739750)["spks.zip"]["download_url"]))
    for name in sorted(n for n in z.namelist() if n.endswith(".mat")):
        uid = name.split("spks")[-1].split("_")[0]
        if uid in skip:
            yield {"id": uid, "cached": True}
            continue
        m = sio.loadmat(io.BytesIO(z.read(name)), squeeze_me=True, struct_as_record=False)["spks"]
        trains = []
        for p in np.atleast_1d(m):
            st, clu = np.asarray(p.st, float), np.asarray(p.clu, int)
            order = np.argsort(clu, kind="stable")
            st, clu = st[order], clu[order]
            cut = np.flatnonzero(np.diff(clu)) + 1
            trains += np.split(st, cut)
        yield spikes_individual(uid, trains, "spontaneous, 8 probes")


def dandi_nwb(dandiset, path_filter, skip=(), id_of=None, kind=""):
    """Curated units from DANDI NWB files, streamed; one individual per file chosen by `path_filter`."""
    import h5py
    assets = [a for a in dandi_assets(dandiset) if path_filter(a["path"])]
    for a in sorted(assets, key=lambda a: a["path"]):
        uid = id_of(a["path"]) if id_of else a["path"].split("/")[0]
        if uid in skip:
            yield {"id": uid, "cached": True}
            continue
        try:
            with h5py.File(open_url(f"{DANDI}/assets/{a['asset_id']}/download/"), "r") as h:
                if "units" in h:
                    trains = _nwb_units(h)
                else:                                     # curated spikes shipped only as a binned matrix
                    g = h["processing/curated_binning/t_spk_mat/data"]
                    rate = float(g.attrs.get("rate", h["processing/curated_binning/t_spk_mat/starting_time"].attrs["rate"]))
                    B = np.asarray(g[: int(CAP_S * rate)], np.float32)
                    k = int(round(0.02 * rate))
                    X = B[: len(B) // k * k].reshape(-1, k, B.shape[1]).sum(1)
                    yield {"id": uid, "activity": X, "dt": 0.02, "kind": kind + " (binned matrix)",
                           "duration_total_s": len(B) / rate}
                    continue
        except Exception as e:  # noqa: BLE001
            yield {"id": uid, "error": f"unreadable: {type(e).__name__}"}
            continue
        yield spikes_individual(uid, trains, kind)


def _first_per_subject(paths, keep):
    seen, out = set(), set()
    for p in sorted(paths):
        s = p.split("/")[0]
        if keep(p) and s not in seen:
            seen.add(s)
            out.add(p)
    return out


def organoid_sets(prefix, kind, skip=()):
    """R10a-d (amendment 8): DANDI 001603 curated spikes; the first curated-spikes file per subject whose id
    starts with `prefix` (HO, MO, PR); slices (M?S1) use the first slice of each mouse."""
    paths = [a["path"] for a in dandi_assets("001603")]
    curated = lambda p: p.endswith(".nwb") and "ecephys" not in p and "obj-" not in p
    if prefix == "slice":
        chosen = _first_per_subject([p for p in paths if p.split("/")[0][4:5] == "M" and p.split("/")[0].endswith("S1")], curated)
    else:
        chosen = _first_per_subject([p for p in paths if p.split("/")[0][4:].startswith(prefix)], curated)
    yield from dandi_nwb("001603", lambda p: p in chosen, skip, kind=kind)


def finkelstein_alm(skip=()):
    """R6: Finkelstein et al., DANDI 000060; individual = mouse, its first session (whole session, task
    flagged); sorted units."""
    paths = [a["path"] for a in dandi_assets("000060")]
    chosen = _first_per_subject(paths, lambda p: p.endswith(".nwb"))
    yield from dandi_nwb("000060", lambda p: p in chosen, skip, kind="whole session (task)")


def rat_cultures(skip=()):
    """R9: DANDI 002020, individual = culture, its last-day session; unit = electrode (detected spikes)."""
    assets = [a for a in dandi_assets("002020") if a["path"].endswith(".nwb")]
    last = {}
    for a in assets:
        s = a["path"].split("/")[0]
        if s not in last or a["path"] > last[s]["path"]:
            last[s] = a
    for s, a in sorted(last.items()):
        if s in skip:
            yield {"id": s, "cached": True}
            continue
        try:
            p = dandi_get(a, CACHE / "002020" / Path(a["path"]).name)
            d = culture_session(p)
            X = d["activity"][: int(CAP_S / d["dt"])]
            yield {"id": s, "activity": X, "dt": d["dt"], "kind": "last-day session"}
        except Exception as e:  # noqa: BLE001
            yield {"id": s, "error": f"unreadable: {type(e).__name__}"}


KERNEL_S = 2.0           # amendment 16: the deconvolution kernel the data authors used (Stringer et al. 2019,
                         # Methods: OASIS with a fixed indicator decay timescale of 2 s)
INDICATOR_S = 0.50 / np.log(2)   # amendment 16: GCaMP6s 1/e decay from the half-decay in instrument.py's table
                                 # (Chen et al. 2013); sensitivity 1.25 s (amendment 15's value)


def stringer_2p(skip=(), cap_s=None):
    """Species 2 (amendment 15): Stringer et al. 2019 spontaneous two-photon recordings (figshare 6163622),
    `Fsp` (suite2p OASIS deconvolution, neurons x frames), one recording per mouse (the first by date for
    MP030). Frame rate per plane = 30 Hz / number of planes, from dbspont.mat."""
    import scipy.io as sio
    files = figshare_files(6163622)
    db = sio.loadmat(io.BytesIO(open_url(files["dbspont.mat"]["download_url"]).read()), squeeze_me=True,
                     struct_as_record=False)["db"]
    seen = set()
    for x in sorted(np.atleast_1d(db), key=lambda x: (x.mouse_name, x.date)):
        if x.mouse_name in seen:
            continue
        seen.add(x.mouse_name)
        uid = x.mouse_name
        if uid in skip:
            yield {"id": uid, "cached": True}
            continue
        name = f"spont_{x.mouse_name}_{x.date}.mat"
        fs = 30.0 / float(x.nplanes)
        m = sio.loadmat(io.BytesIO(open_url(files[name]["download_url"]).read()), variable_names=["Fsp"])
        X = np.asarray(m["Fsp"], np.float32).T                              # frames x neurons
        del m
        if cap_s:
            X = X[: int(cap_s * fs)]
        yield {"id": uid, "activity": X, "dt": 1.0 / fs, "fs": fs, "indicator_s": INDICATOR_S, "kernel_s": KERNEL_S,
               "kind": f"{x.mouse_type}, {x.date}, {np.atleast_1d(x.expt_name)[0]}"}


# ---------------------------------------------------------------- amendment 24: Allen Visual Coding Neuropixels
ALLEN_DANDISETS = ("000021", "000022")    # brain_observatory_1.1 and functional_connectivity sessions
ALLEN_MIN_BLOCK_S = 60.0
ALLEN_MAX_UNITS = 2400


def _fetch_range(url, a, n, workers=8, piece=16 << 20):
    """Bytes [a, a + n) of a URL by parallel HTTP range requests (retries per piece)."""
    import concurrent.futures as cf

    import requests
    buf = bytearray(n)
    def get(off):
        b = min(off + piece, n) - 1
        for k in range(6):
            try:
                r = requests.get(url, headers={"Range": f"bytes={a + off}-{a + b}"}, timeout=300)
                r.raise_for_status()
                if len(r.content) == b - off + 1:
                    buf[off:b + 1] = r.content
                    return
            except Exception:  # noqa: BLE001
                if k == 5:
                    raise
        raise IOError(f"range {a + off}-{a + b}: wrong length after 6 tries")   # review 16, item 9
    with cf.ThreadPoolExecutor(workers) as ex:
        list(ex.map(get, range(0, n, piece)))
    return bytes(buf)


def _allen_blocks(h):
    """Spontaneous blocks of at least ALLEN_MIN_BLOCK_S, with invalid intervals cut out (s)."""
    sp = h["intervals/spontaneous_presentations"]
    blocks = [(float(a), float(b)) for a, b in zip(sp["start_time"][:], sp["stop_time"][:])]
    inv = []
    if "invalid_times" in h["intervals"]:
        it = h["intervals/invalid_times"]
        inv = [(float(a), float(b)) for a, b in zip(it["start_time"][:], it["stop_time"][:])]
    out = []
    for a, b in blocks:
        pieces = [(a, b)]
        for x, y in inv:
            pieces = [p for q in pieces for p in ([(q[0], min(q[1], x)), (max(q[0], y), q[1])]
                                                  if x < q[1] and y > q[0] else [q])]
        out += [(p, q) for p, q in pieces if q - p >= ALLEN_MIN_BLOCK_S]
    return sorted(out)


ALLEN_CACHE = Path(__file__).resolve().parents[2] / "data/cache/allen"


def _allen_cache(a, max_units):
    """Download one session's spontaneous-block spikes of its good units once; kept locally (third-party data,
    never committed) as float32 times relative to their block's start, per unit."""
    import h5py
    import requests
    ALLEN_CACHE.mkdir(parents=True, exist_ok=True)
    f = ALLEN_CACHE / (a["path"].split("/")[0] + ".npz")
    if f.exists():
        return np.load(f, allow_pickle=False)
    url = f"{DANDI}/assets/{a['asset_id']}/download/"
    with h5py.File(open_url(url), "r") as h:
        blocks = _allen_blocks(h)
        idx = np.asarray(h["units/spike_times_index"][:], np.int64)
        q = h["units/quality"][:]
        st = h["units/spike_times"]
        off, n = st.id.get_offset(), st.shape[0]
        assert st.chunks is None and st.compression is None and st.dtype == np.float64
    good = np.flatnonzero(np.asarray([x in (b"good", "good") for x in q]))
    n_good = len(good)
    if len(good) > max_units:
        good = np.sort(np.random.default_rng(0).choice(good, max_units, replace=False))
    s3 = requests.head(url, allow_redirects=True, timeout=60).url
    T = np.frombuffer(_fetch_range(s3, off, n * 8), np.float64)
    starts = np.concatenate([[0], idx[:-1]])
    assert len(blocks) <= 255                            # uint8 block ids
    times, bids, ptr = [], [], [0]
    for u in good:
        tt = T[starts[u]:idx[u]]
        for k, (b0, b1) in enumerate(blocks):
            sel = tt[(tt >= b0) & (tt < b1)]
            times.append((sel - b0).astype(np.float32))
            bids.append(np.full(len(sel), k, np.uint8))
        ptr.append(sum(len(x) for x in times))
    del T
    np.savez(f, times=np.concatenate(times), block=np.concatenate(bids), ptr=np.asarray(ptr, np.int64),
             blocks=np.asarray(blocks, np.float64), n_good=n_good, n_units=len(idx))
    return np.load(f, allow_pickle=False)


def allen_vcn(skip=(), max_units=ALLEN_MAX_UNITS):
    """Amendment 24: Allen Brain Observatory Visual Coding Neuropixels (DANDI 000021 and 000022), one session
    per mouse. Units: Allen's `quality == good` (at most `max_units`, a seeded random subset); activity: 20 ms
    spike counts in every spontaneous block of at least 60 s after removing invalid intervals, blocks
    concatenated with segment boundaries."""
    from .instrument import SPIKE_BIN_S
    for ds in ALLEN_DANDISETS:
        for a in sorted((x for x in dandi_assets(ds) if "probe" not in x["path"]), key=lambda x: x["path"]):
            uid = a["path"].split("/")[0]
            if uid in skip:
                yield {"id": uid, "cached": True}
                continue
            try:
                z = _allen_cache(a, max_units)
                blocks, ptr, times, bid = z["blocks"], z["ptr"], z["times"], z["block"]
                nbs = [int((b1 - b0) / SPIKE_BIN_S) for b0, b1 in blocks]
                cum = np.concatenate([[0], np.cumsum(nbs)])
                X = np.zeros((int(cum[-1]), len(ptr) - 1), np.float32)
                for j in range(len(ptr) - 1):
                    tt, bb = times[ptr[j]:ptr[j + 1]], bid[ptr[j]:ptr[j + 1]]
                    b = (tt / SPIKE_BIN_S).astype(np.int64)
                    ok = b < np.asarray(nbs)[bb]
                    np.add.at(X[:, j], cum[bb[ok]] + b[ok], 1)
                yield {"id": uid, "activity": X, "dt": SPIKE_BIN_S, "segments": [int(c) for c in cum[1:-1]],
                       "kind": f"Allen VCN {ds}, {len(blocks)} spontaneous blocks, {X.shape[1]} of "
                               f"{int(z['n_good'])} good units", "blocks_s": blocks.tolist()}
            except Exception as e:  # noqa: BLE001
                yield {"id": uid, "error": f"unreadable: {type(e).__name__}: {e}"}


def allen_qc(max_units=ALLEN_MAX_UNITS):
    """Amendment 25 (review 16, item 2): Allen's default unit QC (isi_violations < 0.5, amplitude_cutoff < 0.1,
    presence_ratio > 0.9) for the cached units of every session, as a boolean mask in cache order. Metadata
    only (unit-table quality columns)."""
    import h5py
    out = {}
    for ds in ALLEN_DANDISETS:
        for a in sorted((x for x in dandi_assets(ds) if "probe" not in x["path"]), key=lambda x: x["path"]):
            uid = a["path"].split("/")[0]
            f = ALLEN_CACHE / f"{uid}_qc.npy"
            if not f.exists():
                with h5py.File(open_url(f"{DANDI}/assets/{a['asset_id']}/download/"), "r") as h:
                    q = h["units/quality"][:]
                    isi = h["units/isi_violations"][:]
                    amp = h["units/amplitude_cutoff"][:]
                    pres = h["units/presence_ratio"][:]
                good = np.flatnonzero(np.asarray([x in (b"good", "good") for x in q]))
                if len(good) > max_units:
                    good = np.sort(np.random.default_rng(0).choice(good, max_units, replace=False))
                np.save(f, (isi[good] < 0.5) & (amp[good] < 0.1) & (pres[good] > 0.9))
            out[uid] = np.load(f)
    return out
