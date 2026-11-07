"""Spiking network on the same tests (pre-registered 7 Nov 2026, README "A spiking network on the same
tests, and what makes neurons tire"). Variants S0 to S3, plus the amendment's 4x-gain S2 and S3.

Usage:  python scripts/run_spiking.py [variant ...]
Output: docs/figures/spiking.csv (resumable), docs/figures/checks/matched_sham_state_spk*.txt
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica import spiking as S  # noqa: E402
import run_week1 as W1  # noqa: E402
import run_ladder as LD  # noqa: E402
import check_matched_sham as M  # noqa: E402

OUT = ROOT / "docs" / "figures" / "spiking.csv"
ALL = ["S0", "S1", "S2", "S3", "S2x4", "S3x4", "S4", "S6", "S5"]


def run(name):
    worm_gaps = name.endswith("@w")
    core = name[:-2] if worm_gaps else name
    base = core[:2]
    kf, kd = S.KF, S.KD
    if core.endswith("x4") or core in ("S4", "S5"):
        S.KF, S.KD = 4 * kf, 4 * kd
    try:
        recs = S.recordings(base, n_targets=14 if worm_gaps else None)
    finally:
        S.KF, S.KD = kf, kd
    valid = lambda c: True  # noqa: E731
    worms = [W1.Worm(r, valid_fn=valid) for r in recs]
    fp = LD.fingerprint(worms)
    # state test on real pokes, then matched shams (state and echo)
    ws = [w for w in worms if W1.pc1_state(w) is not None]
    W1.FIG = M.CHK
    W1.run_b2(worms=ws, state_fn=W1.aligned_state_fn(ws), fname=f"state_spk{name}_real.txt", exclude=None)
    real = (M.CHK / f"state_spk{name}_real.txt").read_text().splitlines()
    M.state_test(f"spk{name}", recs, valid_fn=valid)
    sham = (M.CHK / f"matched_sham_state_spk{name}.txt").read_text().splitlines()
    ex = M.echo_excess(f"spk{name}", recs, valid_fn=valid)
    pick = lambda lines: next(l for l in lines if l.startswith("median S minus null"))  # noqa: E731
    rate = float(np.mean([np.nanmean(r.x) for r in recs]) * 20)
    row = {"variant": name, **{k: round(v, 4) for k, v in fp.items()}, "mean_rate_hz": round(rate, 2),
           "state_real": pick(real).split(":")[1].strip(), "state_matched_sham": pick(sham).split(":")[1].strip(),
           "echo_sparseness_excess": ex["sparseness_excess"], "echo_persistence_excess": ex["persistence_excess"],
           "echo_pe_lo": ex["pe_lo"], "echo_pe_hi": ex["pe_hi"]}
    print(row, flush=True)
    rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
    rows = [r for r in rows if r["variant"] != name] + [row]
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    for v in (sys.argv[1:] or ALL):
        run(v)
