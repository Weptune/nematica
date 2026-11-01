"""The optogenetic signal-propagation atlas (Randi et al. 2023, OSF project e2syt), converted
from the archive's exported_data folder to one .npz per recording ("pumpprobe" recordings;
the same packaging also appears in Creamer et al.'s data release):

    x            (T, N) float32 fluorescence, NaN where a neuron was not tracked
    ids          (N,) neuron names, "" where unidentified
    stim_cell    (S,) index of the stimulated neuron; negative = target not tracked
    stim_frame   (S,) frame of each stimulation

Convert the original text folders with `python scripts/convert_pumpprobe.py`. Local use only.
Some loaders here also read the separate Creamer et al. 2025 packaging (data/raw/2025_creamer_lds_npz).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

FRAME_S = 0.5   # [M] frame interval: the original OSF files carry time stamps 0.5 s apart

# classes whose members carry a dorsal/ventral letter before the side (RMDDL, SMDVR, IL1VL)
_DV_CLASSES = {"RMD", "SMD", "SMB", "SIA", "SIB", "SAA", "URY", "URA", "OLQ", "CEP", "IL1", "IL2", "RME", "GLR"}
# unpaired neurons whose name ends in L or R that is part of the name, not a side
_NOT_SIDES = {"AVL", "DVA", "ALA", "RIR", "AQR", "PQR", "AVG", "RIS", "RID", "AMSO"}


def neuron_class(name: str) -> str:
    """Neuron name to the class used across NEMATICA (AVAL -> AVA, RMDVR -> RMD, VA1 -> VA01)."""
    n = name.strip().upper()
    if not n:
        return ""
    m = re.fullmatch(r"([A-Z]{2})(\d+)", n)              # motor neurons: VA1 -> VA01
    if m:
        return f"{m.group(1)}{int(m.group(2)):02d}"
    if n in _NOT_SIDES:
        return n
    if n in ("MCL", "MCR"):
        return "MC"
    side = n[-1] in "LR" and (len(n) >= 4 or re.fullmatch(r"[A-Z]\d[LR]", n) is not None)
    base = n[:-1] if side else n
    if base[-1:] in ("D", "V") and base[:-1] in _DV_CLASSES:
        base = base[:-1]
    return base


@dataclass
class PumpProbe:
    uid: str
    x: np.ndarray                  # (N, T) fluorescence
    names: list[str]
    classes: list[str]
    stims: list[tuple[int, int]]   # (neuron index, frame), tracked targets only
    dt: float = FRAME_S
    n_untracked_stims: int = 0
    all_stim_frames: list = field(default_factory=list)   # every stimulation, tracked target or not
    meta: dict = field(default_factory=dict)

    @property
    def n_frames(self) -> int:
        return self.x.shape[1]


def load_pumpprobe(path: str | Path) -> PumpProbe:
    path = Path(path)
    with np.load(path, allow_pickle=False) as z:
        x = np.asarray(z["x"], dtype=float).T
        names = [str(s) for s in z["ids"]]
        sc = np.asarray(z["stim_cell"], dtype=int)
        sf = np.asarray(z["stim_frame"], dtype=int)
    if len(names) != x.shape[0]:
        raise ValueError(f"{path.name}: {len(names)} ids for {x.shape[0]} neurons")
    ok = (sc >= 0) & (sc < x.shape[0]) & (sf >= 0) & (sf < x.shape[1])
    stims = [(int(c), int(f)) for c, f in zip(sc[ok], sf[ok])]
    return PumpProbe(uid=path.stem.replace("pumpprobe_", ""), x=x, names=names,
                     classes=[neuron_class(n) for n in names], stims=stims,
                     n_untracked_stims=int((~ok).sum()), all_stim_frames=[int(f) for f in sf])


def load_pumpprobe_dir(folder: str | Path) -> list[PumpProbe]:
    return [load_pumpprobe(p) for p in sorted(Path(folder).glob("pumpprobe_*.npz"))]
