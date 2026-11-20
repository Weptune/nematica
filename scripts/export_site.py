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
    # artificial network families against real worms (scripts/summarize_gallery.py)
    track = {"hybrid_kernels_regimes_obsfit": "pokes", "hybrid_kernels": "pokes", "creamer-native": "pokes (published)",
             "linear-rest": "watching", "var3_spontaneous": "watching", "random-wiring": "watching, random wiring",
             "kunert2014": "wiring diagram only", "task-dense": "a task", "task-wired": "a task, real wiring"}
    out["gallery"] = [{"family": r["family"], "label": r["label"], "learned": track.get(r["family"], ""),
                       "echo": num(r["echo_agreement_median"]), "lo": num(r["echo_agreement_min"]),
                       "hi": num(r["echo_agreement_max"]), "real": num(r["real_agreement_median"]),
                       "pattern": int(r["pattern_agrees"]), "pools": int(r["pools"]),
                       "watchLo": int(r["watching_inside_min"]), "watchHi": int(r["watching_inside_max"])}
                      for r in rows("gallery_fingerprint.csv")]
    # synthetic worm: watching against poking (scripts/run_synthetic_watch.py)
    out["synthetic"] = [{"model": r["model"], "regime": r["regime"], "hours": num(r["hours"]),
                         "watching": num(r["watching"]), "poking": num(r["poking"])}
                        for m in ("connectome_constrained", "fully_connected")
                        for r in rows(f"synthetic_watch_{m}.csv") if r["regime"] in ("hidden", "drive05", "drive10")]
    # real worms: more training worms (scripts/run_data_scaling.py)
    out["scaling"] = [{"fold": int(r["fold"]), "model": r["model"], "worms": int(r["train_worms"]),
                       "echo": num(r["echo_agreement"]), "real": num(r["real_agreement"])} for r in rows("data_scaling.csv")]
    # the ruler's resolution (scripts/run_resolution.py)
    out["resolution"] = [{"error": r["error"], "size": num(r["size"]), "verdict": r["verdict"], "agrees": r["agrees"],
                          "agrees15": r["agrees_x1.5"]} for r in rows("resolution.csv")]
    # artificial lab A: watching vs poking in nonlinear brains with known truth (scripts/run_ann_watch.py)
    ann = []
    for fname, rec in (("ann_watch_fullobs.csv", "every"), ("ann_watch.csv", "atlas")):
        for r in rows(fname):
            ann.append({"rec": rec, "seed": int(r["seed"]), "share": num(r["share"]), "tau": num(r["tau"]),
                        "hours": num(r["hours"]), "linear": num(r["linear"]), "mlp": num(r["mlp"]),
                        "gru": num(r["gru"]), "poke": num(r["poke"])})
    out["ann"] = ann
    # artificial lab B: the ruler against known truth (scripts/run_ann_ruler.py), base species
    rb = []
    for tag in ("base", "nodrive", "strongdrive", "sigma0.1", "sigma0.6"):
        rs = rows(f"ann_ruler_{tag}.csv")
        for c in sorted({r["copy"] for r in rs}):
            sub = [r for r in rs if r["copy"] == c]
            me = sum(num(r["mean_echo_copy_vs_individuals"]) for r in sub) / len(sub)
            mi = sum(num(r["mean_echo_individuals_vs_each_other"]) for r in sub) / len(sub)
            rb.append({"species": tag, "copy": c, "ratio": me / mi if mi else None,
                       "inside": sum(r["verdict"] == "inside" for r in sub),
                       "agrees": sum(r["equivalence"] == "agrees" for r in sub), "pools": len(sub)})
    out["annRuler"] = rb
    # artificial lab C: taking the drives out (scripts/run_ann_deconfound.py)
    out["annDeconf"] = [{"rec": r["recording"], "watcher": r["watcher"], "score": num(r["score"])}
                        for r in rows("ann_deconfound.csv")]
    return out


def _q(a):
    a = np.asarray([v for v in a if v is not None and np.isfinite(v)], float)
    return [round(float(np.percentile(a, p)), 4) for p in (25, 50, 75)] if a.size else None


def beyond() -> dict:
    """Chapters beyond the first worm results (added 18 Nov 2026). Summary numbers only, all from committed
    files: the map study's per-mouse test (docs/figures/map_permouse.json), Study 2 (docs/figures/slow_runs),
    the emulator's transfer tests (docs/figures/emulator_transfer.json)."""
    out = {}
    # map study, amendment 27: each mouse against the random RNN recorded at that mouse's own instrument
    pm = json.loads((FIG / "map_permouse.json").read_text())
    slow = {p["mouse"]: p["ai_value"] for p in pm["pairs"]["A1-slow"]}
    mice = sorted(({"m": round(p["mouse_value"], 4), "rnn": round(p["ai_value"], 4),
                    "slow": (round(slow[p["mouse"]], 4) if slow.get(p["mouse"]) is not None and np.isfinite(slow[p["mouse"]]) else None)}
                   for p in pm["pairs"]["A1"]), key=lambda d: d["m"])
    tb, td = pm["tests"]["B' per-mouse slow memory"], pm["tests"]["D' per-mouse slow drives"]
    out["permouse"] = {"mice": mice, "rulerSD": round(pm["ruler_sd"], 4),
                       "lower": sum(d["rnn"] < d["m"] for d in mice), "n": len(mice),
                       "slowHigher": sum(d["slow"] is not None and d["slow"] > d["m"] for d in mice),
                       "nSlow": sum(d["slow"] is not None for d in mice),
                       "medianSD": round(tb["median_diff_ruler"], 2), "ci90SD": [round(v, 2) for v in tb["ci90_ruler"]],
                       "p": tb["p_mouse_above"], "slowSD": round(td["median_diff_ruler"], 2)}
    # Study 2: internal share (M1) and relative slowness (M2) per network family, against 49 mice
    R = FIG / "slow_runs"
    ids = set(json.loads((R / "mice_table.json").read_text())["rows"])
    mrows = [json.loads(l) for l in (R / "mice.jsonl").open()]
    mm = [m for m in mrows if m["id"] in ids]
    ai = {}
    for f in sorted(R.glob("ais*.jsonl")):
        if "dry" in f.name or "retry" in f.name:
            continue
        for l in f.open():
            r = json.loads(l)
            ai[(r["family"], r["run"], r.get("id"), r.get("instance"))] = r
    for l in (R / "ais_retry.jsonl").open():
        r = json.loads(l)
        ai[(r["family"], r["run"], r.get("id"), r.get("instance"))] = r
    rows_ = [r for r in ai.values() if "error" not in r and r.get("reached") and r.get("id") in ids]
    tests = json.loads((R / "tests.json").read_text())
    FAM = {"A2": "Task-trained RNN", "A3": "GRU", "A5": "CfC", "A6": "Pythia", "A7": "Mamba", "A1": "Random RNN", "A4": "Spiking network"}
    groups = defaultdict(list)
    for r in rows_:
        fam, run = r["family"], r["run"]
        if fam in ("A2", "A3", "A5"):
            key = (fam, "")
        elif fam == "A6":
            key = (fam, run.split("pythia-")[1].split("-")[0].upper())
        elif fam == "A7":
            key = (fam, run.split("mamba-")[1].split("-")[0].upper())
        elif fam in ("A1", "A4"):
            key = (fam, "gain " + run.split("gain")[1])
        else:
            continue
        groups[key].append(r)
    fams = []
    for fam in ("A2", "A3", "A5", "A6", "A7", "A1", "A4"):
        h = tests["H1"].get(fam, {})
        entry = {"id": fam, "name": FAM[fam], "counted": h.get("M1", {}).get("counted", True) is not False,
                 "M1": {"verdict": h.get("M1", {}).get("verdict"), "d": num(h.get("M1", {}).get("median_d_ruler"))},
                 "M2": {"verdict": h.get("M2", {}).get("verdict"), "d": num(h.get("M2", {}).get("median_d_ruler"))},
                 "members": []}
        for (f, sub), rs in sorted(groups.items(), key=lambda kv: kv[0][1]):
            if f != fam:
                continue
            entry["members"].append({"label": sub, "n": len(rs), "M1": _q([r["M1"] for r in rs]), "M2": _q([r["M2"] for r in rs])})
        if fam in ("A6", "A7"):
            order = {"14M": 0, "160M": 1, "410M": 2, "1B": 3, "130M": 0, "370M": 1}
            entry["members"].sort(key=lambda m: order.get(m["label"], 9))
        if fam in ("A1", "A4"):
            entry["members"].sort(key=lambda m: float(m["label"].split()[1]))
        fams.append(entry)
    out["slowStudy"] = {"mice": {"n": len(mm), "M1": _q([m["M1"] for m in mm]), "M2": _q([m["M2"] for m in mm]),
                                 "M1all": sorted(round(m["M1"], 3) for m in mm if m["M1"] is not None),
                                 "M2all": sorted(round(m["M2"], 3) for m in mm if m["M2"] is not None)},
                        "rulers": tests["rulers"], "families": fams,
                        "claims": {k: v.get("holds") for k, v in tests["claims"].items()}}
    # where the answer stands: each measured difference and what closed it (home page). Constants are from the
    # record (README sections named in each comment); the rest is computed above.
    counted = [mb["M1"][1] for f in fams if f["counted"] for mb in f["members"]]
    em = json.loads((FIG / "emulator_transfer.json").read_text())
    out["gaps"] = [
        {  # README headline and "Arc 4: the causal Turing test" (repaired data, six held-out pools)
            "title": "Answering a single-neuron poke", "where": "Worm, 113 animals (signal-propagation atlas)",
            "scale": "Echo agreement with real worms", "domain": [0, 0.14], "ticks": [0, 0.05, 0.1], "dp": 2,
            "band": [0.087, 0.121], "bandLabel": "real worms with each other",
            "plain": {"range": [0.004, 0.014], "label": "copy fitted by watching"},
            "fixed": {"range": [0.088, 0.113], "value": 0.1, "label": "copy that also learned from pokes", "below": True},
            "status": {"kind": "closed", "text": "Closed by learning from pokes",
                       "sub": "Pattern shown equivalent in 6 of 6 held-out groups; size and ongoing activity match less well"},
            "tip": [["Copy fitted by watching", "0.004 to 0.014"], ["Real worms with each other", "0.087 to 0.121"],
                    ["Copy that also learned from pokes", "0.088 to 0.113"]],
            "note": "Watching passes 3 to 5 of 6 activity tests in each group, yet misses the echo."},
        {  # README "Arc 1: forecasting is not fidelity" (not pre-registered)
            "title": "Being an individual", "where": "Worm, 27 freely moving animals (copper set)",
            "scale": "Individuality (1 = as distinct as real worms are)", "domain": [0.6, 1.1], "ticks": [0.6, 0.8, 1.0], "dp": 1,
            "band": [0.99, 1.01], "bandLabel": "real worms",
            "plain": {"value": 0.78, "label": "tuned to forecast best"},
            "fixed": {"value": 0.99, "ok": True, "label": "keeps each worm's own dynamics", "below": True},
            "status": {"kind": "closed", "text": "Closed by keeping individuals",
                       "sub": "Costs 0.009 of forecasting skill; 7 of 8 tests inside in a nested check"},
            "tip": [["Best forecaster", "too typical on correlations and behaviour encoding"], ["Individuality", "0.78 against 0.99"]],
            "note": "Not pre-registered; one lab's worms."},
        {  # docs/MAP.md amendments 27 and 28
            "title": "Slow memory at rest", "where": f"Mouse visual cortex, {out['permouse']['n']} animals (Allen Neuropixels)",
            "scale": "Network minus mouse, in between-mouse SDs", "domain": [-2, 1], "ticks": [-2, -1, 0, 1], "dp": 0,
            "band": [-0.5, 0.5], "bandLabel": "within half an SD",
            "plain": {"value": -out["permouse"]["medianSD"], "label": "random network"},
            "fixed": {"value": -0.03, "range": [-0.73, 0.08], "label": "with a slow drive, 18 held-out mice", "below": True},
            "status": {"kind": "closed", "text": "Closed by a slow drive",
                       "sub": "About 6% of each unit's variance; interval too wide to show equivalence"},
            "tip": [["Random network lower in", f"{out['permouse']['lower']} of {out['permouse']['n']} mice"],
                    ["Mouse minus network", f"{out['permouse']['medianSD']} SDs [{out['permouse']['ci90SD'][0]} to {out['permouse']['ci90SD'][1]}]"],
                    ["With a slow drive, held-out mice", "+0.03 SDs [−0.08 to +0.73]"]],
            "note": "Each network is recorded through that mouse's own simulated instrument. The per-mouse rule was set after the mouse values were known."},
        {  # docs/SLOW_SUMMARY.md, tests.json
            "title": "Internal state during a movie", "where": f"Mouse visual cortex, {out['slowStudy']['mice']['n']} animals; five network families counted",
            "scale": "Share of state that is internal, not locked to the input", "domain": [0, 1], "ticks": [0, 0.5, 1], "dp": 1,
            "band": [out["slowStudy"]["mice"]["M1"][0], out["slowStudy"]["mice"]["M1"][2]], "bandLabel": "middle half of the mice",
            "plain": {"values": sorted(counted), "label": "network families and sizes", "below": True, "anchor": "end"},
            "status": {"kind": "none", "text": "No gap: networks on both sides",
                       "sub": "Pre-registered: none of four claims of more, slower internal state held"},
            "tip": [["Mice, median", str(out["slowStudy"]["mice"]["M1"][1])],
                    ["Networks, medians", f"{min(counted):.2f} to {max(counted):.2f}"]],
            "note": "Task-trained RNN and Mamba carry more internal state than the mice; GRU and CfC less; transformer sizes span them."},
        {  # README "Light or activity: what tires a worm neuron?" (exploratory curve, corrected by review 7)
            "title": "Answering the same poke again", "where": "Worm, 56 repeat pairs in 37 animals",
            "scale": "Second response ÷ previous, 0.6 to 2 minutes apart", "domain": [0, 1.2], "ticks": [0, 0.5, 1], "dp": 1,
            "band": [0.34, 0.64], "bandLabel": "real worms",
            "plain": {"value": 1.0, "label": "artificial networks"},
            "status": {"kind": "open", "text": "Open: the light tool, or the neuron",
                       "sub": "A network whose input weakens with use reproduces it; this data cannot tell which the worm has"},
            "tip": [["Real worms", "about half (interval 0.34 to 0.64)"], ["Artificial networks", "the same every time"]],
            "note": "Exploratory curve. About 9% of the atlas's stimulations are repeats within 5 minutes."},
        {  # docs/figures/emulator_transfer.json; README test T
            "title": "Ongoing activity in moving worms", "where": "Worm, 30 freely moving animals (another lab)",
            "scale": "Activity tests passed, of 6", "domain": [0, 6], "ticks": [0, 1, 2, 3, 4, 5, 6], "tickFmt": "int",
            "band": [5, 6], "bandLabel": "pass mark",
            "plain": {"value": em["atanas_control_rest"][0]["rest"], "label": "fitted to rest only"},
            "fixed": {"value": em["atanas"][0]["rest"], "label": "the emulator recipe", "below": True},
            "status": {"kind": "open", "text": "Open: still and moving worms differ",
                       "sub": "The recipe built on immobilised worms fails here; movement or lab conditions"},
            "tip": [["Emulator recipe", f"{em['atanas'][0]['rest']} of 6, in all five noise draws"], ["Fitted to rest only", f"{em['atanas_control_rest'][0]['rest']} of 6"]],
            "note": "Refitted from scratch on these worms; no optogenetic pokes in this data."},
    ]
    # arc 1: forecasting skill and individuality across the shrinkage penalty (docs/figures/shrinkage.csv)
    out["shrinkage"] = [{"lam": r["lam"], "r2": num(r["within_worm_r2"]), "ind": num(r["individuality"]),
                         "typical": sum(v == "too typical" for k, v in r.items() if k.endswith("_verdict")),
                         "outside": sum(v == "outside" for k, v in r.items() if k.endswith("_verdict"))} for r in rows("shrinkage.csv")]
    # the open brain-likeness test: its calibration systems, for the static page at web/test/
    board = []
    for f in sorted((ROOT / "nematica" / "brainlike" / "calibration").glob("*.json")):
        d = json.loads(f.read_text()); r = d["result"]
        if not r.get("valid") or r.get("mean_abs_distance") is None:
            continue
        board.append({"name": d["name"], "about": d.get("description", ""), "score": r["score"], "outOf": r["out_of"], "distance": round(float(r["mean_abs_distance"]), 2),
                      "sig": {k: {"d": round(float(v["distance"]), 2), "in": bool(v["inside"]), "label": v["label"]} for k, v in r["signatures"].items() if v.get("distance") is not None}})
    out["testBoard"] = sorted(board, key=lambda b: (b["distance"], -b["score"]))
    # a repeat poke: response as a share of the previous one, by the time between pokes
    import math
    out["recovery"] = [{"gap": r["gap_min"], "worms": int(r["worms"]), "pairs": int(r["pairs"]), "pct": round(math.exp(float(r["decline"])), 3),
                        "lo": round(math.exp(float(r["lo"])), 3), "hi": round(math.exp(float(r["hi"])), 3)} for r in rows("recovery_curve.csv")]
    # Study V: the watching copy's predicted direction vs the real direction, per mouse (39 held-out mice)
    vr = json.loads((FIG / "opto/vbn_result.json").read_text())
    wt = json.loads((FIG / "opto/vbn_wt_control.json").read_text())["wt_real_up"]
    out["optoSign"] = {"mice": [{"id": m, "line": v["line"], "real": v["real_up"], "w": v["w_up"], "rest": v["rest_r"]}
                                for m, v in vr["mice"].items()],
                       "wt": [round(float(x), 3) for x in np.percentile(wt, [25, 50, 75])], "nWT": len(wt),
                       "claims": {k: vr[k] for k in ("V1", "V2", "V3", "V4", "V5")},
                       "median": {k: vr[f"median_{k}"] for k in ("Sst", "Vip")}}
    # the emulator: passes on the worms it was built on, not on others
    out["emulator"] = json.loads((FIG / "emulator_transfer.json").read_text())
    out["emulator"].pop("note", None)
    for k, v in out["emulator"].items():
        for s in v:
            s.pop("letters", None)
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


def brain() -> dict:
    """Every neuron at its mean soma position (Skuhersky et al. 2022 atlas) with its class, and
    the anatomical wiring between them (Kunert et al. 2014 matrices), for the opening experiment
    on the home page. Local only (the atlas copy is not redistributed)."""
    import ast
    from nematica.data.pumpprobe import neuron_class
    from nematica.export.atlas import load_atlas
    atlas = load_atlas()
    names = sorted(atlas)
    idx = {n: i for i, n in enumerate(names)}
    kn = [str(n) for n in ast.literal_eval((ROOT / "data_assets" / "kunert2014" / "neuron_names.txt").read_text())]
    Gs, Gg = np.load(ROOT / "data_assets" / "kunert2014" / "Gs.npy"), np.load(ROOT / "data_assets" / "kunert2014" / "Gg.npy")
    edges = []
    for i, a in enumerate(kn):
        for j, b in enumerate(kn):
            if a in idx and b in idx and i != j and (Gs[i, j] > 0 or (Gg[i, j] > 0 and i < j)):
                edges += [idx[b], idx[a]]       # from b onto a
    return {"names": names, "cls": [neuron_class(n) for n in names],
            "pos": [round(v, 1) for n in names for v in atlas[n]], "edges": edges}


def wiring() -> dict:
    """The worm's wiring for the home page's scene, from data the repository ships (Kunert et al. 2014 matrices via
    the C. elegans Neural Interactome, BSD 3-Clause): 279 connected somatic neurons, their chemical synapses and gap
    junctions. Positions are schematic, from anatomy alone: the matrices list neurons from head to tail, so the
    order sets each neuron's place along the body (head ganglia, ventral cord, tail ganglia), and its name sets its
    side (left or right) and, where the name says so, dorsal or ventral. No measured coordinates are used."""
    import ast
    import hashlib
    names = [str(n) for n in ast.literal_eval((ROOT / "data_assets" / "kunert2014" / "neuron_names.txt").read_text())]
    Gs, Gg = np.load(ROOT / "data_assets" / "kunert2014" / "Gs.npy"), np.load(ROOT / "data_assets" / "kunert2014" / "Gg.npy")
    N, have = len(names), set(names)
    i_cord, i_tail = names.index("VA01"), names.index("PVPR")
    jit = lambda n, k: int(hashlib.md5(f"{n}{k}".encode()).hexdigest()[:8], 16) / 2 ** 32 - 0.5  # noqa: E731
    pos = []
    for i, n in enumerate(names):
        if i < i_cord:   ap, half = 18 + 120 * i / i_cord, 1.0                                  # head ganglia
        elif i < i_tail: ap, half = 150 + 560 * (i - i_cord) / (i_tail - i_cord), 0.45           # ventral cord and mid-body
        else:            ap, half = 730 + 70 * (i - i_tail) / (N - i_tail), 0.7                   # tail ganglia
        side = 1 if n.endswith("L") and n[:-1] + "R" in have else -1 if n.endswith("R") and n[:-1] + "L" in have else 0
        dv = 1 if len(n) > 3 and n[-2:-1] == "D" and side else -1 if len(n) > 3 and n[-2:-1] == "V" and side else 0
        cord = i_cord <= i < i_tail and n[:2] in ("VA", "VB", "VC", "VD", "DA", "DB", "DD", "AS")
        y = -15 + 3 * jit(n, "y") if cord else (dv * 9 + 14 * jit(n, "y")) * half
        z = 3 * jit(n, "z") if cord else (side * 7 + 6 * jit(n, "z")) * half
        pos += [round(ap + 6 * jit(n, "x"), 1), round(y, 1), round(z, 1)]
    edges = []
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i != j and (Gs[i, j] > 0 or (Gg[i, j] > 0 and i < j)):
                edges += [j, i]                     # from b onto a
    return {"names": names, "pos": pos, "edges": edges, "source": "Kunert et al. 2014 via the C. elegans Neural Interactome (BSD 3-Clause); schematic positions"}


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
    (OUT / "results.js").write_text("window.NEMATICA_RESULTS = " + json.dumps({**results(), **beyond()}, separators=(",", ":")) + ";\n",
                                    encoding="utf-8")
    print("wrote", OUT / "results.js")
    (OUT / "wiring.js").write_text("window.NEMATICA_WIRING = " + json.dumps(wiring(), separators=(",", ":")) + ";\n", encoding="utf-8")
    print("wrote", OUT / "wiring.js")
    if args.sims:
        sims()
    if args.local:
        if not args.echo_only:
            (OUT / "local.js").write_text("window.NEMATICA_LOCAL = " + json.dumps(local(args.data, args.folds, args.frames),
                                          separators=(",", ":")) + ";\n", encoding="utf-8")
            print("wrote", OUT / "local.js")
        (OUT / "brain.js").write_text("window.NEMATICA_BRAIN = " + json.dumps(brain(), separators=(",", ":")) + ";\n", encoding="utf-8")
        print("wrote", OUT / "brain.js")
        (OUT / "echo.js").write_text("window.NEMATICA_ECHO = " + json.dumps(echoes(args.data, args.folds),
                                     separators=(",", ":")) + ";\n", encoding="utf-8")
        print("wrote", OUT / "echo.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
