"""Study 3 feasibility F1 (metadata only; no spike times are read).

For every session of the 58 used in Study 2: which natural-movie stimulus tables exist, how many complete
repeats of natural movie three (3,600 frames, about 120 s) survive Allen's invalid intervals, how the
repeats are grouped in blocks, and how large the session's spike-time array is (the download a spike read
would need). Writes docs/figures/persist/feasibility.json (summary numbers only).
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.map import data as mdata  # noqa: E402
from nematica.slow import data as sd  # noqa: E402

NM3 = ("natural_movie_three_presentations",)
NM3_FRAMES = 3600
OUT = ROOT / "docs/figures/persist"


def complete_repeats(h, key, frames):
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
    return np.asarray(starts), np.asarray(stops), keep


def main():
    import h5py
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "feasibility.json"
    rows = json.loads(f.read_text()) if f.exists() else []
    seen = {r["session"] for r in rows}
    for ds, a in sd.sessions():
        sess = a["path"].split("/")[0]
        if sess in seen:
            continue
        url = f"{mdata.DANDI}/assets/{a['asset_id']}/download/"
        try:
            with h5py.File(mdata.open_url(url), "r") as h:
                keys = sorted(k for k in h["intervals"] if "movie" in k)
                row = {"dandiset": ds, "session": sess, "movie_tables": keys,
                       "spike_time_bytes": int(h["units/spike_times"].shape[0]) * 8}
                if NM3[0] in h["intervals"]:
                    st, en, keep = complete_repeats(h, NM3[0], NM3_FRAMES)
                    d = np.diff(st)
                    row.update({"nm3_complete": len(st), "nm3_valid": len(keep),
                                "nm3_duration_s": float(np.median(en - st)) if len(st) else None,
                                "nm3_blocks": int(1 + np.sum(d > 2 * np.median(d))) if len(d) else len(st)})
        except Exception as e:  # noqa: BLE001
            row = {"dandiset": ds, "session": sess, "error": f"{type(e).__name__}: {e}"}
        rows.append(row)
        f.write_text(json.dumps(rows, indent=1))
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
