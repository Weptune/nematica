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
GROUPS = {"calcium": ["R2"], "spikes": ["R4g"]}   # amendment 12: single-unit spikes closed; 16: the mouse
                                                  # two-photon arm (R5m) failed step 2; 17: pooled R4 units


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


def lm(name, seeds=None, ou=None, keep=KEEP, n_tok=None):
    """Instances: released seeds when given (PolyPythia), else disjoint thirds of the text. `n_tok` tokens per
    instance (amendment 17; default 120,000 for seeds and a third of 200,000 otherwise)."""
    out = []
    if seeds:
        t = np.load(TOK)[:n_tok or 120_000]
        for i, s in enumerate(seeds):                  # amendment 13: each instance its own OU realisation
            out.append(ai.record(s, t, keep=keep, ou_tau=ou, seed=i)[:2])
        return out
    for i, part in enumerate(thirds(3 * n_tok if n_tok else 200_000)):
        out.append(ai.record(name, part, keep=keep, ou_tau=ou, seed=i)[:2])
    return out


def poly(size):
    return [f"EleutherAI/pythia-{size}-seed{i}" for i in (1, 2, 3)]


SPECS = {
    # id: (family, role, instance builder)
    "A1": ("A1", "standard", lambda: [zoo.random_rnn(seed=s)[:2] for s in range(3)]),
    "A1-slow": ("A1", "augmented", lambda: [(zoo.with_slow_drives(zoo.random_rnn(seed=s)[0], seed=s), [])
                                             for s in range(3)]),
    # A2 runs at a timescale of about 930 steps; it is kept every 10th step (the worm instrument samples it
    # every ~115 steps), which leaves its recording unchanged in effect and fits in memory (amendment 13)
    "A2": ("A2", "standard", lambda: [(zoo.task_rnn(seed=s)[0][::10], []) for s in range(3)]),
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
# Amendment 16 (mouse instrument): one 3,000-frame crop spans 3,000 x 8.5 native timescales, so slow networks
# are regenerated longer for R5m (two recordings' worth of distinct activity); the task RNN keeps every 100th
# step (its timescale is about 1,500 steps; the mouse frame spans about 13,000).
MOUSE_SPECS = {
    "A1": lambda: [zoo.random_rnn(seed=s, steps=900_000)[:2] for s in range(3)],
    "A1-slow": lambda: [(zoo.with_slow_drives(zoo.random_rnn(seed=s, steps=1_350_000)[0], seed=s), [])
                        for s in range(3)],
    "A2": lambda: [(zoo.task_rnn(seed=s, trials=1_560_000, every=100)[0], []) for s in range(3)],
    "A10": lambda: [zoo.lab_network(individual=i, frames=300_000)[:2] for i in range(3)],
}
# Amendment 17 (pooled R4 units, groups of 8): at least 400 units; AI individuals are 5,000-timescale crops.
# The language models not yet recorded for the worms are recorded once, with 480 units and 40,000 tokens
# per instance, for both preparations (each crop needs at most about 4,500 tokens).
LM_TOK, G_KEEP = 40_000, 480


def _keep(A, n=G_KEEP, seed=0):
    A = np.asarray(A, np.float32)
    return A[:, np.sort(np.random.default_rng(seed).choice(A.shape[1], n, replace=False))] if A.shape[1] > n else A


R4G_SPECS = {
    "A1": lambda: [zoo.random_rnn(n=480, seed=s, steps=200_000)[:2] for s in range(3)],
    "A1-slow": lambda: [(zoo.with_slow_drives(zoo.random_rnn(n=480, seed=s, steps=280_000)[0], seed=s), [])
                        for s in range(3)],
    "A2": lambda: [_a2(s) for s in range(3)],
    "A3": lambda: [zoo.char_net("gru", seed=s, n=512)[:2] for s in range(3)],
    "A4": lambda: [(_keep(a, seed=s), seg) for s in range(3) for a, seg in [zoo.lif_network(seed=s)[:2]]],
    "A5": lambda: [zoo.char_net("cfc", seed=s, n=512)[:2] for s in range(3)],
    "A6-14m": lambda: lm(None, poly("14m"), keep=G_KEEP, n_tok=LM_TOK),
    "A6-160m": lambda: lm(None, poly("160m"), keep=G_KEEP, n_tok=LM_TOK),
    "A6-410m": lambda: lm(None, poly("410m"), keep=G_KEEP, n_tok=LM_TOK),
    "A6-1b": lambda: lm("EleutherAI/pythia-1b", keep=G_KEEP, n_tok=LM_TOK),
    "A6-410m-ou": lambda: lm(None, poly("410m"), ou=200, keep=G_KEEP, n_tok=LM_TOK),
    "A7-130m": lambda: lm("state-spaces/mamba-130m-hf", keep=G_KEEP, n_tok=LM_TOK),
    "A7-370m": lambda: lm("state-spaces/mamba-370m-hf", keep=G_KEEP, n_tok=LM_TOK),
}
def _a2(s):
    """Amendment 19 (review 15, items 6 and 7): 450,000 trials kept as 100-step block means (270,000
    samples: two recordings of one 5,000-timescale crop each without overlap); accuracy reported."""
    A, seg, meta = zoo.task_rnn(seed=s, n=512, trials=450_000, every=100)
    print("A2 seed", s, "accuracy", meta["accuracy"], flush=True)
    return A, seg


def builder(aid, pid):
    """(activity key, builder) for one AI at one preparation; None: not recorded there. Amendment 19 (review
    15, item 12): the worm and pooled-mouse recordings of an AI share one activity (R4G_SPECS), so every AI
    is re-recorded for the worms too, with the same sizes; A10 (not recorded at R4g) keeps its own."""
    if pid == "R5m" and aid in MOUSE_SPECS:
        return "R5m", MOUSE_SPECS[aid]
    if pid in ("R2", "R4g") and aid in R4G_SPECS:
        return "shared", R4G_SPECS[aid]
    if pid == "R4g":
        return None
    return "std", SPECS[aid][2]


CROSS = {"R4g"}                 # amendment 19 (review 15, item 1): crops may span context boundaries


FITTED_ON = {"A10": ["R1", "R2"]}                          # candidates (c), (d): worm preparations left out


def code_hash():
    import hashlib
    h = hashlib.sha256()
    for f in ("nematica/map/measures.py", "nematica/map/recording.py", "nematica/map/pipeline.py",
              "nematica/map/zoo.py", "nematica/map/ai.py", "scripts/map_ais.py", "scripts/map_ais_fast.py"):
        h.update((ROOT / f).read_bytes())
    return h.hexdigest()[:16]


def profile(pid, d):
    if pid == "R4g":                                    # amendment 17: R4's single-unit numbers, groups of 8
        sys.path.insert(0, str(ROOT / "scripts"))
        from map_step2_r4g import r4g_profile
        return "spikes", r4g_profile(with_crop=False)
    if pid in GROUPS.get("deconv", []):                 # amendment 16: the mouse profile of step 2
        sys.path.insert(0, str(ROOT / "scripts"))
        from map_step2_mouse import mouse_profile
        p = mouse_profile()
        return "deconv", {k: p[k] for k in ("taus_per_frame", "noise", "fs", "indicator_frames", "kernel_frames")}
    rt = "spikes" if pid in GROUPS.get("spikes", []) else "calcium"
    if pid == "R2":                                     # amendment 13: the 14 baseline worms' median
        rows = [r for r in d["R2"]["individuals"] if r.get("kind") == "baseline" and "error" not in r]
        return rt, {k: float(np.median([r[k] for r in rows])) for k in instrument.KEYS[rt]}
    return rt, {k: d[pid]["median"][k] for k in instrument.KEYS[rt]}


VARIANTS = {"": {}, "hold2k": {"hold_mult": 2}, "interp": {"interp": True},
            "noise05": {"noise": 0.05}, "noise10": {"noise": 0.10}}     # amendment 13: worm noise sensitivity
CROP_LEN = {"R2": 1600, "R5m": 3000}      # amendment 13: one baseline worm recording, in frames; 16: mouse
CROP_LEN["R4g"] = int(round(5000 * json.loads((ROOT / "docs/figures/map_step1.json").read_text())
                            ["preparations"]["R4"]["median"]["bins_per_tau"]))   # amendment 17: 5,000 timescales
MAX_CROPS = {"R2": 4, "R5m": 1, "R4g": 1}  # amendments 16 and 17 (compute): one crop per recording
N_DRAWS = 40                               # as for the worms


def run(aid, variant=""):
    """variant "" is primary (with budget); "hold2k" and "interp" are the registered robustness variants,
    re-matched, without budget, 2 recordings per instance (verdicts only, amendment 10)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    d = json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"]
    suf = f"_{variant}" if variant else ""
    def fresh(f):                                       # a cached result counts only if made by this code
        return f.exists() and pickle.loads(f.read_bytes()).get("code_sha256_16") == code_hash()
    todo = [p for g in GROUPS.values() for p in g if not fresh(CACHE / f"{aid}_{p}{suf}.pkl")]
    if ONLY:
        todo = [p for p in todo if p in ONLY]
    if not todo:
        return
    keys = {}
    for p in todo:
        b = builder(aid, p)
        if b is not None:
            keys.setdefault(b[0], (b[1], []))[1].append(p)
    for key, (build, pids) in keys.items():
        _record(aid, variant, build, pids, d, suf)


def _record(aid, variant, build, todo, d, suf):
    t0 = time.time()
    inst = build()
    acts = [np.asarray(a, np.float32) for a, _ in inst]
    segs = [s for _, s in inst]
    del inst
    print(aid, todo, "activity", [a.shape for a in acts], f"{time.time() - t0:.0f}s", flush=True)
    for model in MODELS.get(aid, []):
        if not any(aid2 != aid and model in MODELS.get(aid2, []) and not done(aid2) for aid2 in SPECS):
            _drop_cache(model)
    for pid in todo:
        rt, prof = profile(pid, d)
        opts = dict(VARIANTS[variant])
        if "noise" in opts:
            prof = {**prof, "noise": opts.pop("noise")}
        try:
            r = pipeline.ai_at_prep(acts, rt, prof, segments=segs[0] or None,
                                    recs_per_instance=(7 if aid in PAIRED else 2) if not variant else 2,
                                    budget=not variant, crop_len=CROP_LEN.get(pid), n_draws=N_DRAWS,
                                    max_crops=MAX_CROPS.get(pid, 4), cross_segments=pid in CROSS, **opts)
        except Exception as e:  # noqa: BLE001  (e.g. no timescale: activity white at the native step)
            from nematica.map import measures as M_
            r = {"values": {m: float("nan") for m in M_.MEASURES}, "replicates": [], "reached": False,
                 "error": f"could not be recorded: {type(e).__name__}: {e}", "crop_len": CROP_LEN.get(pid),
                 "native_tau": float(M_.tau_med(acts[0]))}
        r["code_sha256_16"] = code_hash()
        r["family"], r["role"] = SPECS[aid][0], SPECS[aid][1]
        (CACHE / f"{aid}_{pid}{suf}.pkl").write_bytes(pickle.dumps(r))
        print(aid, pid, "reached", r["reached"], {k: round(v, 3) for k, v in r["values"].items() if v == v},
              f"{time.time() - t0:.0f}s", flush=True)


MODELS = {"A6-14m": [], "A6-160m": poly("160m"), "A6-410m": poly("410m"), "A6-410m-ou": poly("410m"),
          "A6-1b": ["EleutherAI/pythia-1b"], "A7-130m": ["state-spaces/mamba-130m-hf"],
          "A7-370m": ["state-spaces/mamba-370m-hf"]}


def done(aid):
    return all((CACHE / f"{aid}_{p}.pkl").exists() and pickle.loads((CACHE / f"{aid}_{p}.pkl").read_bytes())
               .get("code_sha256_16") == code_hash() for g in GROUPS.values() for p in g)


ONLY = []                                  # preparations to restrict a run to (set by run itself or --only=)
PAIRED = {"A3", "A5", "A6-14m", "A6-1b", "A6-410m", "A7-370m"}     # H4, H5, H6: 3 instances x 7 = 21 recordings

if __name__ == "__main__":
    args = sys.argv[1:]
    variant = args.pop(0).split("=")[1] if args and args[0].startswith("--variant=") else ""
    if args and args[0].startswith("--only="):
        ONLY[:] = args.pop(0).split("=")[1].split(",")
    for aid in args or SPECS:
        run(aid, variant)
