# NEMATICA lab (web)

Replay of real worms from the copper-boundary test set: the tracked body, the recorded
whole-brain activity glowing at atlas neuron positions, the arena and its copper boundary.

## Run (Windows, PowerShell)

```powershell
cd lab
npm install
npm run dev        # opens http://localhost:5173
```

The replay bundles in `public/data/` come from the Python side. They are generated, not
committed; run this from the repository root:

```powershell
python scripts/fetch_atlas.py
python scripts/export_replay.py data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 --split configs/splits/copper2026.yaml --out lab/public/data
```

`npm run build` writes the static lab into `../web/lab/`, including the exported replay data.
Serve `web/` to view the main site and lab together (for example,
`python -m http.server 8080 -d web`). Port 5173 is only the Vite development server.

## URL options

- `?mode=which` "Which one is real?": a real worm and a model worm side by side (export
  rounds with `python scripts/export_virtual_worms.py` first)

- `?uid=2024-06-18-12` pick a recording
- `?t=240` start time in seconds, `&paused=1` start paused
- `&neuron=AVAL` pin a neuron (name or class)
- `&view=arena` start in the arena overview

## What is real

- **M measured:** neural activity, body posture, path, copper boundary radius
- **I inferred:** neuron positions (atlas average, Skuhersky et al. 2022), not this worm's own
- **A assumed:** body width profile, interpolation between 1.67 Hz frames, glow mapping, agar texture,
  which side of the body is dorsal, a fitted constant camera-to-stage offset (head error about 20 um)
