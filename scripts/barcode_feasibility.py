"""Study 4 feasibility F1 (metadata only; no spike times read): Allen OpenScope Barcoding, DANDI 000563.
Per session (the *_ogen.nwb file holds units and stimulus tables): repeats of the identical full-field
flicker (RepeatFFF), their timing and identity, overlap with invalid intervals, units (good, Allen QC,
by area group), and the size of the spike-time array a spike read would need.
Writes docs/figures/barcode/feasibility.json (summary numbers only)."""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.map import data as mdata  # noqa: E402

DS = "000563"
OUT = ROOT / "docs/figures/barcode/feasibility.json"


def group(area):
    a = str(area)
    if a.startswith("VIS"):
        return "visual_cortex"
    if a.startswith(("LGd", "LGv", "LP", "PO", "Eth", "TH", "LD", "VP", "SGN", "MG", "IntG", "PIL", "RT", "POL")):
        return "thalamus"
    if a.startswith(("CA", "DG", "SUB", "ProS", "PoST", "PRE", "POST", "HPF")):
        return "hippocampus"
    return "other" if a else "unknown"


def main():
    import h5py
    rows = json.loads(OUT.read_text()) if OUT.exists() else []
    seen = {r["session"] for r in rows}
    for a in sorted((x for x in mdata.dandi_assets(DS) if x["path"].endswith("_ogen.nwb")), key=lambda x: x["path"]):
        sess = a["path"].split("/")[0]
        if sess in seen:
            continue
        try:
            with h5py.File(mdata.open_url(f"{mdata.DANDI}/assets/{a['asset_id']}/download/"), "r") as h:
                g = h["intervals/RepeatFFF_presentations"]
                st, sp = g["start_time"][:], g["stop_time"][:]
                ir = g["index_repeat"][:].astype(int)
                col = np.asarray(g["color"][:])
                o = np.argsort(st, kind="stable")
                st, sp, ir, col = st[o], sp[o], ir[o], col[o]
                reps = np.unique(ir)
                frames = Counter(ir.tolist())
                r_start = np.array([st[ir == k].min() for k in reps])
                r_stop = np.array([sp[ir == k].max() for k in reps])
                ref = col[ir == reps[0]]
                same = [bool(np.array_equal(col[ir == k], ref)) for k in reps]
                inv = []
                if "invalid_times" in h["intervals"]:
                    it = h["intervals/invalid_times"]
                    inv = [(x, y) for x, y in zip(it["start_time"][:], it["stop_time"][:]) if y > x]
                bad = [bool(any(x < b and y > a_ for x, y in inv)) for a_, b in zip(r_start, r_stop)]
                blocks = np.unique(g["stimulus_block"][:]).tolist()
                q = h["units/quality"][:]
                good = np.asarray([x in (b"good", "good") for x in q])
                isi, amp, pres = (np.asarray(h[f"units/{k}"][:]) for k in ("isi_violations", "amplitude_cutoff",
                                                                             "presence_ratio"))
                qc = good & (isi < 0.5) & (amp < 0.1) & (pres > 0.9)
                pk = np.asarray(h["units/peak_channel_id"][:])
                e = h["general/extracellular_ephys/electrodes"]
                lut = dict(zip(np.asarray(e["id"][:]).tolist(),
                               [x.decode() if isinstance(x, bytes) else str(x) for x in e["location"][:]]))
                areas = [lut.get(int(c), "") for c in pk]
                by = Counter(group(a_) for a_, ok in zip(areas, qc) if ok)
                row = {"session": sess, "repeats": int(len(reps)), "frames_per_repeat": sorted(set(frames.values())),
                       "repeat_s_median": float(np.median(r_stop - r_start)),
                       "start_gap_s": [float(np.min(np.diff(r_start))), float(np.max(np.diff(r_start)))],
                       "identical_sequence": bool(all(same)), "blocks": blocks,
                       "repeats_valid": int(len(reps) - sum(bad)), "units_good": int(good.sum()),
                       "units_qc": int(qc.sum()), "qc_by_group": dict(by),
                       "spike_time_bytes": int(h["units/spike_times"].shape[0]) * 8}
        except Exception as ex:  # noqa: BLE001
            row = {"session": sess, "error": f"{type(ex).__name__}: {ex}"}
        rows.append(row)
        OUT.write_text(json.dumps(rows, indent=1))
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
