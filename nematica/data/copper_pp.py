"""The copper set (Baskoylu et al. 2026, Dryad; freely moving worms, Flavell-lab pipeline) in the PumpProbe
shape, as atanas_pp does for Atanas et al. 2023, so the same-worms pipeline and the emulator can run on it:
no stimulations; unlabelled rows keep an empty class; classes use NEMATICA's naming."""
from __future__ import annotations
from pathlib import Path
import numpy as np
from .copper import load_copper_dir
from .pumpprobe import PumpProbe, neuron_class


def load_copper_pp_dir(folder: str | Path) -> list[PumpProbe]:
    out = []
    for m in load_copper_dir(Path(folder)):
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
        out.append(PumpProbe(uid=m.uid, x=x, names=names, classes=classes, stims=[], dt=float(np.median(np.diff(m.t))), all_stim_frames=[]))
    return out
