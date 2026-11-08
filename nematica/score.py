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


def score(factory, data: str | Path | Sequence[PumpProbe], splits: Sequence[str] = ("cv3", "blocks1"), folds=None,
          pci: bool = True, norm: str = "fluct", log: Callable[[str], None] = print, seeds: int = 1,
          split_files: dict | None = None) -> list[dict]:
    """Every (split, fold, seed, level) verdict for the copy made by `factory()`.

    `data`: a folder of converted recordings, or the recordings themselves. `seeds`: how many
    times each held-out worm is simulated with fresh noise (the copy is fitted once per fold;
    seed s uses rng seeds 1000 * fold + worm + 100000 * s, so seed 0 matches the research runs).
    `split_files`: {name: path to a folds YAML}, in place of the two frozen atlas splits."""
    set_norm(norm)
    recs = ({r.uid: r for r in load_pumpprobe_dir(data)} if isinstance(data, (str, Path))
            else {r.uid: r for r in data})
    if not recs:
        raise FileNotFoundError(f"no pumpprobe_*.npz recordings in {data}")
    paths = split_files or {s: SPLITS_DIR / SPLITS[s] for s in splits}
    rows = []
    for split in (split_files or splits):
        all_folds = load_folds(paths[split])["folds"]
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
            for sd in range(seeds):
                for r in ruler.score(name, model, seed_base=1000 * fi + 100000 * sd, refit=sd == 0):
                    rows.append({"split": split, "fold": fi, "seed": sd, **r})
                if seeds > 1:
                    log(f"[{split} fold {fi}] seed {sd + 1}/{seeds} done")
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
    agree = {}
    for r in rows:
        if r.get("metric") in POKE_LEVELS and "equivalence" in r:
            agree.setdefault(r["metric"], []).append(r["equivalence"] == "agrees")
    return {"pools": n_pools, "watching": tally(ACTIVITY_LEVELS), "poking": tally(POKE_LEVELS),
            "poking_agrees": {lv: f"{sum(v)}/{len(v)} agree within tolerance" for lv, v in agree.items()},
            "complexity": tally(PCI), "pools_passing_all_watching": watch_all,
            "pools_passing_all_poking": poke_all, "echo_agreement": round(echo_agreement(rows), 3),
            "echo_agreement_real": round(echo_agreement(rows, "bio_median"), 3)}


def format_answers(name: str, rows: Sequence[dict]) -> str:
    """The benchmark's answer in plain text: the rule per split and seed, then each level's verdict
    letters and excess distance (0 = as far from real worms as real worms are from each other)."""
    from .bench.verdicts import REST_LEVELS, POKE_RULE_LEVELS, OTHER_LEVELS, answers, rule_text
    a = answers(rows)
    out = [f"NEMATICA benchmark: {name}", rule_text(), ""]
    for split, d in a.items():
        n = d["seeds"]
        out.append(f"Split {split} ({d['pools']} held-out pools, {n} noise seed{'s' if n > 1 else ''}): "
                   f"passes at rest in {d['rest_pass_seeds']}/{n}, when poked in {d['poke_pass_seeds']}/{n}, "
                   f"both in {d['both_pass_seeds']}/{n}; every level in {d['all_nine_seeds']}/{n}")
        out.append(f"  {'level':24s} {'verdicts by seed':22s} {'excess distance (median, range over pools)'}")
        for group, lvls in (("at rest", REST_LEVELS), ("when poked", POKE_RULE_LEVELS), ("not in the rule", OTHER_LEVELS)):
            out.append(f"  {group}")
            for lv in lvls:
                L = d["levels"].get(lv)
                if not L:
                    continue
                letters = " ".join(L["letters"].values())
                ex = (f"{L['excess_median']:+.2f} ({L['excess_min']:+.2f} to {L['excess_max']:+.2f}); further than real "
                      f"in {L['runs_further']}/{L['runs']}") if L["excess_median"] is not None else "not scored"
                out.append(f"    {L['label']:22s} {letters:22s} {ex}")
        out.append("")
    out.append("Letters: one per held-out pool. I inside (no difference from real worm-to-worm variation detected), "
               "O outside (too different), T too typical (closer to real worms than they are to each other).")
    return "\n".join(out)


def format_summary(name: str, s: dict) -> str:
    lines = [f"NEMATICA scorecard: {name}  ({s['pools']} held-out pools)", ""]
    for title, key in (("Watching", "watching"), ("Poking", "poking"), ("Complexity", "complexity")):
        if s[key]:
            lines.append(title)
            lines += [f"  {lv:16s} {v}" + (f"; {s['poking_agrees'][lv]}" if key == "poking" and lv in s.get("poking_agrees", {}) else "")
                      for lv, v in s[key].items()]
    lines += ["", f"Pools passing every watching test: {s['pools_passing_all_watching']}/{s['pools']}",
              f"Pools passing every poking test:   {s['pools_passing_all_poking']}/{s['pools']}",
              f"Echo agreement with real worms:    {s['echo_agreement']}  (real worms with each other: {s['echo_agreement_real']})"]
    return "\n".join(lines)


def write_report(name: str, rows: Sequence[dict], out: str | Path, meta: dict | None = None) -> Path:
    from .bench.verdicts import answers
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = dict(meta or {})
    if not meta.get("worms"):
        meta.pop("worms", None)
    doc = {"copy": name, "meta": meta, "answers": answers(rows), "summary": summary(rows), "rows": list(rows)}
    out.write_text(json.dumps(doc, indent=1, default=_json_default), encoding="utf-8")
    return out


def _json_default(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return str(v)


def check(factory, data, log: Callable[[str], None] = print) -> list[str]:
    """A fast contract check before a full run: fits the copy on a few training worms, runs it on one
    held-out worm, and reports problems (shape, rows left empty, poked neurons ignoring their drive)
    and the expected time of a full run. Returns the problems found (empty when none)."""
    import time
    from .bench.scorecard import fold_parts
    if isinstance(data, (str, Path)):
        recs = {r.uid: r for r in load_pumpprobe_dir(data)}
        folds = load_folds(SPLITS_DIR / SPLITS["cv3"])["folds"]
    else:
        recs = {r.uid: r for r in data}
        u = sorted(recs)
        folds = [u[k::3] for k in range(3)]
    train, val, pool = fold_parts(recs, folds, 0)
    copy = factory()
    problems = []
    t0 = time.time()
    if hasattr(copy, "simulate"):
        copy.fit(train, val)
    else:
        copy.fit(list(train) + list(val))
    t_fit = time.time() - t0
    rec = pool[0]
    tpl = template_of(rec)
    t1 = time.time()
    if hasattr(copy, "simulate"):
        log("low-level copy (simulate): only timing is checked")
        copy.simulate(rec, np.random.default_rng(0))
        x = None
    else:
        x = np.asarray(copy.run(tpl, np.random.default_rng(0)), float)
    t_run = time.time() - t1
    if x is not None:
        if x.shape != (len(tpl.names), tpl.n_frames):
            problems.append(f"run() returned {x.shape}; expected ({len(tpl.names)}, {tpl.n_frames})")
        else:
            named = [j for j, n in enumerate(tpl.names) if neuron_class(n)]
            modelled = [j for j in named if np.isfinite(x[j]).any()]
            if len(modelled) < 0.5 * len(named):
                problems.append(f"only {len(modelled)} of {len(named)} identified neurons have activity")
            if any(np.isfinite(x[j]).mean() < 0.95 for j in modelled):
                problems.append("some modelled rows contain NaN frames; a neuron is either modelled for the whole run or not at all")
            if modelled and np.nanmax(np.abs(x[modelled])) > 1e3:
                problems.append("values above 1e3: activity is z-scored before scoring, but check for instability")
            follow = []
            for p in tpl.pokes:
                if p.index in modelled:
                    n = min(len(p.drive), tpl.n_frames - p.frame)
                    a, b = x[p.index, p.frame:p.frame + n], p.drive[:n]
                    ok = np.isfinite(a) & np.isfinite(b)
                    if ok.sum() > 5 and np.std(a[ok]) > 0 and np.std(b[ok]) > 0:
                        follow.append(np.corrcoef(a[ok], b[ok])[0, 1])
            if follow and np.median(follow) < 0.3:
                problems.append(f"poked neurons barely follow their drive (median correlation {np.median(follow):.2f}); "
                                "the benchmark assumes the poked neuron does what it did in the real worm")
    per_fold = t_fit + t_run * len(pool)
    log(f"fit {t_fit:.1f} s, one worm {t_run:.1f} s; a full run (6 folds) needs about "
        f"{6 * per_fold / 60:.0f} min plus about 3 min of scoring per fold and seed")
    for p_ in problems:
        log("PROBLEM: " + p_)
    if not problems:
        log("contract check passed")
    return problems
