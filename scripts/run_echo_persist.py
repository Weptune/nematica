"""What could make responses last? (pre-registered 6 Nov 2026; README, after the matched echo re-test).
Usage: python scripts/run_echo_persist.py   Output: docs/figures/echo_persist.csv"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_echo_matched as EM  # noqa: E402
import run_ladder as LD  # noqa: E402
from nematica import annlab as L  # noqa: E402

OUT = ROOT / "docs" / "figures" / "echo_persist.csv"
R9 = {"share": 0.4, "g": 0.75, "spread": 0.15, "quiet": 0.3, "mod": 0}


def recs(system, hold, rho=1.3):
    LD.KICK_HOLD["frames"] = hold
    if system == "base":
        if rho != 1.3:
            br0 = L.make_brain(rho=rho, share=0.0, tau=90.0, seed=0, q=0.2)
            orig = L.make_brain
            L.make_brain = lambda **kw: br0
            try:
                out = LD.variant_recs("", 0, n_ind=30)
            finally:
                L.make_brain = orig
        else:
            out = LD.variant_recs("", 0, n_ind=30)
    else:
        out = LD.param_recs(R9, 0, n_ind=30, sigma=0.8)
    LD.KICK_HOLD["frames"] = LD.KICK_FRAMES
    return EM.paired(out)


def main():
    EM.TAU["t"] = 1.5
    LD.record = EM.record_ca
    rows = []
    jobs = [("base", "unchanged", 4, 0.5, 1.3), ("base", "hold 8", 8, 0.5, 1.3), ("base", "hold 16", 16, 0.5, 1.3),
            ("base", "leak 0.25", 4, 0.25, 1.3), ("base", "leak 0.1", 4, 0.1, 1.3), ("base", "rho 1.6", 4, 0.5, 1.6),
            ("round9", "unchanged", 6, 0.5, 1.3), ("round9", "hold 16", 16, 0.5, 1.3),
            ("round9", "leak 0.25", 6, 0.25, 1.3), ("round9", "leak 0.1", 6, 0.1, 1.3)]
    for system, change, hold, leak, rho in jobs:
        L.LEAK = leak
        rows.append(EM.summary(f"{system}: {change}", EM.per_rec(recs(system, hold, rho))))
        L.LEAK = 0.5
        with OUT.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
