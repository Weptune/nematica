"""Fetch 30 Atanas et al. 2023 recordings in WormWideWeb JSON format.

Source: a third-party copy inside github.com/mmtree/Celegans_premotor (Morrison & Young
2025), fetched with a sparse git checkout of data/Atanas_data only (about 260 MB).
The original release is Zenodo 10.5281/zenodo.8150514 / WormWideWeb. This copy is for
local development; check the original terms before redistributing anything derived.

Usage:  python scripts/fetch_atanas_copy.py [--dest data/raw/atanas2023_wwweb]
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "https://github.com/mmtree/Celegans_premotor.git"
SUBDIR = "data/Atanas_data"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="data/raw/atanas2023_wwweb")
    args = ap.parse_args()
    dest = Path(args.dest)
    if dest.exists() and any(dest.glob("*.json")):
        print(f"{dest} already has JSON files; nothing to do.")
        return 0
    if shutil.which("git") is None:
        print("git is required", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "repo"
        run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", REPO, str(clone)])
        run(["git", "sparse-checkout", "set", SUBDIR], cwd=clone)
        src = clone / SUBDIR
        files = sorted(src.glob("*.json"))
        if not files:
            print("No JSON files found in the checkout", file=sys.stderr)
            return 1
        dest.mkdir(parents=True, exist_ok=True)
        lines = []
        for f in files:
            target = dest / f.name
            shutil.copy2(f, target)
            lines.append(f"{sha256(target)}  {f.name}")
        (dest / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (dest / "SOURCE.txt").write_text(
            f"Copied from {REPO} ({SUBDIR}).\n"
            "Original data: Atanas, Kim et al. 2023, Cell; Zenodo 10.5281/zenodo.8150514.\n",
            encoding="utf-8",
        )
    print(f"Copied {len(files)} recordings to {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
