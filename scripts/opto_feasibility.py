"""Study O feasibility (docs/OPTO.md): metadata only. For each Allen Visual Coding Neuropixels session
(DANDI 000021 and 000022, session files only), record the mouse's genotype, the optogenetic table (if any:
its columns' names, the stimulus names, durations, light levels, trial count, start times), and the
spontaneous blocks' total length. No spike, LFP or response value is read.

Output: docs/figures/opto/feasibility.jsonl (one line per session; resumable)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import h5py  # noqa: E402
import numpy as np  # noqa: E402

from nematica.map import data as mdata  # noqa: E402

OUT = ROOT / "docs/figures/opto"


def _s(x):
    return x.decode() if isinstance(x, bytes) else str(x)


def probe(h):
    r = {}
    g = h.get("general/subject")
    if g is not None:
        r["genotype"] = _s(g["genotype"][()]) if "genotype" in g else None
        r["subject_id"] = _s(g["subject_id"][()]) if "subject_id" in g else None
    r["processing"] = sorted(h["processing"].keys()) if "processing" in h else []
    r["intervals"] = sorted(h["intervals"].keys()) if "intervals" in h else []
    if "intervals/spontaneous_presentations" in h:
        sp = h["intervals/spontaneous_presentations"]
        d = sp["stop_time"][:] - sp["start_time"][:]
        r["spont_total_s"] = float(d.sum())
        r["spont_blocks_s"] = [round(float(x), 1) for x in d]
    ot = None
    for path in ("processing/optotagging/optogenetic_stimulation", "intervals/optogenetic_stimulation"):
        if path in h:
            ot = h[path]
            r["opto_path"] = path
            break
    if ot is not None:
        cols = sorted(ot.keys())
        r["opto_columns"] = cols
        st = ot["start_time"][:]
        sp = ot["stop_time"][:]
        r["opto_n"] = int(len(st))
        r["opto_first_last_s"] = [float(st.min()), float(sp.max())]
        r["opto_min_gap_s"] = float(np.min(np.diff(np.sort(st)))) if len(st) > 1 else None
        for c in ("stimulus_name", "condition", "level", "duration"):
            if c in ot and ot[c].ndim == 1:
                v = ot[c][:]
                if v.dtype.kind in "SO":
                    v = np.array([_s(x) for x in v])
                else:
                    v = np.round(v.astype(float), 4)
                u, n = np.unique(v, return_counts=True)
                r[f"opto_{c}"] = {str(a): int(b) for a, b in zip(u, n)}
    return r


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "feasibility.jsonl"
    done = {json.loads(line)["id"] for line in f.open()} if f.exists() else set()
    for ds in mdata.ALLEN_DANDISETS:
        for a in sorted((x for x in mdata.dandi_assets(ds) if "probe" not in x["path"]), key=lambda x: x["path"]):
            uid = a["path"].split("/")[0]
            if uid in done:
                continue
            try:
                with h5py.File(mdata.open_url(f"{mdata.DANDI}/assets/{a['asset_id']}/download/"), "r") as h:
                    r = probe(h)
            except Exception as e:  # noqa: BLE001
                r = {"error": repr(e)[:200]}
            r.update(id=uid, dandiset=ds)
            with f.open("a") as fh:
                fh.write(json.dumps(r) + "\n")
            print(uid, r.get("genotype"), r.get("opto_n"), r.get("error", ""), flush=True)


if __name__ == "__main__":
    main()
