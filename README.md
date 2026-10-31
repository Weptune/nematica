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
| behaviour | `B.rev_rate`, `B.rev_duration` | How often the worm starts a reversal, and how long reversals last |
| 6 | `L6.encounter`, `L6.approach`, `L6.occupancy` | Does the brain respond like a real one when the head meets the copper boundary? Does reversing rise near it? Does the worm spend realistic time near copper? (population level) |
| 8 | `L8.discriminability` | Can a classifier, cross-validated by worm, tell 30 s windows of the system from real ones? |

Verdicts: **inside** (indistinguishable from another real worm), **outside**, or **too
typical** (significantly closer to every real worm than real worms are to each other).

## Results so far (copper test worms)

- The ruler hits every designed calibration outcome at the pairwise levels (including the
  two reversal-statistics metrics, whose expectations were written before they were run)
  and 8 of 8 at Level 6. Real worms from another lab's unstimulated sessions score inside
  everywhere.
- In the copper arena, ASH (the canonical nociceptor) is the strongest responder when the
  head meets the boundary, followed by AWC. Two random halves of the worms agree on the
  pooled encounter response at r = 0.62.
- None of the baseline systems passes (pairwise levels, frozen test pool; behaviour levels
  are not scored for systems that produce no behaviour). Arc 1 below builds a model that
  passes all eight pairwise levels but still fails Level 8:

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
- **Neither does explicit state switching.** Separate forward and reverse dynamics, with
  neural activity driving the switches (`nematica/systems/switching.py`), bring the
  distribution ratio to 1.31 but make reversal bouts too typical: 6 of 8.
- **Diagnosis of the last level:** real traces have median skew 0.84 and excess kurtosis
  0.86; every linear-Gaussian model gives about 0. Detrending real worms barely changes the
  distance, so slow drift is not the cause. A stationary linear-Gaussian process is
  time-reversible, while calcium traces rise fast and decay slowly.
- **Modelling the drive instead of the trace passes all eight levels.** Each trace is
  deconvolved with a first-order calcium decay (d_t = y_t - γ y_{t-1}), the drive is
  modelled with per-worm VAR(3) (λ = 300) in per-worm normal scores, and samples are
  mapped back through the source worm's drive distribution and re-convolved
  (`CalciumStateSpace`, `scripts/run_calcium.py`). With γ = 0.5 (decay time 0.87 s) the
  model is **inside on 8 of 8 levels** combined over the three pools, skew 0.86 (real 0.84).
  γ was one of three values fixed in advance (0.5, 0.7, 0.85); choosing it on two pools and
  scoring the third gives 8/8, 7/8 and 8/8.
- **But a classifier still tells it apart (Level 8 AUC 0.94; other real worms 0.68).** The
  giveaway is short-timescale structure: within 30 s windows the model's lag-1
  autocorrelation is 0.755 against 0.656 in real worms (that feature alone gives AUC 0.88).
  Real worms have more power at both ends of the spectrum (33% of power in periods over
  3 minutes, against 19% in the model, plus more frame-to-frame variation). A VAR with
  1.8 s of memory cannot produce minute-scale structure.
- **For linear models, the eight levels and the classifier pull in opposite directions.**
  Real worms' slow power is not bleaching (raw brightness changes by about 1%, neurons rise
  and fall in equal numbers) but a slow brain-state shift: each neuron's slow part correlates
  about 0.63 with time, half of it one shared component. Adding 8 s and 50 s memory
  (`MultiScaleFeatures`) and a per-worm slow state (`SlowFastVAR`) lowers the Level 8 AUC
  from 0.94 to 0.84 on the frozen pool, but breaks pairwise levels: 6 of 8 inside instead
  of 8 (`scripts/run_slowfast.py`, `docs/figures/slowfast_combined.csv`). No linear model
  found so far passes both; real worms do.
- **A nonlinear model (GRU) has the same problem.** On the same drive-space state, a GRU
  trained for likelihood (`nematica/systems/gru.py`, `scripts/run_gru.py`), with size and
  stopping point chosen on validation worms only, is too typical on correlations and
  behaviour encoding and too low-dimensional: 3 of 8 inside for one shared GRU, 2 of 8 with
  an 8-number identity per worm, Level 8 AUC 0.95. Without early stopping it overfits
  badly (validation error 0.97 against 0.086). Selected for held-out likelihood (a
  forecasting criterion), a far more flexible model still produces an average worm; the
  per-worm linear model remains the most realistic one so far. Tables:
  `docs/figures/gru_combined.csv`, `gru_l8.csv`. PyTorch is optional (`pip install -e ".[gru]"`).
- **Reversal statistics catch the 8/8 model, and a decoder fixes it: 10 of 10.** Two
  behaviour metrics were added (onset rate per minute, `B.rev_rate`; bout-length
  distribution, `B.rev_duration`) after the closed-loop work showed that thresholding a
  noisy reversal channel goes unnoticed by the other levels. The calibration expectations
  were written first and all matched (frame shuffle outside, neural-only perturbations
  inside, other real worms inside). On the rotating pools the calcium model fails both
  (distance ratios 4.85 and 2.04): it reverses 8 times a minute for 1.8 s, against 2.9 times
  for 6.6 s in real worms, though the share of time reversing is about right (36% vs 31%).
  It flickers. Reading the same channel with hysteresis (start above `hi`, stop below `lo`,
  both fitted on training worms only: 0.25 and 0.75) gives 2.7 per minute and 6 s bouts, and
  the model is **inside on all 10 pairwise levels** (`Debounced`, `scripts/run_reversals.py`,
  `docs/figures/reversals_combined.csv`). The switching VAR, whose reversals are discrete
  states, already passed both (8 of 10 overall).
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
python scripts/run_calcium.py --data $copper --folds configs/splits/copper2026_cv3.yaml
python scripts/run_reversals.py --data $copper --folds configs/splits/copper2026_cv3.yaml
python scripts/fetch_creamer_lds.py
python scripts/run_published.py --data $copper --folds configs/splits/copper2026_cv3.yaml
```

## Replay lab

```powershell
python scripts/fetch_atlas.py
python scripts/export_replay.py data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 --split configs/splits/copper2026.yaml --out lab/public/data
cd lab; npm install; npm run dev
```

## Arc 5: a worm that senses copper

`nematica/systems/closed_loop.py`, `scripts/run_closed_loop.py`. The calcium brain model
gets a copper input (fitted on training worms), reversals are discrete events whose rate
depends on copper, and a motion-matched body moves the head, whose distance to copper feeds
back into the brain. Simulated in each held-out worm's own arena over the three rotating
pools, against the identical model blind to copper.

**Version 1 failed:** model worms spent 40% of their time within 0.5 mm of copper (blind:
46%), against 3.2% for real worms. That failure exposed a gap in the ruler (encounter and
approach could not reject even the blind model in pools of 9), so `L6.occupancy` was added,
and it flagged both models. A diagnosis on one rotation then compared the simulation with
the real worms directly:

- **Real worms do not steer away frame by frame.** Turning rate at 0.6 s frames is not
  predictable from brain activity, reversal state or geometry (held-out R² about 0), and
  turning away from copper is negligible. What they do: reverse more when close to copper
  AND facing it (onset rate per frame 0.095 at under 0.3 mm facing out, 0.033 far away),
  starting 1 to 2 mm out; turn more right after a reversal (0.174 vs 0.124 rad per frame);
  and crawl at a bimodal speed (about +0.09 forward, -0.08 mm/s reversing).
- **Version 2** adds exactly those: a directional sense (proximity x facing the copper);
  a sensing distance chosen from {0.25, 0.5, 1, 2, 4} mm by held-out likelihood on
  validation worms (1, 1 and 2 mm in the three rotations: copper is felt from a distance,
  as expected for ions diffusing into agar); speed drawn per state from real speed
  quantiles while the brain sets fast and slow moments; and motion matching that knows
  when a reversal just ended and how the worm has been turning.

Results, held-out pools combined (`docs/figures/closed_loop.csv`):

| | real | v2 senses copper | v2 blind |
|---|---|---|---|
| time within 0.5 mm of copper or beyond (median) | 3.2% | 19% | 69% |
| beyond the copper line | | 6% | 62% |
| L6.encounter / approach / occupancy | | inside / inside / inside | outside / inside / outside |
| pairwise levels inside | | 7 of 10 | 7 of 10 |

- The sensing model now passes Level 6 and the blind one fails it: copper input is what
  keeps the model worms in the arena. But 19% is still six times the real share; the
  population test (pools of 9) does not reject it, which says more about its power than
  about the model. Not solved yet.
- The pairwise misses have known causes: the reversal hazard is shared by all worms, so
  reversal rates are too uniform across worms (too typical, 0.75), and reversals are not
  driven by the brain, so the brain's lead-lag and reversal encoding fail. Next: per-worm
  hazards and a brain term that keeps the calibrated rate.

## Leaderboard: published models

`nematica/systems/published.py`, `scripts/fetch_creamer_lds.py`, `scripts/run_published.py`.
First entry: the three linear dynamical systems of Creamer, Leifer & Pillow (2024,
bioRxiv 10.1101/2024.09.22.614271, MIT licence), fitted to the Randi et al. (2023)
optogenetic atlas: weights restricted to the connectome, unrestricted, or restricted to a
shuffled connectome. Their trained parameters are read from the authors' pickles as plain
data (`nematica/data/safe_pickle.py`: none of their code is imported or run), and the models
are run with stimulation off to produce spontaneous activity. They make no behaviour, so the
behaviour levels are not scored. Rotating pools (`docs/figures/published_combined.csv`):

| Model | Inside (of 6) | Correlation | Dimension | Timescale |
|---|---|---|---|---|
| connectome-constrained | 0 | 1.43 | 2.92 | 1.56 |
| fully connected | 1 | 1.46 | 1.24 (inside) | 1.51 |
| shuffled connectome | 0 | 1.56 | 4.04 | 1.62 |

(numbers are distance ratios: 1 = as far as another real worm)

- **Not a fair test yet, and the caveat is the point:** these models describe immobilised
  worms, and the reference worms here crawl freely. A model of a still brain is far from a
  crawling one, as it should be. The comparison that matters for arc 3 (what the wiring
  buys) is against immobilised reference worms; the Randi recordings are on OSF, which
  neither this workspace nor the lab machine can reach yet.
- Within that caveat, the wiring helps on what it should: the real connectome beats the
  shuffled one on correlations (1.43 vs 1.56) and much more on dimensionality (2.92 vs
  4.04). The unconstrained model has the most realistic dimensionality.
- c302 (OpenWorm) is not scored yet.

## "Which one is real?" (prototype)

Two worms crawl side by side on agar. One is a held-out real worm (body, path and brain
as recorded). The other's brain activity, speed and reversals come from the most realistic
model so far; its body shapes and steering are motion-matched from real training worms
(`nematica/export/virtual_worm.py`), so the brain decides how fast and which way it goes.
Under each worm, rolling traces of the command neurons (AVA, AVE, AIB, RIM, RIB …) and the
reversal state show whether brain and behaviour line up the way they do in real worms.
Guess, then see the model's scorecard. Neither worm shows the copper ring: the model
cannot sense copper yet.

```powershell
python scripts/fetch_atlas.py
python scripts/export_virtual_worms.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 --split configs/splits/copper2026.yaml
cd lab; npm install; npm run dev        # then open http://localhost:5173/?mode=which
```

The answer for each round is in the round index, so this is a demo, not yet a fair test of
human viewers.

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
- Creamer, Leifer & Pillow 2024 trained models (MIT licence, Copyright (c) 2026 Matthew S.
  Creamer), downloaded by `scripts/fetch_creamer_lds.py`, not redistributed.
