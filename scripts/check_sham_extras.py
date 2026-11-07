"""Code for two 7 Nov sham checks that were run interactively and not committed at the time (review 6,
item 3): perturbational complexity and spread at sham onsets (worms), and the state test run on the
first (30 s rule) shams for worms and the base and drives lab brains. Sham construction as
scripts/check_echo_sham.py (seed 0).

Usage:  python scripts/check_sham_extras.py
Output: printed; state files in docs/figures/checks/
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica.bench.perturbational import event_matrices  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from check_echo_sham import sham  # noqa: E402
import run_week1 as W  # noqa: E402
import run_ladder as LD  # noqa: E402


def pci_check():
    worms = load_pumpprobe_dir(str(W.ATLAS))
    for name, rr in (("real", worms), ("sham", sham(worms))):
        ev = [e for r in rr for e in event_matrices(r)]
        print(name, "events", len(ev), "PCI median", round(float(np.nanmedian([e["pci"] for e in ev])), 4),
              "spread median", round(float(np.nanmedian([e["spread"] for e in ev])), 4), flush=True)


def state_check():
    W.FIG = ROOT / "docs" / "figures" / "checks"
    rs = sorted(load_pumpprobe_dir(W.ATLAS), key=lambda r: r.uid)
    ws = [w for w in (W.Worm(r) for r in sham(rs, seed=0)) if W.pc1_state(w) is not None]
    W.run_b2(worms=ws, state_fn=W.aligned_state_fn(ws), fname="b2_pc1_aligned_worms_SHAM.txt", exclude=None)
    for name, code in (("base", ""), ("D", "D")):
        recs = LD.variant_recs(code, 0)
        for kind, rr in (("real", recs), ("sham", sham(recs, seed=0))):
            lw = [w for w in (W.Worm(r, valid_fn=lambda c: True) for r in rr) if W.pc1_state(w) is not None]
            W.run_b2(worms=lw, state_fn=W.aligned_state_fn(lw), fname=f"b2_pc1_aligned_lab_{name}_{kind}_check.txt",
                     exclude=None)


if __name__ == "__main__":
    pci_check()
    state_check()
