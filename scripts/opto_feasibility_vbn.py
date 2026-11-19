"""Study O follow-up feasibility on Allen Visual Behavior Neuropixels (DANDI 000713): metadata only, the
earliest session of each mouse. Same probe as scripts/opto_feasibility.py; no spike or response read.
Output: docs/figures/opto/feasibility_vbn.jsonl (resumable)."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import h5py  # noqa: E402

from nematica.map import data as mdata  # noqa: E402
from opto_feasibility import probe  # noqa: E402

OUT = ROOT / "docs/figures/opto/feasibility_vbn.jsonl"


def main():
    done = {json.loads(l)["id"] for l in OUT.open()} if OUT.exists() else set()
    A = [a for a in mdata.dandi_assets("000713") if re.fullmatch(r"sub-\d+/sub-\d+_ses-[0-9T]+\.nwb", a["path"])]
    first = {}
    for a in sorted(A, key=lambda a: a["path"]):
        first.setdefault(a["path"].split("/")[0], a)
    for uid, a in sorted(first.items()):
        if uid in done:
            continue
        try:
            with h5py.File(mdata.open_url(f"{mdata.DANDI}/assets/{a['asset_id']}/download/"), "r") as h:
                r = probe(h)
                if "units" in h:
                    r["n_units"] = int(h["units/id"].shape[0])
        except Exception as e:  # noqa: BLE001
            r = {"error": repr(e)[:200]}
        r.update(id=uid, dandiset="000713", path=a["path"])
        with OUT.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(uid, r.get("genotype"), r.get("opto_n"), r.get("opto_stimulus_name"), r.get("error", ""), flush=True)


if __name__ == "__main__":
    main()
