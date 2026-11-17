"""Test R feasibility (docs/EMU_R.md): metadata only. For each candidate DANDI set, stream each NWB file's
header and record its structure: every dataset's path, shape, dtype and rate/time attributes, short string
datasets (neuron labels, stimulus names) and time stamps of interval or stimulus tables. Activity arrays are
never read. Output: docs/figures/emur/structure_<dandiset>.json.

Usage: python -I scripts/emur_feasibility.py 000565 [max_files]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import h5py  # noqa: E402
import numpy as np  # noqa: E402

from nematica.map import data as mdata  # noqa: E402

OUT = ROOT / "docs/figures/emur"
TIME_KEYS = ("rate", "starting_time", "resolution", "unit", "conversion", "description", "comments")


def _attr(v):
    if isinstance(v, bytes):
        return v.decode(errors="replace")[:300]
    if isinstance(v, np.ndarray):
        return v.tolist() if v.size <= 8 else f"array{v.shape}"
    if isinstance(v, (np.integer, np.floating)):
        return v.item()
    return str(v)[:300]


def walk(h):
    rows = []

    def visit(name, obj):
        if not isinstance(obj, h5py.Dataset):
            return
        r = {"path": name, "shape": list(obj.shape), "dtype": str(obj.dtype)}
        at = {k: _attr(v) for k, v in obj.attrs.items() if k in TIME_KEYS}
        if at:
            r["attrs"] = at
        leaf = name.rsplit("/", 1)[-1]
        # labels and protocol: strings, and time stamps of tables (not activity)
        if obj.dtype.kind in "SOU" and obj.size <= 2000:
            r["values"] = [_attr(x) for x in np.atleast_1d(np.asarray(obj[()], dtype=object)).ravel()[:400]]
        elif leaf == "timestamps" and obj.ndim == 1:
            t = obj[[0, 1, obj.shape[0] - 1]] if obj.shape[0] > 2 else obj[()]
            r["timestamps_first_second_last"] = [float(x) for x in t]
        elif (name.startswith("intervals/") or name.startswith("stimulus/")) and obj.size <= 5000:
            r["values"] = [_attr(x) for x in np.atleast_1d(np.asarray(obj[()], dtype=object)).ravel()[:200]]
        rows.append(r)

    h.visititems(visit)
    return rows


def main(ds, max_files=None):
    OUT.mkdir(parents=True, exist_ok=True)
    assets = sorted(mdata.dandi_assets(ds), key=lambda a: a["path"])
    if max_files:
        assets = assets[:int(max_files)]
    res = []
    for a in assets:
        url = f"{mdata.DANDI}/assets/{a['asset_id']}/download/"
        try:
            with h5py.File(mdata.open_url(url), "r") as h:
                res.append({"path": a["path"], "size": a.get("size"), "datasets": walk(h)})
        except Exception as e:  # noqa: BLE001
            res.append({"path": a["path"], "error": repr(e)[:300]})
        print(a["path"], "ok" if "error" not in res[-1] else res[-1]["error"], flush=True)
    (OUT / f"structure_{ds}.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
