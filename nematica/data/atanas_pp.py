"""Atanas et al. 2023 freely moving recordings (WormWideWeb JSON) in the PumpProbe shape, so the
same-worms pipeline and the emulator can run on them: no stimulations; unlabelled rows keep an
empty class; classes use NEMATICA's naming (pumpprobe.neuron_class)."""
from __future__ import annotations
from pathlib import Path
import numpy as np
from .pumpprobe import PumpProbe, neuron_class
from .wormwideweb import load_wormwideweb_json


def load_atanas_pp(path: str | Path) -> PumpProbe:
    m = load_wormwideweb_json(Path(path))
    names, classes = [], []
    for i in range(m.traces.shape[0]):
        lab = m.labels.get(i)
        if lab is None:
            names.append(""); classes.append("")
        else:
            names.append(lab.name)
            classes.append(neuron_class(lab.name.replace("?", "")) or lab.neuron_class)
    x = np.asarray(m.traces, dtype=float)
    if m.valid is not None:
        x = x[:, np.asarray(m.valid, bool)]
    return PumpProbe(uid=m.uid, x=x, names=names, classes=classes, stims=[], dt=float(m.frame_interval),
                     all_stim_frames=[])


def load_atanas_pp_dir(folder: str | Path) -> list[PumpProbe]:
    return [load_atanas_pp(p) for p in sorted(Path(folder).glob("*.json"))]
