"""Matched shams (pre-registered 7 Nov 2026, README "Matched shams: are the worm's state dependence and
echo specific to pokes?").

For each real stimulation, a sham onset is drawn (seed 0) from the state test's own pseudo-onset pool in
the same recording: every 5th frame t with no stimulation in [t - PRE, t + POST) and a finite 10 s state
value (aligned PC1, as run_week1.run_b2), keeping the target. Real stimulations stay in the recording.

Test 1: run_week1.run_b2 on the matched shams (worms, base and drives lab brains).
Test 2: per-event echo sparseness and persistence (run_echo_sparse.measures) at real pokes minus at their
matched shams, per recording; median over recordings with a 90% bootstrap interval (worms; base, drives
and silent-links lab brains, 40 individuals each).

Usage:  python scripts/check_matched_sham.py
Output: docs/figures/checks/matched_sham_state_*.txt, docs/figures/matched_sham_echo.csv
"""
from __future__ import annotations

import csv
import dataclasses
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_week1 as W  # noqa: E402
import run_ladder as LD  # noqa: E402
from run_echo_sparse import measures  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402

CHK = ROOT / "docs" / "figures" / "checks"


def matched_sham(worms, state_fn, seed=0):
    """worms: run_week1.Worm objects of the real recordings. Returns sham PumpProbe recordings (None
    where no pool exists)."""
    rng = np.random.default_rng(seed)
    out = []
    for w in worms:
        z = state_fn(w)
        if z is None or not np.isfinite(z).any():
            out.append(None)
            continue
        T = w.T
        s10 = np.full(T, np.nan)
        for t in range(W.PRE, T):
            seg = z[t - W.PRE:t]
            if np.isfinite(seg).sum() >= W.PRE // 2:
                s10[t] = np.nanmean(seg)
        pool = [t for t in range(W.PRE, T - W.POST, 5)
                if np.isfinite(s10[t]) and not any(t - W.PRE <= f < t + W.POST for f in w.r.all_stim_frames)]
        if not pool:
            out.append(None)
            continue
        out.append(dataclasses.replace(w.r, stims=[(k, int(rng.choice(pool))) for k, _ in w.r.stims]))
    return out


def state_test(name, recs, valid_fn=None):
    ws = [W.Worm(r, valid_fn=valid_fn) for r in recs]
    ws = [w for w in ws if W.pc1_state(w) is not None]
    fn = W.aligned_state_fn(ws)
    sham = [r for r in matched_sham(ws, fn) if r is not None]
    sw = [W.Worm(r, valid_fn=valid_fn) for r in sham]
    sw = [w for w in sw if W.pc1_state(w) is not None]
    print(f"=== state test, matched sham: {name}", flush=True)
    W.FIG = CHK
    W.run_b2(worms=sw, state_fn=W.aligned_state_fn(sw), fname=f"matched_sham_state_{name}.txt", exclude=None)
    return ws, fn


def echo_excess(name, recs, valid_fn=None, seed=0):
    ws = [W.Worm(r, valid_fn=valid_fn) for r in recs]
    ws = [w for w in ws if W.pc1_state(w) is not None]
    fn = W.aligned_state_fn(ws)
    shams = matched_sham(ws, fn, seed=seed)
    dsp, dpe = [], []
    for w, sh in zip(ws, shams):
        if sh is None:
            continue
        a, b = measures([w.r]), measures([sh])
        if a["pokes"] < 5 or b["pokes"] < 5:
            continue
        dsp.append(a["ever_respond"] - b["ever_respond"])
        dpe.append(a["mean_run"] - b["mean_run"])
    rng = np.random.default_rng(1)

    def summ(v):
        v = np.array(v)
        bs = [np.median(v[rng.integers(0, len(v), len(v))]) for _ in range(2000)]
        return float(np.median(v)), *[float(x) for x in np.percentile(bs, [5, 95])]
    s, sl, sh_ = summ(dsp)
    p, pl, ph = summ(dpe)
    row = {"system": name, "recordings": len(dsp), "sparseness_excess": round(s, 4), "sp_lo": round(sl, 4),
           "sp_hi": round(sh_, 4), "persistence_excess": round(p, 3), "pe_lo": round(pl, 3), "pe_hi": round(ph, 3)}
    print(row, flush=True)
    return row


def main():
    CHK.mkdir(parents=True, exist_ok=True)
    worms = sorted(load_pumpprobe_dir(W.ATLAS), key=lambda r: r.uid)
    labs = {"base": LD.variant_recs("", 0), "D": LD.variant_recs("D", 0)}
    lab_valid = lambda c: True  # noqa: E731
    state_test("worms", worms)
    for name, recs in labs.items():
        state_test(f"lab_{name}", recs, valid_fn=lab_valid)
    rows = [echo_excess("worms", worms)]
    labs40 = {"lab base": LD.variant_recs("", 0, n_ind=40), "lab D": LD.variant_recs("D", 0, n_ind=40),
              "lab G": LD.variant_recs("G", 0, n_ind=40)}
    for name, recs in labs40.items():
        rows.append(echo_excess(name, recs, valid_fn=lab_valid))
    with (ROOT / "docs" / "figures" / "matched_sham_echo.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
