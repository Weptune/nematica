"""Export real and artificial echoes for the lab's "Poke it yourself" view (lab ?mode=poke).

One held-out worm from rotation 0 of the original atlas archive: for up to --n stimulations
of different neuron classes, the real worm's class-level echo (30 s, in units of each
neuron's pre-stimulus fluctuation size) and the echoes of artificial brains fitted on the
training worms, stimulated at the same moments. Class positions come from the local
Skuhersky et al. 2022 atlas (not redistributed; the export stays in lab/public/data).

Usage:
  python scripts/export_poke.py --data data/raw/randi2023_wt_npz --folds configs/splits/pumpprobe_cv3.yaml
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nematica.bench.perturbational import event_matrices  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir, neuron_class  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from run_same_worms import make_model  # noqa: E402

PREFERRED = ["AVA", "AVE", "RIM", "AIB", "AVJ", "AWB", "RMD", "SMD", "IL1", "OLQ", "URX", "ASH", "RIA", "M3",
             "I2", "AVD", "RME", "AFD", "ASE", "AWC", "RIB", "AIY", "AIZ", "FLP", "BAG"]
LABELS = {"AVA": "command interneuron for backing up", "AVE": "backward command interneuron",
          "RIM": "motor interneuron, reversals", "AIB": "interneuron, turning and reversals",
          "AVJ": "interneuron", "AWB": "smell neuron (repellents)", "RMD": "head motor neuron",
          "SMD": "head-bending motor neuron", "IL1": "lip mechanosensory neuron", "OLQ": "nose-touch neuron",
          "URX": "oxygen-sensing neuron", "ASH": "pain and danger sensor", "RIA": "head-steering interneuron",
          "M3": "pharynx motor neuron", "I2": "pharynx interneuron", "AVD": "touch command interneuron",
          "RME": "head motor neuron", "AFD": "temperature sensor", "ASE": "salt sensor", "AWC": "smell neuron (attractants)",
          "RIB": "forward-running interneuron", "AIY": "interneuron, forward runs", "AIZ": "interneuron, turning",
          "FLP": "harsh-touch sensor", "BAG": "carbon dioxide and oxygen sensor"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--models", default="var3_spontaneous,creamer2024_fully_connected")
    ap.add_argument("--atlas", default="data_assets/skuhersky2022_atlas.csv")
    ap.add_argument("--out", default="lab/public/data/poke1")
    ap.add_argument("--n", type=int, default=10)
    args = ap.parse_args()
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    folds = load_folds(args.folds)["folds"]
    pool = [recs[u] for u in folds[0]]
    rest = sorted(u for f in folds[1:] for u in f)
    val_uids = rest[::5]
    train = [recs[u] for u in rest if u not in val_uids]
    val = [recs[u] for u in val_uids]

    def pick(r):
        evs = event_matrices(r, keep=True)
        if not evs:
            return []
        med = float(np.median([e["spread"] for e in evs]))
        chosen = []
        for c in PREFERRED:          # per class, its most typical stimulation (spread nearest the worm's median)
            cand = [e for e in evs if e["stim_class"] == c and e["spread"] > 0]
            if cand:
                chosen.append(min(cand, key=lambda e: abs(e["spread"] - med)))
        return chosen

    # a typical worm: among those with stimulations of at least 8 listed classes, the one whose
    # median echo spread is nearest the pool's median
    picks = {r.uid: pick(r) for r in pool}
    spreads = {u: float(np.median([e["spread"] for e in event_matrices(recs[u])] or [np.nan])) for u in picks}
    pool_med = float(np.nanmedian(list(spreads.values())))
    ok = [u for u, p in picks.items() if len(p) >= 8] or list(picks)
    worm = recs[min(ok, key=lambda u: abs(spreads[u] - pool_med))]
    events = picks[worm.uid][:args.n]
    print(f"pool median spread {pool_med:.3f}; worm {worm.uid} median {spreads[worm.uid]:.3f}")
    frames = {e["frame"] for e in events}
    print(f"worm {worm.uid}: {len(events)} events: {[e['stim_class'] for e in events]}")
    out_models = []
    for spec in args.models.split(","):
        m = make_model(spec).fit(train, val)
        sim = m.simulate(worm, np.random.default_rng(7))
        sev = {e["frame"]: e for e in event_matrices(sim, keep=True) if e["frame"] in frames}
        out_models.append({"name": spec, "events": sev})
        print(f"  {spec}: {len(sev)} matching events")
    # class positions: mean of members' (x, y) in the atlas
    pos: dict = {}
    if Path(args.atlas).exists():
        with open(args.atlas, encoding="utf-8") as fh:
            for row in csv.reader(fh):
                c = neuron_class(row[0])
                pos.setdefault(c, []).append((float(row[1]), float(row[2])))
    pos = {c: np.mean(v, axis=0).round(2).tolist() for c, v in pos.items()}

    def pack(e):
        if e is None:
            return None
        return {"classes": e["classes"], "R": np.round(np.clip(np.nan_to_num(e["R"]), -8, 8), 2).tolist(),
                "pci": round(e["pci"], 3), "spread": round(e["spread"], 4)}

    bundle = {"format": "nematica-poke/1", "worm": worm.uid, "dt": worm.dt, "threshold": 3.0,
              "positions": pos, "labels": LABELS,
              "brains": ["Real worm"] + [m["name"] for m in out_models],
              "events": [{"stim": e["stim_class"], "frame": e["frame"],
                          "echoes": [pack(e)] + [pack(m["events"].get(e["frame"])) for m in out_models]}
                         for e in events]}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "poke.json").write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out / 'poke.json'} ({(out / 'poke.json').stat().st_size / 1e3:.0f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
