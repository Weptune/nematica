"""Score your own brain copy on the NEMATICA ruler.

A brain copy is any program that, given a worm's list of neurons and a schedule of pokes,
produces activity for those neurons. It is judged the way real worms judge each other: its
simulated worms are compared with held-out real worms, and the verdict for each level is
inside (as close to real worms as they are to each other), outside (further) or too typical
(closer than real worms ever are to each other).

Write a copy:

    import numpy as np
    from nematica.score import BrainCopy

    class MyCopy(BrainCopy):
        name = "my-copy"

        def fit(self, worms):
            # worms: training recordings (nematica.data.pumpprobe.PumpProbe): uid,
            # x (neurons x frames, NaN where not tracked), names, classes, stims, dt
            ...

        def run(self, worm, rng):
            # worm: a Template: names, n_frames, dt and pokes. Each poke names the neuron
            # switched on, the frame, and `drive`: that neuron's own measured response in
            # the real worm (in units of its SD, from its pre-poke baseline). Hold the poked
            # neuron to its drive, or use it as an input, and let the rest respond.
            # Return an array (len(worm.names), worm.n_frames); NaN rows for neurons the
            # copy does not model.
            ...

Score it:

    python -m nematica score path/to/my_copy.py:MyCopy            # both frozen splits
    python -m nematica score path/to/my_copy.py:MyCopy --quick    # one fold, about 5 min

The recordings are not redistributed: see scripts/convert_pumpprobe.py for where to get them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from .bench.causal import window
from .bench.scorecard import ACTIVITY_LEVELS, POKE_LEVELS, SPLITS, SPLITS_DIR, FoldRuler, fold_parts, set_norm
from .data.pumpprobe import PumpProbe, load_pumpprobe_dir, neuron_class
from .data.splits import load_folds

PCI = ("P1.complexity", "P2.spread")


@dataclass(frozen=True)
class Poke:
    neuron: str          # name of the neuron switched on, e.g. "AVAL"
    index: int           # its row in Template.names
    frame: int           # frame at which the light pulse starts
    drive: np.ndarray    # its measured response from that frame on, in SD units from baseline


@dataclass(frozen=True)
class Template:
    uid: str
    names: tuple         # neuron names in the real worm ("" where unidentified)
    n_frames: int
    dt: float            # seconds per frame (0.5)
    pokes: tuple = field(default_factory=tuple)

    @property
    def classes(self) -> list[str]:
        """Left/right partners pooled: AVAL and AVAR are both AVA."""
        return [neuron_class(n) for n in self.names]


class BrainCopy:
    """Base class for a copy to be scored. Override run(); fit() is optional."""

    name = "copy"

    def fit(self, worms: Sequence[PumpProbe]) -> None:
        return None

    def run(self, worm: Template, rng: np.random.Generator) -> np.ndarray:
        raise NotImplementedError


def template_of(rec: PumpProbe) -> Template:
    """What a copy is told about a held-out worm: its neurons, its length and its pokes. The
    drive is computed exactly as NEMATICA's own models compute it."""
    npre, npost = window(rec.dt)
    sd = np.nanstd(rec.x, axis=1)
    pokes = []
    for k, f in rec.stims:
        if f - npre < 0 or f + npost > rec.n_frames or not sd[k] > 0:
            continue
        drive = (rec.x[k, f:f + npost] - np.nanmean(rec.x[k, f - npre:f])) / sd[k]
        pokes.append(Poke(rec.names[k], k, int(f), np.asarray(drive, float)))
    return Template(rec.uid, tuple(rec.names), rec.n_frames, rec.dt, tuple(pokes))


class CopyAdapter:
    """Turns a BrainCopy into the fit / simulate pair the ruler calls."""

    def __init__(self, copy: BrainCopy):
        self.copy = copy

    def fit(self, train, val):
        self.copy.fit(list(train) + list(val))
        return self

    def simulate(self, rec: PumpProbe, rng: np.random.Generator) -> PumpProbe:
        tpl = template_of(rec)
        x = np.asarray(self.copy.run(tpl, rng), float)
        if x.shape != (len(tpl.names), tpl.n_frames):
            raise ValueError(f"{self.copy.name}.run returned shape {x.shape}; expected "
                             f"({len(tpl.names)}, {tpl.n_frames}) for worm {tpl.uid}")
        keep = [j for j, n in enumerate(tpl.names) if neuron_class(n) and np.isfinite(x[j]).any()]
        row = {j: i for i, j in enumerate(keep)}
        stims = [(row[p.index], p.frame) for p in tpl.pokes if p.index in row]
        return PumpProbe(uid=rec.uid, x=x[keep], names=[tpl.names[j] for j in keep],
                         classes=[neuron_class(tpl.names[j]) for j in keep], stims=stims, dt=rec.dt,
                         all_stim_frames=list(rec.all_stim_frames))


def load_copy(spec: str) -> Callable[[], BrainCopy]:
    """'path/to/file.py:ClassName' -> a factory that makes a fresh copy for each fold."""
    import importlib.util
    path, _, cls = spec.rpartition(":")
    if not path or not cls:
        raise ValueError("give the copy as path/to/file.py:ClassName")
    p = Path(path).resolve()
    mod_spec = importlib.util.spec_from_file_location(p.stem, p)
    mod = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mod)
    return getattr(mod, cls)


def score(factory, data: str | Path, splits: Sequence[str] = ("cv3", "blocks1"), folds=None,
          pci: bool = True, norm: str = "fluct", log: Callable[[str], None] = print) -> list[dict]:
    """Every (split, fold, level) verdict for the copy made by `factory()`."""
    set_norm(norm)
    recs = {r.uid: r for r in load_pumpprobe_dir(data)}
    if not recs:
        raise FileNotFoundError(f"no pumpprobe_*.npz recordings in {data}")
    rows = []
    for split in splits:
        all_folds = load_folds(SPLITS_DIR / SPLITS[split])["folds"]
        missing = sorted({u for f in all_folds for u in f} - set(recs))
        if missing:
            raise FileNotFoundError(f"{len(missing)} worms of split {split} are missing from {data}, e.g. {missing[0]}")
        for fi in range(len(all_folds)):
            if folds is not None and fi not in folds:
                continue
            log(f"[{split} fold {fi}] building the real-worm ruler")
            ruler = FoldRuler(*fold_parts(recs, all_folds, fi), pci=pci)
            copy = factory()
            model = copy if hasattr(copy, "simulate") else CopyAdapter(copy)
            name = getattr(copy, "name", "copy")
            log(f"[{split} fold {fi}] fitting and running {name} on {len(ruler.pool)} held-out worms")
            for r in ruler.score(name, model, seed_base=1000 * fi):
                rows.append({"split": split, "fold": fi, **r})
    return rows


def echo_agreement(rows: Sequence[dict], key: str = "system_median") -> float:
    """Correlation of echo patterns (1 minus the median C1 distance), averaged over pools:
    with key="system_median", copy against real worms; with "bio_median", real worms against
    each other."""
    v = [1 - float(r[key]) for r in rows if r.get("metric") == "C1.pattern" and key in r]
    return float(np.mean(v)) if v else float("nan")


def summary(rows: Sequence[dict]) -> dict:
    by_level: dict = {}
    for r in rows:
        by_level.setdefault(r["metric"], []).append(r["verdict"])
    def tally(levels):
        cells = [(lv, by_level.get(lv, [])) for lv in levels]
        return {lv: f"{sum(v == 'inside' for v in vs)}/{len(vs)} inside" for lv, vs in cells if vs}
    n_pools = len({(r["split"], r["fold"]) for r in rows})
    watch_all = sum(all(r["verdict"] == "inside" for r in rows if (r["split"], r["fold"]) == key and r["metric"] in ACTIVITY_LEVELS)
                    for key in {(r["split"], r["fold"]) for r in rows})
    poke_all = sum(all(r["verdict"] == "inside" for r in rows if (r["split"], r["fold"]) == key and r["metric"] in POKE_LEVELS)
                   for key in {(r["split"], r["fold"]) for r in rows})
    return {"pools": n_pools, "watching": tally(ACTIVITY_LEVELS), "poking": tally(POKE_LEVELS),
            "complexity": tally(PCI), "pools_passing_all_watching": watch_all,
            "pools_passing_all_poking": poke_all, "echo_agreement": round(echo_agreement(rows), 3),
            "echo_agreement_real": round(echo_agreement(rows, "bio_median"), 3)}


def format_summary(name: str, s: dict) -> str:
    lines = [f"NEMATICA scorecard: {name}  ({s['pools']} held-out pools)", ""]
    for title, key in (("Watching", "watching"), ("Poking", "poking"), ("Complexity", "complexity")):
        if s[key]:
            lines.append(title)
            lines += [f"  {lv:16s} {v}" for lv, v in s[key].items()]
    lines += ["", f"Pools passing every watching test: {s['pools_passing_all_watching']}/{s['pools']}",
              f"Pools passing every poking test:   {s['pools_passing_all_poking']}/{s['pools']}",
              f"Echo agreement with real worms:    {s['echo_agreement']}  (real worms with each other: {s['echo_agreement_real']})"]
    return "\n".join(lines)


def write_report(name: str, rows: Sequence[dict], out: str | Path) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"copy": name, "summary": summary(rows), "rows": list(rows)}, indent=1, default=float),
                   encoding="utf-8")
    return out
