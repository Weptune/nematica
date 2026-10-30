"""Download the neuron position atlas used by the replay export.

Skuhersky et al. 2022, "Toward a more accurate 3D atlas of C. elegans neurons",
BMC Bioinformatics (paper CC BY 4.0). The file comes from the authors' repository
https://github.com/bluevex/elegans-atlas, which has no licence file, so it is fetched
from the source rather than redistributed with NEMATICA. Attribute the paper.

Usage:  python scripts/fetch_atlas.py
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

URL = ("https://raw.githubusercontent.com/bluevex/elegans-atlas/master/"
       "LowResAtlasWithHighResHeadsAndTails.csv")
MD5 = "eeb5e18f98d1fbc0bd60254016c74486"   # the version NEMATICA was built and tested with
OUT = Path(__file__).resolve().parents[1] / "data_assets" / "skuhersky2022_atlas.csv"


def main() -> int:
    if OUT.exists() and hashlib.md5(OUT.read_bytes()).hexdigest() == MD5:
        print(f"{OUT} already present")
        return 0
    with urllib.request.urlopen(URL, timeout=60) as r:
        data = r.read()
    digest = hashlib.md5(data).hexdigest()
    if digest != MD5:
        print(f"warning: checksum {digest} differs from the tested version {MD5}; "
              "the atlas may have changed upstream", file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(data)
    print(f"wrote {OUT} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
