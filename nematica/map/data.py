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
