"""Study O data cache (docs/OPTO.md). For each registered mouse, stream the Allen session file from DANDI and
keep, locally only (data/cache/opto, never committed): unit metadata (area, waveform duration, Allen QC
columns, firing rate), the optogenetic table, the spontaneous blocks, and the spike times of units passing
the registered QC, restricted to spontaneous blocks and the optogenetic block. Computes no response.

python -I scripts/opto_cache.py            (resumable; one .npz per mouse)"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import h5py  # noqa: E402
import numpy as np  # noqa: E402

from nematica.map import data as md  # noqa: E402

OUT = ROOT / "data/cache/opto"
CRE = ["sub-769360771", "sub-775876808", "sub-776061236", "sub-763808588", "sub-774672354", "sub-791857600",
       "sub-795770029", "sub-803390283", "sub-811322604", "sub-813701555", "sub-817060743", "sub-820866111",
       "sub-821469659"]
WT = ["sub-772616820", "sub-754477355", "sub-769319621", "sub-800249582", "sub-800250054", "sub-827809879"]


def _s(a):
    return np.array([x.decode() if isinstance(x, bytes) else str(x) for x in a])


def session_asset(mouse):
    for ds in ("000021", "000022"):
        for a in ASSETS[ds]:
            p = a["path"]
            if p.startswith(mouse + "/") and "probe" not in p and p.endswith(".nwb"):
                return ds, a
    raise KeyError(mouse)


def curl_range(url, off, n):
    r = subprocess.run(["curl", "-sSfL", "--retry", "5", "-r", f"{off}-{off + n - 1}", url], capture_output=True, check=True)
    assert len(r.stdout) == n, (len(r.stdout), n)
    return r.stdout


def cache(mouse):
    dest = OUT / f"{mouse}.npz"
    if dest.exists():
        return "cached"
    ds, a = session_asset(mouse)
    url = f"{md.DANDI}/assets/{a['asset_id']}/download/"
    t0 = time.time()
    with h5py.File(md.open_url(url), "r") as h:
        u = h["units"]
        meta = {k: u[k][:] for k in ("id", "isi_violations", "amplitude_cutoff", "presence_ratio", "waveform_duration",
                                     "peak_channel_id", "firing_rate", "spike_times_index")}
        quality = _s(u["quality"][:])
        el = h["general/extracellular_ephys/electrodes"]
        loc = dict(zip(el["id"][:], _s(el["location"][:])))
        area = np.array([loc.get(c, "") for c in meta["peak_channel_id"]])
        ot = h["processing/optotagging/optogenetic_stimulation"]
        opto = {"start": ot["start_time"][:], "stop": ot["stop_time"][:], "condition": _s(ot["condition"][:]),
                "level": ot["level"][:].astype(float), "duration": ot["duration"][:].astype(float),
                "name": _s(ot["stimulus_name"][:])}
        sp = h["intervals/spontaneous_presentations"]
        spont = np.stack([sp["start_time"][:], sp["stop_time"][:]], 1)
        d = u["spike_times"]
        assert d.dtype == np.dtype("<f8") and d.chunks is None and d.compression is None
        off, n = d.id.get_offset(), d.shape[0]
        head = d[:5]
    st = np.frombuffer(curl_range(url, off, n * 8), "<f8")
    assert np.array_equal(st[:5], head)
    qc = ((quality == "good") & (meta["isi_violations"] < 0.5) & (meta["amplitude_cutoff"] < 0.1)
          & (meta["presence_ratio"] > 0.9))
    lo, hi = opto["start"].min() - 2.0, opto["stop"].max() + 2.0
    idx = meta["spike_times_index"]
    keep_t, keep_i = [], [0]
    for i in np.flatnonzero(qc):
        s = st[(idx[i - 1] if i else 0):idx[i]]
        m = (s >= lo) & (s <= hi)
        for a0, b0 in spont:
            m |= (s >= a0) & (s < b0)
        keep_t.append(np.round(s[m] * 1e5).astype(np.int64))   # 10 us units
        keep_i.append(keep_i[-1] + int(m.sum()))
    np.savez_compressed(dest, unit_id=meta["id"][qc], area=area[qc], waveform_ms=meta["waveform_duration"][qc],
                        firing_rate=meta["firing_rate"][qc], spikes_10us=np.concatenate(keep_t),
                        spikes_index=np.array(keep_i[1:]), spont=spont,
                        **{"opto_" + k: v for k, v in opto.items()},
                        info=json.dumps({"mouse": mouse, "dandiset": ds, "path": a["path"], "n_units": int(len(qc)),
                                         "n_qc": int(qc.sum())}))
    return f"{int(qc.sum())} QC units of {len(qc)}, {time.time() - t0:.0f} s"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    ASSETS = {ds: md.dandi_assets(ds) for ds in ("000021", "000022")}
    for m in (sys.argv[1:] or CRE + WT):
        for attempt in range(3):
            try:
                print(m, cache(m), flush=True)
                break
            except Exception as e:  # noqa: BLE001
                print(m, "attempt", attempt, type(e).__name__, str(e)[:200], flush=True)
                time.sleep(30)
