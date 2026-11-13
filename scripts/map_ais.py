"""Record every artificial network of the map at every mapped preparation's instrument (docs/MAP.md,
amendments 4 and 10). Activity is generated per AI (several instances), recorded through
`pipeline.ai_at_prep` at each preparation's step-1 numbers, and only the results are kept (values,
replicates, budget, achieved numbers) in data/cache/map_ais/<ai>_<prep>.pkl; activity is discarded.
Instances: network seeds; for Pythia-1B (no released seeds) and Mamba, disjoint thirds of the book sample.
No brain activity is read here.

Usage: python scripts/map_ais.py [AI ids]
"""
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.map import ai, instrument, pipeline, zoo  # noqa: E402

CACHE = ROOT / "data/cache/map_ais"
TOK = ROOT / "data/external/books/tokens.npy"
KEEP = 300
GROUPS = {"spikes": ["R4", "R9", "R10b", "R10d"], "calcium": ["R2"]}


def thirds(n=200_000):
    t = np.load(TOK)[:n]
    k = len(t) // 3
    return [t[i * k:(i + 1) * k] for i in range(3)]


def _drop_cache(model):
    """Disk is limited (about 6 GB free): the downloaded weights of a model this script fetched are removed
    from the local Hugging Face cache once its activity is recorded."""
    from huggingface_hub import scan_cache_dir
    info = scan_cache_dir()
    revs = [r.commit_hash for repo in info.repos if repo.repo_id == model for r in repo.revisions]
    if revs:
        info.delete_revisions(*revs).execute()


def lm(name, seeds=None, ou=None):
    """Instances: released seeds when given (PolyPythia), else disjoint thirds of the text."""
    out = []
    if seeds:
        t = np.load(TOK)[:120_000]
        for s in seeds:
            out.append(ai.record(s, t, keep=KEEP, ou_tau=ou)[:2])
            if ou is None:
                pass
        return out
    for part in thirds():
        out.append(ai.record(name, part, keep=KEEP, ou_tau=ou)[:2])
    return out


def poly(size):
    return [f"EleutherAI/pythia-{size}-seed{i}" for i in (1, 2, 3)]


SPECS = {
    # id: (family, role, instance builder)
    "A1": ("A1", "standard", lambda: [zoo.random_rnn(seed=s)[:2] for s in range(3)]),
    "A1-slow": ("A1", "augmented", lambda: [(zoo.with_slow_drives(zoo.random_rnn(seed=s)[0], seed=s), [])
                                             for s in range(3)]),
    "A2": ("A2", "standard", lambda: [zoo.task_rnn(seed=s)[:2] for s in range(3)]),
    "A3": ("A3", "standard", lambda: [zoo.char_net("gru", seed=s)[:2] for s in range(3)]),
    "A4": ("A4", "standard", lambda: [zoo.lif_network(seed=s)[:2] for s in range(3)]),
    "A5": ("A5", "standard", lambda: [zoo.char_net("cfc", seed=s)[:2] for s in range(3)]),
    "A6-14m": ("A6", "standard", lambda: lm(None, poly("14m"))),
    "A6-160m": ("A6", "standard", lambda: lm(None, poly("160m"))),
    "A6-410m": ("A6", "standard", lambda: lm(None, poly("410m"))),
    "A6-1b": ("A6", "standard", lambda: lm("EleutherAI/pythia-1b")),
    "A6-410m-ou": ("A6", "augmented", lambda: lm(None, poly("410m"), ou=200)),
    "A7-130m": ("A7", "standard", lambda: lm("state-spaces/mamba-130m-hf")),
    "A7-370m": ("A7", "standard", lambda: lm("state-spaces/mamba-370m-hf")),
    "A10": ("A10", "augmented", lambda: [zoo.lab_network(individual=i)[:2] for i in range(3)]),
}
FITTED_ON = {"A10": ["R1", "R2"]}                          # candidates (c), (d): worm preparations left out


def profile(pid, d):
    rt = "spikes" if pid in GROUPS["spikes"] else "calcium"
    return rt, {k: d[pid]["median"][k] for k in instrument.KEYS[rt]}


VARIANTS = {"": {}, "hold2k": {"hold_mult": 2}, "interp": {"interp": True}}


def run(aid, variant=""):
    """variant "" is primary (with budget); "hold2k" and "interp" are the registered robustness variants,
    re-matched, without budget, 2 recordings per instance (verdicts only, amendment 10)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    d = json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"]
    suf = f"_{variant}" if variant else ""
    todo = [p for g in GROUPS.values() for p in g if not (CACHE / f"{aid}_{p}{suf}.pkl").exists()]
    if not todo:
        return
    t0 = time.time()
    inst = SPECS[aid][2]()
    acts = [np.asarray(a, np.float32) for a, _ in inst]
    segs = [s for _, s in inst]
    print(aid, "activity", [a.shape for a in acts], f"{time.time() - t0:.0f}s", flush=True)
    for model in MODELS.get(aid, []):
        if not any(aid2 != aid and model in MODELS.get(aid2, []) and not done(aid2) for aid2 in SPECS):
            _drop_cache(model)
    for pid in todo:
        rt, prof = profile(pid, d)
        r = pipeline.ai_at_prep(acts, rt, prof, segments=segs[0] or None,
                                recs_per_instance=(7 if aid in PAIRED else 2) if not variant else 2,
                                budget=not variant, **VARIANTS[variant])
        r["family"], r["role"] = SPECS[aid][0], SPECS[aid][1]
        (CACHE / f"{aid}_{pid}{suf}.pkl").write_bytes(pickle.dumps(r))
        print(aid, pid, "reached", r["reached"], {k: round(v, 3) for k, v in r["values"].items() if v == v},
              f"{time.time() - t0:.0f}s", flush=True)


MODELS = {"A6-14m": [], "A6-160m": poly("160m"), "A6-410m": poly("410m"), "A6-410m-ou": poly("410m"),
          "A6-1b": ["EleutherAI/pythia-1b"], "A7-130m": ["state-spaces/mamba-130m-hf"],
          "A7-370m": ["state-spaces/mamba-370m-hf"]}


def done(aid):
    return all((CACHE / f"{aid}_{p}.pkl").exists() for g in GROUPS.values() for p in g)


PAIRED = {"A3", "A5", "A6-14m", "A6-1b", "A6-410m", "A7-370m"}     # H4, H5, H6: 3 instances x 7 = 21 recordings

if __name__ == "__main__":
    args = sys.argv[1:]
    variant = args.pop(0).split("=")[1] if args and args[0].startswith("--variant=") else ""
    for aid in args or SPECS:
        run(aid, variant)
