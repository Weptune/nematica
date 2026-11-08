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


def validate_rows(x: np.ndarray, tpl: "Template", where: str) -> None:
    """A copy's output must be finite where it is not NaN. NaN frames inside a modelled row are allowed
    and treated exactly like a real worm's tracking gaps: gaps up to 5% of the frames are interpolated,
    a class missing more than that is left out of that worm's scores (and lowers the copy's coverage)."""
    if np.isinf(x).any():
        raise ValueError(f"{where}: infinite values")


def partial_rows(x: np.ndarray, tpl: "Template") -> list[str]:
    fin = np.isfinite(x)
    return [tpl.names[j] or f"row {j}" for j in range(len(x)) if fin[j].any() and fin[j].mean() < 0.95]


def _as_model(copy):
    """A BrainCopy goes through the adapter; anything else must offer fit(train, val) and simulate."""
    if isinstance(copy, BrainCopy):
        return CopyAdapter(copy)
    if hasattr(copy, "simulate") and hasattr(copy, "fit"):
        return copy
    raise TypeError(f"{type(copy).__name__} is neither a BrainCopy nor a model with fit(train, val) and simulate(rec, rng)")


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
        validate_rows(x, tpl, f"{self.copy.name}.run, worm {tpl.uid}")
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
    if seeds < 1:
        raise ValueError("seeds must be at least 1")
    paths = split_files or {s: SPLITS_DIR / SPLITS[s] for s in splits}
    rows = []
    for split in (split_files or splits):
        all_folds = load_folds(paths[split])["folds"]
        if folds is not None and any(not 0 <= f < len(all_folds) for f in folds):
            raise ValueError(f"split {split} has folds 0 to {len(all_folds) - 1}; asked for {sorted(folds)}")
        missing = sorted({u for f in all_folds for u in f} - set(recs))
        if missing:
            raise FileNotFoundError(f"{len(missing)} worms of split {split} are missing from {data}, e.g. {missing[0]}")
        for fi in range(len(all_folds)):
            if folds is not None and fi not in folds:
                continue
            log(f"[{split} fold {fi}] building the real-worm ruler")
            ruler = FoldRuler(*fold_parts(recs, all_folds, fi), pci=pci)
            copy = factory()
            model = _as_model(copy)
            name = getattr(copy, "name", "copy")
            log(f"[{split} fold {fi}] fitting and running {name} on {len(ruler.pool)} held-out worms")
            for sd in range(seeds):
                for r in ruler.score(name, model, seed_base=1000 * fi + 100000 * sd, refit=sd == 0):
                    rows.append({"split": split, "fold": fi, "n_folds": len(all_folds), "pool_size": len(ruler.pool), "seed": sd, **r})
                if seeds > 1:
                    log(f"[{split} fold {fi}] seed {sd + 1}/{seeds} done")
    if not rows:
        raise ValueError("nothing was scored (check --split and --fold)")
    return rows


def score_many(factories: dict, data, splits: Sequence[str] = ("cv3", "blocks1"), folds=None, pci: bool = True,
               norm: str = "fluct", log: Callable[[str], None] = print, seeds: int = 1,
               split_files: dict | None = None) -> dict[str, list[dict]]:
    """Several copies on the same held-out pools: the real side of each fold is built once and shared
    (identical rows to scoring each copy alone). {name: factory} -> {name: rows}."""
    set_norm(norm)
    if seeds < 1:
        raise ValueError("seeds must be at least 1")
    recs = ({r.uid: r for r in load_pumpprobe_dir(data)} if isinstance(data, (str, Path))
            else {r.uid: r for r in data})
    if not recs:
        raise FileNotFoundError(f"no recordings in {data}")
    paths = split_files or {s: SPLITS_DIR / SPLITS[s] for s in splits}
    out: dict[str, list[dict]] = {k: [] for k in factories}
    for split in (split_files or splits):
        all_folds = load_folds(paths[split])["folds"]
        missing = sorted({u for f in all_folds for u in f} - set(recs))
        if missing:
            raise FileNotFoundError(f"{len(missing)} worms of split {split} are missing, e.g. {missing[0]}")
        if folds is not None and any(not 0 <= f < len(all_folds) for f in folds):
            raise ValueError(f"split {split} has folds 0 to {len(all_folds) - 1}; asked for {sorted(folds)}")
        for fi in range(len(all_folds)):
            if folds is not None and fi not in folds:
                continue
            log(f"[{split} fold {fi}] building the real-worm ruler")
            ruler = FoldRuler(*fold_parts(recs, all_folds, fi), pci=pci)
            for name, factory in factories.items():
                model = _as_model(factory())
                log(f"[{split} fold {fi}] {name}")
                for sd in range(seeds):
                    for r in ruler.score(name, model, seed_base=1000 * fi + 100000 * sd, refit=sd == 0):
                        out[name].append({"split": split, "fold": fi, "n_folds": len(all_folds), "pool_size": len(ruler.pool), "seed": sd, **r})
    if not any(out.values()):
        raise ValueError("nothing was scored (check splits and folds)")
    return out


def echo_agreement(rows: Sequence[dict], key: str = "system_median") -> float:
    """Correlation of echo patterns (1 minus the median C1 distance), averaged over pools:
    with key="system_median", copy against real worms; with "bio_median", real worms against
    each other."""
    v = [1 - float(r[key]) for r in rows if r.get("metric") == "C1.pattern" and key in r]
    return float(np.mean(v)) if v else float("nan")


def format_answers(name: str, rows: Sequence[dict], note: str | None = None) -> str:
    """The benchmark's answer in plain text: the rule per split and seed, then each level's verdict
    letters and excess distance (0 = as far from real worms as real worms are from each other)."""
    from .bench.verdicts import REST_LEVELS, POKE_RULE_LEVELS, OTHER_LEVELS, answers, rule_text
    a = answers(rows)
    out = [f"NEMATICA benchmark: {name}", rule_text()] + ([f"Note: {note}"] if note else []) + [""]
    for split, d in a.items():
        n = d["seeds"]
        cov = (f"; models {d['coverage']:.0%} of scored classes (median)" if d.get("coverage") is not None
               else f"; {d['coverage_note']}" if d.get("coverage_note") else "")
        if d["judged"]:
            out.append(f"Split {split} ({d['pools']} held-out pools, {n} noise seed{'s' if n > 1 else ''}{cov}): "
                       f"passes at rest in {d['rest_pass_seeds']}/{n}, when poked in {d['poke_pass_seeds']}/{n}, "
                       f"both in {d['both_pass_seeds']}/{n}; all nine rule levels in {d['all_nine_seeds']}/{n}")
        else:
            out.append(f"Split {split}: NOT JUDGED ({'; '.join(d['not_judged_because'])}). Letters and distances "
                       f"below are a look, not a verdict{cov}.")
        out.append(f"  {'level':24s} {'verdicts by seed':22s} {'excess distance (median, range over pools and seeds)'}")
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


def write_report(name: str, rows: Sequence[dict], out: str | Path, meta: dict | None = None) -> Path:
    from .bench.verdicts import answers
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = dict(meta or {})
    if not meta.get("worms"):
        meta.pop("worms", None)
    doc = {"copy": name, "meta": meta, "answers": answers(rows), "rows": list(rows)}
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


def check(factory, data, log: Callable[[str], None] = print, seeds: int = 3) -> list[str]:
    """A fast contract check before a full run: fits the copy on fold 0's training worms of split cv3,
    runs it on three held-out worms, and returns the problems found (empty when none): wrong shape,
    infinite values, partly-NaN rows, too few neurons modelled, noise that ignores `rng`. Warnings
    (printed, not returned): poked neurons that do not follow their drive (allowed if the copy uses
    the drive as an input), and the expected time of a full run with `seeds` noise seeds."""
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
    problems, warnings_ = [], []
    t0 = time.time()
    model = _as_model(copy)
    model.fit(train, val)
    t_fit = time.time() - t0
    low_level = not isinstance(copy, BrainCopy)
    t_runs = []
    for rec in pool[:3]:
        tpl = template_of(rec)
        t1 = time.time()
        if low_level:
            a = np.asarray(model.simulate(rec, np.random.default_rng(1)).x, float)
            b = np.asarray(model.simulate(rec, np.random.default_rng(2)).x, float)
            t_runs.append((time.time() - t1) / 2)
            if a.shape == b.shape and np.array_equal(a, b, equal_nan=True):
                problems.append("two different rng seeds gave identical simulations: the copy ignores rng")
            continue
        try:
            x = np.asarray(copy.run(tpl, np.random.default_rng(1)), float)
            x2 = np.asarray(copy.run(tpl, np.random.default_rng(2)), float)
            x1b = np.asarray(copy.run(tpl, np.random.default_rng(1)), float)
        except Exception as e:                                   # noqa: BLE001
            problems.append(f"run() raised {type(e).__name__}: {e}")
            break
        t_runs.append((time.time() - t1) / 3)
        if x.shape != (len(tpl.names), tpl.n_frames):
            problems.append(f"run() returned {x.shape}; expected ({len(tpl.names)}, {tpl.n_frames})")
            break
        try:
            validate_rows(x, tpl, f"worm {tpl.uid}")
        except ValueError as e:
            problems.append(str(e))
        gaps = partial_rows(x, tpl)
        if gaps:
            warnings_.append(f"rows missing more than 5% of frames ({', '.join(gaps[:3])}{'...' if len(gaps) > 3 else ''}) "
                             "are left out of the scores, as untracked neurons are in real worms")
        if np.array_equal(x, x2, equal_nan=True):
            problems.append("two different rng seeds gave identical output: use the rng you are given for all noise")
        elif not np.array_equal(x, x1b, equal_nan=True):
            problems.append("the same rng seed gave different output: use only the rng you are given (no global random state)")
        named = [j for j, n in enumerate(tpl.names) if neuron_class(n)]
        modelled = [j for j in named if np.isfinite(x[j]).mean() >= 0.95]
        if len(modelled) < 0.8 * len(named):
            problems.append(f"only {len(modelled)} of {len(named)} identified neurons modelled (at least 80% needed)")
        follow = []
        for p in tpl.pokes:
            if p.index in modelled:
                n = min(len(p.drive), tpl.n_frames - p.frame)
                a_, b_ = x[p.index, p.frame:p.frame + n], p.drive[:n]
                ok = np.isfinite(a_) & np.isfinite(b_)
                if ok.sum() > 5 and np.std(a_[ok]) > 0 and np.std(b_[ok]) > 0:
                    follow.append(np.corrcoef(a_[ok], b_[ok])[0, 1])
        if follow and np.median(follow) < 0.3:
            warnings_.append(f"poked neurons barely follow their drive (median correlation {np.median(follow):.2f}); fine "
                             "if your copy uses the drive as an input, but the real neuron did follow it")
    problems = list(dict.fromkeys(problems))
    if t_runs:
        per_fold = t_fit + np.mean(t_runs) * len(pool) * seeds
        log(f"fit {t_fit:.1f} s, one worm {np.mean(t_runs):.2f} s; a full run with {seeds} seeds needs about "
            f"{6 * per_fold / 60:.0f} min of your copy's time plus about 3 min of scoring per fold and seed")
    for w in dict.fromkeys(warnings_):
        log("WARNING: " + w)
    for p_ in problems:
        log("PROBLEM: " + p_)
    if not problems:
        log("contract check passed")
    return problems
