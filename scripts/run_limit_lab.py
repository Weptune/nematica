"""Watching limit, part A (pre-registered 7 Nov 2026, README "The watching limit"):
linear lab networks with known truth. For each network and recording length: the Cramer-Rao
bound's expected agreement, the best watcher (Whittle MLE of the correct model class, k known,
best of 2 generic starts) and the VAR(1) watcher. Agreement: correlation of estimated and true
off-diagonal poke responses (15 s summed).

Usage:  python scripts/run_limit_lab.py [--part i/k]
Output: docs/figures/limit_lab.csv (resumable)
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica import limits as L  # noqa: E402

OUT = ROOT / "docs" / "figures" / "limit_lab.csv"
N, K = 10, 2
TS = (1000, 4000, 16000)


def conditions():
    out = []
    for load in (0.5, 1.0, 2.0):
        for rho in (0.9, 0.98):
            for seed in (0, 1, 2):
                out.append(dict(kind="drive", load=load, drho=rho, seed=seed))
    for seed in (0, 1, 2):
        out.append(dict(kind="unit", load=0.0, drho=0.0, seed=seed))
    return out


def net_of(c):
    if c["kind"] == "drive":
        return L.random_net(n=N, k=K, seed=c["seed"], drive_load=c["load"], drive_rho=c["drho"],
                            hidden_kind="drive")
    return L.random_net(n=N, k=K, seed=c["seed"], hidden_kind="unit")


def drive_share(net):
    """Share of seen units' stationary variance that comes from the hidden units."""
    d, n = net.d, net.n
    import scipy.linalg as sl
    S = sl.solve_discrete_lyapunov(net.F, net.Q)
    F0 = net.F.copy()
    F0[:n, n:] = 0
    S0 = sl.solve_discrete_lyapunov(F0, net.Q)
    return float(1 - np.trace(S0[:n, :n]) / np.trace(S[:n, :n]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="0/1")
    a = ap.parse_args()
    pi, pk = [int(x) for x in a.part.split("/")]
    rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
    done = {(r["kind"], r["load"], r["drho"], r["seed"], r["T"]) for r in rows}
    cells = [(c, T) for c in conditions() for T in TS]
    for ci, (c, T) in enumerate(cells):
        if ci % pk != pi:
            continue
        key = (c["kind"], str(c["load"]), str(c["drho"]), str(c["seed"]), str(T))
        if key in done:
            continue
        t0 = time.time()
        net = net_of(c)
        G = L.offdiag(L.poke_response(net.F, N))
        cov, info = L.crb_G(net, T)
        b_mean, b_lo, b_hi = L.agreement_from_cov(G, cov)
        y = L.simulate(net, T, np.random.default_rng(7919 * T + 31 * c["seed"] + int(100 * c["load"] + 10 * c["drho"])))
        best = None
        for s in range(2):
            Gh, _, loss = L.whittle_fit([y], N, K, steps=800, lr=0.01, band=max(4, T // 1000), seed=s)
            if best is None or loss < best[1]:
                best = (Gh, loss)
        mle = float(np.corrcoef(L.offdiag(best[0]), G)[0, 1])
        var = float(np.corrcoef(L.offdiag(L.var_watcher([y], N)), G)[0, 1])
        row = dict(kind=c["kind"], load=c["load"], drho=c["drho"], seed=c["seed"], T=T,
                   hidden_share=round(drive_share(net), 4), bound=round(b_mean, 4), bound_lo=round(b_lo, 4),
                   bound_hi=round(b_hi, 4), best=round(mle, 4), var=round(var, 4),
                   cond=f"{info['cond']:.2e}", secs=round(time.time() - t0, 1))
        print(row, flush=True)
        rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
        rows.append(row)
        with OUT.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(row))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
