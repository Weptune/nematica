"""Data for the research site (web/).

Two outputs:
  web/data/results.js   summaries of the committed result tables (docs/figures), safe to commit
  web/data/local.js     one held-out real worm and two artificial brains run on the same
                        stimulation schedule, for the opening figure. Derived from third-party
                        recordings, so it stays local (gitignored); the site works without it.
  web/data/echo.js      average echoes of every poked pair over one held-out group, real and simulated,
                        with neuron positions from the local atlas copy (also local only).

Usage:
  python scripts/export_site.py                       # results.js only
  python scripts/export_site.py --local --data data/raw/randi2023_wt_npz --folds configs/splits/pumpprobe_cv3.yaml
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FIG = ROOT / "docs" / "figures"
OUT = ROOT / "web" / "data"


def rows(name):
    with (FIG / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(v):
    try:
        f = float(v)
        return None if not np.isfinite(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def results() -> dict:
    out = {}
    # watching vs poking
    out["restPoke"] = [{"fold": int(r["fold"]), "brain": r["brain"], "rest": int(r["rest_inside"]),
                        "restScore": num(r["rest_score"]), "poke": num(r["poke_pattern"]),
                        "verdict": r["pattern_verdict"]} for r in rows("rest_vs_poke.csv")]
    # scorecard: every model x level x pool
    card = []
    for r in rows("ingredients.csv"):
        card.append({"fold": int(r["fold"]), "system": r["system"], "kind": r["kind"], "metric": r["metric"],
                     "median": num(r["system_median"]), "bio": num(r["bio_median"]), "p05": num(r["bio_p05"]),
                     "p95": num(r["bio_p95"]), "verdict": r["verdict"]})
    out["scorecard"] = card
    # power of the poke-pattern level
    pw = defaultdict(list)
    meta = {}
    for r in rows("causal_power.csv"):
        pw[(int(r["fold"]), float(r["f"]))].append((float(r["system_median"]), r["verdict"]))
        meta[int(r["fold"])] = {"bio": num(r["bio_median"]), "p05": num(r["bio_p05"]), "p95": num(r["bio_p95"]),
                                "realR": num(r["real_r_with_atlas"])}
    out["power"] = {"pools": meta, "points": [
        {"fold": k[0], "f": k[1], "d": round(float(np.median([a for a, _ in v])), 4),
         "verdicts": [b for _, b in v]} for k, v in sorted(pw.items())]}
    # signal vs noise
    out["signalNoise"] = [{"system": r["system"], "avg10": num(r["r_with_atlas_avg"]),
                           "single": num(r["r_single_with_atlas_avg"])} for r in rows("signal_noise_f0.csv")]
    # causal fingerprints
    m = np.load(FIG / "fingerprint_matrix_fluct.npy")
    out["fingerprint"] = {"n": int(m.shape[0]), "values": [None if not np.isfinite(v) else round(float(v), 3)
                                                           for v in m.ravel()]}
    out["fingerprintRows"] = [{k: (num(v) if k != "worm" else v) for k, v in r.items()}
                              for r in rows("own_rest_fingerprint_fluct.csv")]
    # perturbational complexity
    out["pci"] = [{"fold": int(r["fold"]), "system": r["system"], "metric": r["metric"],
                   "median": num(r["system_median"]), "verdict": r["verdict"], "pci": num(r["median_pci"]),
                   "spread": num(r["median_spread"])} for r in rows("pci.csv")]
    # calibrations
    out["calibration"] = [{"fold": int(r["fold"]), "system": r["system"], "metric": r["metric"],
                           "verdict": r["verdict"], "expected": r["expected"], "ok": r["as_designed"] == "True"}
                          for r in rows("causal_calibration.csv")]
    # mind levels
    out["mind"] = [{"dataset": r["dataset"], "fold": int(r["fold"]), "system": r["system"], "metric": r["metric"],
                    "verdict": r["verdict"], "expected": r.get("expected", "")}
                   for f in ("mind_copper.csv", "mind_atanas.csv") for r in rows(f)]
    return out


def pack(x: np.ndarray, lo=-1.5, hi=3.0) -> str:
    q = np.clip((x - lo) / (hi - lo), 0, 1)
    q = np.where(np.isfinite(x), np.round(q * 254) + 1, 0).astype(np.uint8)
    return base64.b64encode(q.tobytes()).decode()


def local(data: str, folds_path: str, frames: int) -> dict:
    from nematica.data.pumpprobe import load_pumpprobe_dir
    from nematica.data.splits import load_folds
    from nematica.systems.causal_models import ClassVAR, class_matrix
    sys.path.insert(0, str(ROOT / "scripts"))
    from run_same_worms import make_model

    recs = {r.uid: r for r in load_pumpprobe_dir(data)}
    folds = load_folds(folds_path)["folds"]
    pool = [recs[u] for u in folds[0]]
    rest = sorted(u for f in folds[1:] for u in f)
    val_uids = rest[::5]
    train = [recs[u] for u in rest if u not in val_uids]
    val = [recs[u] for u in val_uids]
    classes = ClassVAR(3, "all").fit(train, val).classes
    # the held-out worm with the most observed classes over the window
    best = max(pool, key=lambda r: np.isfinite(class_matrix(r, classes)[:, :frames]).all(axis=1).sum())
    real = class_matrix(best, classes)[:, :frames]
    keep = np.isfinite(real).mean(axis=1) > 0.95
    t = np.arange(real.shape[1])
    for i in np.where(keep)[0]:
        ok = np.isfinite(real[i])
        real[i] = np.interp(t, t[ok], real[i, ok])
    cls = [c for c, k in zip(classes, keep) if k]
    real = real[keep]
    # order rows by the first principal component of the real worm
    z = (real - real.mean(1, keepdims=True)) / (real.std(1, keepdims=True) + 1e-9)
    u, _, _ = np.linalg.svd(z, full_matrices=False)
    order = np.argsort(u[:, 0])
    brains = {}
    for spec, label in (("hybrid_kernels_regimes_obsfit", "Hybrid brain (passes the poke test)"),
                        ("var3_spontaneous", "Linear brain learned from rest")):
        m = make_model(spec).fit(train, val)
        sim = m.simulate(best, np.random.default_rng(7))
        x = class_matrix(sim, classes)[:, :frames][keep]
        x = np.nan_to_num(x)
        brains[spec] = {"label": label, "data": pack(x[order])}
        print("simulated", spec, flush=True)
    stims = [{"frame": int(f), "cls": best.classes[k]} for k, f in best.stims if f < frames]
    return {"worm": best.uid, "dt": best.dt, "frames": int(real.shape[1]), "classes": [cls[i] for i in order],
            "real": pack(real[order]), "brains": brains, "stims": stims}


def echoes(data: str, folds_path: str, fold: int = 0) -> dict:
    """Average echo of every (poked class, responding class) pair over one held-out group: real
    worms, and two artificial brains run on the same worms with the same pokes. Neuron classes are
    placed at their mean soma position in the head (Skuhersky et al. 2022 atlas, local copy)."""
    from nematica.bench.causal import response_set
    from nematica.data.pumpprobe import load_pumpprobe_dir, neuron_class
    from nematica.data.splits import load_folds
    from nematica.export.atlas import load_atlas
    sys.path.insert(0, str(ROOT / "scripts"))
    from run_same_worms import make_model

    atlas = load_atlas()
    pos: dict = {}
    for n, (ap, dv, lr) in atlas.items():
        if ap > 160:            # head only
            continue
        pos.setdefault(neuron_class(n), []).append((ap, dv))
    pos = {c: (float(np.mean([p[0] for p in v])), float(np.mean([p[1] for p in v]))) for c, v in pos.items()}

    recs = {r.uid: r for r in load_pumpprobe_dir(data)}
    folds = load_folds(folds_path)["folds"]
    pool = [recs[u] for u in folds[fold]]
    rest = sorted(u for i, f in enumerate(folds) if i != fold for u in f)
    val_uids = rest[::5]
    train = [recs[u] for u in rest if u not in val_uids]
    val = [recs[u] for u in val_uids]

    def average(sets):
        acc: dict = {}
        for rs in sets:
            for k, tr in rs.traces.items():
                acc.setdefault(k, []).append(tr)
        return {k: (np.nanmean(np.vstack(v), axis=0), len(v)) for k, v in acc.items()}

    sets = {"real": average([response_set(r) for r in pool])}
    for spec in ("hybrid_kernels_regimes_obsfit", "var3_spontaneous"):
        m = make_model(spec).fit(train, val)
        sims = [m.simulate(r, np.random.default_rng(300 + i)) for i, r in enumerate(pool)]
        sets[spec] = average([response_set(s) for s in sims])
        print("echoes:", spec, flush=True)
    real = sets["real"]
    stim_n: dict = {}
    for (a, b), (_, n) in real.items():
        stim_n[a] = max(stim_n.get(a, 0), n)
    stims = sorted(a for a, n in stim_n.items() if n >= 3 and a in pos)
    resp = sorted({b for (a, b) in real if a in stims and b in pos})
    T = len(next(iter(real.values()))[0])
    step = 2                                   # 1 s per sample
    nt = len(range(0, T, step))
    out = {}
    for key, ss in sets.items():
        arr = np.full((len(stims), len(resp), nt), np.nan)
        for i, a in enumerate(stims):
            for j, b in enumerate(resp):
                v = ss.get((a, b))
                if v is not None and (key != "real" or v[1] >= 2) and a != b:
                    arr[i, j] = v[0][::step][:nt]
        q = np.where(np.isfinite(arr), np.clip(np.round(arr / 3.0 * 127), -127, 127), -128).astype(np.int8)
        out[key] = base64.b64encode(q.tobytes()).decode()
    return {"stims": stims, "resp": resp, "pos": {c: [round(pos[c][0], 1), round(pos[c][1], 1)] for c in set(stims) | set(resp)},
            "nt": nt, "dtSample": 1.0, "scale": 3.0, "sets": out, "nWorms": len(pool),
            "labels": {"real": f"Real worms, average of {len(pool)}", "hybrid_kernels_regimes_obsfit": "Hybrid brain",
                       "var3_spontaneous": "Linear brain"}}


def sims(lab_data: Path = ROOT / "lab" / "public" / "data") -> int:
    """Simulation demos for web/sim.html, from the lab's exported bundles: six real held-out worms
    beside their closed-loop model worms in the same copper arena (which3), and a 32-worm swarm
    (swarm1). The real worms come from the copper-boundary recordings; written as script files
    so the page also opens from disk. Local only (gitignored)."""
    out = OUT / "sim"
    out.mkdir(parents=True, exist_ok=True)
    idx = json.loads((lab_data / "which3" / "index.json").read_text(encoding="utf-8"))
    pairs = []
    for rd in idx["rounds"]:
        files = {"real": rd["left"] if rd["answer"] == "left" else rd["right"]}
        files["model"] = rd["right"] if rd["answer"] == "left" else rd["left"]
        sides = {k: json.loads((lab_data / "which3" / f).read_text(encoding="utf-8")) for k, f in files.items()}
        def levels(b):
            acc = defaultdict(list)
            for n in b["neurons"]:
                acc[n["cls"]].append(np.asarray(n["level"], float))
            return {c: np.nanmean(np.vstack(v), axis=0) for c, v in acc.items()}
        lv = {k: levels(b) for k, b in sides.items()}
        classes = sorted(set(lv["real"]) & set(lv["model"]))
        # order rows by the real worm's correlation with AVA, so reversal neurons sit together
        ref = lv["real"].get("AVA")
        if ref is not None:
            def score(c):
                x = lv["real"][c]
                ok = np.isfinite(x) & np.isfinite(ref)
                return float(np.corrcoef(x[ok], ref[ok])[0, 1]) if ok.sum() > 10 and np.std(x[ok]) > 0 else 0.0
            classes.sort(key=score, reverse=True)
        pair = {"uid": rd["real_uid"], "classes": classes, "sides": {}}
        for k, b in sides.items():
            n = b["n_frames"]
            q = np.vstack([lv[k][c] for c in classes])
            q = np.where(np.isfinite(q), np.round(np.clip(q, 0, 1) * 254) + 1, 0).astype(np.uint8)
            pair["sides"][k] = {
                "t": [round(v, 2) for v in b["t"]], "k": b["body"]["k"], "length": b["body"]["length_mm"],
                "angles": [round(v, 3) for v in b["body"]["angles"]], "path": [round(v, 4) for v in b["path_mm"]],
                "reversing": b["behaviour"]["reversing"], "centre": b["arena"]["centre_mm"], "radius": b["arena"]["radius_mm"],
                "levels": base64.b64encode(q.tobytes()).decode(), "n": n}
        name = f"pair{rd['round']}"
        (out / f"{name}.js").write_text(f"(window.NEMATICA_SIM = window.NEMATICA_SIM || {{}})[{json.dumps(name)}] = "
                                        + json.dumps(pair, separators=(",", ":")) + ";\n", encoding="utf-8")
        pairs.append({"id": name, "uid": rd["real_uid"], "rev": rd["reversal_fraction"]})
    sw = json.loads((lab_data / "swarm1" / "swarm.json").read_text(encoding="utf-8"))
    for w in sw["worms"]:
        w["head"] = [round(v, 3) for v in w["head"]]
        w["angles"] = [round(v, 2) for v in w["angles"]]
    (out / "swarm.js").write_text("(window.NEMATICA_SIM = window.NEMATICA_SIM || {}).swarm = " + json.dumps(sw, separators=(",", ":")) + ";\n", encoding="utf-8")
    (out / "index.js").write_text("(window.NEMATICA_SIM = window.NEMATICA_SIM || {}).index = " + json.dumps(
        {"pairs": pairs, "model": idx["model"], "note": idx["note"], "scorecard": idx.get("scorecard")}, separators=(",", ":")) + ";\n", encoding="utf-8")
    print("wrote", out, len(pairs), "pairs and the swarm")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--data", default="data/raw/randi2023_wt_npz")
    ap.add_argument("--folds", default="configs/splits/pumpprobe_cv3.yaml")
    ap.add_argument("--frames", type=int, default=960)
    ap.add_argument("--echo-only", action="store_true")
    ap.add_argument("--sims", action="store_true", help="also write the simulation demos (web/data/sim)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.js").write_text("window.NEMATICA_RESULTS = " + json.dumps(results(), separators=(",", ":")) + ";\n",
                                    encoding="utf-8")
    print("wrote", OUT / "results.js")
    if args.sims:
        sims()
    if args.local:
        if not args.echo_only:
            (OUT / "local.js").write_text("window.NEMATICA_LOCAL = " + json.dumps(local(args.data, args.folds, args.frames),
                                          separators=(",", ":")) + ";\n", encoding="utf-8")
            print("wrote", OUT / "local.js")
        (OUT / "echo.js").write_text("window.NEMATICA_ECHO = " + json.dumps(echoes(args.data, args.folds),
                                     separators=(",", ":")) + ";\n", encoding="utf-8")
        print("wrote", OUT / "echo.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
