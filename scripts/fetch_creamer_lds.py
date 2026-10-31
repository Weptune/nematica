"""Fetch the three trained models of Creamer, Leifer & Pillow (2024, bioRxiv
10.1101/2024.09.22.614271; MIT licence, github.com/Nondairy-Creamer/Creamer_LDS_2024) and
convert their parameters to plain .npz files under data/external/creamer_lds/.

The pickles are read as data only (nematica.data.safe_pickle): none of the authors' code is
imported or run. Kept: dynamics weights A (154 x 154, one lag), dynamics noise covariance Q,
emissions covariance R (emissions are the identity), neuron names, sample rate (2 Hz).

Usage:
  python scripts/fetch_creamer_lds.py [--from-clone path/to/Creamer_LDS_2024]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.data.safe_pickle import load  # noqa: E402

COMMIT = "bba43302d50a4947804d98b01779856e648237cc"
URL = "https://raw.githubusercontent.com/Nondairy-Creamer/Creamer_LDS_2024/{commit}/models/{name}.pkl"
MODELS = ("connectome_constrained", "fully_connected", "shuffled_constrained")
OUT = Path(__file__).resolve().parents[1] / "data" / "external" / "creamer_lds"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-clone")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for name in MODELS:
        pkl = OUT / f"{name}.pkl"
        if args.from_clone:
            pkl.write_bytes((Path(args.from_clone) / "models" / f"{name}.pkl").read_bytes())
        elif not pkl.exists():
            print(f"downloading {name}")
            with urllib.request.urlopen(URL.format(commit=COMMIT, name=name), timeout=120) as r:
                pkl.write_bytes(r.read())
        m = load(pkl)
        A = np.asarray(m.dynamics_weights, float)
        if m.dynamics_lags != 1 or A.shape != (m.dynamics_dim, m.dynamics_dim):
            raise ValueError(f"{name}: unexpected dynamics shape {A.shape}, lags {m.dynamics_lags}")
        if not np.allclose(m.emissions_weights, np.eye(m.emissions_dim)):
            raise ValueError(f"{name}: emissions are not the identity")
        np.savez(OUT / f"{name}.npz", A=A, Q=np.asarray(m.dynamics_cov, float),
                 R=np.asarray(m.emissions_cov, float), cell_ids=np.array([str(c) for c in m.cell_ids]),
                 sample_rate=float(m.sample_rate), source=f"Creamer_LDS_2024@{COMMIT}/models/{name}.pkl",
                 pkl_md5=hashlib.md5(pkl.read_bytes()).hexdigest())
        rho = np.max(np.abs(np.linalg.eigvals(A)))
        print(f"{name}: {A.shape[0]} neurons, {int((A != 0).sum())} weights, spectral radius {rho:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
