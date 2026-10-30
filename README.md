# NEMATICA

**A Turing test for artificial brains, starting with the worm.**

People are building digital nervous systems for *C. elegans* and the fruit fly, but there is
no agreed way to say whether one is right. NEMATICA is that test. It scores an artificial
worm brain against whole-brain recordings from real worms, level by level, using **how
different real worms are from each other** as the unit of measurement. A model passes a
level when it is as close to real worms as real worms are to each other: no closer, no
further.

> Real worms are weird. Fake ones are average.

The best model scored so far is "too typical": closer to every real worm than real worms
are to each other, which means it learned the average worm, not a worm.

## What is built

| Part | What it does |
|---|---|
| `nematica/data` | Loaders for Flavell-lab whole-brain recordings (copper-boundary set, Atanas 2023), NeuroPAL labels read straight from `.jld2`, worm-level frozen splits |
| `nematica/bench` | The ruler: eight pairwise metrics (Levels 1, 2, 4, 5), a population-level environment test (Level 6), a classifier two-sample test (Level 8), a worm-level bootstrap, calibration systems with designed outcomes |
| `nematica/forward` | Imaging model: turns simulated activity into what the microscope would record (calcium and indicator kinetics, frame exposure, noise, the template worm's labelled neurons) |
| `nematica/systems` | Systems under test: independent AR, joint VAR with behaviour, the Kunert 2014 connectome model (implicit-Euler integrator, validated against LSODA) |
| `lab/` | React and Three.js replay of real worms: tracked body, whole-brain activity glowing at atlas neuron positions, the copper arena |

### Levels

| Level | Metric | Question |
|---|---|---|
| 1 | `L1.distribution`, `L1.timescale` | Does each neuron class have realistic activity values and timescales? |
| 2 | `L2.correlation`, `L2.dimension` | Do the right classes move together, with realistic dimensionality? |
| 4 | `L4.leadlag`, `L4.dwell` | Who leads and who follows; how long reversal-command states last |
| 5 | `L5.encoding`, `L5.reversal` | Which classes track velocity and change during reversals |
| 6 | `L6.encounter`, `L6.approach` | Does the brain respond like a real one when the head meets the copper boundary? Does reversing rise near it? (population level) |
| 8 | `L8.discriminability` | Can a classifier, cross-validated by worm, tell 30 s windows of the system from real ones? |

Verdicts: **inside** (indistinguishable from another real worm), **outside**, or **too
typical** (significantly closer to every real worm than real worms are to each other).

## Results so far (copper test worms)

- The ruler hits every designed calibration outcome: 44 of 44 at the pairwise levels and
  5 of 5 at Level 6. Real worms from another lab's unstimulated sessions score inside
  everywhere.
- In the copper arena, ASH (the canonical nociceptor) is the strongest responder when the
  head meets the boundary, followed by AWC. Two random halves of the worms agree on the
  pooled encounter response at r = 0.62.
- No system passes yet (pairwise levels; behaviour levels are not scored for systems that
  produce no behaviour):

| System | Inside | Too typical | Outside | L8 AUC |
|---|---|---|---|---|
| joint VAR with behaviour | 2 | 3 | 3 | 0.99 |
| independent AR | 1 | 1 | 4 | 0.99 |
| Kunert 2014 connectome model | 0 | 0 | 6 | 1.00 |

## Arc 1: forecasting is not fidelity

![Shrinkage sweep](docs/figures/shrinkage.png)

**Tuning a model to forecast best makes it too typical.** Each training worm gets its own
linear model (VAR(3)), shrunk toward the shared model by a penalty λ. Forecasting skill
(within-worm R²) peaks at λ = 3,000. There, the simulated worms are too typical on
correlations and on velocity and reversal encoding (individuality 0.78). At λ = 300,
forecasting is only 0.009 R² lower and those levels sit on the real-worm line
(individuality 0.99). Fully shared dynamics (λ → ∞) are too typical on four levels.

Evidence is combined over three frozen, date-spread reference pools of 9 worms
(`configs/splits/copper2026_cv3.yaml`); every model is refitted on the other 18 worms of
each rotation. Nested check: choosing λ by realism on two pools and scoring it on the third
gives **7 of 8 levels inside on every held-out pool**. The one failure is the shape of
activity distributions (distance ratio about 1.5): Gaussian noise cannot make the skewed
calcium signal.

![Arc 1](docs/figures/arc1.png)

Other findings (`scripts/run_arc1.py`, `scripts/run_cv.py`; tables in `docs/figures/`):

- **Forecasting skill does not rank realism.** Models within 0.006 of each other in
  one-step R² (per-neuron AR, VAR, reservoirs of 400 and 1,500 units) range from 2 to 6 of 8
  levels outside and from 0.33 to 1.37 in individuality.
- **Shared dynamics make an average worm.** VAR(1), VAR(3) and the reservoir are too
  typical on correlations, lead-lag and behaviour encoding in all three pools. Tripling the
  reservoir changes nothing.
- **What has to vary between simulated worms is the dynamics, not the noise.** At the
  forecasting-chosen shrinkage, per-worm noise alone closes about 15% of the gap to real
  worms; per-worm dynamics close 55 to 77%; per-worm deviations of the same size with their
  structure scrambled close 40 to 91% (they fix correlations and lead-lag but not behaviour
  encoding).
- **A static warp does not fix the last level.** Running the same linear dynamics in a
  Gaussian-copula space (each neuron's own empirical distribution) brings the activity
  distribution ratio from about 1.5 to 1.06, but breaks reversal-state dwell times (1.00
  to 1.23): 6 of 8 inside instead of 7. With shared marginals the distributions become too
  typical (0.93). Skewed activity and realistic bout durations seem to need genuine state
  switching, which is the next model (`scripts/run_warp.py`, `docs/figures/warp_combined.csv`).
- A correction: on the single frozen 6-worm test pool the per-worm model looked fully
  inside on these levels; the rotating pools show that at the forecasting-chosen shrinkage
  it is still slightly too typical. The shrinkage sweep explains why.

Caveats: 27 worms from one lab; the per-worm and shrinkage analyses were proposed after
the first ladder results and are tested with controls and nested selection, not
pre-registered; Level 8 (classifier) has not yet been run on the sweep.

## Setup (Windows, PowerShell)

```powershell
git clone https://github.com/Weptune/nematica
cd nematica
uv venv --python 3.12
.venv\Scripts\activate
uv pip install -e ".[dev]"
python -m pytest -q
```

## Data

Raw data is not in this repository. Download it into `data/raw/`:

- **Copper-boundary set** (Baskoylu et al. 2026, CC0):
  https://datadryad.org/dataset/doi:10.5061/dryad.w9ghx3g4v into
  `data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415/`
- **Atanas et al. 2023**: `python scripts/fetch_atanas_copy.py` (a third-party copy of the
  WormWideWeb JSON, for local development; the processed `.h5` files are on Zenodo)
- **Neuron position atlas** (Skuhersky et al. 2022): `python scripts/fetch_atlas.py`

## Running the benchmark

```powershell
$copper = "data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415"
python scripts/run_ruler.py --dataset copper --data $copper --split configs/splits/copper2026.yaml --other-data data/raw/atanas2023_wwweb
python scripts/run_ruler.py --dataset copper --data $copper --split configs/splits/copper2026.yaml --env-only
python scripts/precompute_kunert.py --amplitudes 0.5 --seeds 6     # cached connectome simulations
python scripts/run_benchmark.py --dataset copper --data $copper --split configs/splits/copper2026.yaml --amplitudes 0.5
python scripts/run_l8.py --dataset copper --data $copper --split configs/splits/copper2026.yaml
python scripts/plot_profile.py --dataset copper                     # results/bench/fidelity_copper.png
python scripts/run_arc1.py --data $copper --split configs/splits/copper2026.yaml --seeds 4 --out results/arc1_controls
python scripts/plot_arc1.py --results results                        # results/arc1/arc1.png
python scripts/run_cv.py --data $copper --folds configs/splits/copper2026_cv3.yaml
python scripts/run_shrinkage.py --data $copper --folds configs/splits/copper2026_cv3.yaml
python scripts/plot_shrinkage.py                                     # results/shrinkage/shrinkage.png
```

## Replay lab

```powershell
python scripts/fetch_atlas.py
python scripts/export_replay.py data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 --split configs/splits/copper2026.yaml --out lab/public/data
cd lab; npm install; npm run dev
```

## Rules that keep the benchmark honest

- `trace_array` in the Flavell files is z-scored over the whole recording, which leaks the
  future into the past; NEMATICA loads `trace_original` / `trace_array_original`.
- Splits are by worm, made once, frozen with a hash and never regenerated after results
  are seen.
- A system is never compared with the worm it was derived from.
- Every ruler change is checked against calibration systems whose answers were written
  down before running.
- Every quantity carries a provenance tag: **M** measured, **I** inferred, **L** learned,
  **A** assumed.

## Sources and licences

- Copper-boundary whole-brain recordings: Baskoylu et al. 2026, Dryad
  10.5061/dryad.w9ghx3g4v (CC0).
- Atanas et al. 2023, *Cell*: brain-wide representations of behavior (Flavell lab).
- Kunert, Shlizerman, Kutz 2014 connectome model; matrices from the C. elegans Neural
  Interactome (BSD 3-Clause, `data_assets/kunert2014/LICENSE`).
- Skuhersky et al. 2022 neuron atlas (paper CC BY 4.0), downloaded by script, not
  redistributed.
