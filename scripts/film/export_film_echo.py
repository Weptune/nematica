"""Write lab/public/data/film_echo.json for the film's stimulation shot (shot=echo).

Takes the first event of the lab's poke export (AVE in one atlas worm: lab/public/data/poke1/poke.json,
from scripts/export_poke.py) and places each responding neuron class at its average 3D position from
the Skuhersky et al. (2022) atlas (data_assets/skuhersky2022_atlas.csv, downloaded locally, not
redistributed). The output is derived from third-party data and stays in the gitignored data folder.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
poke = json.loads((ROOT / "lab/public/data/poke1/poke.json").read_text())
ev = poke["events"][0]
atlas = [(r[0], [float(r[1]) + 20, float(r[2]), float(r[3])])            # +20 um: the replay's nose offset
         for r in csv.reader(open(ROOT / "data_assets/skuhersky2022_atlas.csv"))]
SUFFIX = {"L", "R", "DL", "DR", "VL", "VR", "D", "V", ""}
classes = sorted({c for e in ev["echoes"] for c in e["classes"]} | {ev["stim"]})
neurons = [{"name": n, "cls": c, "pos_um": p} for c in classes for n, p in atlas
           if n.startswith(c) and n[len(c):] in SUFFIX]
out = {"stim": ev["stim"], "dt": poke["dt"], "threshold": poke["threshold"], "neurons": neurons,
       "brains": [{"name": b, "R": dict(zip(e["classes"], e["R"])), "spread": e["spread"]}
                  for b, e in zip(poke["brains"], ev["echoes"])],
       "background": [{"name": n, "pos_um": p} for n, p in atlas if p[0] < 450]}
dst = ROOT / "lab/public/data/film_echo.json"
dst.write_text(json.dumps(out))
print(f"{len(neurons)} neurons in {len(classes)} classes -> {dst}")
