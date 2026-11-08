"""Score a copy written in any language, through files.

1. Export the benchmark kit (held-out worms' templates and the fold lists; made locally from your own
   copy of the atlas, never redistributed):

       python -m nematica export --out kit/

   kit/manifest.json lists, per split and fold, the training, validation and held-out worms (uids
   of the converted files `pumpprobe_<uid>.npz`, readable from any language with an npz reader:
   `x` frames x neurons, `ids` neuron names, `stim_cell` and `stim_frame` the pokes, `t` times).
   kit/templates/<split>/fold<k>/<uid>.npz holds what the copy is told about each held-out worm:
   `names` (neuron names, "" where unidentified), `n_frames`, `dt`, and its pokes: `poke_index`
   (row in names), `poke_frame`, `poke_drive` (pokes x 61 frames: the poked neuron's own measured
   response, in units of its SD from its pre-poke baseline; NaN-padded).

2. Fit your copy on each fold's training (and validation) worms only, simulate every held-out worm
   of that fold with its own pokes, and save sims/<split>/fold<k>/seed<s>/<uid>.npz with one array
   `x` of shape (len(names), n_frames): one row per neuron of the real worm, NaN rows for neurons
   you do not model.

3. Score:

       python -m nematica score-files sims/ --name my-copy

Missing worms or wrong shapes are reported, not silently skipped.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

import numpy as np

from .bench.scorecard import SPLITS, SPLITS_DIR, FoldRuler, fold_parts, set_norm
from .data.pumpprobe import PumpProbe, load_pumpprobe_dir, neuron_class
from .data.splits import load_folds
from .score import template_of, validate_rows

KIT_VERSION = 1


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def export(data: str | Path, out: str | Path, splits=("cv3", "blocks1")) -> Path:
    data, out = Path(data), Path(out)
    recs = {r.uid: r for r in load_pumpprobe_dir(data)}
    if not recs:
        raise FileNotFoundError(f"no pumpprobe_*.npz recordings in {data}")
    manifest = {"kit_version": KIT_VERSION, "data_files": {}, "splits": {},
                "rule": "level passes if inside in >= 2 of 3 pools; rest >= 5 of 6 activity levels; poked: "
                        "C1.pattern, C2.magnitude and P2.spread all pass"}
    for uid in sorted(recs):
        manifest["data_files"][f"pumpprobe_{uid}.npz"] = _sha(data / f"pumpprobe_{uid}.npz")
    for split in splits:
        folds = load_folds(SPLITS_DIR / SPLITS[split])["folds"]
        manifest["splits"][split] = []
        for fi in range(len(folds)):
            train, val, pool = fold_parts(recs, folds, fi)
            manifest["splits"][split].append({"fold": fi, "train": [r.uid for r in train],
                                              "validation": [r.uid for r in val], "held_out": [r.uid for r in pool]})
            d = out / "templates" / split / f"fold{fi}"
            d.mkdir(parents=True, exist_ok=True)
            for r in pool:
                t = template_of(r)
                L = max((len(p.drive) for p in t.pokes), default=0)
                drive = np.full((len(t.pokes), L), np.nan)
                for i, p in enumerate(t.pokes):
                    drive[i, :len(p.drive)] = p.drive
                np.savez(d / f"{r.uid}.npz", names=np.array(t.names, dtype=str), n_frames=t.n_frames, dt=t.dt,
                         poke_index=np.array([p.index for p in t.pokes], int),
                         poke_frame=np.array([p.frame for p in t.pokes], int), poke_drive=drive)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (out / "README.txt").write_text(__doc__, encoding="utf-8")
    return out


def verify_data(kit: str | Path, data: str | Path) -> list[str]:
    """Files whose hash differs from the kit's manifest (the kit was made from other data)."""
    man = json.loads((Path(kit) / "manifest.json").read_text(encoding="utf-8"))
    if man.get("kit_version") != KIT_VERSION:
        return [f"kit version {man.get('kit_version')}, this tool expects {KIT_VERSION}"]
    return [f for f, h in man["data_files"].items() if not (Path(data) / f).exists() or _sha(Path(data) / f) != h]


class FileModel:
    """A 'model' whose simulations are read from files written by the user's own program."""

    def __init__(self, folder: Path, name: str):
        self.folder, self.name = folder, name

    def fit(self, train, val):
        return self

    def simulate(self, rec: PumpProbe, rng) -> PumpProbe:
        p = self.folder / f"{rec.uid}.npz"
        if not p.exists():
            raise FileNotFoundError(f"missing simulation {p}")
        with np.load(p, allow_pickle=False) as z:
            x = np.asarray(z["x"], float)
        tpl = template_of(rec)
        if x.shape != (len(tpl.names), tpl.n_frames):
            raise ValueError(f"{p}: shape {x.shape}, expected ({len(tpl.names)}, {tpl.n_frames}) "
                             f"(one row per neuron of the real worm, one column per frame)")
        validate_rows(x, tpl, str(p))
        keep = [j for j, n in enumerate(tpl.names) if neuron_class(n) and np.isfinite(x[j]).any()]
        row = {j: i for i, j in enumerate(keep)}
        stims = [(row[p_.index], p_.frame) for p_ in tpl.pokes if p_.index in row]
        return PumpProbe(uid=rec.uid, x=x[keep], names=[tpl.names[j] for j in keep],
                         classes=[neuron_class(tpl.names[j]) for j in keep], stims=stims, dt=rec.dt,
                         all_stim_frames=list(rec.all_stim_frames))


def score_files(sims: str | Path, data, name: str, pci: bool = True, norm: str = "fluct",
                log: Callable[[str], None] = print, split_files: dict | None = None) -> list[dict]:
    """Score simulations saved as sims/<split>/fold<k>/seed<s>/<uid>.npz. Splits, folds and seeds are
    taken from the folders present; every held-out worm of a present fold must be there."""
    sims = Path(sims)
    set_norm(norm)
    recs = ({r.uid: r for r in load_pumpprobe_dir(data)} if isinstance(data, (str, Path))
            else {r.uid: r for r in data})
    paths = split_files or {k: SPLITS_DIR / v for k, v in SPLITS.items()}
    rows = []
    from .bench.verdicts import FOLD_DIR, SEED_DIR
    for split in sorted(p.name for p in sims.iterdir() if p.is_dir() and p.name in paths):
        folds = load_folds(paths[split])["folds"]
        fdirs = {}
        for d in (sims / split).iterdir():
            m = FOLD_DIR.match(d.name)
            if not d.is_dir() or not m:
                raise ValueError(f"unexpected entry {d} (folders must be named fold0, fold1, ...)")
            fi = int(m.group(1))
            if fi in fdirs or not 0 <= fi < len(folds):
                raise ValueError(f"{d}: fold {fi} is duplicated or out of range (split {split} has {len(folds)} folds)")
            fdirs[fi] = d
        seed_sets = {}
        for fi, d in fdirs.items():
            ss = {}
            for sd in d.iterdir():
                m = SEED_DIR.match(sd.name)
                if not sd.is_dir() or not m:
                    raise ValueError(f"unexpected entry {sd} (folders must be named seed0, seed1, ...)")
                ss[int(m.group(1))] = sd
            seed_sets[fi] = ss
        if len({frozenset(v) for v in seed_sets.values()}) > 1:
            raise ValueError(f"split {split}: folds have different seeds: "
                             + ", ".join(f"fold{k}: {sorted(v)}" for k, v in sorted(seed_sets.items())))
        if len(fdirs) < len(folds):
            log(f"WARNING: split {split} has {len(fdirs)} of {len(folds)} folds: it will be shown but not judged")
        for fi in sorted(fdirs):
            ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=pci)
            missing_all = [f"{sdir}/{r.uid}.npz" for sdir in seed_sets[fi].values() for r in ruler.pool
                           if not (sdir / f"{r.uid}.npz").exists()]
            if missing_all:
                raise FileNotFoundError(f"{len(missing_all)} simulations missing, e.g. {missing_all[0]}")
            for sd, sdir in sorted(seed_sets[fi].items()):
                log(f"[{split} fold {fi} seed {sd}] scoring {len(ruler.pool)} simulated worms")
                for r in ruler.score(name, FileModel(sdir, name)):
                    rows.append({"split": split, "fold": fi, "n_folds": len(folds), "pool_size": len(ruler.pool), "seed": sd, **r})
    if not rows:
        raise FileNotFoundError(f"no simulations found under {sims} (expected <split>/fold<k>/seed<s>/<uid>.npz)")
    return rows
