# NEMATICA

**Real and artificial brains, neuron by neuron. We built artificial brains that pass for
real. Then we poked them.**

People are building digital nervous systems, and one day someone will claim an artificial
brain is a faithful copy of a real one. Nobody agrees how to check that claim. NEMATICA is
the check, run on the only brain small enough to compare completely: *C. elegans*, 302
neurons, every connection mapped, every neuron in its head imaged while it lives. An
artificial brain is tested the way doctors test a brain that cannot speak: watched at
rest, then perturbed, with the echo read using the same measures consciousness science
uses on people (perturbational complexity). Every test is measured in units of **how
different real worms are from each other**: a model passes when it is as close to real
worms as real worms are to each other, no closer and no further.

> Real worms are weird. Fake ones are average. And a brain can look real at rest while
> being wrong about cause and effect.

The headline so far (arc 4, rerun on the repaired data, 1 Nov 2026): on the same 113
stimulated worms, a model fitted to their ongoing activity passes 3 to 5 of 6 activity tests
in each of six held-out pools, yet its echoes to a single-neuron poke agree with real worms
at 0.004 to 0.014 (real worms agree with each other at 0.087 to 0.121). A model that also
learned from pokes agrees at 0.088 to 0.113, and on a stricter test (agreement within a
tolerance fixed in advance, not merely no difference detected) its echo pattern is shown to
match real worms in all six pools, while the model fitted to ongoing activity is shown not
to in all six. Watching a brain did not reveal which copy was right; poking it did.

> **Data repair, 1 Nov 2026.** Rebuilding the stimulated-worm data from the original archive
> with a script anyone can run (`scripts/convert_pumpprobe.py`) showed that 3 of the 113
> worms (20211128_112504, 20220331_142924, 20230304_112842) had been cut short when the
> archive was unpacked here, and had been scored as about one minute of scrambled data each.
> The other 110 rebuild exactly. The 3 are repaired. The three headline models are rerun
> on both splits (`results/fixed_cv3`, `results/fixed_blocks1`): 16 of 132 verdicts changed,
> almost all on activity levels near the boundary, and the headline above uses the repaired
> numbers. Other results that use the stimulated worms (arcs 4 onward) were computed before
> the repair and stay provisional until rerun.

Nothing here claims that a worm or a model is conscious; the question is whether artificial
brains have the measurable properties that, in people, separate a responsive brain from
an unresponsive one.

## What the project is

**One question: how do you know whether an artificial brain is right?** Digital nervous
systems are usually judged by forecasting skill or by looking plausible. NEMATICA builds a
better yardstick, the **ruler**: a set of levels (activity, correlations, timing,
behaviour coupling, behaviour, environment, a classifier), each measured in units of
worm-to-worm variation and each checked with deliberately broken calibration systems whose
outcomes are written down before running. Everything else is that ruler applied to harder
questions, one arc per question:

| Arc | Question | Answer so far |
|---|---|---|
| 1. Forecasting is not fidelity | Does the best forecaster make the most realistic worm? | No: forecasting-optimal models are too typical; realism needs each worm to keep its own dynamics. |
| 2. Digital twins | Can a model be a particular worm? | Per-worm models pass all 10 pairwise levels on the copper set, and a classifier cannot tell them from the worms they imitate; on a second dataset (Atanas 2023) the classifier result replicates but the pairwise levels only partly do (5 to 6 of 10). |
| 3. What the wiring buys | Does the real connectome make models more realistic? | Real wiring beats random wiring of the same density on every measure, by small margins; no wiring constraint beats data-chosen coupling at class resolution. |
| 4. Causal Turing test | Do models respond to perturbations like real brains? | Models that pass the activity tests (and the consciousness-science signatures of ongoing activity) answer pokes wrongly, including the published atlas models; watching a worm does not reveal its own causal fingerprint. The first model to pass the poke test needed causal links learned from pokes, dynamics learned by watching, non-propagating noise and calm/active regimes; it still fails perturbational complexity. Perturbational complexity (the consciousness-science measure): real echoes are sparse and differentiated; published models' are wide and stereotyped. |
| 5. Closed loop | Can a model brain drive a body in a real environment and behave like a worm? | Nearly: in the copper arena, all environment levels and 9 of 10 pairwise; copper's effect runs through ASH in real worms, and the model's ASH responds too slowly. |
| 6. Swarm (in progress) | Does it hold when many model brains interact? | Swarm engine built (32 closed-loop worms, touch and exclusion as stated assumptions). Individual worms make very different crowds; a swarm of the pooled "average worm" is more crowded than a mix of the worms it was fitted on. Scoring against real multi-worm tracking (Level 7) awaits the data. |

Outputs: the benchmark (calibrated levels, fair classifier test, a leaderboard of
published models), the findings above with their pre-written expectations and negative
results, and "Which one is real?", the public face of the same test.

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

## Results so far (copper set, Oct 31 2026)

**Headline numbers** (three rotating held-out pools of 9 worms unless stated; every
choice made on training and validation worms only, except where marked post hoc):

| | Pairwise levels inside | Level 8 classifier AUC (real control 0.46) | Copper arena |
|---|---|---|---|
| Baselines (joint VAR, independent AR, Kunert 2014 connectome model; frozen pool) | 0 to 2 of 8 | 0.99 to 1.00 | not modelled |
| Published: Creamer, Leifer & Pillow 2024 LDS (immobilised-worm models) | 0 to 1 of 6 | not run | not modelled |
| Per-worm calcium-drive VAR(3), hysteresis reversals | **10 of 10** | 0.82 held-out, 0.77 in-sample | not modelled |
| Same with 10 frames of memory | **10 of 10** | **0.62 held-out (not distinguishable in 2 of 3 pools), 0.50 in-sample** | not modelled |
| Same, coupling restricted to the connectome (arc 3) | 8 of 10 | 0.68 held-out, 0.57 in-sample (shuffled wiring: 0.69 to 0.72, 0.59 to 0.64) | not modelled |
| Same, connectome as a forecasting-chosen prior (arc 3) | 9 of 10 | 0.70 held-out (shuffled priors 0.72, 0.73) | not modelled |
| VAR(10), copper-trained, scored on Atanas 2023 worms | 6 of 10 (copper worms themselves: 7) | 0.87 (copper worms: 0.735) | not modelled |
| VAR(10) trained and tested within Atanas 2023 (replication) | 5 of 10 (VAR(3): 6) | 0.70 held-out, 0.57 in-sample (VAR(3) 0.79, 0.77; control 0.56) | not modelled |
| Closed loop v7 (3-frame brain senses copper, steers, reverses) | 9 of 10 | 0.95 (v6, frozen split) | occupancy and approach inside; 14 to 17% of time near copper (real 3.2%) |
| Closed loop v8 (10-frame brain) | 9 of 10 | not yet run | occupancy and approach inside; 11% near copper; encounter outside |
| Closed loop v9 (copper acts only through ASH and the brain) | 8 of 10 | not yet run | **all three Level 6 metrics inside**; 10.4% near copper |
| Closed loop v10 (v9 + tonic copper input) | 6 of 10 | not yet run | all three Level 6 inside; 25% near copper |
| **Closed loop v11 (copper enters only through ASH)** | **9 of 10** | 0.82 held-out, 0.79 in-sample | **all three Level 6 inside**; 13% near copper |
| Closed loop v12 (v11 with the 10-frame brain) | 9 of 10 | **0.67 held-out, 0.48 in-sample** | occupancy and approach inside, encounter outside; 19% near copper |

What these say:
1. **Forecasting is not fidelity.** The model that forecasts best is too typical; letting
   each worm keep more of its own dynamics than forecasting prefers is what makes models
   pass (arc 1).
2. **The ruler finds real errors.** Each new level (reversal statistics, arena occupancy,
   the fair classifier) caught a model that passed everything before it, and each caught
   error had a specific cause that was then fixed: flickering reversals, a data offset,
   too little memory, a missing outward drift.
3. **The remaining gaps are specific.** In the closed loop, copper reaches the reversal
   decision directly instead of through ASH, so the nociceptor's lead over the command
   neurons is halved (the one pairwise miss). The classifier's remaining giveaways in the
   one pool that still separates the model are AVA's smoothness and CEP's correlations
   with the command neurons.

Supporting facts:
- The ruler hits every designed calibration outcome at the pairwise levels (including the
  two reversal-statistics metrics, whose expectations were written before they were run)
  and 8 of 8 at Level 6. Real worms from another lab's unstimulated sessions score inside
  everywhere.
- In the copper arena, ASH (the canonical nociceptor) is the strongest responder when the
  head meets the boundary, followed by AWC. Two random halves of the worms agree on the
  pooled encounter response at r = 0.62.
- Baselines on the frozen test pool (behaviour levels not scored for systems without
  behaviour):

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
- **But a classifier still tells it apart (Level 8 AUC 0.94; other real worms 0.68).**
  (Update, Oct 31, measured with the fair design below: the frozen split overstates the
  gap. Its test worms are atypically unsmooth (median window lag-1 autocorrelation 0.64
  vs 0.72 for the training worms), which raises the control to 0.68. Over the three
  rotating pools the real control is at chance (0.46) and the model scores 0.82 against
  held-out worms and 0.77 against the very training worms it imitates. So the model does
  have a genuine, consistent giveaway, about 0.8 rather than 0.94.) The
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

**How Level 8 is reported from now on** (`scripts/run_l8_fair.py`,
`docs/figures/l8_fair.csv`; design written before the first run). For each of the three
rotating pools, the same classifier is run three ways: the model against held-out worms
(the usual test), the model against the very training worms it imitates (model error
alone), and real training worms against the held-out worms (individuality alone).

| | rotation 1 | rotation 2 | rotation 3 | mean |
|---|---|---|---|---|
| real control | 0.500 | 0.442 | 0.434 | 0.459 |
| calcium model, held-out | 0.904 | 0.793 | 0.758 | 0.818 |
| calcium model, in-sample | 0.712 | 0.796 | 0.800 | 0.769 |
| with heavy-tailed noise, held-out | 0.904 | 0.797 | 0.727 | 0.809 |
| with heavy-tailed noise, in-sample | 0.749 | 0.753 | 0.808 | 0.770 |

Real drive increments are heavy-tailed (excess kurtosis 1.8 in drive space); Student-t
innovations with per-worm degrees of freedom fitted to each training worm's residuals
(median 8.5; `IndividualVAR(innovations="student")`) bring the calcium-trace increment
kurtosis close to real (2.37 vs 2.73) but do not change the classifier result. The
remaining giveaway is second-order: model windows are about 0.03 smoother than their own
source worms, with too much power at 10 to 60 s periods and too little at 1 to 5 s.

**More memory closes most of the gap.** In-sample on one rotation's training worms (no
reference pools involved), VAR(3) windows are smoother than the worms they imitate
(lag-1 autocorrelation 0.747 vs 0.707; power share at 1 to 5 s periods 0.137 vs 0.162,
at 10 to 60 s 0.459 vs 0.413). Giving the drive model 6 frames of memory matches those
statistics (0.709; 0.161; 0.432) and 10 frames slightly overshoots (0.694; 0.169; 0.409).
On the rotating pools all three stay inside on all 10 pairwise levels (VAR(6) improves
the timescale ratio from 1.14 to 1.02; dimensionality ratio rises to 1.25 and 1.34, still
inside; `scripts/run_lags.py`, `docs/figures/lags_combined.csv`). The fair Level 8
(`docs/figures/l8_fair_lags.csv`):

| | in-sample | held-out (rotations 1, 2, 3) | held-out mean |
|---|---|---|---|
| real control | | 0.500, 0.442, 0.434 | 0.459 |
| VAR(3) | 0.769 | 0.904, 0.793, 0.758 (all p 0.02) | 0.818 |
| VAR(6) | 0.563 | 0.783 (p 0.02), 0.650 (p 0.02), 0.579 (p 0.23) | 0.671 |
| VAR(10) | 0.499 | 0.735 (p 0.02), 0.611 (p 0.08), 0.514 (p 0.44) | 0.620 |

**With 10 frames (6 s) of memory, a classifier can no longer tell the model from the worms
it imitates, and cannot tell it from held-out real worms in two of the three rotations**:
the first model to pass Level 8 anywhere. Honest bookkeeping: the in-sample criterion
pointed to 6 lags; 10 is ahead only on the Level 8 result, which uses the reference pools,
so "10 beats 6" is a post-hoc observation, while "longer memory than 3 frames" was chosen
without them. Rotation 1 still separates every model; its worms are not atypical (against
all other real worms AUC 0.50), and the features that give the model away there are AVA's
within-window smoothness (the model's AVA is rougher) and CEP's correlations with AIB and
AVA, which real worm groups do not differ on.

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
- **Stimulated-worm atlas** (Randi et al. 2023, OSF project e2syt): download
  `exported_data.tar.gz` from https://osf.io/e2syt/, unpack it, then
  `python scripts/convert_pumpprobe.py --src path/to/exported_data --out data/raw/randi2023_wt_npz`
  (113 wild-type worms; the script reports any file that does not read cleanly)

## Score your own brain copy

A copy is any program that, given a worm's neurons and a schedule of single-neuron pokes,
produces their activity. Subclass `nematica.score.BrainCopy` and implement `run(worm, rng)`
(and optionally `fit(worms)`); the docstring in `nematica/score.py` gives the contract. Then

```powershell
python -m nematica score examples/copies/linear_rest.py:LinearRest --quick   # one pool, about 4 minutes
python -m nematica score path/to/my_copy.py:MyCopy                           # all six held-out pools
```

It prints the verdict on every level and writes a JSON report to `results/scores/`. The
copy is fitted on the training worms and run on each held-out worm with that worm's own
pokes; the poked neuron's measured response is given to the copy as `drive`. Two examples:
`examples/copies/silent.py` (independent noise, the floor) and
`examples/copies/linear_rest.py` (a linear model learned only from activity with no pulse
nearby). The tool runs exactly the procedure of `scripts/run_same_worms.py`: on one pool,
all eleven verdicts and values match when both use the same
response units (`score` uses `fluct`; pass `--norm fluct` to the runner).

**Inside is not agreement.** A verdict of inside means no difference was detected. For the
poke levels the report also gives an equivalence verdict, with a rule fixed on 1 Nov 2026
before any copy was checked against it: a copy *agrees* when the whole 90% bootstrap
interval of its shift lies within plus or minus half the shift of a known-wrong control
built from the same held-out worms (targets permuted for the pattern, responses tripled for
the magnitude, time reversed for the kinetics). `scripts/annotate_equivalence.py` applies it
to cached results. On the repaired data, over six pools:

| Copy | Pattern agrees | Kinetics agrees | Magnitude agrees (x3 rule) | Magnitude agrees (x1.5 rule) |
|---|---|---|---|---|
| hybrid that learned from pokes (`hybrid_kernels_regimes_obsfit`) | 6 of 6 | 6 of 6 | 6 of 6 | 2 of 6 |
| plain hybrid (`hybrid_kernels`) | 4 of 6 | 6 of 6 | 6 of 6 | 0 of 6 |
| linear model fitted to ongoing activity (`var3_spontaneous`) | 0 of 6 | 6 of 6 | 6 of 6 | 0 of 6 |

The magnitude column shows a flaw in the rule as fixed: the tripled-response control is so
far off (a shift of about 0.9 in distance) that half of it, a tolerance of about 0.45,
admits copies whose magnitude is detectably wrong (outside in most pools). It is reported as fixed and will be replaced in the next pre-registration by a
control closer to the size of real differences between worms.

*Replacement written before the full gallery results (1 Nov 2026):* for magnitude, the
known-wrong control becomes every response scaled by 1.5 (a 50% error, clearly wrong but
near the size of real differences between worms), tolerance again half its shift. The
pattern and kinetics rules are unchanged. Both the old and the new magnitude verdicts will
be reported for every copy.
Under the x1.5 rule (tolerance 0.10 to 0.11 on the distance shift), magnitude separates the
copies: only the copy that learned from pokes is shown to agree, in 2 of 6 pools; the others
are further from real worms than real worms are from each other in every pool (the measure
is a distance, so it does not say whether their responses are too large or too small).

**The ruler's resolution (1 Nov 2026, `scripts/run_resolution.py`, `docs/figures/resolution.csv`).**
How large an error must a copy make before the ruler sees it? Known errors are put into real
held-out worms' own responses, and the damaged worms are scored against the rest of their pool
as a copy would be, in all six pools:

| Error put into real worms | Called outside | Shown to agree (equivalence) |
|---|---|---|
| none (the worms as recorded) | 0 of 6 | 6 of 6 |
| poked neuron misattributed in 25% of pulses | 2 of 6 | 4 of 6 |
| misattributed in 50%, 75%, 100% | 6 of 6 each | 0 of 6 each |
| every response x1.1 | 0 of 6 | 6 of 6 (x3 rule), 6 of 6 (x1.5 rule) |
| every response x1.25 | 3 of 6 | 6 of 6 (x3 rule), 0 of 6 (x1.5 rule) |
| every response x1.5 | 6 of 6 | 6 of 6 (x3 rule), 0 of 6 (x1.5 rule) |
| every response x2 | 6 of 6 | 0 of 6 (both rules) |

No false alarms on real worms. The ruler reliably catches a copy that gets half of who-drives-
whom wrong, or misjudges response size by half; errors of about a quarter often pass. So a
pass means "within about 25% of a real worm on these levels", not "faithful". The table also
confirms the x3 magnitude rule is too lenient (a 50% error passes) and that the x1.5 rule
draws the line at about 25%. Any claim made with this ruler should carry these numbers.

**The reverse test, written before running (1 Nov 2026).** unc-31 worms cannot release
neuropeptides from dense-core vesicles: real brains with one biological ingredient removed.
Scored as a "copy" against each wild-type pool on all levels, with the equivalence check
(`scripts/run_reverse_unc31.py`, 15 unc-31 worms with neuron identities, both splits).
Expectations: echo pattern and kinetics agree within tolerance in most pools (they are real
worms, and the mutation changes a minority of pairs; arc 4 found them inside on pattern);
activity levels mostly inside. If instead unc-31 worms fail to agree on the pattern, losing
neuropeptides moves a real brain toward the artificial fingerprint, and peptide signalling
is a candidate for what the artificial networks lack.

Result (`results/reverse_unc31`, six pools, repaired data): as expected. unc-31 worms are
inside on 35 of 36 activity verdicts and on all 12 complexity verdicts; their echo pattern
agrees within tolerance in 4 of 6 pools and kinetics and magnitude in 6 of 6. In the two
pools where the pattern does not, it fails on the other side: unc-31 worms agree with the
wild-type pool more closely than wild-type worms agree with each other (0.116 against
0.087, and 0.112 against 0.093), so the interval runs below the tolerance. Across pools
they agree with wild-type worms at 0.097 to 0.122, against 0.087 to 0.121 among wild-type
worms. So removing neuropeptide release does not move a real brain toward the artificial
fingerprint on these levels: on this evidence peptides are not what the artificial networks
lack here, or the ruler cannot see their effect one worm at a time (arc 4 found the same).
That unc-31 worms come out, if anything, slightly more alike than wild type is a lead for
the individuality question, not a finding: 15 worms, and two of six pools.

**Are real worms individuals? (1 Nov 2026, exploratory, `scripts/analyse_individuality.py`).**
Each worm's stimulations are split in two, and the echo pattern from one half is compared
with the other half of the same worm and with halves of other worms (98 wild-type worms with
at least 20 pulses, repaired data):

| Split | Same worm, two halves | Different worms | Per-worm excess (95% interval) | Worms with excess > 0 |
|---|---|---|---|---|
| alternate pulses | 0.146 | 0.083 | 0.100 (0.069 to 0.132) | 75% |
| first half against second half | 0.170 | 0.088 | 0.099 (0.064 to 0.134) | 76% |

A worm's echo agrees with itself almost twice as well as with other worms, and this holds
across the length of a recording. So worm-to-worm differences in the echo are not only
noise: each worm has a stable echo of its own. Two explanations remain open and this test
cannot separate them: genuine individuality (wiring, state, history), or worm-specific
measurement (neuron identities assigned once per worm, imaging conditions). If the first,
it is a property that every copy scored so far lacks: they reproduce one average echo, and a
single average cannot agree with a worm the way the worm agrees with itself. That makes
individuality a measurable ingredient for move 3, and a copy built from one worm's own
recordings is the next test.

**Can one worm be copied from its own recording? (same script, first half against second
half.)** Each worm's second-half echoes are predicted from a blend of its own first half and
the average of all other worms, and scored by correlation with the worm's second half
(median over 96 worms):

| Weight on the worm's own first half | 0 (average worm) | 0.25 | 0.5 | 0.75 | 1 (own half only) |
|---|---|---|---|---|---|
| Agreement with its second half | 0.225 | 0.232 | 0.217 | 0.203 | 0.187 |

The average of 95 other worms predicts a worm better than the worm's own first half does,
and the best blend adds only 0.007 over the average. Individual echoes exist (the table
above), but about 45 pulses per worm are too few to pin one down: with this much data, a
copy of the average worm is nearly as good as a copy of the individual. More pulses of the
same kind would not simply fix this. In this atlas a pulse mostly hits a new neuron (1.8
pulses per stimulated neuron class per worm; 42% of stimulated classes hit more than once),
so more pulses add breadth, not repeats, and an attempt to extrapolate the data needed with
a reliability curve failed for that reason (agreement did not rise with the number of
pulses used). Copying one particular animal needs repeated pokes of the same neurons in the
same worm: a concrete design request for a lab, not something this atlas can settle.

**Artificial networks against real worms: the fingerprint (1 Nov 2026; all six held-out pools,
repaired data; `scripts/run_gallery.py`, `scripts/summarize_gallery.py`,
`docs/figures/gallery_fingerprint.csv`).** Each family is scored as a copy
(`nematica/gallery.py`, `nematica/taskworm.py`). Echo agreement is the median over pools;
real worms agree with each other at 0.097. Counts are pools out of 6.

| Network | Learned from | Watching tests inside (of 6) | Echo agreement [range] | Pattern agrees | Kinetics agrees | Magnitude agrees (x1.5 rule) |
|---|---|---|---|---|---|---|
| hybrid (`hybrid_kernels_regimes_obsfit`) | watching and pokes | 1 to 3 | 0.097 [0.088, 0.113] | 6 | 6 | 2 |
| plain hybrid (`hybrid_kernels`) | watching and pokes | 4 | 0.084 [0.076, 0.096] | 4 | 6 | 0 |
| Kunert 2014 wiring model (`kunert2014`) | nothing: wiring diagram and textbook physiology | 2 | 0.022 [0.015, 0.026] | 0 | 0 | 6* |
| linear, fitted to recordings (`linear-rest`) | watching | 3 to 5 | 0.013 [0.008, 0.018] | 0 | 6 | 0 |
| linear VAR, fitted to recordings (`var3_spontaneous`) | watching | 3 to 5 | 0.011 [0.004, 0.014] | 0 | 6 | 0 |
| Creamer et al., own stimulation (`creamer-native`) | watching and pokes (published fit) | 2 to 4 | 0.008 [0.003, 0.009] | 0 | 6 | 6** |
| task-trained, wiring-shaped (`task-wired`) | a worm task, no neural data | 1 to 3 | 0.004 [0.003, 0.007] | 0 | 0 | 2 |
| task-trained, dense (`task-dense`) | a worm task, no neural data | 0 to 3 | 0.004 [0.002, 0.008] | 0 | 0 | 0 |
| linear with who-drives-whom randomised (`random-wiring`) | watching | 2 to 4 | 0.001 [-0.003, 0.004] | 0 | 6 | 0 |

\* The Kunert model's poke strength is an assumption (current = 1 x the measured drive), so
its magnitude verdict reflects that choice, not the model. \*\* Creamer et al.'s models take
a unit input at every stimulation, while the other copies are given the poked neuron's
measured response (which also tells them which stimulations took); the comparison is not
like for like on magnitude.

What the fingerprint says, within the ruler's resolution (about 25%, above):

- **Only networks that learned from pokes answer a poke like a worm.** Everything else falls
  four to a hundred times short on the echo pattern, in every pool, whatever its origin:
  fitted to recordings, randomly wired, built from the wiring diagram, trained on a task
  with or without the real wiring, or published and fitted to this atlas.
- **The watching tests do not order the networks.** No family passes all six in any pool,
  and the randomly wired network passes as many as the one fitted to real worms.
- **Among networks that never saw a poke, structure helps a little.** The wiring-diagram
  model, fitted to nothing, gets the most (0.022); a network fitted by watching gets 0.013,
  and the same network with its couplings dealt out at random gets 0.001. Watching recovers
  a little cause and effect, and the wiring diagram a little more, but both are far from a
  real worm.
- **Networks with their own dynamics get the time course wrong.** The wiring-diagram model
  and the task-trained networks fail kinetics in every pool; the linear networks pass it.
- **Training on a task does not produce a worm-like brain**, with or without the real wiring
  as a constraint: the two task-trained networks are indistinguishable from each other here.

**Why does watching fail? A synthetic worm with known cause and effect (1 Nov 2026,
`scripts/run_synthetic_watch.py`, `docs/figures/synthetic_watch_*.csv`).** Real worms cannot
tell us their true cause and effect, so a model brain stands in: one of Creamer et al.'s
published linear dynamical systems (154 neurons, ongoing activity and poke responses from
the same dynamics), with their densely connected model as a second ground truth. It is
recorded like the atlas (37-minute recordings at 2 Hz) and its cause and effect (each
neuron's summed 30 s response to a kick of each other neuron) is learned two ways: by
watching (a linear model fitted to ongoing activity, as NEMATICA's watching copies are) or by
poking (a kick to an observed neuron every 30 s, responses averaged; no model). Score:
correlation of the learned with the true cause and effect.

| How the synthetic worm is recorded | Watching, 2.5 h | Watching, 70 h | Poking, 2.5 h | Poking, 70 h |
|---|---|---|---|---|
| every neuron, measurement noise | 0.81 / 0.90 | 0.92 / 0.97 | 0.10 / 0.12 | 0.43 / 0.60 |
| half the neurons per recording, 30% never seen | 0.47 / 0.42 | 0.56 / 0.66 | 0.10 / 0.15 | 0.34 / 0.51 |
| the same, plus slow shared unrecorded drives (5% of input) | 0.20 / 0.28 | 0.20 / 0.27 | 0.05 / 0.06 | 0.24 / 0.37 |
| the same, shared drives at 10% of input | 0.13 / 0.21 | 0.11 / 0.18 | 0.04 / 0.05 | 0.19 / 0.29 |

(First number: connectome-constrained ground truth; second: densely connected. 70 hours is
about the size of the atlas, which has about 8,000 pulses.)

- **Watching can learn cause and effect in principle.** When each neuron's fluctuations
  are its own, watching recovers it well even when much of the brain is never recorded,
  and better than poking at the atlas's size.
- **Shared, unrecorded drives break it, and more data does not help.** A few slow
  brain-wide signals that no recording captures put a ceiling on watching that is reached
  within a few hours and never lifted (0.20 at 2.5 h and at 70 h). Poking is not fooled:
  it keeps improving and passes watching between 40 and 70 hours of recording. (True of
  the zero-filling linear watcher used here. In the artificial lab's nonlinear brains, with
  drives at 25% of input, a stitched watcher with slow drift removed gets much closer to
  poking; see part D of the artificial lab below. This synthetic worm was not re-tested.)
- **Real worms look like the drive-dominated case.** In the two unstimulated immobilised
  worms of the atlas archive, the top three principal components carry 40% of the
  variance; in the synthetic worm that level is reached with drives of about 5% of the input
  (none: 21%; 5%: 42%; 10%: 55%). This would explain why every copy that learned only by
  watching fails on real worms.
- **Removing the strongest shared patterns before fitting does not reliably fix it**
  (`scripts/diag_synthetic_deconfound.py`): it helps one ground truth (0.21 to 0.29 at a 5%
  drive) and hurts the other (0.31 to 0.22).

The implication for copying brains: if real brains are driven by strong shared signals that
recordings miss, a brain cannot be copied by watching it, however long; interventions are
not a refinement but a necessity. Caveats: linear ground truths, themselves fitted to this
atlas; the drive level is matched to only two resting worms; the poking estimator is a plain
average (a model that uses pokes, like the hybrid, needs fewer).

**Which pokes should a lab run? (`scripts/run_synthetic_design.py`,
`docs/figures/synthetic_design_*.csv`.)** Same synthetic worm, shared drives at 5% of input,
10 hours of watching plus a fixed budget of pokes, spent three ways: at random (as in the
atlas), spread evenly (least-poked neuron first), or guided by watching (pokes go to the
neurons a watching model says drive others most). Each pair's estimate blends its poke
average with the watching model's value; the blend weight is tuned on the ground truth and
applied equally to all strategies, so these are upper bounds.

| Pokes | Watching alone | Random | Spread evenly | Guided by watching |
|---|---|---|---|---|
| 500 | 0.21 / 0.31 | 0.22 / 0.32 | 0.22 / 0.32 | 0.22 / 0.32 |
| 2,000 | 0.21 / 0.31 | 0.24 / 0.36 | 0.24 / 0.36 | 0.23 / 0.35 |
| 8,000 | 0.21 / 0.31 | 0.30 / 0.46 | 0.30 / 0.46 | 0.28 / 0.44 |

(connectome-constrained / densely connected ground truth.) Pokes added to watching lift the
ceiling that watching alone cannot pass; how they are chosen hardly matters, with spreading
them evenly marginally best and aiming them by a watching model slightly worse (the hidden
drives mislead it about which neurons matter). Single pokes are weak evidence: the best
blend weighs one poke at about 1/200 of the watching estimate for a pair. For a lab, the
request this supports is simple: spread pulses evenly over neurons, record ongoing activity
too, and above all, more pulses.

**The prediction checked on real worms (`scripts/run_data_scaling.py`,
`docs/figures/data_scaling.csv`).** If watching hits a ceiling early and poking does not, a
real copy that learns by watching should not improve with more training worms, and one that
learns from pokes should. Each was fitted on 10% to 100% of the training worms (split cv3,
pools 0 and 1) and its echo agreement with held-out real worms measured:

| Training worms | 6 | 14 | 29 | 58 |
|---|---|---|---|---|
| learns by watching (`var3_spontaneous`) | 0.004 / 0.009 | 0.011 / 0.008 | 0.005 / 0.010 | 0.010 / 0.014 |
| learns from pokes (`hybrid_kernels`) | 0.073 / 0.057 | 0.072 / 0.073 | 0.085 / 0.079 | 0.092 / 0.081 |
| real worms with each other | 0.095 / 0.107 | | | |

As predicted: watching stays near zero from 6 to 58 worms, while pokes from just 6 worms
already beat 58 worms of watching by a factor of four to seven, and keep improving with
more worms.

## Four tests on the data we have (2 Nov 2026)

The worm results above come from one experiment. These four use every dataset on disk
(113 wild-type and 15 identified unc-31 stimulated worms, 30 freely moving Atanas worms, 27
copper-arena worms) to test the explanation, not repeat the demonstration.

*Data note found along the way:* the atlas names a stimulated neuron it could not identify
"target", and NEMATICA's class mapping had treated that as a neuron class (1.2% of echo
pairs, in 19 worms). It barely touches scoring (real-to-real echo agreement over 60 worms is
0.1229 with and without it), so earlier results stand; tests 2 and 4 below exclude it.

**1. Are the hidden drives neuropeptides? (prediction stated in the project log before
running, though not in a dated block here: yes, so watching should do better in unc-31
worms.)** Neuropeptides spread through the body without the
wiring, which makes them a natural candidate for the shared drives that defeat watching
(see the synthetic worm). unc-31 worms release far fewer of them. Both strains get the same small
design: 15 worms, train on 10 (8 for fitting, 2 for choosing the ridge), test on 5, three folds, re-split 6 times (wild type re-drawn
from 113 each time), copies fitted and scored within the strain
(`scripts/run_unc31_watch.py`, `docs/figures/unc31_watch.csv`):

| Echo agreement (mean of 18 splits) | Watching copy | Poke-trained copy | Real worms with each other |
|---|---|---|---|
| wild type | 0.017 | 0.058 | 0.107 |
| unc-31 | 0.009 | 0.072 | 0.095 |

**The prediction failed.** Watching is no better without neuropeptides (unc-31 minus wild
type: -0.008, 90% interval -0.027 to +0.011, resampling the 6 re-splits), and the gap
between watching and poking is, if anything, wider (+0.022, 0.007 to 0.037). A model-free
look agrees (`scripts/diag_shared_drive.py`, `docs/figures/shared_drive.csv`): in the few
seconds before each poke, neurons' baseline levels rise and fall together from one poke to
the next just as much in unc-31 (median worm's mean |r| 0.162, 16 worms) as in wild type
(0.175, 99 worms; p = 0.2). In both strains about 7 shared components stand above a shuffle null, and the
main one is slow: its correlation between windows 31 s apart is 0.7 in both, a timescale of
about 90 s. Caveats: the 15 unc-31 worms are reused in every re-split, so the intervals
are too narrow if anything; unc-31 reduces rather than abolishes dense-core vesicle release;
and baseline co-fluctuation includes real coupled dynamics, not only hidden drives.

So the shared slow structure is present with neuropeptide release much reduced, and there
is no evidence that peptides are the main source of the drives. This is weaker than ruling
them out: watching sits near zero in both strains, so a floor effect could hide a real gain
(the interval allows unc-31 watching up to about 65% better than wild type), and release
is reduced, not abolished.

The synthetic worm was rerun with drives shaped like these measurements: 7 drives with a
90 s timescale instead of 3 at 10 s (`--drive-k 7 --drive-tau 90`,
`docs/figures/synthetic_watch_slowdrives.csv`, connectome-constrained ground truth). Seven
components above a shuffle null is not proof of seven drives; this is a shape check, not a
fit. Watching still peaks within hours and then falls with more data, but where poking
catches up depends on how much of the input the drives carry, which these measurements do
not pin down:

| Slow drives' share of input | Watching, 2.5 h | Watching, 70 h | Poking, 40 h | Poking, 70 h |
|---|---|---|---|---|
| 5% (the share that matched resting worms for the fast drives above) | 0.34 | 0.27 | 0.18 | 0.25 |
| 10% | 0.30 | 0.20 | 0.14 | 0.20 |
| 25% | 0.21 | 0.11 | 0.09 | 0.13 |

With slow drives at 5% of input, poking has not overtaken watching by 70 hours (0.25
against 0.27); at 10% they tie; at 25% poking passes between 40 and 70 hours. So the claim
"poking overtakes at about the atlas's size" holds for fast drives and for strong slow
ones, and needs more data than the atlas for weak slow ones. The ceiling itself holds in
every case.

**2. How many pokes, and of which neurons? (`scripts/run_poke_budget.py`,
`docs/figures/poke_budget*.csv`.)** For each neuron poked in at least 6 worms (74 targets),
the echo from one group of worms is correlated with the echo from another group. One
worm's echo agrees with another worm's at a median of 0.074. Averaging helps more slowly
than independent noise would (for the 33 neurons poked in at least 24 worms: 4 worms per
group, 0.14 measured against 0.24 expected; 12 worms, 0.23 against 0.49). Projecting from
one worm's agreement with the textbook formula would say about 50 worms per neuron for a
reliability of 0.8; projecting the same formula from the largest split actually measured
(column `k80_half`) says a median of about 160 (half of targets between 80 and 370; 4%
within 20). Because the measured curves keep flattening, even 160 is probably an
underestimate. The atlas, the largest such dataset, has a median of 22 or 23 worms per
target (of those poked in at least 6).

Which neurons pay off is not random (exploratory, found after looking): pharyngeal neurons
(the feeding organ's own small nervous system, joined to the rest by one pair of neurons)
give echoes three times as reproducible as the rest (4 worms per group: 0.39 against 0.13;
Mann-Whitney p = 0.0002). That fits the idea that echoes are cleaner where brain-wide state
reaches least, but it was not a test of where the drives act, and the pharynx has other
reasons to be reproducible (its neurons respond strongly and together). Beyond the pharynx
there is no clean rule: the five most reproducible non-pharyngeal targets by one-worm
agreement are sensory (ASH, ASG, ASK, ASI, ASE), but other sensory neurons (AWC-ON, FLP,
URB, ASJ) sit in the bottom fifth of 62, and sensory against other neurons is not
significant (p from 0.06 to 0.34, depending on the measure and which neurons count as
sensory). For a lab:
budget pokes per neuron by its measured reliability, which this file lists, rather than
evenly.

**3. Do copies learned from freely moving worms pass the poke test? (pre-registered in arc
4 as model 2, expected to do worse than atlas copies; `scripts/run_behaving_pokes.py`,
`docs/figures/behaving_pokes.csv`.)** VARs fitted by watching freely moving worms (Atanas,
copper, or both, resampled to the atlas's 0.5 s frames; next-frame prediction R^2 0.87 to
0.91) are poked on the held-out atlas worms of each fold:

| Copy | Echo agreement with held-out atlas worms (split cv3, pools 0 / 1 / 2) | Pattern verdicts |
|---|---|---|
| watching Atanas worms (30) | 0.001 / 0.006 / -0.004 | outside in 3 of 3 |
| watching copper worms (27) | 0.006 / 0.005 / -0.002 | outside in 3 of 3 |
| watching both (57) | 0.002 / 0.003 / -0.004 | outside in 3 of 3 |
| watching the atlas's own unpoked frames | 0.009 / 0.014 / 0.004 | outside in 3 of 3 |
| learned from pokes (`hybrid_kernels`) | 0.092 / 0.081 / 0.076 | inside in 2 of 3 |
| real worms with each other | 0.095 / 0.107 / 0.093 | |

Expectation (c) is met, but only nominally: copies of moving worms answer a poke at about
chance, below the watching copy fitted to the atlas itself by 0.005 to 0.01, with both at
the floor, and an order of magnitude below the poke-trained copy. Watching 57 moving worms
does no better than watching 27 or 30. That fits the ceiling, but at the floor it cannot be
told apart from a plain mismatch between datasets (moving against immobilised worms,
different labs' pipelines). Their response size passes more often (magnitude inside in 7
of 9 pools) but this is not a mark of quality: the poke-trained copy fails magnitude in all
3, and these VARs are slightly unstable before the simulator rescales them (spectral
radius 1.006 to 1.009).

**4. Is meeting copper like poking ASH? (`scripts/run_copper_vs_pokes.py`,
`docs/figures/copper_vs_pokes*.csv`; question set before running, no expectation
written.)** ASH is the worm's copper sensor. If pokes show how signals really flow, the
brain-wide response of freely moving worms meeting the copper boundary (Level 6 definition,
70 encounters in 27 worms) should resemble the echo of poking ASH in immobilised worms. Each
of 74 poked neurons' mean echo is correlated with the encounter response over the classes
seen in both (44 to 70). **It does not.** ASH ranks 36th of 74 (r = -0.01, 90% interval
-0.23 to +0.16, resampling worms on both sides). The best match is AIB, an interneuron
just downstream of ASH (r = 0.30), but the best of 74 is no better than chance: with the
encounter shuffled across classes, the best of 74 reaches 0.31 at the median (p = 0.53).
The two ends are reproducible on their own (encounter split-half 0.62; ASH echo split-half
0.40 at 21 worms). On full samples (Spearman-Brown: 0.77 and 0.57) a true resemblance of
0.3 would show as about 0.3 x sqrt(0.77 x 0.57) = 0.20, just above the interval's top
(0.16): a real resemblance of that size is unlikely but not excluded. Copies poked at ASH
match the encounter no better (VAR fitted by watching copper worms: 0.07; by watching the atlas's unpoked frames: -0.08).

**What the four say together.** On these data, nothing transfers across contexts. Copies
learned by watching moving worms reproduce those worms well (arcs 2 and 5) and know
nothing about pokes; the echo of poking the copper sensor in still worms does not resemble
how moving worms' brains answer copper. That is one stimulus, and copper reaches more
sensory neurons than ASH, and a moving worm's response includes activity from moving, so
it is a warning, not a law. Slow shared structure is present in both strains and is not
removed by reducing neuropeptide release. The working conclusion: a faithful copy needs
pokes, the brain state they were given in, and the context it will be used in. We know of
no public dataset with all three for the same worms.


## The artificial lab: brains whose cause and effect is known (2 Nov 2026)

Real worms cannot tell us their true cause and effect, so every worm result above is a
comparison between imperfect measurements. In artificial brains it can be known.
`nematica/annlab.py` builds nonlinear rate networks of 120 tanh units (sparse random
wiring, saturating, so responses depend on the state the network is in), optionally with
slow drives that no recording sees. True cause and effect K[i, j] is unit i's summed 15 s
response to a kick of unit j, estimated by twin runs (the same network run twice from the
same visited state with identical noise, once kicked), averaged over 40 visited states
(two independent estimates correlate at 0.96 to 0.99, lower with strong hidden drives). Kicks push the hidden state of the unit for
4 s, like an optogenetic pulse, and the networks are calibrated so that two individuals'
single-poke echoes agree about as well as two worms' do (0.09 to 0.12 in the base species
of lab B, against 0.09 to 0.12 in the atlas; 0.05 to 0.15 across all species tested).
Recordings copy the atlas: 37 minutes at 2 Hz, with measurement noise. These ground truths
differ from the synthetic worm above in more than nonlinearity (held kicks, a 15 s window,
a different network), so the two are not directly comparable.

**A. Can a nonlinear brain be copied by watching it, if the copy is a neural network too?
(`scripts/run_ann_watch.py`, `docs/figures/ann_watch.csv`, `ann_watch_fullobs.csv`; two
independently drawn brains, averaged; differences between the two of up to 0.04, so
differences that small mean nothing.)** Four ways to learn K: a linear model fitted by
watching (NEMATICA's watching copy), a neural network that predicts the next frame from the
current one, a recurrent neural network with memory (which could in principle infer slow
hidden drives from history; trained for a fixed 1,500 steps, not tuned), each fitted by
watching and then kicked in silico; and plain averaging of real kicks. In this table the
watchers' in-silico kick adds 3 to the kicked unit's recorded value on each of 8 frames,
which is not the same as the truth's kick to the hidden state; the follow-up below repeats
the key settings with the unit held near saturation instead. Score: correlation with K.

| Recording | Hidden drives | Hours | Linear watcher | Neural-network watcher | Recurrent watcher | Poking |
|---|---|---|---|---|---|---|
| every unit, every time | none | 2.5 | 0.68 | 0.82 | 0.42 | 0.42 |
| every unit, every time | none | 10 | 0.69 | 0.83 | 0.42 | 0.71 |
| every unit, every time | none | 40 | 0.69 | 0.83 | 0.41 | 0.91 |
| every unit, every time | 25%, 90 s | 2.5 | 0.57 | 0.61 | 0.36 | 0.33 |
| every unit, every time | 25%, 90 s | 10 | 0.57 | 0.61 | 0.31 | 0.57 |
| every unit, every time | 25%, 90 s | 40 | 0.58 | 0.61 | 0.29 | 0.81 |
| half the units, 30% never | none | 2.5 | 0.28 | 0.30 | 0.11 | 0.43 |
| half the units, 30% never | none | 10 | 0.31 | 0.50 | 0.31 | 0.61 |
| half the units, 30% never | none | 40 | 0.28 | 0.50 | 0.32 | 0.88 |
| half the units, 30% never | none | 70 | 0.25 | 0.52 | 0.36 | 0.93 |
| half the units, 30% never | 5%, 10 s | 2.5 | 0.29 | 0.28 | 0.06 | 0.39 |
| half the units, 30% never | 5%, 10 s | 10 | 0.33 | 0.43 | 0.29 | 0.53 |
| half the units, 30% never | 5%, 10 s | 40 | 0.31 | 0.42 | 0.32 | 0.82 |
| half the units, 30% never | 5%, 10 s | 70 | 0.30 | 0.42 | 0.35 | 0.89 |
| half the units, 30% never | 5%, 90 s | 2.5 | 0.29 | 0.27 | 0.08 | 0.42 |
| half the units, 30% never | 5%, 90 s | 10 | 0.33 | 0.41 | 0.32 | 0.57 |
| half the units, 30% never | 5%, 90 s | 40 | 0.30 | 0.38 | 0.38 | 0.85 |
| half the units, 30% never | 5%, 90 s | 70 | 0.31 | 0.39 | 0.42 | 0.90 |
| half the units, 30% never | 25%, 10 s | 2.5 | 0.28 | 0.24 | 0.10 | 0.23 |
| half the units, 30% never | 25%, 10 s | 10 | 0.32 | 0.30 | 0.20 | 0.35 |
| half the units, 30% never | 25%, 10 s | 40 | 0.30 | 0.29 | 0.20 | 0.65 |
| half the units, 30% never | 25%, 10 s | 70 | 0.30 | 0.26 | 0.19 | 0.75 |
| half the units, 30% never | 25%, 90 s | 2.5 | 0.29 | 0.25 | 0.10 | 0.31 |
| half the units, 30% never | 25%, 90 s | 10 | 0.32 | 0.34 | 0.31 | 0.48 |
| half the units, 30% never | 25%, 90 s | 40 | 0.29 | 0.28 | 0.34 | 0.77 |
| half the units, 30% never | 25%, 90 s | 70 | 0.30 | 0.24 | 0.36 | 0.84 |

- **Given enough pokes, poking beats every watcher in every setting.** By 40 hours poking
  reaches 0.65 to 0.91, above every watcher in the same setting (highest watcher: 0.83).
- **Watchers plateau early.** None improves much beyond 10 hours, with one exception: the
  recurrent watcher keeps climbing slowly under slow drives (0.08 to 0.42 from 2.5 to 70
  hours in the atlas-like recording with 5% drives at 90 s).
- **Even with everything recorded and no hidden drives, watching stops short.** The
  neural-network watcher reaches 0.82 at 2.5 hours and stays there; poking passes it by 40
  hours (0.91). The linear watcher stops at 0.69: in a nonlinear brain, a linear copy is
  wrong in shape.
- **Hidden drives lower the plateau.** With every unit recorded and slow drives at 25% of
  input, the linear and neural-network watchers stop near 0.6 (the recurrent one near 0.3);
  poking ties them at 10 hours and passes them by 40 (0.81).
- **Atlas-like recording lowers it further** (half the units each time, 30% never): 0.3
  (linear) to 0.5 (neural network) with no drives. This run changes two things at once
  (units never seen, and different units seen each time), and the watchers fill unseen
  units with zeros and then roll out on their own predictions, so how much of the drop is
  the brain's and how much the estimators' is not separated.

**Follow-up: is the plateau the watchers' fault? (`scripts/run_ann_memory.py`,
`docs/figures/ann_memory.csv`; one brain, 40 hours.)** Two objections, tested where they
matter most: the watchers' kick ("added": 3 added to the recorded value for 4 s, as in the
table above; "held": the unit's recorded value held at 0.95, near saturation, as a strongly
driven unit is and as NEMATICA clamps a stimulated neuron), and memory (a network given the
last 5 s of activity, and the recurrent watcher trained four times longer with twice the
memory). The plain network is also trained twice as long here (6,000 steps against
3,000), so its "added" scores are not the same estimator as in the table above.

| Recording (one brain, 40 h) | Linear, added / held | Network, added / held | Network with 5 s of history, held | Recurrent (4x training, larger), added / held | Poking, same brain |
|---|---|---|---|---|---|
| every unit, drives 25%, 90 s | 0.58 / 0.58 | 0.61 / 0.60 | 0.62 | 0.57 / 0.53 | 0.82 |
| atlas-like, no drives | 0.29 / 0.30 | 0.52 / 0.23 | 0.46 | 0.42 / 0.30 | 0.86 |
| atlas-like, drives 5%, 90 s | 0.34 / 0.37 | 0.42 / 0.41 | 0.48 | 0.47 / 0.37 | 0.84 |

With every unit recorded and slow drives at 25%, no watcher passes 0.62 however it is
kicked or however much memory it has, against 0.82 for poking: that plateau is robust. In
the atlas-like recordings the watchers' scores depend on how they are kicked (the plain
network falls from 0.52 to 0.23 when the unit is held rather than added to), so the exact
values there are fragile, but no version reaches 0.55 against 0.84 to 0.86 for poking.
Short memory helps a little (the network with 5 s of history is the best held-kick watcher
in every setting) and does not close the gap. That is all this shows: the drives last 90 s,
longer than either watcher's memory (5 s of history, 30 s of warm-up), and it is one brain
and one training run.

**B. Does the ruler's verdict match the truth? (`scripts/run_ann_ruler.py`,
`docs/figures/ann_ruler_*.csv`.)** A species of 60 individuals that differ (every
connection scaled by 1 + sigma x N(0, 1)), each recorded once like an atlas worm, split
3 ways as the atlas is, and scored with the unchanged NEMATICA ruler. Copies with known
truth: the species brain the individuals vary around, one more individual, and the species
brain with 10%, 25% or all of its connections moved; plus NEMATICA's watching copy
(`var3_spontaneous`) and poke-trained copy (`hybrid_kernels`), fitted to the training
individuals. Truth: correlation of each copy's true K with held-out individuals' true K
(defined for brain copies only), and, for every copy, a noise-averaged echo (16 simulated
full recordings) correlated with individuals' noise-averaged echoes.

| Species | Copy | True agreement with individuals (individuals with each other) | Noise-averaged echo agreement (individuals) | Ruler: pattern | Ruler: shown to agree |
|---|---|---|---|---|---|
| sigma 0.3, drives 5% | species_mean | 0.82 (0.68) | 0.46 (0.39) | inside 3 of 3 | 3 of 3 |
| sigma 0.3, drives 5% | another_individual | 0.70 (0.68) | 0.39 (0.39) | inside 3 of 3 | 3 of 3 |
| sigma 0.3, drives 5% | scrambled_0.1 | 0.56 (0.68) | 0.33 (0.39) | inside 2 of 3 | 3 of 3 |
| sigma 0.3, drives 5% | scrambled_0.25 | 0.30 (0.68) | 0.18 (0.39) | inside 0 of 3 | 0 of 3 |
| sigma 0.3, drives 5% | scrambled_1.0 | 0.00 (0.68) | 0.00 (0.39) | inside 0 of 3 | 0 of 3 |
| sigma 0.3, drives 5% | hybrid_kernels | not defined (0.68) | 0.35 (0.39) | inside 2 of 3 | 2 of 3 |
| sigma 0.3, drives 5% | var3_spontaneous | not defined (0.68) | 0.24 (0.39) | inside 0 of 3 | 0 of 3 |
| sigma 0.3, no drives | species_mean | 0.81 (0.66) | 0.48 (0.40) | inside 2 of 3 | 0 of 3 |
| sigma 0.3, no drives | another_individual | 0.69 (0.66) | 0.40 (0.40) | inside 3 of 3 | 3 of 3 |
| sigma 0.3, no drives | scrambled_0.1 | 0.55 (0.66) | 0.32 (0.40) | inside 3 of 3 | 2 of 3 |
| sigma 0.3, no drives | scrambled_0.25 | 0.29 (0.66) | 0.17 (0.40) | inside 0 of 3 | 0 of 3 |
| sigma 0.3, no drives | scrambled_1.0 | 0.00 (0.66) | 0.00 (0.40) | inside 0 of 3 | 0 of 3 |
| sigma 0.3, no drives | hybrid_kernels | not defined (0.66) | 0.32 (0.40) | inside 3 of 3 | 1 of 3 |
| sigma 0.3, no drives | var3_spontaneous | not defined (0.66) | 0.23 (0.40) | inside 0 of 3 | 0 of 3 |
| sigma 0.3, drives 25% | species_mean | 0.83 (0.71) | 0.36 (0.31) | inside 3 of 3 | 1 of 3 |
| sigma 0.3, drives 25% | another_individual | 0.73 (0.71) | 0.31 (0.31) | inside 3 of 3 | 0 of 3 |
| sigma 0.3, drives 25% | scrambled_0.1 | 0.60 (0.71) | 0.27 (0.31) | inside 3 of 3 | 1 of 3 |
| sigma 0.3, drives 25% | scrambled_0.25 | 0.36 (0.71) | 0.16 (0.31) | inside 0 of 3 | 0 of 3 |
| sigma 0.3, drives 25% | scrambled_1.0 | 0.00 (0.71) | 0.00 (0.31) | inside 0 of 3 | 0 of 3 |
| sigma 0.3, drives 25% | hybrid_kernels | not defined (0.71) | 0.27 (0.31) | inside 3 of 3 | 0 of 3 |
| sigma 0.3, drives 25% | var3_spontaneous | not defined (0.71) | 0.16 (0.31) | inside 2 of 3 | 0 of 3 |
| sigma 0.1, drives 5% | species_mean | 0.96 (0.94) | 0.54 (0.52) | inside 3 of 3 | 3 of 3 |
| sigma 0.1, drives 5% | another_individual | 0.95 (0.94) | 0.52 (0.52) | inside 3 of 3 | 3 of 3 |
| sigma 0.1, drives 5% | scrambled_0.1 | 0.65 (0.94) | 0.37 (0.52) | inside 0 of 3 | 1 of 3 |
| sigma 0.1, drives 5% | scrambled_0.25 | 0.34 (0.94) | 0.19 (0.52) | inside 0 of 3 | 0 of 3 |
| sigma 0.1, drives 5% | scrambled_1.0 | 0.00 (0.94) | 0.00 (0.52) | inside 0 of 3 | 0 of 3 |
| sigma 0.1, drives 5% | hybrid_kernels | not defined (0.94) | 0.44 (0.52) | inside 2 of 3 | 3 of 3 |
| sigma 0.1, drives 5% | var3_spontaneous | not defined (0.94) | 0.25 (0.52) | inside 0 of 3 | 0 of 3 |
| sigma 0.6, drives 5% | species_mean | 0.53 (0.32) | 0.31 (0.19) | inside 3 of 3 | 0 of 3 |
| sigma 0.6, drives 5% | another_individual | 0.31 (0.32) | 0.16 (0.19) | inside 3 of 3 | 0 of 3 |
| sigma 0.6, drives 5% | scrambled_0.1 | 0.40 (0.32) | 0.24 (0.19) | inside 3 of 3 | 1 of 3 |
| sigma 0.6, drives 5% | scrambled_0.25 | 0.23 (0.32) | 0.14 (0.19) | inside 2 of 3 | 0 of 3 |
| sigma 0.6, drives 5% | scrambled_1.0 | 0.00 (0.32) | 0.00 (0.19) | inside 0 of 3 | 0 of 3 |
| sigma 0.6, drives 5% | hybrid_kernels | not defined (0.32) | 0.16 (0.19) | inside 3 of 3 | 0 of 3 |
| sigma 0.6, drives 5% | var3_spontaneous | not defined (0.32) | 0.13 (0.19) | inside 2 of 3 | 0 of 3 |

Each species configuration uses one draw of the species brain, of the extra individual and
of each scrambled brain, so its three pools share those copies and are not independent
replicates. Model copies are simulated by replaying the kicked unit's own response recorded
from the species brain (NEMATICA's clamp), while brain copies and individuals are kicked
physically. The pattern verdict ("inside") and the equivalence check ("shown to agree") are
separate tests and disagree in a few pools; both are reported.

- **Where echoes are as reliable as worms', the ruler separates good from bad copies.** In
  the three species with worm-like echo reliability (sigma 0.3 with 5% or no drives, sigma
  0.1), brains with a quarter or all of their connections moved are outside in every pool,
  and so is NEMATICA's watching copy, whose noise-averaged echo reaches about half to two
  thirds of an individual's (48% to 70% across all species). The poke-trained copy
  reaches 80% to 90%; it is shown to agree in 2 of 3 pools (sigma 0.3, 5% drives), 3 of 3
  (sigma 0.1), 1 of 3 with no drives (inside in all 3, but its interval runs past the
  tolerance on the too-close side) and 0 of 3 in the two species where echoes are less
  reliable.
- **It does not rank close copies correctly.** With no drives, the ruler puts the
  poke-trained copy above a genuine individual in every pool (echo agreement 0.115 to 0.14
  against 0.097 to 0.115), while the truth puts it below (0.32 against 0.40). The ruler
  answers "close enough or not", not "which is closer".
- **"Shown to agree" means within about 20%, not "as good as an individual".** With sigma
  0.3 and 5% drives, the species brain with 10% of its connections moved has true agreement
  0.56 against individuals' 0.68 (17% short) and is shown to agree in all 3 pools, though
  the pattern verdict puts it outside in one. On worms the same ruler's resolution was
  measured as about 25% by planting errors; here the truth gives a similar answer.
- **Its resolution is set by how different individuals are**, as designed: when individuals
  are nearly identical (sigma 0.1, agreement 0.94), the same 10% scrambling (true 0.65) is
  outside in all 3 pools on the pattern verdict, though the equivalence check confirms it
  in 1.
- **Some species cannot be judged with atlas-sized data.** When hidden drives carry 25% of
  input, or individuals differ a lot (sigma 0.6, true agreement 0.32), single echoes agree
  at only 0.05 to 0.07. Then the ruler can neither reject the watching copy reliably
  (inside in 2 of 3 pools in both) nor confirm a genuine individual (0 of 3 in both), and
  with sigma 0.6 a brain with a quarter of its connections moved passes the pattern level in
  2 of 3 pools. Real worms sit at 0.09 to 0.12, near the edge of that regime: more worms per
  neuron would sharpen every verdict, which is test 2's conclusion reached from the other
  side.
- **With twice the individuals the two checks pull apart** (`docs/figures/ann_ruler_base_n120.csv`;
  120 individuals, sigma 0.3, 5% drives, so 40 per held-out pool). The pattern verdict gets
  stricter: the 10%-scrambled brain (17% short of an individual) is now outside in 2 of 3
  pools. The equivalence check gets more lenient, because its tolerance is fixed (half the
  shift of a known-wrong copy) while the intervals narrow: it now confirms the watching copy
  in 2 of 3 pools, although that copy's noise-averaged echo is 30% short of an
  individual's. So the tolerance chosen on 1 Nov is sized for atlas-sized data; with more
  data it must be tightened, or "shown to agree" will certify copies that watching made.
- **The average brain is flagged, as the project's motto predicts.** The species brain is
  closer to every individual than individuals are to each other (0.82 against 0.68), and the
  activity levels call it too typical in every pool of every species. With no hidden drives
  its echo is so much closer than individuals' that the two-sided equivalence check does not
  confirm it either.

**C. Can the hidden drives be taken out of a watching copy? (`scripts/run_ann_deconfound.py`,
`docs/figures/ann_deconfound.csv`; one brain, slow drives at 25% of input, 40 hours, kicks
held.)** A linear watcher is given extra inputs while it is fitted: the true drives (an
upper bound no experiment has), or the k strongest slow patterns of the recorded activity
itself (activity smoothed over 30 s; the truth has 3 drives).

| Linear watcher given | Every unit recorded | Atlas-like recording |
|---|---|---|
| nothing | 0.61 | 0.30 |
| the true drives | 0.86 | 0.48 |
| 3 slow patterns | 0.77 | 0.30 |
| 6 slow patterns | 0.73 | 0.30 |
| 12 slow patterns | 0.72 | not run |
| (poking, for comparison) | 0.81 | 0.76 |

With every unit recorded, taking out the slow patterns recovers most of what the drives cost
(0.61 to 0.77, near poking's 0.81), and knowing the drives would beat poking. With
atlas-like recording the estimated patterns do nothing (0.30 to 0.30), and even the true
drives lift the watcher only to 0.48, far below poking's 0.76: once much of the brain goes
unrecorded, knowing the drives is not enough. (Part D, below, shows this holds only for this zero-filling
watcher.)

**The same on real worms (`scripts/run_deconfound_atlas.py`,
`docs/figures/deconfound_atlas.csv`).** NEMATICA's watching copy was refitted with each
worm's own 3 or 6 strongest slow patterns as extra inputs (dropped again when the copy is
poked). Echo agreement, pools 0 / 1 / 2: 0.0095 / 0.0137 / 0.0040 without, 0.0092 / 0.0143
/ 0.0037 with 3 patterns, 0.0097 / 0.0145 / 0.0036 with 6; outside in every pool. Exactly
what the artificial lab predicts for recordings that miss much of the brain. (The atlas's
unpoked stretches are short, so a 30 s smoothing is a coarse estimate of the slow patterns;
that is a second reason this could fail.)

**D. Is the watching limit the data or the method? (3 Nov 2026, `scripts/run_ann_stitch.py`,
`docs/figures/ann_stitch.csv`; reviewed independently before release.)** Every watching copy
above, like NEMATICA's watching copy for worms, fills each recording's unrecorded units with
zeros, so its regressions silently drop the inputs it did not see. A watcher that STITCHES
recordings together avoids this: the lag-0 and lag-1 covariance of each pair of units is
pooled over the recordings where both were seen, and the dynamics are A = C1 C0^-1. A second
version first removes each unit's 30 s moving average (the smoothing used in part C, fixed
before any of these scores) to take out slow drives. The ridge is chosen on held-out
recordings (fit on half, predict the other half's lag-1 covariances; no poke data). This rule
was added after a fixed ridge collapsed in one setting; an automatic choice of the drift
window was tried and dropped, because held-out losses on differently filtered data are not
comparable. Poking is scored two ways: the plain average response (as in parts A to C) and
with a drift-corrected baseline (a line between the 10 frames before the kick and the 10
after the response window), so both sides get drift correction. Every estimate is scored on
the same pairs. Two brains (seeds 0, 1; worm-calibrated: rho 1.3, kicks of 6 held for 4 s);
mean (range) of the correlation with the true cause and effect:

| Recording, hidden drives, data | Old watcher | Stitched | Stitched, drift removed | Poking | Poking, drift-corrected |
|---|---|---|---|---|---|
| every unit, none, 40 h | 0.92 | 0.91 | 0.89 | 0.90 | 0.92 |
| half per recording, none, 40 h | 0.54 | 0.91 | 0.88 | 0.82 | 0.85 |
| atlas-like, none, 40 h | 0.46 | 0.81 | 0.77 | 0.88 | 0.90 |
| every unit, 25% slow, 40 h | 0.64 | 0.63 | 0.87 | 0.81 | 0.87 |
| half per recording, 25% slow, 40 h | 0.36 | 0.32 | 0.86 | 0.70 | 0.79 |
| atlas-like, 25% slow, 40 h | 0.34 | 0.30 | 0.79 (0.78 to 0.80) | 0.78 | 0.85 |
| the same, 2.5 h of each | 0.38 | 0.23 | 0.49 | 0.35 | 0.43 |
| the same, 10 h of each | 0.33 | 0.26 | 0.71 | 0.48 | 0.59 |
| the same, fast drives (10 s) | 0.32 | 0.39 | 0.59 | 0.67 | 0.76 |
| the same, a different individual per recording (sigma 0.3) | 0.38 | 0.32 | 0.80 (0.78 to 0.82) | 0.73 | 0.81 |
| the same, individuals, 5 h of each | 0.33 | 0.25 | 0.59 (0.53 to 0.64) | 0.33 | 0.41 |
| atlas-sized: 113 individuals, 2.5 min watched and 37 min poked each | 0.36 | 0.40 | 0.75 (0.72 to 0.77) | 0.81 | 0.87 |

"Stitched" columns use the held-out ridge. What this shows, in the artificial lab:
- **Most of the watching gap was the method.** Under atlas-like recording with slow drives
  the old watcher reaches 0.34; built to use only what each recording saw, with slow drift
  removed, the same data gives 0.79. Part C's sentence "once much of the brain goes
  unrecorded, knowing the drives is not enough" was true of the zero-filling watcher only.
- **Poking still leads when it has comparable data.** Against drift-corrected poking the
  fixed watcher is behind by 0.06 (atlas-like, 40 h), 0.13 without drives, 0.12 at atlas size
  (the atlas pokes far more than it records unpoked), and 0.17 with fast drives, which a 30 s
  filter cannot separate from responses. It is level only with a different individual per
  recording (0.80 against 0.81).
- **With equal, scarce data, watching leads** (2.5 h: 0.49 against 0.43; 10 h: 0.71 against
  0.59; individuals, 5 h: 0.59 against 0.41), because every frame of watching informs every
  pair while a poke informs one column.
- **Caveats.** Two brains per setting; differences of about 0.04 or less mean nothing. Scores
  depend on the drift window: in a check by the reviewer, windows of 10, 30, 60 and 120 s gave
  0.72, 0.80, 0.74 and 0.66 (40 h, slow drives, seed 0), and without drives longer windows do
  better. The kick is a clamp near saturation, which suits the lab's kick; the worm protocol
  clamps to the measured response. A latent state-space watcher (`fit_latent`) is written
  but not run.

**The same on real worms (`scripts/run_worm_stitch.py`, `docs/figures/worm_stitch.csv`).**
The stitched copy (VAR(3) on unpoked frames, covariances pooled per pair of classes over the
worms that recorded both, ridge chosen on the fold's validation worms by the same rule,
unrecorded classes left running when poked; for the drift-removed version the 30 s average
is taken over unpoked frames only) was scored on the poke test exactly like every copy.
Each atlas worm records a median of about two thirds of the fold's neuron classes, so the old
copy zero-fills about a third of its inputs. Echo agreement, pools 0 / 1 / 2 (real
worm-to-worm agreement 0.095 / 0.107 / 0.093):

| Copy | Pool 0 | Pool 1 | Pool 2 |
|---|---|---|---|
| existing watching copy (zero-filled) | 0.0095 | 0.0137 | 0.0040 |
| stitched | 0.0102 | 0.0241 | 0.0186 |
| stitched, slow drift removed | 0.0143 | 0.0117 | 0.0047 |
| the same, unrecorded classes held at zero | 0.0126 | 0.0137 | 0.0073 |
| (poke-trained copy, earlier runs) | 0.092 | 0.081 | 0.076 |

All watching copies are outside in every pool. Stitching helps somewhat in pools 1 and 2
(about 2 and 5 times the old copy's agreement) but reaches only 11% to 22% of the worm-to-worm
agreement; removing drift adds nothing. The poke-trained copy reaches 76% to 97%.

**The decisive check: lab brains through the worm pipeline (`scripts/run_ann_ruler_stitch.py`,
`docs/figures/ann_ruler_stitch_*.csv`).** The lab and worm numbers above are not comparable
(correlation with the true K against echo agreement with real worms; long continuous watching
against short fragments between pokes). So lab brains were recorded exactly like atlas worms
(113 individuals, sigma 0.3, 37 min each, half the units seen, 30% never, a poke every 30 s
after about 2 minutes of unpoked activity, matching the atlas median of 232 usable unpoked
frames), and every copy was fitted and scored by the unchanged pipeline. (A first attempt
with the earlier lab recording design, pokes from the first 30 s, left only 57 usable
unpoked frames per individual and was stopped; in its first pool every watching copy failed.)
Echo agreement as a share of the individuals' agreement with each other:

| Copy | Lab brains, drives 5% | Lab brains, drives 25% | Real worms |
|---|---|---|---|
| existing watching copy | 63 / 64 / 72% | 68 / 64 / 68% | 10 / 13 / 4% |
| stitched | 52 / 51 / 53% | 60 / 51 / 57% | 11 / 22 / 20% |
| stitched, slow drift removed | 62 / 66 / 71% | 78 / 82 / 79% (inside in 2 of 3) | 15 / 11 / 5% |
| poke-trained copy | 75 / 85 / 89% (inside in 2 of 3) | 76 / 82 / 84% (inside in 2 of 3) | 97 / 76 / 82% |
| another individual (lab only) | 91 / 93 / 97% | 90 / 108 / 95% | |

Pools 0 / 1 / 2. In lab brains scored exactly as worms are, every watching copy reaches
about half to four fifths of the individuals' agreement, and with strong drives the
drift-removed stitched copy is level with the poke-trained copy (78 to 82% against 76 to 84%,
both inside in 2 of 3 pools). On real worms the same copies reach 4% to 22% while the
poke-trained copy reaches 76% to 97%. The gap between the poke-trained copy and the best watching
copy is about 0 to 20 points of the individuals' agreement in lab brains and 54 to 82 points in worms, with the same data design, copies
and test. **So real worms are much harder to copy by watching than these artificial brains,
and the reason is not the recording design, the amount of unpoked data or the scoring.**
Even the old watching copy reaches about two thirds in lab brains, so this was already true
before stitching; part D makes it the clearest open question. Untested candidates: optogenetic
pokes drive neurons far beyond the range they visit at rest, waking links that are silent in
ongoing activity; worm activity is dominated by a few global behavioural states rather than
many weak couplings; worm neurons respond to inputs nonlinearly in ways tanh units do not.

**E to G. Why do worms resist watching? (3 Nov 2026, exploratory, not pre-registered;
`scripts/run_ann_calcium.py`, settings for every output in `docs/figures/ann_EFG_settings.md`;
reviewed independently.)** Candidate explanations were built into the lab brains one at a time,
each scored through the unchanged worm pipeline (as in part D's decisive check, 113
individuals, atlas-format recordings). Shares are a copy's echo agreement divided by the
individuals' agreement with each other; worms: watching copies 4% to 22%, poke-trained 76% to
97%, individuals agree at 0.09 to 0.11.

- **E. A slow calcium indicator** (dynamics integrated in 5 substeps per frame, seen through a
  1.5 s indicator; pool 0 only): watching copies 60% to 75%, poke-trained 93%, the same as with
  direct readout (old watching copy 0.60 both ways). A 1.5 s indicator does not explain the
  gap here. Narrow: one indicator speed, one pool, individual agreement not recalibrated (0.15),
  and the model neurons were not made faster than the frame, which is where an indicator
  should matter most.
- **F. Worm-like resting activity.** In the atlas's longest unpoked stretches, resting
  activity is smoother and lower-dimensional than in the lab brains (lag-1 autocorrelation
  0.90 against 0.64; participation ratio 0.11 of recorded units against 0.43). Two lab brains
  were tuned toward the worm values, one with unrecorded slow drives at 75% of input and one
  with the network's own rank-3 global modes, with 15 s pokes so that individuals agree at
  0.07 to 0.10. Watching still works: the drift-removed stitched copy reaches 90% to 94%
  (drives) and 84% to 107% (internal modes), all inside, beside poke-trained 90% to 121%; the old
  watching copy falls to 49% to 64% with strong drives. Caveats from review: the comparison of
  resting statistics was not like-for-like (worm segments have about 115 units and 121 frames,
  lab segments about 45 units and 400 frames; at matched sizes the drives brain matches worm
  dimensionality but not smoothness, the internal brain the reverse), and these brains used
  longer pokes than the others.
- **G. Links that are silent at rest.** A second, sparse set of connections that carries a
  unit's signal only above 0.98 (resting activity crosses it in 0.3% to 1.4% of frames; a held
  poke drives the unit to 0.99999), on the baseline brain, with 2 s pokes so that individuals
  agree at 0.10 to 0.12. Watching copies fall to 19% to 28%; the poke-trained copy reaches 82%
  to 86% (all 3 pools). With weaker silent links, watching is 48% to 52%. A control on the
  baseline brain with the same 2 s pokes keeps watching at 59% to 63%, so the poke length is
  not the cause.

**What this does and does not show.** Among the mechanisms tested, only one brought watching
copies near the worms' level: links that are silent at rest yet carry most of the response to a
poke (in the strong setting, about 70% of the evoked pattern travels through them). This is a
constructed demonstration of sufficiency in one species brain with fixed random seeds, not
evidence that worms have threshold-gated links. Anything that a poke evokes but ongoing activity
does not express would do the same: other silent pathways, outputs that a neuron's calcium
signal does not reflect, state changes caused by the poke, or side effects of the stimulation
itself (off-target activation, light artefacts). The lab brains also differ from the atlas in
ways not tested here (perfect neuron identities, no naming errors or class pooling). An attempt
to see a threshold fingerprint directly in worm data (`scripts/diag_gating_fingerprint.py`) was
uninformative: it did not detect the gating in a lab brain known to have it. Control (pool 0):
the same silent links added to the two worm-like brains of F (8 s pokes) give watching copies
19% to 28% and the poke-trained copy 93% (drives brain) and 96% (internal modes), both inside,
with individuals agreeing at 0.14 and 0.16 (somewhat more reliable than worms). So the effect
does not depend on the baseline brain's resting activity. Telling these explanations apart needs
new data, above all the same neuron stimulated at several strengths in the same worms.

**Robustness checks, run unattended on 5 Nov 2026 (`scripts/lab_queue.py`, settings in
`docs/figures/ann_queue_settings.md`, outputs `docs/figures/ann_queue_*.csv`; pool 0 unless
stated; shares of the individuals' agreement).**

- *Silent links in two new species brains* (brain seeds 1 and 2, GATED 1.5, 2 s pokes): best
  watching copy 18% and 34%, poke-trained 81% and 87% (individuals agree 0.127 and 0.094). The
  effect replicates, weaker in seed 2 (34% is above the 30% line used later in labs H and I).
- *Their baselines without silent links* (same seeds and pokes): individuals agree only 0.041 and
  0.042, below the 0.05 at which the test can tell copies apart (labs H and I), so these controls
  are uninformative; every copy is inside.
- *Slow calcium indicator, more pools and a slower indicator*: 1.5 s in pools 1 and 2, best
  watching 72% and 80%, poke-trained 85% and 98%; 3.0 s in pool 0, best watching 70%,
  poke-trained 101%. Calcium smearing still does not make the lab brains resist watching.


**Per-worm test of "record everything", written before running (2 Nov 2026,
`scripts/run_own_worm_watch.py`).** The atlas names a median of 72 neurons per worm but
tracks 123; the unnamed ones are recorded, only not identifiable across worms. So within one
worm, a watching copy can include every tracked neuron. For each wild-type worm, a linear
model (one-frame lag, ridge chosen on held-out stretches of the same worm) is fitted to that
worm's unpoked frames only, in three versions: (A) named neurons only; (B) every tracked
neuron; (C) every tracked neuron plus the worm's 3 strongest slow patterns as extra inputs
while fitting. Each is then poked like the worm was (the target held to its own measured
response) and its echo compared with the worm's own measured echo, over pairs where both
neurons are named, so all three are scored on the same pairs. Reference: the average echo of
the other worms for the same pairs.

Expectations: if what is unrecorded is what defeats watching, C beats B beats A. What we
expect to actually see: all three near zero and no reliable difference, because a worm has
only about 7 minutes of unpoked activity, far less than the hours watching needed in the
artificial lab. A positive result would be a reason to ask for long unpoked recordings; a
null result says only that this data cannot answer the question.

**Result (`docs/figures/own_worm_watch.csv`).** 44 of 113 worms had enough unpoked
activity to fit (at least 200 frames in at least 5 stretches, and 10 stimulations of named
neurons); in those, a median of 124.5 neurons tracked and 91.5 named, and only 354 unpoked
frames (about 3 minutes), less than the 7 minutes estimated above. As expected, all three
watching copies are near zero: median echo agreement with the worm's own echo 0.044 (named
only), 0.050 (all tracked), 0.052 (all tracked plus slow patterns). Adding the unnamed
neurons helps a little and fairly consistently (median +0.003, mean +0.012, better in 26 of
44 worms, Wilcoxon p = 0.024); the slow patterns add nothing on top (better in 16 of 44,
p = 0.14). The average echo of other worms predicts each worm's own echo at 0.22, better
than all three watching copies in 43 of 44 worms. So a worm's own 3 minutes of watching,
even with every tracked neuron, tells you less about its echoes than other worms' pokes
do. The small gain from recording more of the worm is in the direction the theory
predicts, but far too small, on far too little data, to carry weight. This is the limit of
what existing data can say.

## Checks on the worm headline (3 Nov 2026)

**Is the poke test measuring specific cause and effect, or a stereotyped response to any poke?
(`scripts/run_generic_poke.py`, `docs/figures/generic_poke.csv`.)** If most of what follows a
poke were the same whichever neuron was poked (a state change, a startle, a side effect of the
light), copies trained on pokes could pass by learning that one response, and the gap between
watching and poking would say little about causal structure. A "generic" copy, identical to the
poke-trained copy except that every class answers every poke with its average response to pokes
of all classes, was scored with the unchanged test. Echo agreement, pools 0 / 1 / 2:

| Copy | Pool 0 | Pool 1 | Pool 2 |
|---|---|---|---|
| poke-trained (knows which class was poked) | 0.092 | 0.081 | 0.076 |
| generic (knows only that something was poked) | 0.007 | 0.012 | 0.001 |
| real worms with each other | 0.095 | 0.107 | 0.093 |

The generic copy fails as badly as the watching copies. So the test measures which neuron causes
what, and a stereotyped response to stimulation is not what the poke-trained copy learns. This
also makes a generic side effect of stimulation an unlikely explanation of why worms resist
watching (it remains possible for effects specific to each stimulated neuron).

**Independent recomputation (`scripts/check_headline_independent.py`,
`docs/figures/headline_independent.txt`).** A standalone script using only numpy and the raw
atlas files, with its own simple definitions (classes by stripping L/R, responses over 0 to
15 s in units of each neuron's unpoked SD, Pearson agreement over shared pairs, every third
worm held out, a zero-filled ridge VAR(1) as the watching copy) gives, pools 0 / 1 / 2:
worm-to-worm 0.115 / 0.120 / 0.132; the poke average of training worms 0.231 / 0.235 / 0.227;
watching 0.051 / 0.043 / 0.068. The order holds: watching does a fifth to a quarter as well as
the poke average. How far watching falls short of a real worm depends on how noise is handled:
here noise-free predictions are compared (watching 36% to 52% of worm-to-worm, the poke average
above it), while the ruler simulates single, noisy pokes (4% to 22%). "Watching is several
times worse than poking" is robust to this; the exact share of a real worm is not.

**Design for the experiment that could test the silent-pathway lead
(`scripts/design_graded_stim.py`, `docs/figures/design_graded_stim.txt`).** Stimulating the same
neuron at five strengths in lab brains: with silent links, downstream responses rise more
steeply at the top strengths in 6 of 6 stimulated units; with ordinary links, in 3 of 6, because
ordinary responses also saturate. Per neuron, 20 trials per strength detect it 5% to 80% of the
time, with false alarms up to 31% in the ordinary brain. So a decisive experiment needs many
stimulated neurons, 4 or 5 strengths and 20 or more trials each, judged on the pattern across
neurons, not on single neurons.

## Do worms have links that are silent at rest? (pre-registered 5 Nov 2026)

The artificial lab found one mechanism, among those tried, that makes lab brains resist
watching the way worms do: links that carry a neuron's signal only when it is driven beyond the
range it visits at rest (part G). That shows such links are sufficient, not that worms have
them. An earlier attempt to see them in worm data (`scripts/diag_gating_fingerprint.py`) failed
its check on a lab brain known to have them, for a reason we now understand: in that brain every
poke drove the target far beyond its resting range, so comparing weak with strong pokes never
compared below-threshold with above-threshold drive. This test anchors drive strength to each
neuron's own resting range instead. Written before computing anything below on worm data;
`scripts/run_silent_links_test.py`.

**Hypothesis H.** In worms, a neuron's downstream effects are carried mostly when it is driven
beyond the range of activity it visits at rest.

**Definitions (atlas, wild type, 113 worms).** Unpoked frames: frames outside [f, f + 60) for
every stimulation f (any target). Worms with fewer than 100 unpoked frames are excluded. For
each neuron, its resting mean and SD are taken over the worm's unpoked frames, and its
resting range is the distribution of its 4-frame (2 s) running mean over runs of 4 consecutive
unpoked frames, in resting-SD units. For each stimulation of a named target j: evoked level
E = the largest 4-frame running mean of j over frames 0 to 29 after onset, in the same units;
drive D = j's mean over frames 0 to 29 minus its mean over the 20 frames before, in resting-SD
units; for every other named neuron i, response R = the same change for i in i's resting-SD
units. A stimulation is "beyond" if E exceeds the target's resting 99th percentile and
"within" if E is at or below its resting 95th percentile (stimulations in between are not
used in T2).

**T1, a necessary condition.** H needs pokes to push targets beyond their resting range.
Reported: the fraction of stimulations that are beyond, and the median of E minus the resting
99th percentile (worm-weighted, bootstrap over worms). H's necessary condition fails if the
median E lies at or below the resting 95th percentile. Caveat stated in advance: calcium
fluorescence is a slow, saturating readout of activity, so a poke within the fluorescence
range could still be beyond it in voltage.

**T2, a gain jump.** If links open only beyond the resting range, a unit of drive should move
downstream neurons more in beyond stimulations than in within stimulations; with ordinary
saturating links it should move them less or equally. Pairs (stimulated class, responding
class) are chosen and signed on one half of the worms (alternate worms by file order; at least
6 stimulations and |t| > 3 for the mean response over all of them) and scored on the other
half, then the halves swap. In the scoring half each response is multiplied by the pair's sign
and divided by the pair's mean |R| from the choosing half. Gain in a category = summed
normalised response over summed D, over all scored trials in it. Statistic Q = log(gain beyond
/ gain within), with a 95% interval from 2000 bootstrap resamples of worms. If either gain's
summed drive is not positive, or a gain is not positive, Q is undefined and reported as such.

**Check on lab brains first (positive and negative control).** The same code runs on lab
brains recorded like atlas worms (113 individuals, sigma 0.3, half the units seen, 30% never,
first poke at frame 230, a poke every 30 s held for 4 frames) with the silent links of part G
(GATED 1.5, threshold 0.98) and without (baseline). Because the lab pokes all drive targets far
beyond rest, each poke's strength is scaled by a factor drawn log-uniformly from [a, 1] with a
chosen from 0.02, 0.05, 0.1, 0.2, 0.3 as the value whose share of beyond stimulations is
closest to the worms' share in T1 (judged on the baseline brain, brain seed 0). The test is
valid only if Q(silent links) minus Q(baseline) has a 95% interval above zero for brain seeds
0 and 1. If it is not valid, T2 is reported as uninformative and the worm Q is still shown,
marked as such. If valid, the decision line is fixed from the lab before T2 is run on worms:
the midpoint between the baseline and silent-link Q, averaged over the two seeds. Worms support
H if their Q interval lies above the line, count against H if it lies below the baseline Q of
both seeds, and are inconclusive otherwise.

**What would and would not follow.** Support would make silent-at-rest links the leading
explanation of why worms resist watching, and predicts that graded stimulation of single
neurons shows a threshold at the edge of their resting range. A result against H, with T1
passing, would point to the alternatives already named in part G: pathways a poke opens that do
not depend on the target's own activity level (outputs that calcium does not reflect, state
changes, side effects of the light). A T1 failure would rule out threshold gating on the
target's measured activity as the explanation.

**Result (5 Nov 2026; `docs/figures/silent_links_*`; reviewed independently).**

- **T1 holds.** In 110 worms (3517 stimulations), pokes push the target beyond its resting
  99th percentile in 63.5% of stimulations (95% interval 60.5 to 66.2%) and leave it within the
  95th percentile in 24.5%; the median evoked level is 1.74 resting SD above the 95th percentile.
  The review measured how often the same statistic calls a sham onset "beyond" when nothing was
  poked: 6.0% (1070 sham onsets), so 63.5% is far above chance. H passes its necessary condition.
- **T2 is uninformative, as the rule says.** The lab check failed in both seeds: Q(silent links)
  minus Q(baseline) was +0.76 (interval -1.68 to +3.93) for seed 0 and undefined for seed 1,
  because the gain of within-range pokes divides by a summed drive close to zero (weak pokes in
  the lab barely move their target) and swings wildly. The calibrated pokes (a = 0.02, the edge
  of the grid) give 69% beyond, against the worms' 64%. The worm Q (-1.34, interval -1.64 to
  -1.06) is shown only for completeness and should not be read: the lab baseline is also
  strongly negative (-2.61).
- **Deviations found by the review (none can change the verdict, which is decided on lab
  brains).** Responses are kept per responding class with the last tracked member of a class
  overwriting the others (about 41% of named-neuron entries in worms dropped; lab units are
  unique); neurons of the stimulated class itself are excluded from responses; bootstrap
  resamples with an undefined Q are dropped, so lab intervals are conditional on the defined ones
  (47% to 80% undefined); the two lab brains share bootstrap indices (paired, not independent
  as first labelled); halves alternate over the 110 worms with trials, not all 113 files; T1
  uses 500 resamples.

**Exploratory, after the pre-registered test.** Two further analyses, written after seeing the
above (`scripts/run_silent_links_followup.py`, saved after the worm T2 output existed;
`scripts/run_target_decoupling.py`, written after a binned look at its curve).

- *Does watching predict weak pokes better than strong ones?* Unusable: it has the same
  near-zero-denominator problem (in lab brains, weak pokes evoke no reproducible pattern, so the
  ratio swings from -8.5 to +12.3) and was declared not usable by its own rule (4 of 6 lab
  comparisons, 5 needed).
- *Does a poke's effect need the target's measured activity to change?* Per stimulation, the
  target's change D and the mean signed downstream response r (pairs chosen and signed on the
  other half of the worms). Linear errors-in-variables fit, with the noise in D measured at sham
  times: intercept (response at zero target change) +0.22 (interval +0.12 to +0.31) in worms,
  with no response at sham times (-0.05). Scored instead with every other target's pairs, the
  intercept is +0.035, so under the linear model most of it is specific to the target (+0.18,
  +0.10 to +0.27). Lab brains at the same settings give intercepts of -0.10 to +0.02.

**What the review found, and what survives.** The review reproduced every number and then
broke the strong reading:

1. The response curve is not a straight line (mean r about 0.24 near zero drive, about 0.5
   between 0.75 and 2.5 SD, 1.23 at 5.9 SD). Noise in D smears weak but real target activity
   into the "zero" trials (after deconvolving with the sham noise, trials with |D| < 0.3 have a
   mean true drive of +0.36). Fitting curves with one bend after deconvolution, the
   target-specific part at zero drive is +0.00 to +0.06 with intervals from about -0.4 to +0.27,
   while the total response stays about +0.12 to +0.21. Directly, trials with |D| < 0.3 show r
   = +0.20 (+0.10 to +0.31), but only +0.10 (-0.13 to +0.32) more than when scored with other
   targets' pairs. **So a target-specific effect without target activity is not established.**
2. The lab is not a clean negative control: silent-link brains poked harder (a = 0.2) give
   intercepts of +0.24 and +0.39, through brief transients in the target that the 15 s average
   misses. Worm trials with D near zero have no such transient (median peak 0.36 resting SD,
   the same as at sham times; mean over 0 to 5 s 0.02), while lab trials do (2.3 to 2.5 SD).
3. The total response is robust (per worm: positive in 75% of 96 worms; across windows and
   halves of the recordings); the target-specific part loses significance under several
   reasonable choices (short 0 to 4.5 s window, dropping the first quarter of each recording,
   sham noise measured on stimulated targets only, excluding classes with 4 to 6 members).
4. Trials with D near zero cluster in multi-member and head classes (RMD alone gives 45; URA,
   I1, RIA and AIN have 30 to 35% of their trials there), and 19% of them have another tracked
   neuron rising above 3 SD early (10% at sham times): misidentification within a class or
   light reaching neighbours is not excluded.

**What this does and does not show.** Supported: in worms, stimulations after which the
stimulated neuron's measured calcium shows nothing at all (no change over 15 s and no early
transient) are still followed by downstream changes above sham, mostly not specific to the
target. That is unlike the lab's silent links, which act through target activity the
measurement can see. Not shown: that worms have pathways invisible to calcium, or that this is
why watching fails. What would decide it: neuron positions (to test neighbours of the target),
the atlas's own per-trial flags for whether the target responded, and graded stimulation of
single neurons.

## Trained networks through the worm pipeline (pre-registered 5 Nov 2026)

Every artificial brain so far was an untrained random network, and those can be copied by
watching (lab D), unlike worms. The networks people usually mean by "artificial neural
networks" are trained. If training alone makes a network hide its cause and effect from its
ongoing activity, the worm/artificial difference found above is really a trained/untrained
difference. Written before any ruler run; `scripts/run_ann_trained.py`.

**Networks.** The lab's own dynamics (x <- 0.5 x + 0.5 (W tanh x + b + B u) + 0.2 noise, 120
units, sparse random wiring with 10% of connections, spectral radius 1.3 at the start), trained
with the wiring mask kept fixed on one of two classic tasks for trained recurrent networks:
a 3-bit flip-flop (Sussillo and Barak 2013: three lines of brief +1/-1 pulses, three outputs
that hold the last sign; memory) and context-dependent integration (Mante et al. 2013: two noisy
evidence lines, two context lines, report the sign of the evidence the context names after 20 s
of evidence; integration). 3000 steps of Adam, 64 sequences of 200 frames each. The control for
each task is the identical network before training (same mask, starting weights, input weights
and inputs). While recorded, every network performs its task without pause, so the task inputs
are its unrecorded drives.

**Individuals.** Every connection and input weight scaled by (1 + sigma N(0, 1)); sigma is the
largest of 0.3, 0.2 and 0.1 at which 10 trained individuals keep on average at least 80% of the
trained species network's above-chance accuracy; the control uses the same sigma.

**Pipeline.** Lab D's decisive check unchanged: 113 individuals recorded like atlas worms (37
min, half the units seen, 30% never seen, first poke at frame 230, a poke every 30 s, kick 6 held
8 frames), copies fitted on the training individuals and scored by the unchanged ruler. Copies:
another individual, the watching copy (VAR(3), zero-filled), the stitched watching copy with
slow drift removed, the poke-trained copy. Pool 0 first for all four networks; pools 1 and 2 if
time allows, and every pool run is reported.

**Scoring.** Share = a copy's echo agreement divided by the individuals' agreement with each
other; best watching = the larger of the two watching copies. Per network:
worm-like if best watching < 30% and poke-trained >= 60%; lab-like if best watching >= 50% and
poke-trained >= 60%; intermediate otherwise; unusable if poke-trained < 60% or the individuals
agree at less than 0.05 (the test then cannot tell copies apart). Worms: watching 4% to 22%,
poke-trained 76% to 97%.

**Reading.** Training hides cause and effect, for a task, if the trained network is worm-like
while its untrained control is lab-like. If both are lab-like, training alone does not produce
the worm difference in these networks. Any other combination is reported as it is. No
expectation about the direction: training could create attractors that pokes push between in
ways small fluctuations never show (worm-like), or could make activity follow a few strong
internal patterns that watching recovers easily (lab-like).

**Amendment (5 Nov 2026, written after the first pool-0 runs and before any calibration).**
With the pre-registered poke (kick 6 held 8 frames) the individuals' echoes barely agree (0.019
to 0.041 in the first three networks run), so by the rule above those runs are unusable: the
networks are driven so strongly by their unrecorded task inputs that a single poke's echo is
mostly noise, and every copy, good or bad, comes out inside. As was done for labs F and G, the
poke is lengthened until individuals agree like worms: for each of the four networks, the
smallest hold of 16, 30 or 60 frames at which the individuals' agreement in pool 0 is at least
0.07 (judged on the individuals alone, with no copy scored), then the full set of copies is run
with that hold. If no hold reaches 0.07 the network is reported as unusable. The unusable runs
are kept (`docs/figures/ann_trained_*_fold0.csv`).

**Result (5 Nov 2026; `docs/figures/ann_trained_summary.txt`, `scripts/summarize_lab_h.py`;
training logs: flip-flop accuracy 1.00 trained, 0.51 untrained; context-dependent integration
0.86 trained, 0.49 untrained; sigma 0.3 kept for both tasks by the rule).** The calibration
chose a hold of 30 frames for both trained networks (individuals agree 0.082 and 0.089 in pool
0; 16 frames gave 0.050 and 0.049) and 16 frames for both untrained ones (0.097 and 0.177).
Shares of the individuals' agreement, pools 0 / 1 / 2:

| Network | Individuals agree | Watching (VAR(3)) | Stitched, drift removed | Poke-trained | Verdict |
|---|---|---|---|---|---|
| flip-flop, untrained | 0.18 | 66 / 68 / 71% | 63 / 68 / 68% | 95 / 103 / 98% | lab-like in 3 of 3 |
| flip-flop, trained | 0.08 to 0.09 | 77 / 91 / 82% | 64 / 79 / 76% | 98 / 103 / 106% | lab-like in 3 of 3 |
| integration, untrained | 0.09 to 0.10 | 55 / 44 / 54% | 52 / 52 / 58% | 73 / 72 / 67% | lab-like in 3 of 3 |
| integration, trained | 0.07 to 0.08 | 75 / 75 / 79% | 69 / 88 / 83% | 83 / 98 / 87% | lab-like in 3 of 3 |
| real worms (for reference) | 0.09 to 0.12 | 4 to 16% | 5 to 15% | 76 to 97% | |

**Reading, as pre-registered: training alone does not produce the worm difference in these
networks.** Every trained and untrained network is lab-like in every pool; watching copies of the
trained networks reach 75% to 91% of the individuals' agreement, against 4% to 22% for any
watching copy of worms. If anything the trained networks were easier to copy by watching than
the same networks before training (by 11 to 36 points per pool for the best watching copy), but
that comparison is confounded: the trained networks needed longer pokes to make their
individuals agree, and longer pokes change what the test measures. Limits: two tasks, one
network size and wiring density, one training seed per task, tanh rate units; the trained
integration network's own individuals agree less than worms do in pool 1 (0.073), and in pool 0
its watching copy scores above another individual (75% against 63%), so its ceiling is noisy.
The poke-length amendment was made after the first runs, before any copy was scored at the new
lengths.

## Lab I: the worm experiment's imperfections (pre-registered 5 Nov 2026)

Artificial networks recorded like atlas worms can be copied by watching, trained or not (labs D
and H); worms cannot. Before calling that a difference between biological and artificial
networks, the worm experiment's own imperfections must be ruled out as its cause. Here they are
built into the lab D brains one at a time and all together. Written before any run;
`scripts/run_ann_imperfect.py`.

**Imperfections (levels chosen to be generous, not measured):**

- *Class pooling*: units 2k and 2k + 1 form one class, as left and right neurons are pooled in
  the atlas. The pooled units are wired independently, which is harsher than real left/right
  pairs.
- *Misidentification*: in every recording, 15% of the seen units have their class labels
  shuffled among themselves (a stimulated unit can be among them).
- *Off-target stimulation*: every unit has two fixed neighbours, the same in every individual,
  and a poke also kicks them at half strength; copies are told only the intended target.
- *All three together.*

The slow calcium indicator (lab E) and the short unpoked stretches (lab D, about 2 minutes) are
already covered. Everything else is lab D's decisive check unchanged (113 individuals, sigma
0.3, drives 5%, kick 6 held 8 frames); the reference is lab D itself (watching 51% to 72%,
poke-trained 75% to 89%, pools 0 / 1 / 2).

**Scoring, as in lab H.** Share = echo agreement over the individuals' agreement; best watching =
the better of the watching copy and the stitched drift-removed copy. Worm-like: best watching
< 30% and poke-trained >= 60%. Lab-like: best watching >= 50% and poke-trained >= 60%.
Intermediate otherwise. Unusable if poke-trained < 60% or individuals agree < 0.05; in the
second case the hold is lengthened to 16, 30 or 60 frames as in lab H's amendment, judged on the
individuals alone. Pool 0 for all four conditions; pools 1 and 2 for every condition, time
allowing.

**Reading.** If no condition is worm-like, these imperfections at these levels do not explain the
worm gap, which strengthens (but does not prove) a biological explanation. If one is worm-like,
it becomes the leading artefact explanation, and its signature should then be looked for in the
worm data (for off-target stimulation: responses of the target's physical neighbours, which
needs neuron positions). If only the combination is, the gap could be a joint effect of the
experiment.

## Does stimulation in worms reach neighbouring neurons? (pre-registered 5 Nov 2026)

Lab I's first pool suggests that off-target stimulation (a poke that also activates two
neighbours) can make an artificial brain resist watching the way worms do. Whether it happens in
the atlas can be checked directly: the original archive (`exported_data_full.tar.gz`, OSF e2syt)
holds every tracked neuron's position in every volume (`brains.json`, `matches.txt`). Written
after extracting the positions (median position of each tracked neuron over the recording, in
pixels; `scripts/extract_positions.py`) and before computing anything from them;
`scripts/run_offtarget_worms.py`.

**Measures.** For each stimulation (onset f, target k, wild type, the 113 atlas worms) and every
other tracked neuron i: the early response (mean over frames f to f + 3, 0 to 2 s, minus the mean
over the 20 frames before, in units of i's SD over unpoked frames) and the late response (frames
f + 10 to f + 29). Distance between i and k: Euclidean in pixels with z (slice index) scaled by
s_z; s_z is unknown, so three values are run, 2, 4 and 8 pixels per slice, with 4 primary.
Responses of named neurons are compared within their (stimulated class, responding class) pair:
the within-pair residual is the response minus that pair's mean over every worm and stimulation
(pairs seen in at least 2 worms).

**Statistic.** S = Spearman correlation between the within-pair residual early response and the
log distance, pooled over all entries, with a 95% interval from 2000 bootstrap resamples of
worms. Because a neuron's identity is held fixed, synaptic effects cancel; only effects that
change with where the neuron happens to sit relative to the target remain. Sham: the same at
random unpoked onsets (windows entirely outside [f, f + 60) of every stimulation), with a random
named neuron as the "target". Also reported: S for the late response, and the mean residual early
response by distance rank (nearest neuron, 2nd and 3rd, 4th to 10th, the rest).

**Decision.** Off-target signature present if S < 0 with its interval excluding 0 for all three
s_z and the real-minus-sham difference excluding 0. Absent if the interval of S includes 0 and
its lower end is above -0.02 for s_z = 4. Otherwise inconclusive. If present, its size is
estimated as the nearest neighbour's mean residual early response relative to the target's own
early response, to compare with lab I's assumption (half the target's kick).

**Caveats stated in advance.** An imaging artefact near the stimulation spot would produce the
same signature; either way it is a part of a "response" that a copy cannot learn by watching.
Positions are medians in pixels; neurons move little in these immobilised worms but tracking
errors add noise, which biases S toward zero.

**Result (5 Nov 2026; `docs/figures/offtarget_worms.txt`; positions extracted for all 113 worms, but in 3 the position file and the traces have different neuron counts, so 108 contribute; reviewed independently).** By its
pre-registered rule the signature is **absent**: S (early) = -0.005 (95% interval -0.012 to
+0.002) at s_z = 4, -0.006 and -0.001 at s_z = 2 and 8, real minus sham never excluding zero.
But the rank correlation pools about 247,000 neuron-stimulation entries, of which about 223,000
are beyond the 10th-nearest neuron, so a local effect is diluted to nothing; the pre-registered
summary by distance rank shows one plainly (s_z = 4; sham in brackets):

| Distance rank from the target | Mean within-pair residual early response |
|---|---|
| nearest | +0.191 (sham +0.010) |
| 2nd and 3rd | +0.142 (+0.008) |
| 4th to 10th | +0.053 (+0.002) |
| beyond | -0.009 (-0.000) |

The same pattern holds at s_z = 2 and 8 (nearest +0.204 and +0.168). The nearest neighbour's
residual early response is 0.31 of the target's own early response. The rule chose a statistic
that could not see a local effect; we report the verdict as written and the table beside it.

**Exploratory follow-up: poke-specific or present at rest?
(`scripts/diag_offtarget_crosstalk.py`, `docs/figures/offtarget_crosstalk.txt`, written after the
result above.)** If neighbours rose because of optical crosstalk between adjacent cells or local
coupling, they would also rise when a neuron rises on its own. Per event, the neighbours' early
change beyond that of neurons past the 10th rank, divided by the source neuron's early change
(events with a source change between 1 and 4 resting SD; bootstrap over worms):

| Event | Events (worms) | Nearest neighbour | 2nd and 3rd |
|---|---|---|---|
| stimulation | 1220 (106) | 0.31 (0.28 to 0.34) | 0.21 (0.19 to 0.24) |
| spontaneous rise | 1873 (102) | 0.06 (0.03 to 0.08) | 0.04 (0.02 to 0.05) |

**What the independent review found (it reproduced every number above).**

- *The effect is robust and stimulation-specific.* Matched in size, spontaneous rises give 0.05 to
  0.08 at every source size (stimulation 0.26 to 0.34); the same neurons in the same worms give
  0.30 against 0.05; it is a broad shift (74% of stimulation events positive against 54%), present
  for unnamed neighbours (0.28), for neighbours that are not wired to the target (0.31) and not its
  homolog (0.30).
- *It is not an early effect.* The nearest neighbour's within-pair residual is +0.19 at 0 to 2 s,
  +0.34 at 2 to 5 s, +0.74 at 5 to 10 s and +0.94 at 10 to 15 s (sham about 0), about 0.3 of the
  target's own response throughout: the neighbour carries a scaled copy of the target's response.
- *It appears only when the target itself responds.* When the target's 15 s change is at or below
  zero, the nearest neighbour's residual is at or below zero in every window; it then grows with
  the target. So it is not light reaching neighbours independently of the target.
- *Distance means distance in the image plane.* The z coordinate spans about 10 slices and adds
  nothing; the excess is flat (0.32 to 0.35) for nearest neighbours within 12 pixels and falls to
  0.07 beyond.

**So in the atlas, the stimulated neuron's nearest neighbours in the image carry about 0.3 of the
target's response, over the whole 15 s, beyond what their identity predicts and only when the target
responds; spontaneous rises of the same neurons spread about a sixth as much.** Its cause is not
identified. Light reaching neighbours with delivery shared with the target, a measurement effect of
stimulation tied to the target (the stimulation photobleaches the red tracking fluorophore in the
target, which could disturb tracking or segmentation next to it), and occasional mis-targeting all
fit; an artefact limited to the light pulse is excluded and plain optical bleed-through is unlikely.
Whatever it is, it is part of the measured echo, it is consistent across worms where anatomy is, and
no copy can learn it by watching.

**Lab I amendment (written after the pre-registered result and the exploratory follow-up, and lab
I's first pool, before these runs; the review's findings came later).**
Lab I's off-target setting (neighbours kicked at half strength) is far stronger than this: measured
the same way in lab brains, it gives a neighbour excess of 2.0 times the target's change. Kicks of
0.03 and 0.015 of the target's give 0.30 and 0.15 (`scripts/calib_offtarget_lab.py`, 30
individuals). Two more lab I conditions are run with the unchanged scoring: off-target 0.03
(matched to the worms' nearest neighbour) and 0.015 (half that), pools 0 to 2.

**Second lab I amendment (written after the independent review, before these runs).** The review
showed that the worms' neighbour excess is a scaled copy of the target's response over the whole
15 s and appears only when the target responds, while lab I's off-target kick acts on the
neighbours' dynamics whether or not the target responds. A condition closer to what the atlas shows
is added: no change to the brain, but each poke adds 0.3 times the target's measured response to
its two neighbours' measured traces for the 15 s after the poke (`NEMATICA_LEAK=0.3`), pools 0 to 2,
unchanged scoring.

**Lab I result (5 Nov 2026; `docs/figures/ann_imperfect_summary.txt`, `scripts/summarize_lab_i.py`).**
Best watching copy and poke-trained copy as shares of the individuals' agreement, pools 0 / 1 / 2:

| Condition | Individuals agree | Best watching | Poke-trained | Verdict |
|---|---|---|---|---|
| lab D, no imperfection (reference) | 0.08 to 0.13 | 63 / 66 / 72% | 75 / 85 / 89% | lab-like |
| class pooling, hold 8 | 0.057 / 0.043 / 0.037 | 70 / 81 / 110% | 66 / 74 / 113% | lab-like / unusable / unusable |
| class pooling, hold 16 (chosen by the rule: 0.115) | 0.09 to 0.12 | 81 / 91 / 101% | 79 / 83 / 99% | lab-like 3 of 3 |
| misidentification 15% | 0.071 / 0.048 / 0.062 | 67 / 78 / 68% | 80 / 92 / 84% | lab-like / unusable / lab-like |
| off-target, half-strength kicks | 0.25 to 0.27 | 25 / 21 / 25% | 85 / 89 / 97% | worm-like 3 of 3 |
| all three (half-strength off-target) | 0.070 to 0.080 | 25 / 27 / 23% | 90 / 96 / 99% | worm-like 3 of 3 |
| off-target 0.03 (matched to the worms, amendment 1) | 0.09 to 0.13 | 61 / 62 / 70% | 77 / 86 / 90% | lab-like 3 of 3 |
| off-target 0.015 (amendment 1) | 0.09 to 0.12 | 62 / 65 / 71% | 77 / 84 / 89% | lab-like 3 of 3 |
| measured leak 0.3 into neighbours (amendment 2) | 0.09 to 0.13 | 59 / 61 / 67% | 76 / 85 / 88% | lab-like 3 of 3 |
| pooling + misidentification + leak 0.3, hold 16 (exploratory) | 0.057 to 0.074 | 76 / 88 / 89% | 80 / 88 / 105% | lab-like 3 of 3 |

**Reading, corrected after an independent review (the first version is in the git history).** By
the pre-registered rule, off-target stimulation is now the leading experimental explanation: at
half-strength kicks, alone and combined with the other two imperfections, the lab brains were
worm-like in every pool, and the combination matches worms on every number (individuals agree
0.070 to 0.080, best watching 23% to 27%, poke-trained 90% to 99%; worms 0.09 to 0.12, 4% to 22%,
76% to 97%), while off-target alone makes individuals agree far more than worms do (0.25 to 0.27).
The first version of this reading said that the off-target strength measured in worms was far too
weak to matter. That rested on amendment 1's calibration, which was not comparable: it used the
first 2 s and only pokes whose target changed by 1 to 4 resting SD, which in lab brains keeps
unusually weak pokes of strongly saturating targets. Measured over the ruler's own 15 s window
(the review's numbers; neighbour excess over the target's change, pokes whose target responds):
worms 0.57 raw and about 0.3 identity-controlled; lab off-target 0.5 gives 0.86, 0.2 gives 0.66,
0.1 gives 0.39, 0.03 gives 0.11 and 0.015 gives 0.05; leak 0.3 gives 0.27. So the "matched" runs
were 3 to 10 times too weak, the worm-like run is only about 1.5 to 3 times the worms' level, and
the worms sit between 0.1 and 0.2, which were not run. The leak runs are at the bottom of the worm
range and spread nothing through the network. **Whether off-target activation at the worms' level
makes these lab brains worm-like is open.** Pooled classes and misidentified neurons (about 13%
effectively, since a shuffle leaves some labels in place) do not, in any run. Scope: these are
random tanh rate networks with two fixed neighbours per unit, identical in every individual, which
makes the artefact a consistent kernel the poke-trained copy can learn; in worms the effect survives
identity control, so it partly depends on where neurons happen to sit. Pooling at hold 16 has no
unpooled hold-16 reference.

**Third lab I amendment (written after the review, before these runs).** Off-target kicks of 0.1
and 0.2 (bracketing the worms' level measured in the scoring window) and a leak of 0.6 (the top of
the worm range), pools 0 to 2, unchanged scoring. `scripts/calib_offtarget_lab.py` is kept as run;
its statistic is not the comparable one.

**Third amendment result (5 Nov 2026).** Shares of the individuals' agreement, pools 0 / 1 / 2
(neighbour excess over the 15 s window, from the review, in brackets):

| Condition | Individuals agree | Best watching | Poke-trained | Verdict |
|---|---|---|---|---|
| off-target 0.1 (0.39) | 0.14 to 0.16 | 47 / 42 / 49% | 80 / 86 / 94% | intermediate 3 of 3 |
| off-target 0.2 (0.66) | 0.20 to 0.22 | 33 / 27 / 33% | 84 / 86 / 95% | intermediate, worm-like, intermediate |
| leak 0.6 (0.55) | 0.11 to 0.15 | 50 / 52 / 58% | 79 / 87 / 93% | lab-like 3 of 3 |
| worms (reference; excess 0.3 to 0.57) | 0.09 to 0.12 | 4 to 22% | 76 to 97% | |

**Reading.** At the worms' measured strength, stimulation that spreads through the network to two
neighbours roughly halves what watching can recover (from 63% to 72% without it, to 27% to 49%),
so if the worms' neighbour excess is real activation it accounts for a large part of the gap, but
in these brains not all of it: watching stays above the worms' 4% to 22% in every run (lowest 27%), and
the spread makes individuals agree more than worms do (0.14 to 0.22). A pure measurement leak at the
top of the worm range costs watching much less (50% to 58%). So what the worms' neighbour excess
is matters: if it is light reaching neighbours or mis-targeting, a substantial part of the
watching-versus-poking gap in the atlas is an experimental effect; if it is a tracking or
measurement effect, little of it is. Either way a gap remains that these imperfections, as
modelled, do not produce. The test proposed below (an excess in the neighbours' own synaptic
partners would mean real activation) is the next step.

Other limits: the misidentification rate is assumed, not measured; the pooled units are wired
independently; neighbour effects beyond the nearest two, neighbours that differ between
individuals, and imperfections not modelled here (stimulation efficacy and time course, which in
worms is weak and variable but in the lab deterministic and saturating; tracking that swaps between
adjacent neurons over time; adaptation across about 70 pokes per worm; the nonlinearity of real
neurons and their calcium readout; effects of stimulation on the whole animal's state) are not
covered. A test the worm data allow: if neighbours are truly activated, their own synaptic partners
should show an excess too; a pure measurement leak predicts none.

## Three new tests on the worm atlas: neuron role, repeat pokes, behavioural state (pre-registered 6 Nov 2026)

Written before any of the three was run. Code: `scripts/run_week1.py` (roles in
`nematica/roles.py`, fixed before running). Data: the 113 wild-type atlas worms. Common
definitions, shared with the independent recomputation (`scripts/check_headline_independent.py`)
except that classes use NEMATICA's class names (`neuron_class`) and only labels with a role in
`nematica/roles.py` count as neurons:

- *unpoked frames*: frames not within 30 s after any stimulation;
- *response* of neuron j to a stimulation at frame f: mean over 0 to 15 s after f minus mean over
  the 10 s before, in units of j's SD over unpoked frames;
- *pools*: worms sorted by file name, every third worm held out (pools 0, 1, 2), the rest train.

**Test A2. Does watching fail more for some kinds of neuron?** For each role (sensory,
interneuron, motor; pharyngeal reported separately; dual-role classes left out), keep only the
response pairs whose *stimulated* class has that role. Per pool and role: worm-to-worm agreement
(median Pearson correlation over pairs of held-out worms, at least 20 shared pairs), watching
agreement (a ridge VAR(1) fitted on the training worms' unpoked frames, poked by holding the
stimulated class at +1 for 15 s, against each held-out worm), poke-average agreement (the
training worms' mean response, against each held-out worm). Score per role: watching share =
watching / worm-to-worm. Interval: 2,000 bootstrap resamples of held-out worms within each pool,
shares averaged over the three pools.
*Prediction:* the watching share is lowest for sensory neurons. At rest a sensory neuron mostly
reports the outside world, so its resting fluctuations say little about what it drives.
*Decision:* supported if the sensory share is below both the interneuron and the motor share in
at least 2 of 3 pools and the 90% interval of [sensory share minus the mean of the interneuron
and motor shares] lies below 0. Refuted if that interval lies above 0. Otherwise inconclusive.
Sensitivity (reported, not decisive): dual-role classes put in their first-listed role.

**Test B1. Does a worm give the same answer twice?** For each worm and each *neuron* (not class)
stimulated two or more times, take its first two stimulations. Echo size e = root mean square
response over the worm's other neurons with a role (excluding the stimulated class). Statistic
L = log(e2 / e1). The same quantity for the target's own response (a, restricted to stimulations
with a > 0) shows whether the stimulation itself took less well. Control for slow drift
(bleaching, changing state): pairs of *first* stimulations of two different neurons in the same
worm, matched to each repeat pair on order and on the gap between them (within 20% or 30 s,
whichever is larger), up to 5 control pairs per repeat pair. D = mean L(repeats) minus mean
L(controls), weighting worms equally; 90% interval by resampling worms (2,000). The same
analysis on artificial networks recorded like the worms (lab brains, `lab_recs` of the
silent-links test, ordinary links, fixed poke strength) shows what a network that does not
change gives through the same pipeline.
*Prediction:* D below 0: the second answer is smaller than drift alone explains (habituation).
*Decision:* habituation if the 90% interval of D lies below 0; sensitisation if above 0; no
detectable change if it straddles 0 and lies within plus or minus 0.10 (about 10%); otherwise
inconclusive. The target's own L is reported beside it: a drop in echo with no drop in the
target's own response points to the network, not the stimulation.

**Test B2. Does the same poke spread differently in different behavioural states?** State =
activity of AVA (command interneuron for reversals; mean of its identified neurons, z-scored over
unpoked frames) averaged over the 10 s before a stimulation; worms where AVA is identified.
High state: above that worm's 67th percentile of the same 10 s average over unpoked frames; low:
below its 33rd. To remove what the state does on its own (activity that was high falls back,
ongoing reversals), every response is corrected by subtracting the mean "pseudo-response" of the
same neuron in the same worm: the same post-minus-pre change at onsets with no stimulation in
the whole window (onsets every 5 frames), taken from the same state (high or low). For each
stimulated class poked in both states (pooled over worms, at least 3 stimulations in each
state): S = correlation between the mean corrected echo in the high state and in the low state,
over responding classes measured at least twice in each state (at least 15). Null: the same
with the high or low labels shuffled among that class's stimulations (500 shuffles). Statistic:
median over stimulated classes of S minus the mean of its null. Interval and p-value: by
resampling stimulated classes (2,000) and by flipping the sign of each class's difference
(10,000), respectively. AVA itself is left out of the responders.
*Prediction:* below 0. The same poke spreads differently depending on what the worm was doing,
which a fixed set of connections cannot do.
*Decision:* supported if the sign-flip p is below 0.05 with the median below 0; refuted (no
detectable state dependence) if the 90% interval includes 0 and its lower end is above -0.05;
otherwise inconclusive. Echo size in the two states (mean absolute corrected response) is
reported beside it.

**Results (6 Nov 2026; `docs/figures/week1_a2.txt`, `week1_a2_mixed.txt`, `week1_b1.txt`,
`week1_b2.txt`).**

*A2, neuron role: inconclusive, and the prediction looks wrong.* Watching share (watching
agreement as a share of worm-to-worm agreement, mean of 3 pools, 90% interval): sensory 0.73
[0.53, 1.05], interneuron 0.70 [0.50, 1.00], motor 0.45 [0.17, 1.28], pharyngeal 0.43 [0.29,
0.83]. The sensory share was below both others in 0 of 3 pools; sensory minus the mean of
interneuron and motor: +0.16 [-0.36, +0.49] (paired resampling, corrected after the independent
review; the first run resampled roles separately and gave [-0.32, +0.50]). With dual-role classes in
their first-listed role: +0.28 [-0.22, +0.60], also 0 of 3. So there is no sign that watching fails
most for sensory neurons, and the per-role shares are too noisy (worm-to-worm agreement within one
role is 0.05 to 0.10) to rank roles at all. (An earlier version of this paragraph said the
pharyngeal share was lowest in two of three pools; it is lowest in one, pool 0; motor is lowest in
pools 1 and 2.) These shares use
noise-free predictions (as in the independent recomputation), so they are higher than the
ruler's 4 to 16%; only their order across roles is the question here.

*B1, repeat pokes: habituation as pre-registered; the clear part is the stimulated neuron's own
response.* 100 worms, 577 repeat pairs. The second echo is smaller than drift explains: D = -0.049
[-0.084, -0.014]. The stimulated neuron's own response falls far more: D = -0.42 [-0.53, -0.31].
Artificial networks recorded the same way (113 individuals, 2,319 repeat pairs, the silent-links
lab configuration) give an echo D of +0.001 [-0.011, +0.014], so the pipeline does not create the
echo effect; they also show a small dip in the target's own response, -0.08 [-0.13, -0.03], which
is unexplained (the ingredient ladder's plain networks give -0.01 to -0.02).

Corrections after the independent review (exploratory, `week1_b1.txt`): (1) the echo is a root
mean square over mostly non-responding neurons, so about 60% of it is noise and the -0.049 is a
diluted number (a lower bound on the drop, not "about 5%"); with the noise floor (measured at
moments with no stimulation) subtracted, the echo D is -0.04 [-0.19, +0.12], too wide to say how
much the echo itself falls. (2) Neurons poked again had larger first responses (median 2.04 against
1.64 SD), so part of the -0.42 could be regression to the mean; corrected for the size of the first
response, the target's own D is -0.28 [-0.40, -0.18]: a second pulse of light activates the same
neuron about a quarter less. Reading: the worm's stimulated neurons tire with use, which the
artificial networks do not; whether the neuron or the light-gated channel used to activate it is
what tires, and how much the spread to other neurons falls, this atlas cannot say. Settling it needs
repeat pokes of matched strength.

*B2, behavioural state: no detectable state dependence.* The first run deviated from the
specification: its "pseudo-responses" required the whole window to lie outside the 30 s after any
stimulation (about 55 s free of stimulation), where the specification asks only for no
stimulation inside the 25 s window. That left 27 of the 68 worms with AVA and 23 stimulated classes
(median S minus null -0.040 [-0.052, +0.046], p = 0.26, inconclusive; kept in
`week1_b2_strict.txt`). Rerun as specified (`week1_b2.txt`): 65 worms, 52 stimulated classes,
median -0.014 [-0.046, +0.012], sign-flip p = 0.17, echo size high/low median 1.00: **no
detectable state dependence** by the pre-registered rule. Within this test's resolution, the same
poke spreads the same way whether or not the worm is in a reversal-prone state. Caveat: AVA is one
state signal of many, and the threshold for "refuted" (-0.05) is a modest effect, not zero.

## A nonlinear watcher (pre-registered 6 Nov 2026 as "the strongest watcher we can build")

The worm headline rests on watching copies that are linear (VAR) or linear with stitching. The
obvious objection: watching failed because the watchers were too simple. The project already
has a nonlinear model trained only by watching, `AtlasGRU` (a recurrent network pooled over
all training worms' stimulation-free stretches, predicting the next frame's mean and spread,
so it learns calm and active states and carries a hidden state that can stand for unrecorded
neurons and slow drives). So far it was used only as the background of a copy that also
learned from pokes. Here it is scored alone, as a watcher, through the unchanged ruler
(`scripts/run_strong_watcher.py`, split cv3, all three pools, the clamp protocol every copy
uses: at each stimulation the stimulated class is held at its pre-pulse model value plus the
neuron's measured response for 30 s, and the network's own dynamics carry the rest).

Copies: `gru64_watch` (the existing settings: 64 hidden units, 1,500 training steps) and
`gru128ss_watch` (128 hidden units, 4,000 steps, trained partly on its own samples so that it
stays realistic when running alone). Both choose nothing on poke data.

*Prediction:* both stay far below poking: echo agreement below half of the real worms' agreement
with each other in every pool (real worms 0.093 to 0.107; the existing watching copies 0.004 to
0.024; the poke-trained copy 0.076 to 0.092).
*Decision:* the watching gap survives the strongest watcher if both copies are below half the
real-worm agreement in all 3 pools; it closes if either copy's echo pattern is judged inside
(the ruler's verdict) in at least 2 of 3 pools; otherwise it partly closes, and we report by how
much.

**Result (6 Nov 2026; `docs/figures/strong_watcher.csv`).** Echo agreement, pools 0 / 1 / 2 (real
worms 0.095 / 0.107 / 0.093): `gru64_watch` 0.005 / 0.004 / 0.008; `gru128ss_watch` 0.005 / 0.009 /
0.011. All six are outside and below half the real-worm agreement: **the watching gap survives the
nonlinear watcher**, as predicted. Two caveats from the independent review: the recurrent watcher
does a little worse than the linear ones (0.004 to 0.024), and it never saw a clamped input in
training, so its failure could be a failure to cope with the clamp rather than a limit of watching.
Positive control (added after the review; `docs/figures/ladder_ruler.csv`, the ingredient ladder's
base network, brain 0, pool 0): the same `gru64_watch` recovers 0.031 against individuals' 0.060
(52%; the linear watcher 69%, the stitched 57%), against 4% to 12% on worms. So the recurrent
watcher does work where watching can work, and its failure on worms is not a failure to handle the
clamp. The title's claim, "the strongest watcher we can build", was too strong: two sizes, fixed
training, no tuning.

## The ingredient ladder: what does an artificial network need to look like a worm? (pre-registered 6 Nov 2026)

So far each candidate explanation of the worm gap was tested on its own. Here five ingredients are
added to the lab's tanh networks in every combination (2^5 = 32 variants, two independent brains
each), every variant is recorded like the atlas (113 individuals, sigma 0.3, half the units seen
per recording, 30% never seen, a poke every 30 s at fixed strength), and every variant and the
113 real worms are measured on the same six axes by the same code (`scripts/run_ladder.py`).

Ingredients (off / on):
- **D, shared slow drives**: none / three unrecorded drives with a 90 s timescale carrying 25% of
  each unit's input variance;
- **G, silent links**: none / the silent-links test's thresholded links (density 5%, strength 1.5,
  active only above tanh 0.98);
- **S, stimulation spread**: none / each poke also kicks two fixed neighbours at 0.15 of its size
  (between the two strengths that bracketed the worm's measured neighbour excess);
- **H, stimulation that tires**: none / the k-th poke of the same unit in a recording is scaled by
  0.65^(k-1) (the worms' second activation is about 35% weaker, test B1);
- **M, modules**: random wiring / four modules of 30 units, 90% of connections inside a module
  (same overall density and spectral radius).

Axes (definitions as in the three tests above; worms use classes with a role, lab units are
their own classes):
1. *watching share*: noise-free ridge VAR(1) watching agreement over worm-to-worm agreement, mean
   of three pools (test A2's method, all stimulated classes);
2. *echo breadth*: share of the other seen units or classes whose response to a poke exceeds 1
   resting SD in size, median over pokes;
3. *stimulation tiring*: D of the target's own response (test B1);
4. *rest dimensionality*: share of variance in the top three principal components of unpoked
   activity (z-scored seen units or classes), median over recordings;
5. *individuality*: same-recording agreement between alternate pokes minus agreement with other
   recordings' halves, median over recordings (at least 20 shared pairs);
6. *echo reliability*: worm-to-worm agreement (median over pairs, all three pools).

Distance from the worms: for each axis, (variant minus worm) divided by that axis's standard
deviation across the 64 lab runs; distance = root mean square over the six axes. Contribution
of each ingredient: its Shapley value (the change it makes, averaged over every order of adding
the five), on the watching share and on the distance.

*Predictions:* (1) shared drives lower the watching share most, silent links second; spread
helps less; tiring and modules hardly change it. (2) No single ingredient brings a network to the
worm; the closest variant has at least drives and silent links. (3) Modules make echoes narrower
(lower echo breadth), toward the worm. (4) Tiring is the only ingredient that moves axis 3.
*Decision:* each prediction is judged on the Shapley values (mean of the two brains), with the
sign and order as stated; predictions (1) and (3) need the effect in both brains. The full ruler
is then run on the closest variant, to check that the cheap axis agrees with the expensive one.

**Results (6 Nov 2026; `docs/figures/ladder_worms.csv`, `ladder_lab_seed0.csv`,
`ladder_lab_seed1.csv`, `ladder_summary.txt`).** The worms: watching share 0.61, echo breadth
0.085, stimulation tiring -0.42, rest dimensionality 0.43, individuality 0.089, reliability
0.094 (the last three agree with earlier, separate measurements: 40%, 0.10 and 0.09 to 0.11).

| Axis | Worms | Lab base (brain 0 / 1) | What moves a network toward the worm (Shapley, mean of the two brains) |
|---|---|---|---|
| watching share | 0.61 | 2.46 / 2.38 | silent links -1.32, spread -0.55, modules -0.15; drives +0.18 and tiring +0.10 move it away |
| echo breadth | 0.085 | 0.100 / 0.095 | modules -0.004 (only); drives +0.017 and silent links +0.022 widen echoes |
| stimulation tiring | -0.42 | -0.02 / -0.01 | tiring -0.06 (only); no variant goes below -0.13 |
| rest dimensionality | 0.43 | 0.27 / 0.25 | drives +0.17 (only); every variant with drives is at 0.40 to 0.43 |
| individuality | 0.089 | 0.028 / 0.016 | silent links +0.034; drives -0.037 erase it |
| reliability | 0.094 | 0.076 / 0.075 | silent links +0.084 overshoot, drives -0.078 undershoot; together about right |

Pre-registered predictions:
1. *Drives lower the watching share most, silent links second.* **Wrong as stated**, and the
   independent review showed why. The share is watching agreement divided by individuals'
   agreement. Silent links lower it in both brains (Shapley -1.32), but mainly by raising the
   denominator: they make individuals' echoes agree with each other about twice as well (0.076 to
   0.173). The numerator ranks the ingredients the other way round: the implied watching agreement
   (share times individuals' agreement, an approximation; exploratory) falls most with drives
   (Shapley -0.084) and only a little with silent links (-0.017), the order the prediction gave.
   Worms' implied watching agreement is 0.057, below every round-1 variant (0.072 to 0.20).
2. *No single ingredient brings a network to the worm; the closest has drives and silent links.*
   First half holds; second half **refuted as stated**: by the pre-registered distance the closest
   variant is spread plus tiring (SH, 3.85 against 4.49 for the base). But that distance turned out
   to be dominated by one axis no variant approaches (tiring: the worms sit ten lab SDs away), so
   it mostly ranks variants by whether they include tiring. Without that axis (exploratory), the
   closest by mean of the two brains is modules plus spread (1.29), and single runs range from 1.23
   to 2.26: no combination of these five ingredients comes near the worm on all axes. Counting axes
   within 25% of the worm value (exploratory), no variant manages more than 3 of 6 in either brain.
3. *Modules make echoes narrower.* **No detectable effect**: -0.004 in both brains, smaller than
   the difference between the two base brains (0.005); the modular network is also a new random
   draw, so modularity and the draw cannot be separated here (tiring gives the same -0.004).
4. *Tiring is the only ingredient that moves axis 3.* **Supported**, but even a poke 35% weaker
   the second time lowers the lab target's measured response by only about 8%: a strongly driven
   tanh unit saturates, so its response hides the weaker input.

Full ruler on three variants (brain 0, pool 0; `docs/figures/ladder_ruler.csv`; watching copy,
then stitched watcher, against individuals' agreement): base 0.041 and 0.034 against 0.060 (69%
and 57%); SH 0.040 and 0.031 against 0.083 (48%, 37%); DGSM (drives, silent links, spread, modules)
0.021 and 0.020 against 0.107 (19%, 18%). The poke-trained copy is inside in all three. Worms:
4 to 16%. So on the ruler the variant with drives and silent links comes near the worms, and it does
so both ways: its watching agreement is half the base's and its individuals agree almost twice as
well. One pool and one brain each: a check of the cheap axis's order, not a result in itself.

**What this says.** No one ingredient makes an artificial network look like a worm. Shared slow
drives are what most degrade what watching can recover, and they give the worm's resting
structure; silent links are what make individuals' echoes as reproducible and as individual as
worms'. But drives also erase individuality and widen echoes, so the ingredients pull against
each other, and no combination of these five sits at the worm's values on all axes at once. Two
worm properties no variant reaches: very narrow echoes (8.5% of neuron classes move by more than one
resting SD) and stimulation that tires by a quarter to a third. Caveats (several from the
independent review): two brains, so no noise floor for the Shapley values (the drives' Shapley on
distance even has opposite signs in the two); the cheap watching axis uses noise-free predictions
and sits on a different scale from the ruler; ingredient strengths are single choices, not fitted;
in variants with silent links the drives carry somewhat less than 25% of the input, because their
size was set without them.

**Round 2, one more ingredient (pre-registered 6 Nov 2026, after round 1).** Every variant's
echoes are wider than the worm's, and an earlier diagnosis found that a third of a real worm's
neuron classes never respond in the 30 s after a poke. Ingredient **Q, quiet units**: half the
units (the same in every individual) get a bias of -2.5, so they sit near the flat bottom of
their range and move only with strong input. Q is added to base, D, G, DG, DGS, GSM and DGSM
(both brains; same code, `--codes`).
*Predictions:* (1) Q lowers echo breadth in every one of the 7 pairs, in both brains; (2) Q does
not raise the watching share by more than 0.1 in any pair; (3) the variant with the most axes
within 25% of the worm (exploratory count, now pre-registered as the summary) includes Q.

**Round 2 result (`docs/figures/ladder_summary.txt`).** (1) **Supported**: quiet units narrow
echoes in 14 of 14 comparisons (for example base 0.100 to 0.022; DGSM 0.139 to 0.050; the worm
0.085). (2) **Supported**, and more: they lower the watching share every time (base 2.46 to 1.14;
DGSM 0.63 to 0.20, now below the worm's 0.61). (3) **Wrong**: at half the units they overshoot,
making echoes narrower than the worm's and halving rest dimensionality (0.42 to 0.21), so the
variants closest to the worm still have no quiet units (best: 3 of 6 axes within 25% in one
brain). The watching share is a ratio (see prediction 1 above), so part of this drop may again be
individuals agreeing more. So the lab now has a lever for each axis but no single network where all
of them sit at the worm's values at once. A smaller quiet fraction is the obvious next setting; the general
lesson is that the worm's properties are mutually constraining, and matching them jointly, not
one at a time, is the test any model of a real brain has to pass.

**Round 3, a joint fit (pre-registered 6 Nov 2026, after the independent review).** Rounds 1 and 2
switched ingredients fully on or off. Here their strengths vary together: drive share {0, 0.1, 0.25,
0.4}, silent-link strength {0, 0.75, 1.5, 3}, spread {0, 0.15, 0.3}, quiet fraction {0, 0.1, 0.2,
0.3}, modules {off, on} (no tiring; its axis is left out). 48 settings drawn at random (seed 2026)
are measured on brain 0; the 5 with the lowest root-mean-square relative error over the other five
axes are re-measured on brain 1, which played no part in choosing them (`run_ladder.py fit`).
*Prediction:* no setting has all five axes within 25% of the worm in both brains; drives' erasure of
individuality is the likely blocker. *Decision:* a setting with all five within 25% in both brains
means this family of networks can match the worm on these axes jointly; otherwise it cannot at this
resolution, and the axis that fails most often is reported.

**Round 3 result (`docs/figures/ladder_fit_seed0.csv`, `ladder_fit_seed1.csv`,
`ladder_fit_summary.txt`).** 43 distinct settings on brain 0 (five of the 48 draws repeated; "44" in an earlier version); the 5
best re-measured on brain 1. **No setting has all five axes within 25% in both brains (0 of 5), as
predicted, and individuality is the blocker: it is outside in all 10 runs** (at most 0.057 against
the worm's 0.089; the best settings give 0.013 to 0.018). Rest dimensionality is next (outside in 6
of 10). The best setting (drives 0.25, silent links 0.75, spread 0.15, quiet 0.2, no modules) has
the same relative error on the brain it was chosen on and on the held-out brain (0.40 and 0.40) and
puts three axes within 25% in both: watching share (0.55, 0.59; worm 0.61), echo breadth (0.073,
0.087; worm 0.085) and reliability (0.093, 0.103; worm 0.094). So an artificial network of this
family can match how hard a worm is to copy by watching, how narrow its echoes are and how
reproducible they are, all at once and on a brain it was not fitted to; it then has a fifth of the
worm's individuality and too little resting structure. In these networks the slow drives that
give resting structure erase individual differences; the worm has both. (Qualified by rounds 7 and 8
and the second review: this holds at the lab's original individual variation; with individuals that
differ more, drives and individuality coexist.)

**Round 4, private drives (pre-registered 6 Nov 2026, after round 3).** In every network so far the
slow drives' loadings are the same in all individuals (one species-wide set of background signals),
which may be exactly what erases individuality. Ingredient **P, private drives**: each individual
gets its own drive loadings (same number, timescale and share, drawn independently per individual).
P is added to round 3's two best settings (drives 0.25 and 0.4; `run_ladder.py fit --private`),
measured on both brains. *Prediction:* individuality rises (in all 4 runs) while rest
dimensionality stays within 0.05 of its value without P. *Decision:* supported if both hold in all
four runs; the run with the most axes within 25% is reported, and if any has all five within 25%,
that setting is the first network in this project to match the worm on every axis we can measure.

**Round 4 result (`docs/figures/ladder_private.csv`).** Individuality with private drives against
the same setting with shared drives (round 3), brains 0 / 1: drives 0.25 setting 0.026 / 0.016
(shared 0.017 / 0.014); drives 0.4 setting 0.012 / 0.006 (shared 0.013 / 0.014). It rises in 2 of 4
runs and falls in 2; rest dimensionality stays within 0.019 in all four ("0.01" in an earlier version). **Prediction refuted**:
private drives do not restore individuality, so it is not the sharing of the drives across
individuals that erases it. The individuality measure is a recording's agreement with itself minus
its agreement with others, and in these networks slow drives lower the first term: they make one
individual's echoes inconsistent from poke to poke, whoever's drives they are. Worms combine a
strongly structured resting state with echoes that stay consistent within an animal (same-worm
agreement 0.146 against 0.083 between worms). One reading, to be tested: something in the worm keeps
slow background activity out of its responses to pokes (another: part of the worm's individuality is
measurement, such as neuron identities assigned once per worm, which the 1 Nov test could not rule
out). The first reading gives the next round: drives that change how excitable neurons are, instead
of adding to their activity.

**Round 5, drives that change excitability (pre-registered 6 Nov 2026, after round 4).** Ingredient
**K**: the slow drives multiply each unit's recurrent input by (1 + k x its drive), with the drive
normalised to unit variance, instead of adding to it; no additive drives. Settings: round 3's best
setting without its additive drives (silent links 0.75, spread 0.15, quiet 0.2) with k = 0, 0.3
and 0.6, both brains (`run_ladder.py fit --gain`). *Prediction:* compared with k = 0, rest
dimensionality rises and individuality does not fall (by more than 0.005) at k = 0.6, in both brains.
*Decision:* supported if both hold in both brains; the run with the most axes within 25% is reported.

**Round 5 result (`docs/figures/ladder_gain.csv`).** k = 0 / 0.3 / 0.6, brain 0: rest dimensionality
0.155 / 0.220 / 0.320, individuality 0.040 / 0.008 / -0.011; brain 1: 0.164 / 0.227 / 0.331 and
0.038 / 0.026 / -0.003. **Refuted**: excitability drives give resting structure but erase
individuality just as additive drives do. In these networks any slow drive, however it enters, makes
an individual's echoes inconsistent from poke to poke.

**Is the worm's individuality about cause and effect? (pre-registered 6 Nov 2026, after round 5.)**
Before building more machinery to reproduce worm individuality, check what it is. If each worm has
a response profile shared by all its pokes whatever the target (a state, or a recording property
such as how its neurons were identified or imaged), two halves of one worm agree for that reason
alone. Two checks with the ladder's individuality measure (`scripts/run_individuality_check.py`):
(a) *generic profile removed*: in each half, subtract from every (target, responder) response that
responder's mean over all targets in that half, then recompute the excess; (b) *targets shuffled*:
same-worm agreement when the second half's target labels are permuted among its targets (100
permutations), minus the same for different worms. *Prediction:* the excess shrinks by more than
half under (a), and (b) keeps more than half of it: worm individuality is mostly a worm-wide
profile, not individual cause and effect. *Decision:* "mostly generic" if both hold; "mostly causal"
if (a) keeps more than three quarters of the excess and (b) less than a quarter; otherwise mixed.
The same checks on lab networks (round 1 base and G, brain 0) show what causal individuality looks
like through this measure.

**Result (`docs/figures/individuality_check.txt`).** Worms (107): excess +0.090; (a) with each half's
generic profile removed +0.098 (109% kept); (b) with targets shuffled +0.009 (10% kept). Lab base
network: 86% and 15% kept; with silent links: 88% and 16%. **Prediction refuted.** By the
pre-registered rule the verdict is "mostly causal", but that label says more than the check can (second
review): it shows that the worm's individuality is specific to which neuron is poked, **mostly
target-specific**, as it is in networks whose individuals differ by construction in their connections,
not that it is cause and effect. (Deviation: (b) used 30 permutations, not
the 100 specified; the mean over permutations is stable to about 0.001.) One alternative remains
that this check cannot remove: target-specific measurement, such as a neuron misidentified in one
worm's recording, is also individual and target-specific; so is the 5 Nov neighbour effect if it is a
leak, since which neurons neighbour a target differs from worm to worm.

So the ladder ends on a sharp contrast. Worms have strongly structured resting activity (43% of
variance in three patterns) and echoes that are individual, specific to the poked neuron, and
consistent within an animal. In every artificial network we built, the ingredients that produce
that resting structure (slow drives, added or multiplied, shared or private) make echoes
inconsistent within an individual and erase its individuality. Worms keep their slow
background activity and their individual cause and effect apart; ours do not. (Narrowed by the
next test: in the networks this works as added noise, not as state-dependent routing. Both this
paragraph and that narrowing are withdrawn: the next test was flawed, and rounds 7 and 8 show that
with individuals that differ more the networks keep resting structure and individuality together.)

**Does slow background activity change where a poke goes, in worms and in the lab? (pre-registered
6 Nov 2026.)** Test B2's method, unchanged except for the state signal: instead of AVA, each
recording's state is its activity projected on the first principal component of its own unpoked
activity (z-scored seen units or classes), the most neutral "slow background" signal available in
both worms and networks. Run on the 113 worms, the ladder's base network and the drives-only
network (round 1, brain 0) (`run_week1.py b2-pc1`). *Prediction:* the drives network shows state
dependence (sign-flip p < 0.05, median below 0); the worms do not (as with AVA); the base network does
not. If so, worms differ from the networks in exactly this: their slow background state leaves the
pattern of a poke's spread alone.

**Result (`docs/figures/b2_pc1_worms.txt`, `b2_pc1_lab_base.txt`, `b2_pc1_lab_D.txt`).** Median S
minus null: worms (83 recordings, 59 stimulated classes) -0.020 [-0.051, +0.005], p = 0.10; lab base
-0.020 [-0.029, -0.003], p = 0.055; lab drives -0.007 [-0.027, +0.015], p = 0.41. **Prediction
refuted**: the drives network shows no state dependence by this measure, and none of the three is
clearly different from the others. So the drives do not lower within-individual consistency by
routing pokes differently in different states; the simpler reading is that they add slow
fluctuations inside each 15 s response window, which act as noise on every echo. The contrast
stated above therefore narrows: worms combine strong resting structure with echoes that stay
consistent within an animal, and in our networks the drives that give resting structure also add
noise to echoes. Whether the worm's resting structure is slower than its response window, comes
from the network's own dynamics rather than outside drives, or is simply smaller next to its
responses than in our networks, is the next question.

**Correction after the second independent review: this test was flawed.** The sign of a principal
component is arbitrary, and `pc1_state` took it as the SVD returned it, so "high" and "low" were
swapped in about a quarter to a third of recordings (28% of worms, 34% of the base network's, 22% of
the drives network's), diluting any effect. The reviewer's exploratory rerun with signs aligned to the
consensus loading gave worms -0.049 [-0.084, -0.020], p = 0.002, the drives network -0.018 (p = 0.13)
and the base network 0.000 (p = 0.52): the opposite of the reading above, which is withdrawn. *Amended
test (written after seeing the reviewer's rerun, so not blind):* the same test with each recording's
sign set so its loadings correlate positively with the consensus (`run_week1.py b2-pc1-aligned`), on
the worms, the base and drives networks, and a positive control that should show state dependence:
round 5's excitability-drive network (k = 0.6). Decision rule as in B2.

*Amended result (`docs/figures/b2_pc1_aligned_*.txt`).* Worms (83 recordings, 63 stimulated classes):
-0.049 [-0.084, -0.020], sign-flip p = 0.002, **supported**: the pattern of a poke's spread depends on
where the worm sits along its main resting pattern (echo size high/low 0.92). Lab base 0.000 (p = 0.52),
drives -0.018 (p = 0.13), and the **positive control fails**: the excitability-drive network, built so
that the drives change how units respond, gives -0.003 (p = 0.46). So this test cannot detect state
dependence in these networks even where it exists by construction, and nothing follows about whether
the networks lack it. For the worms, two cautions: the amended test was written after the reviewer's
rerun had shown this result, so it is not an independent confirmation; and with AVA as the state signal
(test B2) no dependence was detected, so the worm's main resting pattern is not simply its reversal
state. As an observation on worms it stands, and it is the first sign in this project that the same
poke spreads differently depending on the worm's slow background state.

**How much of an echo is the poke? (exploratory, 6 Nov; `docs/figures/echo_noise_share.txt`.)** The
mean square post-minus-pre change over a recording's neurons, after stimulations against at moments
with no stimulation: worms 0.617 against 0.446, so 28% of the change after a poke is evoked by it;
lab networks 2% (base), 4% (silent links), 6% (drives), 8% (both) and 12% (DGSM). Worm pokes stand
out from the background several times more than the lab's do. The lab's poke strength was calibrated
so that individuals' echoes agree about as well as worms' (reliability), not on how much they stand
out, so this is a mismatch in the lab's design, and a plausible cause of both the individuality
gap and the difficulty of matching narrow echoes.

**Correction after the second review: these numbers were wrong.** The reference windows excluded only
the frames where pokes start, not the 30 s after them, so in the lab most reference windows began 25 to
35 frames after a poke and in worms 98.5% sat in the tail of the previous echo. Recomputed with
reference windows entirely outside the 30 s after any poke (`run_ladder.py evoked`; in worms and in the
lab this leaves the rest before the first poke; `docs/figures/echo_noise_share.txt`): worms 0.42; lab
base 0.14, silent links 0.24, drives 0.28, both 0.32, DGSM 0.43, DGSM with 16-frame holds 0.70, round
9's setting 0.50. **Worm pokes do not stand out more than the lab's** once the networks have drives and
silent links; the motivation given for round 6 was mistaken.

**Round 6, stronger pokes (pre-registered 6 Nov 2026).** Each poke is held for 16 frames (8 s)
instead of 4, so its downstream effect grows (the target itself already saturates). Settings: round
3's best setting and DGSM (round 1), both brains (`run_ladder.py fit --long`). *Prediction:* the
evoked share rises toward the worms' 28% and individuality rises, in all four runs. *Decision:*
supported if both rise in all four; the run with the most of the five axes within 25% is reported.

**Round 6 result (`docs/figures/ladder_long.csv`).** Holding pokes 16 frames instead of 4: individuality
rises in all four runs, from 0.014 to 0.045 to 0.106 to 0.148 (worm 0.089), and reliability with it
(0.093 to 0.136 to 0.42 to 0.47; worm 0.094); rest dimensionality is unchanged (DGSM 0.41 to 0.42,
worm-like; unchanged by construction, since in the lab "unpoked" frames are only those before the
first poke). The evoked share fell instead of rising, to between -0.87 and -0.01, because the measure
itself was broken (see the correction above; recomputed properly, DGSM goes from 0.43 at a 4-frame hold
to 0.70 at 16). **Not supported as stated.** The individuality half holds in all four runs, but the
reading first given here, that the individuality gap was "in large part" the lab's poke calibration, is
withdrawn (second review): individuality and reliability rise together with the hold, and their ratio,
which is 0.95 in worms (0.089 against 0.094), stays at 0.13 to 0.37 at every hold length with the lab's
original individual variation. Only larger individual differences move it (0.71 to 0.89 at sigma 0.5,
1.9 to 2.5 at 0.8; round 8). So what the networks lacked was not poke strength but individuals that
differ from each other as much, relative to how reproducible each is, as worms do.

**Round 7, a sweep of poke strength (pre-registered 6 Nov 2026).** Holds of 6, 8 and 10 frames for
the same two settings, both brains (`run_ladder.py fit --hold-sweep`). *Prediction:* for at least
one setting and hold, individuality and reliability are both within 25% of the worm in both brains.
The run with the most of the five axes within 25% is reported; if any setting has all five within 25%
in both brains, it is the first network here to match the worm on every axis we can measure.

**Round 7 result (`docs/figures/ladder_holds_seed0.csv`, `ladder_holds_seed1.csv`).** At holds of 6, 8
and 10 frames, reliability is 0.16 to 0.33 in every run (worm 0.094; 25% band 0.071 to 0.118), while
individuality (band 0.067 to 0.112) reaches it for DGSM at hold 10 on brain 0 (0.093) and at holds 6
and 8 on brain 1 (0.078, 0.100); brain 1's hold 10 (0.120) is just outside.
**Refuted**: no setting and hold has both within 25% in both brains. Stronger pokes raise
individuality and reliability together. Worms combine the two differently: their ratio of
individuality to reliability is 0.95, while these networks stay at 0.16 to 0.37 at every hold
(corrected after the second review; an earlier version compared "1.8" for worms with "about 1.3" for
the networks, a figure in no output file). Worms differ from each other more, relative to how
reproducible each one is, than the lab's individuals (connection strengths varying with an SD of 30%).

**Round 8, more different individuals (pre-registered 6 Nov 2026).** The individual variation sigma
(each connection scaled by 1 + sigma x N(0, 1)) raised from 0.3 to 0.5 and 0.8, DGSM with holds of 8
and 16 frames, both brains (`run_ladder.py fit --sigma-sweep`). *Prediction:* for at least one
combination, individuality and reliability are both within 25% of the worm in both brains.

**Round 8 result (`docs/figures/ladder_sigma_seed0.csv`, `ladder_sigma_seed1.csv`).** At sigma 0.8 and
hold 8, reliability reaches the worm's band (0.075; 0.070 is at its lower edge, 0.0704) but individuality is twice the worm's
(0.166, 0.175); at sigma 0.5, individuality 0.12 to 0.24 and reliability 0.16 to 0.30. **Refuted**: no
combination has both within 25% in both brains. But the two knobs move the pair differently
(individual variation lowers reliability, stronger pokes raise both), so the pair can be bracketed,
while stronger pokes widen echoes (0.18 to 0.27 against the worm's 0.085), which quiet units narrow.

**Round 9, the full joint search (pre-registered 6 Nov 2026).** Rather than tuning knobs one at a
time: 60 settings drawn at random (seed 909) over drive share {0, 0.1, 0.25, 0.4}, silent-link
strength {0, 0.75, 1.5}, spread {0, 0.15}, quiet fraction {0, 0.1, 0.2, 0.3}, individual variation
sigma {0.3, 0.5, 0.65, 0.8}, poke hold {4, 6, 8, 10} frames, no modules; measured on brain 0; the 5
with the lowest relative error over the five axes re-measured on brain 1 (`run_ladder.py fit9`).
*Prediction:* the best setting reaches 4 of 5 axes within 25% in both brains, but not 5, because
stronger pokes widen echoes while raising individuality. *Decision:* "matched" if any of the 5 has all
five within 25% in both brains (then this family of networks can look like a worm on every axis we
measure, and the remaining question is which of its ingredients the worm actually has); otherwise
the axis that fails most often across the 10 runs is reported as the open mismatch.

**Round 9 result (`docs/figures/ladder_fit9_*.csv`, `ladder_fit9_summary.txt`).** 57 distinct settings ("58" in an earlier version)
on brain 0; the best five re-measured on brain 1. **Not matched**: no setting has all five axes within
25% in both brains, and none has four (the prediction's "4 of 5" is refuted; "not 5" holds). But the
search came much closer than any earlier round: the most stable setting (drives 0.4, silent links
0.75, spread 0.15, quiet 0.3, sigma 0.8, hold 6) has a relative error of 0.21 on the brain it was
chosen on and 0.22 on the held-out brain (round 3's best: 0.40), with watching share and
individuality within 25% in both. Every axis fails somewhere (echo breadth and reliability most
often, 6 of 10 runs each), and two random networks with the same setting differ about as much as the
remaining error. Corrections and limits from the second review: the relative error is a root mean
square over the five fitted axes, and single axes are off by up to 36% (reliability); only two axes are
within 25% in both brains; tiring, left out of the fit, is a tenth of the worm's on brain 0 and of the
wrong sign on brain 1 (with it, the error is 0.42 and 0.51); the "most stable" setting ranks second on
brain 0 and was picked after seeing brain 1, so for that choice brain 1 is not held out (the brain-0
winner went from 0.17 to 0.27), and brain 1 also shaped rounds 4 to 8; and sigma 0.8 means connection
strengths vary with an SD of 80%, which flips the sign of about 11% of connections. Reading: networks
with these ingredients come within roughly a fifth of the worm on average over five axes, not inside a
25% band on all of them, and only with strong slow drives, very different individuals, many quiet units
and longer pokes. Which of these the worm actually has is not answered by fitting; the tiring of
stimulation is still unmatched. Full-ruler check of the most stable setting, written before running:
its watching copy should fall in or near the worms' 4% to 16% of individuals' agreement.

**Full-ruler check (`docs/figures/ladder_ruler.csv`, `fit9best`, pool 0, both brains).** Watching copy
0.0085 and 0.0102 against individuals' 0.055 and 0.062 (15.5% and 16.4%); stitched watcher 16.6% and
15.6%; poke-trained copy inside in both (95% and 86%). Worms: watching 4% to 16% (absolute 0.004 to
0.014), poke-trained 76% to 97%. All three pools of brain 0 (added after the second review): watching
15.5%, 28.8% and 11.4% (absolute 0.0085, 0.0147, 0.0070), stitched 16.6%, 13.5% and 18.8%, poke-trained
inside in all three. **Roughly as expected**: on the full worm test this network sits at or just above
the top of the worm range for watching (4 of 8 values above the worms' 16%, one well above), its
absolute watching agreement is mostly inside the worms' range, and a copy that learns from pokes
passes, as in worms. The share is not inflated by the network's lower individuals' agreement (0.051 to
0.062, against 0.087 to 0.121 in worms): the absolute values tell the same story. An earlier version
called this "the first artificial network in the project" to do this; DGSM (round 1) gave 19% and 18%,
so that claim rests on a few points and is withdrawn.

**What the ladder says, in one paragraph (rewritten after the second review).** Artificial networks can
be made roughly as hard to copy by watching as a worm on the full test, and at the same time brought to
within about a fifth of the worm on average over five measured properties, but only by combining
strong slow background drives that no recording sees, some links silent at rest, many units that sit
quiet unless strongly driven, individuals that differ far more than in our default lab, and longer
pokes; no single ingredient does it, and several trade off against each other. The search that found
this setting was run the same night, round after round, with each round designed after seeing the
last, so the setting is a description of what is sufficient in this family, not an estimate of what the
worm has. Two worm properties remain unmatched: the tiring of a neuron's response to repeated
stimulation, and (an exploratory observation on worms) a spread that depends on the worm's main
resting pattern. What the worm actually has among these ingredients is a question for experiments:
recordings of the drive sources, repeated pokes at matched strength, and stimulation at several
strengths.

## Real wiring diagrams through the worm measurements (pre-registered 6 Nov 2026)

Every artificial network so far had random wiring. Here the lab's tanh dynamics run on two real
connectomes (`scripts/run_wired.py`):

- **worm-wired**: the worm's own wiring (Kunert et al. 2014: 279 neurons, chemical synapse counts
  signed by each presynaptic neuron's reversal potential, plus gap junctions as symmetric excitatory
  links), each neuron's class from its name (left/right pooled), as in the atlas;
- **fly-wired**: the fly visual system connectome bundled with flyvis (Lappalainen et al. 2024;
  fib25/fib19, 65 cell types, signed synapse counts with their column offsets), expanded over a patch
  of 19 columns (hexagonal radius 2), each cell type a class. (The trained flyvis models could not be
  used: their download from Google Drive is blocked from both the sandbox and the laptop.)
- **controls**: the same networks with their weights reassigned to random pairs (same number of
  links and same weights; "shuffled").

Each network is scaled to spectral radius 1.3, recorded like the atlas (113 individuals, sigma 0.3,
half the units seen, 30% never, a poke every 30 s from frame 230, held 4 frames), with and without
shared slow drives (25%), and measured on the ladder's six axes at class level; the full ruler is
run on pool 0 for the worm-wired and fly-wired networks without drives.
*Predictions:* (1) real wiring alone does not make a network worm-like on watching: watching share at
least 1.3 for both, without drives; (2) real and shuffled wiring differ by less than 0.3 in watching
share. *Decision:* each prediction judged separately; a real-wired network at or below 0.8 without
drives would mean the wiring itself carries part of the worm's resistance to watching.

**Result (`docs/figures/wired_fingerprints.csv`): unusable as designed, stopped after five of the
eight runs.** Individuals' echoes do not agree with each other in any real-wired run (reliability:
worm-wired 0.004 without drives and 0.003 with; fly-wired 0.0007; shuffled worm-wired 0.012 and
0.005), so the watching shares (6.3, -1.1, 3.8, 1.7, -1.9) are ratios over nothing and no prediction
can be judged. Diagnosis: scaled to spectral radius 1.3, the worm wiring's mean total input per
neuron is 0.74 against 3.4 in the lab's random networks, because 98% of its signed links are
excitatory (the diagram marks only GABAergic synapses as inhibitory), so one coherent excitatory mode
sets the radius and every other link ends up tiny; pokes barely spread (echo breadth 0.026). The
fly patch is better balanced (a third inhibitory; mean input 1.44), but a poke to one of 1,203 cells
pooled into 65 types moves no type measurably (echo breadth 0.0). Putting a real wiring diagram into
these dynamics is a modelling problem of its own (signs, scaling, which units count as a class); the
project's existing Kunert et al. model (wiring plus textbook physiology) is the better starting
point and is left for a separate design. The ruler runs were stopped before finishing.

**Replication of the worm state dependence (pre-registered 6 Nov 2026, before looking).** The
sign-aligned PC1 test found state-dependent spread in the wild-type worms after the reviewer had seen
it. Replication sample: the 18 unc-31 worms of the atlas (reduced neuropeptide release, recorded the
same way), never used in any state test. Same code and sign rule (`run_week1.py b2-pc1-unc31`).
Positive control that the first one lacked: a network whose slow drives both add to activity (share
0.25, so the first component tracks them) and scale each unit's recurrent input by (1 + 1.0 x drive),
so the same poke must spread differently in different states (round 1 base wiring, brain 0).
*Predictions:* the control shows state dependence (sign-flip p < 0.05); the unc-31 worms show it too
(median below 0, p < 0.05). *Decision:* if the control fails, the test is declared unable to detect
state dependence in these networks and the worm result stays unreplicated whatever unc-31 shows; if the
control passes, unc-31 p < 0.05 is a replication, p > 0.05 a failure to replicate (with 18 worms, a
weak test, stated now).

**Replication result (`docs/figures/b2_pc1_aligned_lab_control.txt`, `b2_pc1_aligned_unc31.txt`).**
Positive control: -0.019 [-0.049, -0.000], p = 0.046, **passes** (barely: the test is not very
sensitive in these networks). unc-31 worms (15 of 18 usable, 13 stimulated classes): -0.080 [-0.106,
+0.001], p = 0.033, echo size high/low 0.84. **Replicated by the pre-registered rule**: in a second set
of worms never used in any state test, the pattern of a poke's spread differs depending on where the
worm sits along its main resting pattern, by more than in the network built to show it. Caveats: 15
worms and 13 classes; a different strain (reduced neuropeptide release); and with AVA as the state
signal no dependence was detected in wild type, so the worm's main resting pattern is not simply its
reversal state. The worm's slow background state changes where its pokes go; among our networks, only the one
built to do this shows it (the plain and drives-only networks give 0.000 and -0.018, not
significant), and less strongly than the worms. The ladder's best-fitting networks have not yet been
put through this test.

**The ladder's best network through the state test (pre-registered 6 Nov 2026).** Round 9's most
stable setting (drives 0.4, silent links 0.75, spread 0.15, quiet 0.3, sigma 0.8, hold 6), brains 0
and 1, through the same sign-aligned state test (`run_week1.py b2-pc1-fit9`). *Prediction:* no state
dependence (p > 0.05 in both brains), because its drives only add to activity. If so, state-dependent
spread is a worm property that even the closest network here lacks.

**Result (`docs/figures/b2_pc1_aligned_lab_fit9_seed0.txt`, `..._seed1.txt`).** Brain 0: -0.031
[-0.048, -0.010], p = 0.0008; brain 1: -0.011 [-0.031, +0.004], p = 0.12. **Prediction refuted**: the
best-fitting network shows state-dependent spread in one of its two brains, without anything built in
for it (its strong additive drives, with saturating and quiet units, can change how a poke travels).
So state dependence is not a worm property beyond the reach of these networks; the worms show it more
strongly (-0.049 and -0.080) and more consistently. The earlier sentence that only the network built to
have it shows it holds only for the networks tested before this one.

## Is the neighbour effect real activation? (pre-registered 6 Nov 2026)

The 5 Nov test found that a poked worm neuron's nearest neighbours respond more than expected
(about a third of the target's own response), contingent on the target; a measurement leak and
true activation of the neighbours both fit. They differ downstream: a truly activated neighbour
drives its own synaptic partners; a leak in the recording drives nothing. Specification
(`scripts/run_neighbour_partners.py`; positions, scaling s_z = 4, early 0 to 2 s and late 5 to
15 s windows, and within-pair residuals exactly as in the 5 Nov test; wiring at class level from
Kunert et al. 2014, a class's partners being the classes it makes a chemical synapse onto or
shares a gap junction with):

- for each stimulation with a positioned target, the nearest positioned, named neuron is the
  *neighbour*;
- excluded from everything below: the target's class, its partners, the neighbour's class, and
  any neuron among the three nearest to the target;
- *neighbour-partners*: the remaining neurons whose class is a partner of the neighbour's class;
- *control partners*: the same for up to three control neurons chosen at random among neurons
  ranked 11th or further from the target (not excluded, in the wiring diagram), minus any
  neighbour-partner;
- per stimulation: mean residual late response of neighbour-partners minus that of control
  partners; averaged within each worm, then over worms; 95% interval by resampling worms (2,000);
- *sham*: the same at onsets with no stimulation (10 per worm, a random named neuron as the
  "target"), as in the 5 Nov test.

*Prediction:* if the neighbour effect is real activation, neighbour-partners respond more than
control partners in the late window, more than in the sham.
*Decision:* real activation supported if the 95% interval of the late difference lies above 0
and that of (real minus sham) lies above 0; downstream silence (consistent with a leak) if the
late interval includes 0 and its upper end is below +0.02 resting SD; otherwise inconclusive.
The early window is reported beside it (a real downstream effect should be later than the
neighbour's own). Power caveat, stated before running: the expected effect is a fraction of the
neighbour's own excess (about 0.3 of the target's response), so an inconclusive result is likely.

**Result (6 Nov 2026; `docs/figures/neighbour_partners.txt`).** 2,251 stimulations in 106
worms (sham: 629 onsets). Late window (5 to 15 s): neighbour-partners minus control partners
-0.032 [-0.063, -0.002]; sham -0.021 [-0.056, +0.011]; real minus sham -0.011 [-0.055, +0.035].
Early window: -0.002 [-0.028, +0.026]; real minus sham +0.016 [-0.028, +0.061]. **Inconclusive by
the pre-registered rule**, and, as the independent review showed, **the design cannot detect what it
was built to detect**. Its positive control, run afterwards with the same machinery: the target's
own synaptic partners, whose activation is expected, against control partners. With the
pre-registered within-pair residuals, -0.006 [-0.027, +0.015]: nothing, because subtracting each
(target, responder) pair's mean removes any effect that is consistent for a target. On raw
responses the control is clearly seen, +0.067 [+0.036, +0.094]; but the neighbour test on raw
responses gives +0.002 [-0.069, +0.059], against an expected effect of about 0.02 (a third of the
control). So this test says nothing about whether the neighbour effect is real activation or a
leak; an earlier version of this paragraph said it "leans toward a leak", which the numbers do not
support. A test with power would need many more stimulations per target, or recordings in which
the light's reach can be measured directly.

## A transformer through the same test (pre-registered 6 Nov 2026)

Every artificial network tested so far is recurrent: units feed back on each other over time.
The networks behind today's language models are transformers: information flows forward through
layers, and sideways in time only through attention to earlier tokens. This pilot puts a small
transformer through the exact measurements of the ingredient ladder (`scripts/run_transformer_test.py`).

- *Task:* next-token prediction on a synthetic language: a hidden Markov chain with 8 sticky hidden
  states (stay probability 0.98) emitting 32 tokens, so a good model must keep track of a slow
  hidden state from context.
- *Network:* 4 layers, width 64, 4 heads, 128 hidden units per layer (GELU), causal attention over
  the last 64 tokens, no position embedding. Base model trained 3,000 steps.
- *Individuals:* 113 copies of the base model, each with 10% multiplicative weight noise and then
  200 steps of training on its own data, so units stay aligned across individuals (like neuron
  classes across worms) while each individual differs.
- *Neurons and time:* the 512 hidden units are the neurons; one token is one frame. Each individual
  reads its own 4,440-token stream (the atlas's 37 minutes at 2 Hz); recorded activity is each
  unit's value plus measurement noise of 0.1 of its SD; half the units are seen in each recording
  and 30% never, as in the lab.
- *Pokes:* from token 230, every 60 tokens, a random seen unit has 3 of its own SDs added for 4
  tokens (activation patching), all in the same pass, as in the lab.
- *Control:* the same with untrained weights (the base model before training, individuals by
  weight noise only).
- *Measures:* the ladder's six axes, computed by the same code.

*Two hypotheses, stated before running:* (H1) the transformer is like the other artificial
networks: watching share at least 1.3 (the lowest ladder variant without silent links or quiet
units). (H2) it is worm-like: watching share at most 0.8, because its activity is driven by the
token stream (a shared input no copy sees) and its causal flow is one-way across layers, which a
model fitted to how units follow each other in time cannot represent. *Decision:* H1 or H2 by
those thresholds for the trained transformer; between them, intermediate. The untrained control
shows how much of the result comes from training.

*Amendment before running (6 Nov):* timing showed 0.4 s per training step on this machine, so
113 individuals at 200 steps each would take about 2.5 hours; each individual is trained for 50
steps instead (learning rate unchanged). Nothing else changes.

**Result (6 Nov 2026; `docs/figures/transformer_test.csv`): unusable as designed.** The trained
transformer learned the language (loss 2.69 against 3.47 for guessing), but its individuals' echoes
do not agree with each other (reliability 0.001; untrained: -0.0001), and neither do two halves of
one individual's pokes (individuality 0.001), so the watching share (1.57) is a ratio over nothing
and neither hypothesis can be judged. A diagnostic (exploratory, noise-free twin runs on one trained
network, 12 units, 25 contexts each) shows why: the exact echo of a poke is fairly consistent across
contexts (mean correlation 0.41 at 3 SD, 0.43 at 10 SD), but tiny when averaged over the 15-token
window, 0.005 of a unit's SD at 3 SD and 0.019 at 10 SD, far below the 0.1 SD measurement noise and
the token-driven fluctuations. A single hidden unit held for 4 tokens barely moves a transformer.
This says the design was too weak, not that transformers resist watching.

*Amendment (pre-registered before the second run):* the same test with each poke held for the whole
30-token window at 10 SD (KICK_FR 30, KICK_SD 10), everything else unchanged. If individuals'
agreement is still below 0.05, the test is declared unusable for this architecture at this scale,
and no reading is made.

**Transformer, amended run (`docs/figures/transformer_test.csv`, `trained_kick10x30`): unusable.**
Individuals' agreement 0.011, below the 0.05 floor set in the amendment, so no reading is made: a
transformer of this size, poked one hidden unit at a time, does not give echoes reproducible enough
to judge with this ruler. A fair test needs a different unit of poking (for example a direction in
the residual stream) and is left for a separate, pre-registered design.

## Transformers, a programme (6 Nov 2026; plan in `docs/TRANSFORMER_PLAN.md`)

The two transformer pilots above were unusable. This programme fixes the design and asks the
project's questions of transformers in eleven phases (diagnostics, the worm test in token time, the
test in depth with known truth, training, scale, state dependence, silent links, tiring, real
language models if they can be downloaded, the interpretability bridge, review). Small transformers
are built and patched with `nematica/tlab.py`.

**Phase 0 (diagnostic, exploratory): which kind of poke gives a measurable echo?**
(`scripts/run_tlab_phase0.py`, `docs/figures/tlab_phase0.txt`.) Exact echoes from paired runs, for
pokes to one MLP unit, one residual-stream dimension, a random residual direction, a principal
residual direction, and one attention head's gain, at two strengths and durations; reported: echo
size, consistency across contexts, evoked share (worms about 0.4). Chooses the design for phase 1.

*Phase 0 result.* Base model loss 2.77 (guessing: 3.47). Weak, brief pokes (3 SD for 4 tokens) are
invisible whatever is poked (evoked share -0.07 to -0.10): that is why both pilots failed. Held for 30
tokens at 10 SD: one MLP unit still invisible (-0.04); one attention head's gain inconsistent across
contexts (consistency 0.09 to 0.12); a residual-stream dimension 0.49 (consistency 0.88); a random
residual direction 0.42 (0.86); a principal residual direction 0.89 (0.92, far stronger than worms).
Chosen for phase 1: residual-stream dimensions as the units, pokes of 10 SD held 30 tokens. *(Corrected
after review 3: this originally said the choice was "the closest match to the worms' evoked share (about
0.4)"; the random direction, 0.42, was closer. The real reason was that single dimensions are
identifiable units that can be seen or unseen, like neurons, with a usable evoked share and high
consistency.)*

**Phases 3 and 4: training and size (pre-registered 6 Nov 2026).** The depth test of phase 2 (same
code, `run_tlab_depth.py --steps N --width D --layers L`). Phase 3, training: the default network
(width 64, 4 layers) at 300, 1,000 and 10,000 training steps, beside 0 and 3,000 from phase 2. Phase 4,
size: width 32 and 128 with 4 layers, and 2 and 8 layers with width 64, all at 3,000 steps.
*Predictions:* (3) in the residual basis, watching (all seen) falls as training proceeds: lower at
each later checkpoint in at least 3 of the 4 steps, and the MLP basis stays below 0.15 throughout;
(4) watching falls with width (32 above 64 above 128) and with depth (2 above 4 above 8). *Decision:*
each ordering supported if it holds exactly, otherwise reported as it falls.

**Phases 5, 6 and 9 in depth (pre-registered 6 Nov 2026).** Default network (width 64, 4 layers),
untrained and trained (3,000 steps), residual and MLP bases, 6 individuals, the same truth computation
as phase 2 (`scripts/run_tlab_more.py`).
- *Phase 5, state dependence with a known state.* The true effect matrix is computed separately for
  positions where the language's hidden state is each of its 8 states; state dependence = 1 minus the
  mean correlation between two states' matrices, against the same for two random halves of positions
  regardless of state (the noise floor). *Prediction:* in the trained network, effects depend on the
  hidden state well above the noise floor (state dissimilarity at least twice the floor, residual
  basis); less so untrained.
- *Phase 6, silent links.* For each true effect vector (one column of the matrix), the share of its
  squared size lying in the lower half of the later layers' natural principal components, against the
  share of natural variance there. *Prediction:* trained effects put more of their size in
  low-variance directions than untrained, in both bases.
- *Phase 9, attribution patching.* The gradient (Jacobian) of later units with respect to a first-block
  unit at natural activations, times that unit's SD, averaged over the same positions: the standard
  cheap stand-in for patching. Score: correlation with the truth, beside watching's. *Prediction:*
  attribution patching recovers the truth far better than watching (at least 0.8 in the residual
  basis, and above watching by at least 0.3 in both bases), so the failure is specific to inferring
  cause from correlations, not to linear summaries as such.

**Phase 8: real language models (pre-registered 6 Nov 2026).** The user opened network access to
Hugging Face, so the depth test runs on real models: Pythia-14m (6 layers, width 128, 512 MLP units
per layer) trained with 10 different seeds (EleutherAI's PolyPythia: `pythia-14m` and
`pythia-14m-seed1` to `seed9`), its training checkpoints (steps 0, 1,000, 8,000, 33,000 and the final
143,000), and Pythia-70m (width 512) with 3 seeds, residual basis only. *Amendment, 6 Nov 2026, after a first 70m run ran out of
memory and before any 70m result: 24 windows instead of 48.* Inputs: WikiText-103 test text
(kept locally, not redistributed), 48 windows of 256 tokens. Truth: one push of 1 SD per unit at
position 200 of every window (Pythia attends over the whole context, so one patched position per
window keeps patches from interacting), read at the same position in later layers. Watching: ridge
regression across all positions. Attribution patching: the Jacobian at natural activations, on 256
randomly chosen later units. Seeds are scored separately against their own truth (their units are not
aligned, so there is no ruler of individuals here) (`scripts/run_tlab_pythia.py`). *Exploratory additions, made after
the first three seeds showed attribution scores swinging from 0.14 to 0.88:* rank correlations, and in
the residual basis scores without the skip-connection entries (the same dimension in later layers,
which every method gets nearly for free); all matrices are saved (`results/tlab/pythia`).
*Predictions:* (1) final Pythia-14m, all seen: watching below 0.6 in the residual basis and below 0.2
in the MLP basis (median over seeds); (2) attribution patching above watching by at least 0.3 in the
residual basis; (3) over training, watching in the residual basis is lower at the final checkpoint than
at step 0; (4) Pythia-70m's watching (residual) is lower than Pythia-14m's.

*Results, phases 3, 5, 6, 8 and 9 (`docs/figures/tlab_depth.csv`, `tlab_more.csv`, `tlab_pythia.csv`;
the size sweep and 10,000 training steps are still running).*

Phase 3, training (small network, watching with all seen, residual / MLP): 0 steps 0.675 / 0.091; 300
steps 0.576 / 0.075; 1,000 steps 0.518 / 0.069; 3,000 steps 0.453 / 0.053. **Supported so far**: lower at
every later checkpoint, and the MLP basis stays below 0.15 throughout. *(Caveat added after review 3:
trained networks' individuals get 50 steps of fine-tuning on their own data and untrained ones none, so
the 0-step point differs in that too. "Base loss" in the CSV is the last training minibatch's loss,
not a held-out loss.)*

Phase 5, state dependence with a known state (dissimilarity of effect matrices between hidden states,
against the noise floor): trained 0.045 against 0.0016 (residual) and 0.32 against 0.014 (MLP), about
25 times the floor *(inflated: see the review 3 corrections below)*; untrained 0.004 against 0.0003 and 0.066 against 0.005. **Supported**: what a unit
does depends strongly on the language's hidden state, and training makes it ten times stronger in the
residual basis. This is the transformer counterpart of the worms' state-dependent spread, and it is
much stronger here.

Phase 6, silent links (share of each true effect lying in the lower half of natural principal
components, against the share of natural variance there): trained 0.089 against 0.002 (residual) and
0.132 against 0.018 (MLP); untrained 0.041 against 0.0001 and 0.125 against 0.0009. **Supported** in the residual basis; in the MLP basis 0.132 against 0.125 is a tie with no noise
estimate. Effects reach directions that natural activity hardly uses, 7 to 400 times more than their
share of natural variance. *(Corrected after review 3: this said "training increases it in the
residual basis"; the share itself rises, 0.041 to 0.089, but relative to natural variance it falls,
about 410 times untrained against 44 times trained, because training spreads natural variance into
those directions too.)*

Phase 9, attribution patching (correlation with the truth, beside watching): trained 0.999 against
0.467 (residual) and 0.991 against 0.055 (MLP); untrained 0.9997 against 0.676 and 0.996 against 0.093.
**Supported** in these small networks: the gradient recovers the truth almost perfectly where
correlations fail.

Phase 8, real language models. Pythia-14m, 10 seeds (median and range): watching, all seen, residual
0.69 (0.63 to 0.75) and MLP 0.47 (0.43 to 0.50); half seen 0.60 and 0.41; residual without the
skip-connection entries (exploratory; `watch_all_offdiag`, all later units) 0.59; attribution patching residual 0.33 (0.14 to 0.88) and MLP 0.69 (0.39 to
0.88); by rank, residual 0.51 and MLP 0.76. Training checkpoints (seed 0, residual / MLP watching): step 0
0.94 / 0.74; 1,000 0.86 / 0.70; 8,000 0.79 / 0.62; 33,000 0.74 / 0.48; final 0.71 / 0.45 (attribution
0.99 falling to 0.88; affected by the same artifact, rerun under way). Verdicts: (1) **refuted**: a real language model is more readable from its
correlations than predicted (0.69 and 0.47, not below 0.6 and 0.2), and far more than the small
trained transformers (0.45 and 0.05); (2) **refuted as first run, withdrawn pending rerun**: attribution
patching was not 0.3 above watching and looked unreliable from seed to seed. *Correction after review 3:
the failure sat entirely in the last two layers (layers 1 to 3 scored 0.94 to 0.97 in every seed), and
it is a software artifact: PyTorch's fused attention ("sdpa") returned wrong float32 gradients on CPU in
those layers (a gradient size of 22 where float64 and the plain attention code both give 1.02). Rerun
with plain attention under way (`tlab_pythia_v2.csv`); this verdict will be replaced by the rerun's;* (3)
**supported**: watching falls steadily through training, from near-perfect at initialisation (0.94) to
0.71, and in the MLP basis from 0.74 to 0.45; (4) **supported**: Pythia-70m, 3 seeds, residual
watching 0.54 (0.538 to 0.545; half seen 0.49 to 0.51; without the skip entries 0.32), below every
Pythia-14m seed (0.63 to 0.75). *Caveat after review 3: Pythia-70m's watching was fit on 24 windows for
512 regressors, against 48 windows for 128 in Pythia-14m, a handicap; rerun on 48 windows under way.*
Unplanned observation (exploratory measures): in Pythia-70m attribution patching is high and stable
(0.95 to 0.96; by rank, exploratory, 0.90; without the skip entries, exploratory, 0.91 against
watching's 0.32).

**Phase 8 rerun after review 3 (`docs/figures/tlab_pythia_v2.csv`; plain attention, attribution on every
window, per-layer scores).** Pythia-14m, 10 seeds: attribution patching, residual basis, median 0.994
(0.993 to 0.997; every later layer 0.98 or more, overshoot 0.99 to 1.00), MLP basis 0.998; watching
0.69 (0.63 to 0.75) and 0.47. Prediction (2), attribution above watching by at least 0.3 in the
residual basis: 0.994 - 0.693 = 0.30, **supported, at the threshold** (it replaces the withdrawn
"refuted"). Checkpoints (seed 0, residual / MLP watching; attribution 0.997 to 0.999 throughout):
step 0 0.94 / 0.74; 1,000 0.86 / 0.70; 8,000 0.79 / 0.62; 33,000 0.74 / 0.48; final 0.71 / 0.45. (3)
unchanged: **supported**. Pythia-70m on 48 windows (the review's equal-data check), seed 0: watching
0.61 (24 windows: 0.54), without skip entries 0.41 (14m: 0.53 to 0.65); attribution 0.998. So
prediction (4) still holds on equal data for seed 0, below every Pythia-14m seed; seeds 1 and 2 are
running.

Reading so far (rewritten after review 3; the first version overclaimed in four places, listed in the
corrections below). Training lowers how well correlations reflect cause and effect, in the small
networks (one base seed) and in Pythia-14m's checkpoints (one seed): from 0.94 at initialisation to 0.71
in Pythia, and from 0.68 to 0.45 in the small networks, whose correlations are far from perfect even
untrained. Training also makes effects depend more on the language's hidden state (on a measure that is
not the worms' own; the worms' own test, phase 5b, finds nothing in the transformer). The gradient
shortcut works almost perfectly in the small networks; in Pythia its apparent failure was a software
artifact, being rerun. Whether larger models are less readable is not settled yet: the comparisons
mix in skip-connection entries whose weight changes with width, and Pythia-70m had half the data;
across families the claim already fails (Pythia-14m, width 128, 0.69, against the small width-128
network's 0.31).

**Phase 7 result.** From phase 1's tiring axis: the trained transformer does not tire (-0.002;
untrained 0.000; worms -0.42), as expected: nothing in it changes with use within a context.

**Phase 5b, the worms' own state test on the transformer (pre-registered 6 Nov 2026).** The
sign-aligned first-component state test (`run_week1.py`'s B2 machinery) on phase 1's recordings, trained
and untrained (`scripts/run_tlab_state.py`). *Prediction:* state dependence in the trained transformer
(p < 0.05, median below 0), stronger than in the worms (-0.049); none in the untrained.

*Result (`docs/figures/b2_pc1_aligned_transformer_*.txt`).* Trained: -0.001 [-0.008, +0.005], p = 0.39,
no detectable state dependence; untrained: -0.007 [-0.009, -0.006], p < 0.0001 (tiny but very consistent,
because untrained individuals are nearly identical). **Refuted, in the opposite direction.** Phase 5
found strong dependence on the language's true hidden state in the same trained network, so this test,
which takes the strongest resting pattern as the state, does not see the transformer's real state. A
hypothesis for the worms (not tested there; labelled as such after review 3): their state-dependent
spread is dependence on their main resting pattern, one kind of state, and a test built on the main
resting pattern can miss other kinds.

**Phase 1: the worm test in token time (pre-registered 6 Nov 2026).** The trained base model (HMM
language); units are the residual-stream dimensions after each of the 4 blocks (256 units, each its own
class); individuals are 113 copies with 10% multiplicative weight noise and 50 steps of training on
their own data; each reads its own 4,440-token stream; recorded activity is each unit's value plus
measurement noise of 0.1 of its SD; half the units seen per recording and 30% never; pokes from token
230, every 60 tokens, to a random seen unit, 10 SD held 30 tokens (`run_tlab_phase1.py`). Measured on
the ladder's six axes, then the full ruler on pool 0. Untrained control: the same with untrained
weights. *Prediction:* the trained transformer is copyable by watching like the recurrent networks
(cheap watching share at least 1.3; ruler share at least 40%), because its token-to-token dynamics run
through attention to the token stream, which a lagged linear model of the units can follow.
*Decision:* by those thresholds; between them (or at or below 0.8 and 16%), it is reported as
intermediate (or worm-like). If individuals agree below 0.05 the test is unusable.

*Phase 1 result, six axes (`docs/figures/tlab_phase1.csv`; the full ruler is pending: it ran out of
memory beside other jobs).* Trained: watching share -0.17, echo breadth 0.13, tiring -0.002, rest
dimensionality 0.51, individuality 0.087, reliability 0.38, evoked share 0.54. Untrained: -0.002, 0.011,
0.000, 0.36, 0.028, 0.84, 0.83. Worms: 0.61, 0.085, -0.42, 0.43, 0.089, 0.094, 0.42. **The prediction is
refuted, in the opposite direction**: the trained transformer is not copyable by watching at all
(watching share -0.17, below zero, below the worms' 0.61 and far below the recurrent networks' 1.3 or
more), although its individuals agree with each other (0.38) and its pokes stand out (0.54). So is the
untrained one. Reading: in a transformer a poke's effect lands on later layers within the same token,
and a model of how activity follows activity from one token to the next cannot see that kind of cause
and effect at all; phase 2 measures it directly in depth. On other axes the trained transformer lands close
to the worms: individuality 0.087 against 0.089, resting structure 0.51 against 0.43. *(Qualified after
review 3: individuality depends on the 10% weight noise chosen to make individuals, so the match in
that axis is set by a design choice, not found.)* It does
not tire (-0.002 against the worms' -0.42).

**Phase 2: the test in depth, with known truth (pre-registered 6 Nov 2026).** In a transformer, most
cause and effect runs through depth within one forward pass, where exact intervention effects are
known. True effect matrix: the change in each later-layer unit when a first-block unit is pushed by
one natural SD (paired runs, averaged over 24 contexts x 4 positions spaced beyond one layer's 64-token attention span; *corrected after review 3: across layers the span
compounds, so patches 70 tokens apart can interact weakly in later layers; this was first stated as
"patches cannot affect each other"*; changed from "12 contexts x 24 positions" before any run finished, for speed). Watching estimate: ridge
regression of later-layer units on first-block units across natural activations. Score: correlation
of the two over all pairs, with every first-block unit seen or a random half seen (unseen units are
then unknown confounders, as unrecorded neurons are in worms); reference: two individuals' true
matrices against each other. Two bases: residual-stream dimensions, and MLP hidden units. Trained
(HMM language, 3,000 steps; individuals: 10% weight noise then 50 steps of training) and untrained;
6 individuals each (`scripts/run_tlab_depth.py`). For comparison, the lab's recurrent base network
scored the same way on its own truth (time-lagged linear watcher against true kick responses).
*Predictions:* (1) residual basis, all seen: watching at least 0.8 (the residual stream is additive and
close to linear); (2) half seen: lower than all seen in every condition, but at least 0.4; (3) MLP basis
lower than residual basis in both seen conditions (gated units, the transformer's version of silent
links); (4) trained lower than untrained in the MLP basis.

*Phase 2 result (`docs/figures/tlab_depth.csv`).* Correlation of the watching estimate with the true
effects, every first-block unit seen / half seen (individuals' true matrices agree at 0.95 to 0.998):

| Network | Basis | All seen | Half seen |
|---|---|---|---|
| transformer, untrained | residual stream | 0.675 | 0.447 |
| transformer, trained | residual stream | 0.453 | 0.393 |
| transformer, untrained | MLP units | 0.091 | 0.069 |
| transformer, trained | MLP units | 0.053 | 0.050 |
| lab recurrent network (time-lagged watcher) | units | 0.690 | 0.263 |

(1) **Refuted**: even with every unit seen, correlations recover 0.68 of the residual stream's true
effects untrained and 0.45 trained, not 0.8. (2) Half seen is lower in every condition, as predicted,
but not always above 0.4 (trained residual 0.39; MLP far below): partly refuted. (3) **Supported, and
by far**: in the MLP basis correlations recover almost nothing (0.05 to 0.09). (4) **Supported**:
training lowers it further (0.091 to 0.053; in the residual basis too, 0.675 to 0.453). So in
transformers, as in worms and unlike the recurrent lab networks with everything recorded, watching
recovers little of cause and effect, and training makes it worse; the units that compute (MLP neurons)
are the ones whose correlations say least about their effects. Caveat: individuals here differ very
little (their truths agree at 0.95 to 0.998), so this is a test against truth, not against a ruler of
individual variation.

**Review 3: independent review of the transformer programme (6 Nov 2026).** A separate agent that had
not run the work checked every number against the files, every verdict against its decision rule, the
code, and the prose. All README numbers it checked matched the files. Its findings, and what was done:
1. *The lab recurrent row of the phase 2 table was missing from `tlab_depth.csv`* (overwritten by a later
   job that rewrote the file). Fixed the cause: `run_tlab_depth.py` now re-reads the file before writing;
   the row is being regenerated.
2. *Phase 5's noise floor was too low:* it compared random halves (about 96 samples each) while state
   matrices use about 24, so "25 times the floor" was inflated; sticky states were also confused with
   contexts. Rerun with floors from groups of the same size, and with labels shuffled across whole
   contexts (`tlab_more_v2.csv`).
3. *Pythia-14m's attribution failure was confined to its last two layers.* Checking this found a
   software artifact (wrong float32 gradients from PyTorch's fused attention on CPU; checked against
   float64 and the plain attention code). Rerun with plain attention, all windows, per-layer scores
   (`tlab_pythia_v2.csv`).
4. *Comparisons across sizes were confounded* by skip-connection entries (38 to 58% of the truth's
   energy, weighted differently at each width) and by Pythia-70m's 24 windows. All small-network
   configurations are being rerun with a score without skip entries (`watch_offdiag`) and their matrices
   saved; Pythia-70m is being rerun on 48 windows.
5. *Overclaims, corrected in place and marked:* "at initialisation correlations reflect cause and effect
   almost perfectly" (true only of Pythia); "training is what makes these networks hard to read" (one
   seed each); "larger models are less readable" (confounded, and contradicted across families);
   "two properties the worms share" (the worms' own state test finds nothing in the transformer, and
   phase 6 has no worm counterpart); phase 1's "about zero" (it is -0.17) and "strikingly worm-like"
   individuality (set by the chosen weight noise); phase 5b's lesson for the worms (now labelled a
   hypothesis); phase 0's stated reason for the design; phase 2's "patches cannot affect each other".
6. *Smaller points:* phase 6's MLP result is a tie and its "training increases it" was wrong relative
   to natural variance; phase 3's untrained point lacks the 50-step fine-tune the trained points get;
   "base loss" is a training minibatch's loss; the phase 4 decision rule did not name a basis (the
   residual basis is taken as primary, the MLP basis reported beside it); the 2-versus-4-layer result
   is a tie; exploratory measures are now labelled where reported, and the 70m window change is marked
   as a dated amendment.

## Is it the neuron or the tool that tires? (pre-registered 6 Nov 2026)

The synthesis (`docs/DIFFERENCES.md`) leaves two differences between worms and every artificial
network built here; one is that a worm neuron answers about a quarter less when poked again (test B1).
That matters for the project's question only if the neuron tires, not the light-gated channel used to
poke it. The atlas can separate the two without new experiments: neurons are also driven *without
light on them*, when another neuron is poked and activates them through the network. If use tires the
neuron, a neuron recently driven that way should answer its own first direct poke less; if only the
channel tires, being driven without light should not matter. Written before computing anything below;
`scripts/run_tiring_source.py`.

**Data.** The 113 wild-type atlas worms; definitions of the response (mean over 0 to 15 s after onset
minus the 10 s before, in units of the neuron's SD over unpoked frames), of valid neurons and of
stimulations exactly as in test B1 (`run_week1.py`).

**Units of analysis.** Every direct stimulation of a valid neuron k at frame f with a finite, positive
own response a. Covariates, from the window of 600 frames (5 min) before f, counting only stimulations
whose own 15 s response window ends before f:
- *direct before*: k itself was stimulated in the window (1 or 0);
- *driven*: the largest response of k to a stimulation of another neuron in the window (not of k's
  class, and neither neuron among the other's three nearest positioned neurons, positions and
  z scaling 4 as in the neighbour tests, so that no light could have reached k; *amended before
  running: first written one-way, "the stimulated neuron not among the three nearest to k"*), k counted as driven
  if that largest response is at least 1.0 SD and as not driven if it is below 0.5 SD; stimulations
  between 0.5 and 1.0 are left out of the primary test; at least one stimulation of another neuron in
  the window is required either way, so both groups follow a poke elsewhere;
- *order*: f divided by the recording's length; *pre level*: k's mean over the 10 s before f, in SD
  units relative to its unpoked mean.

**Model.** log a regressed on direct before, driven, order and pre level, with a fixed effect for
k's class (only classes with at least one driven and one not-driven stimulation contribute to the
driven coefficient); 90% interval of each coefficient by resampling worms (2,000); p for driven by
shuffling driven labels within class (5,000).

*Positive control:* the direct-before coefficient must be below 0 with its 90% interval below 0 (the
B1 effect, about -0.3, recovered by this model); otherwise the test is declared unable to see tiring
and no reading is made.
*Prediction:* none is favoured; the two outcomes answer the question either way.
*Decision:* **activity tires the neuron** if the driven coefficient's 90% interval lies below 0 and
p < 0.05; **no detectable tiring from activity alone** (the channel, or something else about light, is
the likelier source) if the interval includes 0 and its lower end is above -0.10 (about 10% smaller
responses, a third of the direct effect); otherwise inconclusive. Sensitivity (reported, not
decisive): the largest indirect response as a continuous covariate instead of the two groups; a 2 min
window. Power caveat, stated before running: indirect responses are usually much smaller than direct
ones, so even a real effect may be small.

**Result (6 Nov 2026; `docs/figures/tiring_source.txt`).** 104 worms, 2,914 direct stimulations
(662 after being driven, 1,401 not driven, 212 after a direct poke). Positive control passes: a
direct poke in the previous 5 min lowers the next own response, -0.38 [-0.57, -0.23] in log units
(about a third smaller), the B1 effect recovered. The test: being driven by another neuron's poke
beforehand goes with a *larger* own response, +0.51 [+0.39, +0.60] (within-class shuffle p = 1.0 for
an effect below 0). **Inconclusive by the pre-registered rule** (the interval lies above 0, a case the
rule did not foresee), and the opposite of tiring by activity. Sensitivity: continuous drive +0.20
[+0.13, +0.26]; 2 min window +0.38 [+0.24, +0.51], direct -0.67 [-1.06, -0.31].

*Exploratory, after seeing that result.* A positive link is what a neuron's lasting responsiveness
would produce (a well-tracked or strongly expressing neuron answers every poke more), so k's largest
response to other neurons' pokes in the 5 min *after* its own was added as a control. The two are
nearly symmetric: per SD of drive, +0.18 before and +0.16 after; before minus after +0.02 [-0.06,
+0.11]. Tiring by activity would make the history matter more than the future, in the negative
direction; it does not, within about -0.06 per SD of drive. A direct poke costs about -0.19 per SD of
the neuron's own response (-0.38 over a typical 2 SD response). *(Review 4: the "after" control is not a
valid null, since a neuron that tires would also answer less to later pokes; and the "typical 2 SD" is
not in any output. Both sentences are withdrawn as evidence. The -0.38 is the uncorrected B1-like
effect, not B1's corrected -0.28.)*

*Exploratory refit after review 4* (`tiring_source.txt`, last line): comparing each neuron only with
itself (each worm's neuron its own fixed effect; 1,007 stimulations of neurons poked at least twice),
with the number of other pokes in the window as a covariate: direct poke before -0.56 [90%: -0.74,
-0.41]; **being driven by other neurons, per SD of drive, -0.10 [-0.17, -0.03]**; other pokes +0.015
[-0.013, +0.044]. Within a neuron, being driven without light *does* go with a smaller next response.

**Reading (corrected after review 4; the first reading said "being active does not detectably tire a
worm neuron; being lit does").** By the pre-registered rule the test is inconclusive. Its positive
coefficient came from comparing different neurons, some more responsive than others; compared with
itself, a neuron recently driven by other neurons answers less, about a sixth as much per SD of drive
as after being lit directly. So activity itself may tire worm neurons. Whether the larger drop after a
direct poke is the neuron or the light-gated channel stays open.

## Do human cortical responses tire? (pre-registered 6 Nov 2026)

The worm tiring may belong to the light-gated channel (section above). The human recordings were poked
electrically, with no channel, and in blocks: each stimulated pair (an ordered pair of electrodes, so
the two polarities are separate) gets about 10 single pulses, one every 5 s, in a row (read from the
events files only). If cortical responses fall across a block, use-dependence is a property of real
brains that the artificial networks lack; if not, the worm result is likely the tool.

**Re-extraction** (`scripts/ccep_extract_v2.py`, streamed one recording at a time in the cloud
workspace with `scripts/ccep_stream.py --extractor ccep_extract_v2`): the stimulation artefact is
replaced by a straight line from 2 ms before to 9 ms after each pulse in the raw signal, before any
filtering (the fix the human section's caveat asked for); per-pulse response strengths are kept
(root mean square from 10 to 100 ms after the same referencing and baseline as before; pre-pulse
strength from -50 to -10 ms). Written before any recording was re-extracted. *Amendment, before any
response was computed: the cloud workspace has less memory than the laptop, so the signal is now
filtered in 120 s pieces with 10 s of padding for the notches (the low-pass was already done in
pieces), and the common average for the watching statistics is taken per segment; numerically the same
up to edge effects of order e^-50. Downloads use curl.*

**Test.** Units: (recording, block, responding channel). A block is a run of consecutive pulses at the
same ordered pair, at least 4 valid pulses. Responding channel: not one of the pair, more than 10 mm
from both stimulated electrodes, and mean over the block of log(response / pre-pulse strength) at least
log 2 (selection on the block mean, which does not favour any order). Per unit: the least-squares slope
of log response strength on pulse number (0, 1, 2, ...), and, as the worm's analogue, log response of
pulse 2 minus pulse 1. Controls, the same slopes for log pre-pulse strength (slow change in ongoing
activity) and for log response in non-responding channels (more than 10 mm away, block-mean ratio
below log 1.2). Per patient: median over units; across patients: median, 95% interval by resampling
patients (2,000), and a sign test.
*Prediction:* none favoured.
*Decision:* **human responses tire** if the 95% interval of the patients' median slope lies below 0
and that of (slope minus the pre-pulse slope, per unit, then the same aggregation) also lies below 0;
**no detectable tiring** if the slope's interval includes 0 and its lower end is above -0.01 per pulse
(about 9% over a block of 10); otherwise inconclusive. Pulse 2 minus pulse 1 is reported beside it.
Caveats stated before running: the gap here is 5 s (minutes in the worm), and electrical pulses
activate axons as well as cell bodies.

Analysis code: `scripts/run_ccep_tiring.py`, written and checked for counts only (`--dry`) before any
statistic was computed.

**Result (6 Nov 2026; `docs/figures/ccep_tiring.txt`).** All 117 recordings re-extracted (none failed),
74 patients, 186,466 responding units, 36,619 non-responding. Slope of log response per pulse (primary):
median over patients +0.0004 [95%: -0.0008, +0.0015], 36 of 74 patients below 0 (sign test p = 0.91).
Slope minus the pre-pulse slope: +0.0012 [+0.0003, +0.0025]. Pulse 2 minus pulse 1: +0.011 [+0.003,
+0.018] (the second pulse is, if anything, slightly larger). Controls: pre-pulse slope -0.0008 [-0.0020,
+0.0011]; non-responding channels +0.0021 [+0.0002, +0.0034]. **No detectable tiring** by the
pre-registered rule: across a block of about 10 pulses the response changes by less than 1.5%, against
the worm's drop of about a quarter at the second poke.

**Reading (corrected after review 4; the first reading said the worm's drop "is most likely a property
of the light-gated tool" and that this "removes the strongest remaining candidate difference").** The
channels scored here are more than 10 mm from the pulse, so this measures the *network's* response, the
analogue of the worm's echo, not the stimulated tissue's own response (the worm's clear drop, -0.28, is
the stimulated neuron's own; the worm echo's drop was small, -0.04 [-0.19, +0.12] after noise
correction). Human network responses do not decline across about 10 pulses 5 s apart; the stimulated
tissue was not measured. Sensitivity (review 4): with stricter responders (ratio at least 4: 43,140
units; at least 8: 10,830) the slope stays near 0 (+0.0012 and +0.0017 per pulse). Relative to
non-responding channels, which drift up (+0.0021), responders fall about 0.0017 per pulse; and the
measure includes ongoing activity, which dilutes the evoked part. Some blocks are not independent
same-site runs (polarity reversals after 5 pulses; one run spans a 130 s gap). Caveats: the human gap is 5 s against minutes in the worm, electrical pulses also drive axons,
the patients have epilepsy, and the response window (10 to 100 ms) is an average over early and later
components.

**Also rerun:** the original human test (`scripts/run_ccep_test.py`, unchanged) on the clean extraction;
its numbers will be reported beside the first ones, which they supersede where they differ.

## The sparse, sustained echo: worms against artificial networks, one measure (pre-registered 6 Nov 2026)

One of the two candidate differences left (`docs/DIFFERENCES.md`): after a poke, a third of a real
worm's neuron classes never respond, and those that do keep responding; fitted worm models flicker
(earlier diagnostic, pool 1 only). Here the same three numbers are computed with the same code
(`nematica.bench.perturbational.event_matrices`, threshold 3 resting SD, the standard post-stimulus
window) on all 113 atlas worms and on the lab networks recorded like them, to see which ingredient,
if any, produces a worm-like echo (`scripts/run_echo_sparse.py`). Lab units are each their own class.

**Measures**, per system: (a) share of classes that ever respond in the window, median over pokes;
(b) median length of a response run (frames above threshold); (c) share of time steps where the set of
responding classes changes, median over pokes. **Systems:** worms; lab brain 0 with 40 individuals each
for base, D (slow drives), G (silent links), Q (quiet units, half the units held near the bottom of
their range), DG, DGQ, and round 9's best setting (drives 0.4, silent links 0.75, spread 0.15, quiet
0.3, individuals differing by 0.8, pokes held 6 frames).
*Predictions:* (1) quiet units are what make echoes sparse and sustained: Q, DGQ and the round 9 setting
are closer to the worm than base on (a) and (c); D and G are not. (2) No system is within 25% of the
worm on all three measures. *Decision:* each judged on the stated comparisons as they fall; "closer"
means a smaller absolute difference from the worm value.

**Result (6 Nov 2026; `docs/figures/echo_sparse.csv`).** Share of classes ever responding / median run
(mean) / share of steps where the responding set changes:

| System | Ever respond | Run, median (mean) | Set changes |
|---|---|---|---|
| Worms (3,516 pokes) | 0.65 | 3 (6.5) | 0.88 |
| Base network | 0.72 | 1 (1.9) | 0.92 |
| D, slow drives | 0.71 | 1 (2.4) | 0.97 |
| G, silent links | 0.74 | 1 (2.0) | 0.92 |
| Q, quiet units | 0.47 | 1 (1.2) | 0.65 |
| DG | 0.73 | 1 (2.5) | 0.97 |
| DGQ | 0.51 | 1 (1.8) | 0.83 |
| Round 9 best | 0.56 | 1 (2.3) | 0.92 |

(1) **Refuted**: quiet units make echoes sparser than the worm's (0.47 against 0.65), further from it than
the base network, and no ingredient makes responses last: every network's responses last one frame
(median), the worm's three. (2) **Supported**: no system is within 25% of the worm on all three.

*Exploratory, after that result:* the worm's activity is read through a calcium indicator whose signal
decays over about a second and a half, and the networks' is not. With the same decay applied to the
networks' traces (`--calcium`, `echo_sparse_calcium.csv`), their responses last as long as the worm's
(base 3 frames, mean 5.2; drives 4, mean 7.0; worm 3, mean 6.5), but more of their units cross the
threshold (0.78 to 0.89 against 0.65) and the responding set changes slightly more often (0.95 against
0.88). *First reading, withdrawn after review 4:* "the sustained half of the worm's echo is mostly the
indicator; the sparse half survives." The check filtered the networks' traces after measurement noise
was added (in worms, camera noise is added after the indicator), so filtered noise itself makes
multi-frame runs and changes the threshold; the 1.5 s decay was chosen after the result; only base and
D reached worm-like runs; and worm classes average their neurons while lab units are single. A matched
re-test is below.

*Matched re-test (exploratory, after review 4; `scripts/run_echo_matched.py`, `docs/figures/echo_matched.csv`).*
The indicator decay now acts on activity before measurement noise is added; lab units are averaged in
fixed random pairs into classes, as worm classes average left and right neurons; decays of 1, 1.5 and
3 s; two lab brains; 30 individuals each; 95% intervals by resampling individuals. Worms: ever respond
0.65 [0.64, 0.68], mean run 6.5 [6.2, 6.8] frames, set changes 0.87. Across all three decays and both
brains: base networks 0.71 to 0.78, runs 2.2 to 2.5; slow drives 0.73 to 0.79, runs 3.2 to 3.3; quiet
units 0.42 to 0.47, runs 1.3 to 1.4; drives, silent links and quiet units 0.49 to 0.52, runs 2.1 to 2.3;
round 9's setting 0.55 to 0.64, runs 2.9 to 3.2 (set changes 0.86 to 0.93). **Reading (replaces the
withdrawn one):** with a matched readout the indicator does not make the networks' responses last
(runs barely change from 1 to 3 s of decay, because the threshold scales with the smoothed
fluctuations too). **Persistence survives**: no network's responses last even half as long as the
worm's. **Sparseness does not**: round 9's setting (strong drives, silent links, 30% quiet units) reaches
the worm's share (0.58 to 0.64 against 0.65). Caveats: the worm stimulation's length was not matched to the lab pokes
(the lab holds pokes 2 to 3 s), and the worms' indicator may decay more slowly than 3 s.

**Review 4: independent review of the tiring, human, mouse and echo tests (6 Nov 2026).** All reported
numbers matched their files (one factual slip, the mouse T4 "none"), and every verdict followed its rule.
Its major findings changed the conclusions, and are applied above, marked:
1. The tiring-source test's "after" control was not a valid null; a within-neuron refit reverses the
   reading (activity does lower a neuron's next response). "Tiring was the tool" is withdrawn.
2. The human tiring test measured the network (channels beyond 10 mm), the analogue of the worm's echo,
   not of the stimulated neuron's own response, which is where the worm's clear drop is.
3. The mouse tiring test had no equivalence bound; its interval allows a 30% to 50% decline.
4. The echo calcium check filtered measurement noise as well as activity, and worm classes average
   their neurons while lab units are single; "sustained was the indicator" and "sparseness survives" are
   withdrawn pending a matched re-test (`scripts/run_echo_matched.py`).
5. The mouse watching checks were misdescribed and their code was not committed (now
   `run_touch_tests.py --explore`).
Minor: responder-threshold and block-definition sensitivities for the human test (stated above); the
blanking window ends 1 ms before the response window, so a sensitivity with the window from 15 ms will
be run on the third extraction; dated amendments; DIFFERENCES.md updated.

**What could make responses last? (pre-registered 6 Nov 2026, after the matched re-test).** Same
measures, matched readout (decay 1.5 s before noise), paired units, lab brain 0, base network and round
9's setting, 30 individuals each, one change at a time: (a) pokes held 8 or 16 frames instead of 4 (6
for round 9); (b) slower units, the leak per frame 0.25 or 0.1 instead of 0.5 (unit time constant 2 or 5
s instead of 1 s); (c) stronger recurrence, spectral radius 1.6 instead of 1.3 (base only).
*Predictions:* (1) slower units lengthen the mean run toward the worm's 6.5 frames, and at leak 0.1 reach
at least 5; (2) longer pokes lengthen runs less than slower units do; (3) stronger recurrence lengthens
runs but also widens echoes (ever respond up). *Decision:* as the numbers fall, each judged on its stated
comparison with the unchanged network (`scripts/run_echo_persist.py`, `docs/figures/echo_persist.csv`).

*Result (`docs/figures/echo_persist.csv`; mean run in frames, share ever responding, 95% intervals by
individuals).* Base network 2.5 / 0.76; pokes held 8 frames 2.5, 16 frames 2.7; leak 0.25 3.7 / 0.85;
leak 0.1 5.6 / 0.91; spectral radius 1.6 3.4 / 0.77. Round 9's setting 3.0 / 0.56; held 16 frames 3.3;
leak 0.25 4.4 / 0.61; **leak 0.1 6.8 [6.7, 7.1] / 0.62** (worm 6.5 [6.2, 6.8] / 0.65 [0.64, 0.68]; set
changes 0.91 against 0.87). (1) **Supported**: slower units lengthen responses toward the worm's, and at
a 5 s unit time constant the base network reaches 5.6 and round 9's setting the worm's own value. (2)
**Supported**: longer pokes barely lengthen them. (3) **Supported weakly**: stronger recurrence lengthens
them (3.4) and widens echoes only within the interval (0.77 against 0.76). **Reading:** the worm's
lasting echo is what slow units produce. The lab's default units settle in about a second, worm neurons
are graded and slow; give artificial units a time constant of a few seconds and, together with drives,
silent links and quiet units, a network's echo is as sparse and as lasting as a worm's. So this
candidate difference dissolves too: it is a property of slow units, not of biology as such.

**Slow units in the closest network (pre-registered 6 Nov 2026, after "What could make responses last?").**
If slower units are what the closest network lacks, adding them should not break the five properties it
already matches. Round 9's setting (drives 0.4, silent links 0.75, spread 0.15, 30% quiet units,
individuals differing by 0.8, pokes held 6 frames) on brains 0 and 1, with the leak per frame at 0.5
(unchanged), 0.25 and 0.1, measured on the six ladder axes by the ladder's own code
(`scripts/run_slow_units.py`; `run_ladder.py`'s round 9 code, deleted by mistake in an earlier commit,
restored unchanged). *Prediction:* at leak 0.1 the root-mean-square relative error over the five axes is
no more than 0.05 above the unchanged setting's, in both brains (persistence can be added without a
trade-off). *Decision:* as stated; otherwise a trade-off, reported axis by axis.

## Does the brain's state change where a pulse spreads in human cortex? (pre-registered 6 Nov 2026)

The worm's state-dependent spread replicated; mouse touch cortex leaned the same way but was
inconclusive. The human recordings repeat each pulse about 10 times at the same site, so the same test
can be run there. The per-pulse strengths saved so far cannot carry it (a noisier moment inflates the
strength of every channel unevenly), so a third extraction (`ccep_extract_v2.py` with
`NEMATICA_CCEP_V3=1`, everything else unchanged) also keeps each pulse's waveform from 10 to 100 ms
(256 Hz) and its **state**: each channel's log variance from 1 s to 50 ms before the pulse (common
average referenced). Written before that extraction ran; `scripts/run_ccep_state.py`.

**Test.** Blocks as in the tiring test (consecutive pulses at one ordered pair, at least 8 valid pulses
with a state). State of a pulse: the first principal component of the block's pulse-by-channel state
matrix (channels more than 10 mm from the pair), sign aligned so the mean loading is positive. High and
low: the upper and lower halves of the block's pulses by state. Response pattern of a group: the root
mean square, from 10 to 100 ms, of the group's *averaged* waveform, on channels more than 10 mm away
(averaging first removes most ongoing activity, unlike per-pulse strengths). S = Pearson correlation of
the log patterns of high and low, minus the mean of 200 random equal splits of the same block. Per
patient: median S over blocks; across patients: median, 95% interval (resampling patients, 2,000),
sign-flip p (10,000). *Positive control:* the same with the split made by pulse order (first half against
second half) must not differ from the random splits more than the state split does, or the null is
too generous. *Prediction:* S below 0 (state dependence, as in worms). *Decision:* supported if the
median is below 0 with sign-flip p < 0.05; none detected if the 95% interval includes 0 and its lower end
is above -0.02; otherwise inconclusive.

## Where the data runs out (2 Nov 2026)

Everything above that can be done with existing data has been tried at least once. What is
left needs data that does not exist yet, as far as we know. In order of what it would
unlock:

1. **Complete, fully identified recordings.** The artificial lab once said watching can be
   rescued only when every neuron is recorded (part C); part D (3 Nov) showed that was the
   zero-filling watcher, not the data: a stitched watcher comes close to poking in the lab,
   even scored through the worm pipeline, but stays far below it on real worms. So whether complete recordings would
   rescue watching in worms is open, and this is the data that would settle it. The atlas
   identifies a median of 72 neurons per worm (of 123 tracked, in a nervous system of 302).
   Needed: whole-brain
   recordings with every neuron identified, ideally in the same worms that are then poked,
   so a copy fitted by watching can be checked against pokes in the same animals.
2. **Repeated pokes of the same neurons in the same worm.** Worms have individual echoes,
   but the atlas rarely pokes one neuron twice in one animal, so no copy of one particular
   worm can be built or checked.
3. **Many more pokes per neuron, aimed by reliability.** About 160 or more worms per neuron
   for a reliable echo, against 22 in the atlas (test 2), and the artificial lab shows the
   ruler cannot certify copies of drive-dominated or highly individual species at atlas
   size. `docs/figures/poke_budget.csv` lists which neurons need the most.
4. **Pokes in freely moving worms, with the behavioural state recorded.** Nothing learned in
   one context transferred to the other (tests 3 and 4).
5. **Recordings of candidate drive sources.** The slow shared structure survives reduced
   neuropeptide release; what carries it (other neuromodulators, unrecorded neurons, the
   body's state) needs reporters for those sources.

One further step is possible without new data and is not done: a watching copy with
latent variables fitted properly over long windows. Part C's bound on such a model (0.48
under atlas-like recording) applied to the zero-filling watcher and no longer holds; part D
shows the simpler stitched watcher already comes close to poking in the lab but not in worms. A
latent state-space version (`fit_latent` in `scripts/run_ann_stitch.py`, fitted by EM with a
steady-state Kalman smoother) is written but has not been run.

## Beyond the worm: the same test in human brains (pre-registered 2 Nov 2026)

**Data.** The open CCEP ECoG dataset of van Blooijs et al. (2023; OpenNeuro ds004080, CC0):
74 epilepsy-surgery patients aged 4 to 51 with electrode grids on the cortex, recorded at
2048 Hz while pairs of electrodes were given single electrical pulses, one every 5 s
(about 390 pulses and 38 minutes in the smallest patient checked). Electrode positions
carry Destrieux atlas labels. Downloaded locally, never redistributed.

**The test, mapped from the worm.** Poking: the average response of every other electrode
to each stimulated pair (the cortico-cortical evoked potential, CCEP). Watching: the
activity between pulses, from 1 s after each pulse to the next. Individuals: the patients.
For each patient, a watching copy (a linear model of the between-pulse activity,
downsampled to 512 Hz, common-average referenced, stimulated and bad channels excluded) is
pulsed at the stimulated pair and its predicted response compared with the patient's own
measured responses. Score: correlation, across (stimulated pair, responding electrode),
of response amplitude in the 10 to 100 ms window. References scored on the same pairs:
(a) a distance-only model (amplitude falling with distance from the stimulated pair);
(b) other patients' measured responses, matched by Destrieux region pair (pokes from other
individuals); (c) the patient's own responses, split by odd and even pulses (the ceiling).

**Expectations, written before any data is downloaded.** An electrode grid records a tiny
fraction of the brain, so by the worm and artificial-lab results almost everything that
drives the recorded cortex goes unrecorded. Therefore: (1) the watching copy predicts the
patient's own responses no better than the distance-only model; in particular, for
responding electrodes more than 2 cm from the stimulated pair, its advantage over distance
has an interval that includes zero; (2) other patients' pokes, matched by region, predict
better than the watching copy (pokes beat watching across individuals, as in worms). If
the watching copy clearly beats distance far from the stimulated site, expectation (1) is
wrong, and recording a small part of a brain is less limiting than the worm suggests.

**Analysis details, fixed 3 Nov 2026 before any reduced human recording was looked at.**
Response strength of an electrode to a stimulated pair: root mean square of the average
response from 10 to 100 ms (sign-free, since a distance model cannot predict sign).
Scores are Spearman rank correlations across (stimulated pair, electrode), computed per
recording and averaged per patient; electrodes of the stimulated pair are excluded. Watching
copy: VAR(5) at 512 Hz from the between-pulse statistics, ridge 0.001 x the mean diagonal,
pulsed by setting the two stimulated electrodes to +1 and -1 for one sample and running
100 ms forward (sensitivity check: both +1). Distance model: 1 / distance to the nearer
stimulated electrode (MNI millimetres). Other patients: mean z-scored log response strength
for the same pair of Destrieux regions (stimulated region taken from the first electrode
of the pair), from all other patients, where at least 3 other patients cover that region
pair. Ceiling: odd against even pulses, Spearman. Far set: electrodes more than 20 mm from
both stimulated electrodes. Patient-level comparisons: paired differences with 95%
bootstrap intervals over patients. Patients with fewer than 10 stimulated pairs or a
ceiling below 0.2 are reported but left out of the comparisons.

**Plan.** All 117 recordings (about 289 GB) are streamed one at a time on a local machine
and reduced to small per-recording summaries (`scripts/ccep_stream.py`, `scripts/ccep_extract.py`),
then scored by `scripts/run_ccep_test.py`.

**Result, 4 Nov 2026, updated 5 Nov with the last recording (all 117 recordings, 74 patients;
`docs/figures/ccep_*`; reviewed independently on 116 recordings). The recording that failed to
download on 4 Nov (UMCU67, run 021704) downloaded on 5 Nov; with it, UMCU67 has 140 stimulated
pairs and is included, and the numbers barely move. Earlier looks: 100 recordings and 63
patients (`docs/figures/interim_100rec_ccep_*`), then 116 recordings and 73 patients. The scoring
code was last changed on 3 Nov, before any look, and was checked beforehand only on two of
patient 01's recordings. UMCU56's two recordings give identical numbers (probably the same data
stored twice); this does not change any patient-level score.** All 74 patients included.
Median Spearman across patients: ceiling 0.70; distance-only model 0.46; other patients' pokes by
region pair 0.37; watching copy 0.29 (same-sign pulse 0.15). Beyond 20 mm: distance 0.30, other
patients 0.23, watching 0.17.

Against the expectations. (1) Not falsified: the watching copy did not beat the distance-only
model, overall or beyond 20 mm. It did clearly worse: -0.161 (95% interval -0.177 to -0.144,
positive in 1 of 74 patients) overall and -0.119 (-0.138 to -0.099; 6 of 74) beyond 20 mm, so
the second clause as worded (an interval including zero) did not hold. A copy that does worse
than a distance rule does not by itself show that unrecorded drivers are the limit; it may also
reflect a crude linear copy (VAR(5) at 512 Hz is a 10 ms memory, linear, common-average
referenced). The watching copy is not uninformative: in the recordings the review checked it
reproduces the fall-off with distance (near/far amplitude ratio 4.2 against 4.9 measured) and
adds a little beyond distance (partial Spearman given distance about 0.16, positive in 27 of 28).
(2) Holds: other patients' region-matched pokes beat the watching copy, +0.059 (+0.040 to
+0.079; 56 of 74 patients); this predictor also encodes distance, since pairs in the same regions
lie close together.

**Caveat that limits every human number above.** The response strength (root mean square, 10 to
100 ms) includes a stimulus-locked part that is not brain activity: the review found that the
same measure 50 to 10 ms BEFORE the pulse falls with distance (median Spearman about 0.35 to
0.39), predicts the measured response (0.40 to 0.47, better than the watching copy) and repeats
from odd to even pulses, and that pulse-locked 50 Hz ringing at nearby electrodes decays like the
notch filter. The extraction filters the continuous record (zero-phase low-pass and notches)
before epoching, which spreads the stimulation artefact forward and backward in time, and volume
conduction adds to it. So the distance model and the ceiling are partly scoring artefact spread,
and the far-field comparison depends on how it is handled: scoring the response relative to the
pre-pulse level (log of post over pre RMS) leaves distance 0.078 and watching 0.063 beyond 20 mm.
Not pre-registered, exploratory (on the 116 recordings reviewed): distance beat other
patients' pokes (+0.101, +0.087 to +0.116; 71 of 73), which must not be read as a fact about human cortex. A post-hoc re-extraction that
blanks and interpolates a few milliseconds around each pulse before any filtering is needed
before any claim about human brains; it requires the raw recordings again.

**Rerun on the clean extraction (6 Nov 2026; `docs/figures/ccep_v2/`; pre-registered in "Do human cortical
responses tire?"; scoring code unchanged).** Stimulation artefact blanked from 2 ms before to 9 ms after
each pulse in the raw signal, before any filtering; all 117 recordings, 74 patients. The artefact's leak
is gone: the pre-pulse strength (-50 to -10 ms) now hardly follows distance (Spearman with 1/distance,
median over patients +0.055, against about 0.35 to 0.39 before; exploratory check,
`artifact_check.txt`), while the response still does (+0.41). Median Spearman across patients: ceiling
0.69; distance 0.45; other patients' pokes 0.35; watching copy 0.30 (same-sign pulse 0.13); beyond 20 mm
distance 0.27, others 0.22, watching 0.18. (1) Watching minus distance: -0.130 (95% interval -0.145 to
-0.115; positive in 1 of 74 patients); beyond 20 mm -0.087 (-0.105 to -0.069; 8 of 74). (2) Other
patients minus watching: +0.036 (+0.016 to +0.055; 50 of 74). **The first result stands on clean data**:
a linear watching copy of human cortex predicts its responses to pokes worse than distance alone, and
worse than other people's measured responses. The caveat above about the artefact no longer applies;
the one about a crude linear copy still does.

Disclosed deviations from the analysis details: patient scores are weighted by the number of
pairs (unweighted gives the same result); stimulated pairs with fewer than 4 pulses are dropped;
the watching VAR is rescaled when its spectral radius exceeds 0.999 (in every recording, a tiny
change); the watching copy's common average includes the stimulated channels, which it must
pulse; "others" is scored where at least 3 other patients cover the region pair (median coverage
96.5%; restricting all models to common pairs changes nothing material); coordinates are
fsaverage (MNI305), not plain MNI; the window is about 9.8 to 97.7 ms (epoch offset of 1.2 ms);
the ceiling is a 5-against-5 split without Spearman-Brown correction (about 0.82 corrected).

## Beyond the worm: mouse hippocampus (pre-registered 3 Nov 2026)

**Data.** The all-optical CA1 recordings of Bocchio, Vorobyev et al. (Cossart lab; Zenodo
11500028, CC BY 4.0): head-fixed mice on a treadmill, two-photon calcium imaging of hundreds
of CA1 neurons per session at about 8.4 frames per second. A session is 15,000 frames: the
first 10,000 untouched, then about 10 optogenetic stimulations of one identified
interneuron, 3 to 4 frames each, about 31 s apart. Running speed is recorded. Streamed
locally in one pass (`scripts/hippo_stream.py`), never redistributed. Before writing this, only
file names, array shapes and the small text files (stimulation frames, stimulated ROI number,
frame times) were looked at; no trace was opened.

**The test, mapped from the worm.** Poking: each recorded cell's mean change after the
interneuron is stimulated. Watching: the 10,000 untouched frames before the first
stimulation. Mouse neurons have no shared identities across animals, so each session is
its own individual, and the "other individuals" reference becomes a generic profile:
the mean response by distance from the stimulated cell, learned from all other sessions.

**Analysis, fixed before any trace is loaded** (`scripts/run_hippo_test.py`; checked only
on synthetic sessions with a known network, where watching reached 0.93 against a ceiling
of 0.97). Traces: F minus 0.7 times neuropil, slow drift removed (501-frame moving
average), z-scored on the watching period. Response to one stimulation: mean over the 25
frames (about 3 s) after the stimulation ends, minus the mean of the 17 frames before it.
The stimulated ROI number is read as an index into all ROIs, into the curated cells, or
through `old_cell_idx`; the reading under which that ROI responds most is used, and it must
be in the top 5% of responders or the session is excluded. Scored cells: curated cells (all ROIs when a session has no curation file),
minus the stimulated ROI and any ROI within 10 pixels of it. Models: (a) watching copy,
a VAR(1) fitted to the watching period (ridge 0.05 times the mean variance), the
stimulated cell driven by +1 for the stimulation's length, read in the same window;
(b) correlation with the stimulated cell during watching; (c) the watching copy after
regressing running speed (lags 0 to 8 frames) out of every trace; (d) the generic profile
from other sessions (distance deciles). Ceiling: odd against even stimulations. Score:
Spearman across scored cells. Included: at least 8 stimulations, 50 scored cells and a
ceiling of at least 0.1; all analysable sessions are also reported. Comparisons: paired
differences with 95% bootstrap intervals over sessions.

**Expectations.** A field of view in CA1 records a few hundred cells out of hundreds of
thousands, and CA1 is driven mostly from CA3 and entorhinal cortex, which are not
recorded. By the worm and artificial-lab results: (1) the watching copy reaches less than
half of the ceiling on average; (2) it does not beat the generic profile from other
sessions (the interval for watching minus generic includes zero or lies below it);
(3) regressing out the one recorded drive, running, changes the watching score little
(the interval for the change includes zero), because most of what drives the cells is not
recorded at all. If the watching copy reaches most of the ceiling here, expectation (1)
is wrong and, at least for the local effect of one interneuron, watching a few hundred
cells is enough.

**Follow-up, written 3 Nov 2026 before it was run (`run_hippo_test.py --multi`).** The
pre-registered rules leave out sessions in which 2 or 3 cells were stimulated together. The
follow-up includes them with the same analysis, except: every listed cell must be in the top
5% of responders (under one common reading of the indices); the watching copy is driven in
all of them at once; scored cells exclude all of them and anything within 10 pixels of any;
the correlation model uses the mean correlation with the stimulated cells; the generic profile
uses distance to the nearest stimulated cell. Same inclusion rules and comparisons, reported
for all included sessions together and for the multi-cell sessions alone. The pre-registered
result stays the primary one.

**Amendments to the pre-registration, recorded 3 Nov 2026 after an independent review.** The
analysis paragraph above was edited in place for the first two; the original wording is kept
here. Changes made before any real trace was opened: (i) the stimulated-ROI check was "top 2%"
under the first reading that passes, among three readings; it became "top 5%" under the reading
with the largest response, among four (all ROIs, curated cells, old_cell_idx in both
directions), after synthetic tests; (ii) sessions without a curation file count every ROI as a
cell. Changes made after real data was seen: (iii) a guard for sessions whose stimulation file
lists nothing; (iv) files zeroed by a PC crash are detected and their sessions excluded (9
sessions: 230, 270, 289, 307, 357, 359, 373, 380, 406; this check was added after a first
partial run had printed per-session scores); (v) bug fix: some stimulation files list every
stimulation twice, which made the odd/even ceiling compare each trial with itself (ceilings of
0.998 to 1.000 in 5 included sessions); entries closer than 50 frames are now merged; (vi) bug
fix: traces were stored at reduced precision and very bright ROIs overflowed, silently failing
the check; such sessions are now reported as such and are re-extracted at full precision by the
recovery pass. Implementation details the paragraph above does not state: the response window
starts one frame after the stimulation ends; watching runs from frame 0 to 50 frames before the
first stimulation and needs at least 2000 frames; the in-silico drive uses the median
stimulation length; the VAR is fitted on scored and stimulated cells and its spectral radius
capped at 0.99; the top 5% is taken over all ROIs; distance deciles are ranks within each
session and the generic profile pools the other analysable sessions.

**Exploratory checks, written before they were run.** The review showed that the
stimulated-ROI check can select sessions in which a cell happened to be active after the
stimulation, and that watching, which learns spontaneous co-activation, then appears to predict
"responses" with no causal effect at all (on synthetic sessions where stimulation does nothing,
8 sessions passed and watching beat the generic profile by 0.35). So: (a) the same analysis at
sham times, 130 frames after each stimulation (midway between stimulations), with the reading
search and with the reading fixed to "all ROIs"; (b) the real analysis with the reading fixed to
"all ROIs"; (c) the ceiling comparison on matched halves (watching scored against the even
stimulations, beside the odd/even ceiling), as a ratio of means with a bootstrap interval and
the median of per-session ratios; (d) the main difference bootstrapped by recording day as well
as by session, since sessions from one day are probably one mouse. Reading: if sham times give
about as many included sessions and a similar watching-minus-generic difference as real
stimulations, the hippocampus result says nothing about pokes.

**Result (3 Nov 2026; `docs/figures/hippo_*`; reviewed independently, and the review's must-fix
points are fixed above).** A PC crash interrupted the one-pass download; 165 sessions with
traces were recovered (the archive order is random, so the missing ones are a random subset)
and a recovery pass is scheduled. Of the 127 single-cell sessions with intact files, 74 fail the
stimulated-ROI check, 37 pass it but have a ceiling below 0.1, and 16 are included. Primary,
pre-registered analysis (16 sessions):

| | Mean (95% interval) |
|---|---|
| ceiling (odd against even stimulations) | 0.21 (0.16 to 0.28) |
| watching copy | 0.14 (0.04 to 0.25) |
| correlation with the stimulated cell | 0.16 (0.06 to 0.28) |
| generic profile from other sessions | −0.03 (−0.06 to −0.00) |
| watching minus generic | +0.17 (+0.08 to +0.29); by recording day (12 days) +0.06 to +0.28 |
| watching with running regressed out, minus watching | +0.002 (−0.03 to +0.04) |
| watching on matched halves / ceiling, ratio of means | 0.70 (0.30 to 1.00); median per session 0.58 |

Against the expectations: (1) "under half of the ceiling" is not supported (0.70, interval
0.30 to 1.00); (2) "no better than the generic profile" is wrong as stated: watching beats it,
though the generic profile itself predicts nothing; (3) running makes no difference: confirmed.
The dynamical copy adds nothing over plain correlation with the stimulated cell.

**But the sham control undercuts the main result.** At sham times, when nothing was poked:

| | Real stimulation | Sham times | Real minus sham |
|---|---|---|---|
| reading search: sessions analysable / included | 53 / 16 | 27 / 9 | |
| reading search: watching minus generic | +0.17 | +0.10 (+0.02 to +0.19) | +0.07 (−0.07 to +0.21) |
| reading fixed to "all ROIs": analysable / included | 40 / 11 | 18 / 8 | |
| reading fixed: watching minus generic | +0.21 (+0.09 to +0.35) | +0.06 (−0.03 to +0.16) | +0.15 (−0.005 to +0.31) |

Half as many sessions pass the check at sham times as at real times, and watching "predicts"
their sham responses too. Real stimulation does better, but the difference is not significant.
**So this data does not show that watching predicts responses to pokes in mouse CA1, as opposed
to the spontaneous co-activity the inclusion check selects for.** In sessions where the
stimulation was verified, ranking cells by how they co-fluctuated with the stimulated
interneuron during watching ordered their responses weakly (Spearman about 0.15) where distance
ordered nothing; whether that reflects the poke needs more sessions with verified stimulation.
Other notes: the 74 failed checks are 58% of single-cell sessions; the review found that the
pre-registered window (starting one frame after the stimulation ends) can miss fast transients,
so some of these may be timing rather than failed stimulation; the multi-cell follow-up adds no
sessions (27 of 29 fail the check). No session overflowed the reduced-precision storage.

## Next test bed: mouse touch cortex (data in hand, 5 Nov 2026; not yet analysed)

Dalgleish et al. 2020 (figshare 13128950, MIT): all-optical experiments in mouse barrel cortex,
groups of 5 to 200 identified neurons photostimulated while about 3,700 neurons per session are
imaged, in 11 sessions. Downloaded unattended on 5 Nov by `scripts/touch_stream.py` (2.7 GB kept,
local only). Structure, as read so far: `Fc.npy` (ROIs x frames, neuropil-corrected, all planes;
for example 3,699 x 24,099 in 20191009_L542, three acquisitions of 8,033 frames), `rois.npz`
(ROI centres and planes), `*_paqanalysis.mat` (MATLAB v7.3: frame times, licks, rewards, and
eight stimulation channels Stim1 to Stim8 with their onset frames), `targets/*_NAPARM_*_Points.mat`
(200 points per pattern with X, Y, Z and group), `cellPose/*Centroids.mat`. The same watching
versus poking test needs trials mapped to their target patterns and targets mapped to ROIs by
position; the analysis will be pre-registered before any response is computed, scoring only trials
without licks (the animals were trained to lick when they felt the stimulation, and licking moves
the whole cortex).

## Mouse touch cortex: the core tests in a second species (pre-registered 6 Nov 2026)

Written before any response in this data was computed; `scripts/run_touch_tests.py`. What was looked at
first, for design only: the file structure, trial counts with and without licks, and an attempt to map
the 200 target points onto the imaged cells. That mapping failed (the target coordinates do not align
with the cell positions under any shift, flip or scale tried; best 20% of targets within 2.5 pixels of a
cell, against 7.5% by chance), so targets are found from their own responses, on held-out trials.

**Data.** Dalgleish et al. 2020, 11 sessions (6 mice; each session one field of view, treated as one
individual), about 3,700 cells in 4 planes imaged at about 6.7 volumes per second. On each laser trial a
subset (5 to 200 cells) of the same 200 targets is stimulated; catch trials have no laser. The mice were
trained to lick when they felt the stimulation, so **only trials with no lick from 1 s before to 2 s after
onset** are used (about 40% of laser trials; most 200-cell trials are licked).

**Definitions.** Activity: each cell's fluorescence divided by its median, z-scored over rest frames.
Rest frames: at least 3 s after any stimulation and at least 2 s from any lick. Response of a cell on a
trial: mean over 0.3 to 1.2 s after onset minus mean over the 1 s before. Trials are split by order into
odd and even. **Directly activated cells** ("targets"): mean response over odd laser trials at least 1.5
and at least 5 times the cell's mean response on catch trials (to exclude licking or drift); everything
below is scored on cells that are not targets and are not within 15 pixels of a target in the same
plane, using even trials. Sessions with fewer than 10 targets or 20 usable laser trials are reported
and left out.

**T1, watching versus poking.** For each non-target cell: its measured response (mean over even laser
trials); the watching prediction, its mean correlation at rest with the target cells; the distance
prediction, minus the distance to the nearest target in the same plane (cells in other planes are left
out of T1); the ceiling, odd against even trials. Score per session: Spearman across cells.
*Prediction:* none favoured. *Decision:* watching beats distance if the paired difference (watching
minus distance) has a 95% interval above 0 across sessions (resampling sessions, 2,000), loses if below
0; otherwise no difference detected. Watching's share of the ceiling is reported beside it.

**T2, tiring.** Over successive usable laser trials in a session: least-squares slope of the log of
the targets' mean response, and of the responding non-target cells' mean response (responding: mean even
response at least 0.5), on trial number. Statistic: network slope minus target slope (the network
tiring beyond its input). *Decision:* the network tires if the median over sessions is below 0 with a
sign test p < 0.05; no detectable tiring if the 95% interval of the median includes 0; otherwise
inconclusive. Each slope is reported on its own (a target slope below 0 can be the opsin, the tool).

**T3, state-dependent spread.** State before each usable laser trial: activity in the 2 s before onset
projected on the first principal component of rest activity of non-target cells, with its sign aligned
so the mean loading is positive. High and low: top and bottom thirds of trials. S = correlation between
the non-target cells' mean responses in high and in low trials, minus the mean of 500 shuffles of the
labels. *Decision:* state dependence if the median S over sessions is below 0 with a sign-flip p < 0.05
(10,000 flips); none detected if the 95% interval includes 0 and its lower end is above -0.05; otherwise
inconclusive.

*Amendment 1 (6 Nov, after the first run).* The first run was **unusable by its own rule**: 10 of 11
sessions had fewer than 10 targets (0 to 5; one session 18), because each trial stimulates only a subset
of the 200 targets, so a target's mean over all trials is diluted. Seen in that run: target counts, and
T1 to T4 for the one included session (uninformative alone). Changed, before computing anything else:
a cell is a target if, on odd laser trials, its response exceeds 3 on at least 3 trials and on at least
10% of them, while on catch trials it exceeds 3 on at most 5%. Its own measured response (for T2) is then
the mean over the even trials on which it exceeds 3 (the trials where it was hit); everything else is
unchanged. If this still leaves fewer than 5 sessions, the package is declared unusable for this data.

**T4, the echo's sparseness (descriptive).** Share of non-target cells whose mean even response exceeds
1 (one resting SD), and of those, the share still above 1 from 2 to 4 s after onset, reported beside
the worm's (about two thirds of classes respond within 30 s, and most of those keep responding).

**Results (6 Nov 2026, amendment 1; `docs/figures/touch_tests.txt`, `touch_sessions.csv`; the unusable
first run is kept as `touch_tests_run1_unusable.txt`).** 7 of 11 sessions included (13 to 41 targets each;
4 sessions had 1 to 8).
- *T1:* median Spearman across cells: ceiling 0.33, watching 0.09, distance -0.02; watching minus distance
  +0.13 [95%: +0.06, +0.18], positive in 7 of 7: **watching beats distance by the rule.** But two
  exploratory checks, run afterwards, undo the reading. Watching "predicts" catch trials, when nothing was
  stimulated, about as well (median 0.04 against 0.09 on laser trials; laser better in only 3 of 7). And on
  laser minus catch responses (the part caused by the light), watching is at 0.00 and distance at -0.02.
  So, as in mouse hippocampus, what watching predicts here is the cells' ordinary co-activity at trial
  times, not the effect of the poke; and with groups of 5 to 200 cells cycling, the poke-specific signal
  is too weak for either predictor. *(Corrected after review 4: "about as well" overstated it, 0.04 is less
  than half of 0.09; on laser minus catch, watching minus distance is +0.042, positive in 5 of 7, with no
  ceiling computed. The pre-registered verdict stands, with the caveat that part of what watching predicts
  is trial-locked co-activity. The exploratory code is now in `run_touch_tests.py --explore`.)*
- *T2:* targets' slope -0.0018, network -0.0016 per trial; network minus target +0.0002 [-0.0061,
  +0.0075], 3 of 7 below 0: **no detectable tiring** by the rule, but *uninformative (review 4)*: the rule
  had no equivalence bound and the interval allows a 30% to 50% decline over a session; the target slope
  uses only trials above 3 SD, which truncates a decline; the lick-free trial mix can change with order.
- *T3:* S median -0.085 [-0.122, -0.005], 6 of 7 below 0, sign-flip p = 0.066: **inconclusive by the
  rule**, in the direction of state dependence (the 95% interval lies below 0, but the pre-registered
  test needs p < 0.05).
- *T4:* averaged over all trials, 0.1% of non-target cells move by more than 1 SD; of those, the share
  still above it 2 to 4 s later is 0 in most sessions (1.0 in one; corrected after review 4, which caught
  "none of them"). Because each trial hits only a small group, this says the averaged echo
  is very sparse, not how sparse a single echo is; it is not comparable with the worm number.

**Reading (corrected after review 4).** This data leans towards state dependence; its tiring test is
uninformative; and its
stimulation design (small groups cycling through 200 targets, most large-group trials licked) cannot
separate watching from poking. A dataset that stimulates the same small group many times, without
behaviour, is what that test needs.

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

## Research site

`web/` is the project's research site: the findings, the method and the research log, with
every figure drawn from the result tables in `docs/figures` (plain HTML, CSS and SVG, no
build step). Regenerate its data and serve it locally:

```
python scripts/export_site.py --local      # results.js, plus the opening figure from the local atlas copy
web\serve.cmd                              # Windows: serves http://localhost:8642 and opens it
sh web/serve.sh                            # elsewhere
```

The opening figure (one held-out real worm next to two artificial brains under the same
pokes) is drawn from the local copy of the atlas and is not committed (`web/data/local.js`);
without it the site still works and says how to generate it. Fonts: Newsreader and Schibsted
Grotesk (SIL Open Font License, `web/fonts`).

## Replay lab

```powershell
python scripts/fetch_atlas.py
python scripts/export_replay.py data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 --split configs/splits/copper2026.yaml --out lab/public/data
cd lab; npm install; npm run dev
```

## Generalisation: copper-trained models against another dataset

**Design, written before running (Oct 31).** Do the models learn worms, or this dataset?
Models are trained on all 27 copper worms (25 training, 2 validation, as in the rotations)
and generate worms on the templates of the 14 unstimulated (baseline) worms of Atanas et
al. 2023 (same lab and microscope family, different experiments: no copper arena,
different session protocol). Sample j comes from copper worm j's model. They are scored
with the ruler against those 14 Atanas worms as the reference, on all 10 pairwise levels,
and with the classifier (model vs Atanas worms). The real control is the copper worms
themselves scored against the Atanas worms the same way; the Atanas heat-stimulated worms
are scored too, as a second real comparison (`scripts/run_cross_dataset.py`).
Expectations: if the models learned worms rather than this dataset, they should do about
as well as the copper worms themselves do against Atanas worms (same levels inside or
outside, similar distance ratios and classifier AUC); a model that does clearly worse
than the copper control has learned something specific to the copper recordings.

**Results** (`docs/figures/cross_dataset.csv`; reference: 14 Atanas baseline worms):

| | pairwise inside | timescale | correlation | dimension | AVA bouts (dwell) | classifier AUC |
|---|---|---|---|---|---|---|
| copper real worms (control) | 7 of 10 | 1.21 out | 1.17 out | 1.57 out | 1.24 | 0.735 |
| Atanas heat-stimulated worms | 10 of 10 | 1.00 | 1.09 | 1.21 | 1.11 | 0.681 |
| copper-trained VAR(3) | 6 of 10 | 1.43 out | 1.15 out | 2.75 out | 1.50 out | 0.933 |
| copper-trained VAR(10) | 6 of 10 | 1.26 out | 1.18 out | 3.00 out | 1.47 out | 0.873 |

- **The two datasets differ.** Real copper worms are themselves outside the Atanas worms on
  timescales, correlations and dimensionality, and a classifier separates the two sets of
  real worms (0.735): different experiments leave a mark that the worm-to-worm ruler can see.
  (Heat-stimulated Atanas worms, by contrast, are inside everywhere next to unstimulated
  ones.)
- **The models inherit that shift, and add their own errors.** They miss the same three
  levels the copper worms miss, with similar correlation distances (1.15 to 1.18 vs 1.17),
  so in that respect they learned copper worms rather than something artificial. On top of
  it they miss AVA bout durations, are much more over-dimensional (2.75 to 3.0 vs 1.57), and
  are far easier to detect (0.87 to 0.93 vs 0.735). The 10-frame model generalises better
  than the 3-frame one on timescales and on the classifier, matching its better in-dataset
  results.
- Expectation partly held: the models do about as well as the copper control on most
  levels but clearly worse on dimensionality, dwell and the classifier. A within-Atanas
  replication of the main result (train and test on Atanas worms) would separate dataset
  shift from model error directly.

**Replication within Atanas 2023. Design, written before running (Oct 31).** The whole
pipeline, unchanged, on the 30 Atanas worms (baseline and heat-stimulated together):
three date-spread rotating pools of 10 (`configs/splits/atanas2023_cv3.yaml`, hash
e1d02f6e843e2774, 5, 5 and 6 heat worms per pool), the ruler's calibration systems on
the frozen Atanas split, the per-worm calcium-drive VAR(3) and VAR(10) with hysteresis
reversals (`run_lags.py`), and the fair Level 8 (`run_l8_fair.py`). Expectations: if the
copper results are about worms rather than one dataset, (1) the calibrations hit their
designed outcomes, (2) VAR(10) is inside on all or nearly all pairwise levels, (3) its
in-sample classifier AUC is near chance and lower than VAR(3)'s.

**Results: a partial replication** (`docs/figures/ruler_atanas.csv`,
`lags_atanas_combined.csv`, `l8_fair_atanas.csv`):
- (1) held: all 44 designed calibration outcomes match on Atanas.
- (2) failed: with the settings chosen on copper unchanged (shrinkage 300, calcium decay
  0.5, hysteresis), VAR(3) is inside on 6 of 10 levels and VAR(6) and VAR(10) on 5 of 10
  (timescale 1.11 to 1.18, lead-lag 1.08 to 1.09 and AVA bouts 1.19 to 1.25 outside,
  reversal bout lengths too typical, dimensionality outside for the longer memories;
  activity values, correlations, velocity encoding and reversal-linked activity inside).
- (3) held: in-sample classifier AUC 0.573 for VAR(10) against 0.768 for VAR(3), and
  held-out 0.703 against 0.785 (real control on these pools 0.562).
So longer memory makes the model much harder to detect in both datasets, but the full
10 of 10 on copper is partly specific to copper or to settings tuned on it. Next: choose
the settings per rotation by in-sample realism on the training worms only, the same
procedure on both datasets, and see whether that recovers the pairwise levels on Atanas.

**Automatic settings. Design, written before running (Oct 31).** Per rotation, the memory
length (3, 6 or 10 frames) and the per-worm shrinkage (100, 300 or 1000) are chosen by
in-sample realism on that rotation's training worms only: each training worm's own model
generates a sample on its own template, the ruler scores those samples against the
training worms, and the criterion is the sum over all 10 pairwise metrics of
|log(system median / real median)| plus 1 for every metric judged too typical
(`scripts/run_auto.py`; no reference worm is used). The same procedure runs on both
datasets' rotating pools. Expectations: on copper it should match the hand-chosen setting
(VAR(10), shrinkage 300: 10 of 10); on Atanas it should recover some of the missing
levels; if it picks settings that score worse on the reference pools than the hand-chosen
ones, in-sample realism is a poor guide and that is reported.

**Result** (`docs/figures/auto_copper_*.csv`, `auto_atanas_*.csv`): in-sample realism
picks 10 frames of memory with shrinkage 100 in most rotations (3 frames in one rotation
of each dataset; shrinkage 300 once). Copper: 9 of 10 (reversal bout lengths slightly too
typical, 0.86), about as good as the hand-chosen setting. Atanas: 5 of 10, the same levels
missing as with the copper settings (timescale 1.16, lead-lag 1.09, AVA bouts 1.19,
dimensionality 1.50; reversal bouts too typical). So the Atanas misses are not a matter of
settings; something about that dataset (behaviour labelling, session protocol, or the
dynamics themselves) is not captured. That is now an open question for arc 2.

## Arc 3: what the wiring buys

**Design, written before any run (Oct 31).** The best open-loop model (per-worm
calcium-drive VAR with 10 frames of memory, hysteresis reversals) is refitted with its
neuron-to-neuron weights restricted to a wiring diagram, everything else identical
(`nematica/systems/wiring.py`, `scripts/run_wiring.py`):

- **full**: every class may influence every class (the current model)
- **connectome**: class j may influence class i only if some member of j synapses onto some
  member of i or they share a gap junction (Kunert 2014 / Neural Interactome matrices). Among
  the 48 core classes this allows 6.6 inputs per class (density 0.14); the pharyngeal
  classes (I1 to I3, M3, M4, MC, MI, NSM) have no somatic inputs and keep only their own
  history
- **shuffled** (3 seeds): the same number of inputs per class, drawn at random
- **diagonal**: no coupling between classes

Self-connections and the two behaviour channels are always allowed; only neuron-to-neuron
weights are restricted. Scored on the three rotating pools (10 pairwise levels), the fair
Level 8 (held-out and in-sample) and forecasting on held-out worms (one-step and 30 s
ahead, R^2).

**Expectations.** (1) Full forecasts best, since it has the most freedom, and diagonal worst.
(2) If the connectome carries real information about which neurons drive which, the
connectome model should beat the shuffled models with the same number of connections on
realism: more pairwise levels inside, especially correlation and lead-lag, and a lower
Level 8 AUC. (3) A null result is possible and would be reported as such: with
calcium-level dynamics, unobserved neurons and class pooling, the anatomical wiring may
not constrain the effective coupling that the recordings reveal.

**Results** (`docs/figures/wiring_combined.csv`, `wiring_forecast.csv`, `l8_fair_wiring.csv`):

| wiring | pairwise inside | correlation | dimension | lead-lag | Level 8 held-out / in-sample | one-step R^2 | 30 s R^2 |
|---|---|---|---|---|---|---|---|
| full | 10 of 10 | 1.03 | 1.34 | 1.04 | **0.620 / 0.499** | 0.4910 | **0.1009** |
| connectome | 8 of 10 | **1.06** | 2.18 | **1.04** | **0.680 / 0.569** | **0.4935** | 0.0827 |
| shuffled, seed 0 | 7 of 10 | 1.09 | 2.19 | 1.05 | 0.716 / 0.636 | 0.4923 | 0.0791 |
| shuffled, seed 1 | 7 of 10 | 1.08 | 2.13 | 1.06 | 0.690 / 0.594 | 0.4923 | 0.0820 |
| shuffled, seed 2 | 8 of 10 | 1.07 | 2.16 | 1.05 | not run | 0.4924 | 0.0820 |
| no coupling | 8 of 10 | 1.09 | 2.21 | 1.05 | 0.716 / 0.626 | 0.4913 | 0.0744 |

(bold: best among the sparse models; full is shown for reference)

- **The real wiring carries information, and the effect is small.** With the same number
  of connections per class, the connectome model beats all three shuffled wirings on
  one-step forecasting of held-out worms (0.4935 vs 0.4923 to 0.4924, and in every
  rotation), on correlations (1.06 vs 1.07 to 1.09) and lead-lag (1.04 vs 1.05 to 1.06),
  and on the classifier in every rotation (held-out 0.787, 0.633, 0.619 against 0.816,
  0.671, 0.660 and 0.799, 0.639, 0.632). It even forecasts one step ahead better than the
  fully coupled model.
- **But anatomical sparsity costs realism.** Every sparse model, connectome included, is
  far too high-dimensional (ratio about 2.2 against 1.34 for full), and the fully coupled
  model is the most realistic on every measure except one-step forecasting. With neurons
  pooled into classes and most neurons unrecorded, the coupling a recording reveals
  includes indirect paths the anatomy does not draw; restricting to direct synapses
  removes the shared drive that keeps real activity low-dimensional.
- Expectation (1) held for 30 s forecasting but not one step; expectation (2) held in
  direction for every measure, at a small size; the null in (3) did not occur.
- What would make it a stronger test: the connectome as a prior (shrink non-synaptic
  weights rather than zero them), weighted by synapse counts, and a wiring mask that
  allows two-step paths.

**The connectome as a prior. Design, written before running (Oct 31).** Instead of zeroing
non-synaptic weights, give them a larger ridge penalty: rho times the penalty of synaptic
ones (rho = 1 is the full model, rho to infinity the hard mask). rho is chosen jointly with
the ridge on validation worms from {1, 3, 10, 30, 100}, separately for the connectome and
for each of the three shuffled wirings, and the same penalty pattern is used in each
worm's shrinkage toward the pooled fit (`WiredVAR(rhos=...)`). Expectations: (1) if the
connectome prior helps, validation picks rho > 1 for it and it beats the shuffled priors on
forecasting and realism; (2) because the prior keeps indirect couplings available, it
should not lose the dimensionality the hard masks lost, and could match or beat full
coupling; (3) if validation picks rho = 1 everywhere, the anatomy adds nothing a
data-driven fit does not already find, and that is the answer.

**Results** (`docs/figures/wiring_prior_combined.csv`, `wiring_prior_forecast.csv`,
`l8_fair_wiring_prior.csv`):

| prior | rho chosen | pairwise inside | dimension | Level 8 held-out / in-sample | one-step R^2 | 30 s R^2 |
|---|---|---|---|---|---|---|
| none (full) | 1 | 10 of 10 | 1.34 | 0.620 / 0.499 | 0.4910 | 0.1009 |
| connectome | 30, 30, 30 | 9 of 10 | 1.86 | 0.701 / 0.627 | 0.4970 | 0.1007 |
| shuffled, seed 0 | 30, 30, 30 | 9 of 10 | 1.98 | 0.727 / 0.653 | 0.4967 | 0.1006 |
| shuffled, seed 1 | 30, 30, 30 | 9 of 10 | 1.95 | 0.716 / 0.645 | 0.4966 | 0.1012 |
| shuffled, seed 2 | 30, 30, 30 | 9 of 10 | 1.88 | not run | 0.4966 | 0.1009 |

- Validation picked rho = 30 for the connectome and for every shuffled wiring alike, in
  every rotation: penalising most couplings helps one-step forecasting (0.497 vs 0.491 for
  full) whichever couplings are spared, so most of the gain is generic regularisation,
  not anatomy (expectation 1 only half held).
- The anatomical part is again small and consistent: the connectome prior forecasts a
  little better than every shuffled prior, is the least over-dimensional (1.86 vs 1.88 to
  1.98), and has the lower classifier AUC in every rotation (0.768, 0.691, 0.644 against
  0.802, 0.718, 0.661 and 0.785, 0.706, 0.656).
- Expectation 2 failed: the rho that forecasts best makes every model too
  high-dimensional and more detectable than full coupling. This is arc 1's lesson
  again: selected for forecasting, a model gets less realistic.
- **Arc 3 so far:** the real wiring beats random wiring of the same density on every
  measure, in every rotation, but the advantage is small, and on realism no wiring
  constraint yet beats letting the data choose the coupling.

**rho chosen by realism. Design, written before running (Oct 31).** Same priors, but rho
is picked from {1, 1.5, 2, 3, 5, 10} by how realistic each model is on its own training
worms: samples from each training worm's model, on that worm's template, are scored
against the training worms with the ruler, and the rho with the smallest sum of absolute
log distance ratios on L2.dimension, L2.correlation and L1.timescale wins (rho = 1, the
full model, is a candidate). No reference worm is involved. Expectations: (1) the chosen rho
will be small (1 to 3), since the forecasting-chosen 30 was too high-dimensional; (2) if
the anatomy helps realism, the connectome's chosen model should beat the shuffled ones and
at least match full coupling; (3) if every wiring picks rho = 1, wiring constraints buy
nothing for realism at this resolution.

**Result: rho = 1 in all 12 cases** (4 wirings x 3 rotations;
`docs/figures/wiring_realism_criterion.csv`). The in-sample realism criterion rises
steadily with rho for every wiring in every rotation (connectome, rotation 1: 0.48 at
rho = 1, 0.53, 0.55, 0.62, 0.64, 0.71 at rho = 10), so a realism-chosen prior is the full
model and scoring it on the reference pools would only repeat the full model's numbers.
At the strongest prior (rho = 10) the connectome loses less realism than all three
shuffled wirings in rotations 1 and 3 (0.71 vs 0.77 to 0.81; 0.48 vs 0.55 to 0.62) but not
in rotation 2 (0.69 vs 0.63 to 0.73). Expectation 3 held.

**Arc 3, conclusion at this resolution.** Anatomical wiring carries real but small
information about how these recorded neuron classes drive each other: given the same
number of connections, the connectome beats random wiring on forecasting, correlations,
lead-lag and the classifier, consistently. But any wiring constraint makes the model less
realistic than letting the data choose the coupling, whether imposed as a mask, as a
forecasting-chosen prior or as a realism-chosen one. At class-level calcium imaging with
most neurons unrecorded, the effective coupling the recordings reveal is denser than the
direct anatomical wiring. Finer tests would need per-neuron (left/right resolved) data,
synapse-weighted priors, or the immobilised optogenetic atlas (Randi 2023), where single
neurons are driven.

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

Results, held-out pools combined (`docs/figures/closed_loop_v2.csv`):

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
  driven by the brain, so the brain's lead-lag and reversal encoding fail.

**Version 3** gives each model worm its own reversal rates (onset and end offsets set in
open loop so it reproduces its training worm's onset rate and mean bout length, shrunk
toward the pooled values), and tries reversals driven by the command interneurons (AVA,
AVE, AIB, RIM, AVB, RIB) against reversals independent of the brain
(`--variants v3`, `docs/figures/closed_loop_v3.csv`):

| | time near copper | Level 6 | pairwise inside |
|---|---|---|---|
| own rates, reversals independent of the brain | 15.7% | inside on all 3 | 8 of 10 |
| own rates, reversals driven by command neurons | 35.9% | occupancy outside | **10 of 10** |
| own rates, blind | 66.2% | encounter, occupancy outside | 8 of 10 |

A real trade-off: when the command neurons decide when to reverse, the brain-behaviour
coupling is right (lead-lag 1.05, reversal encoding 0.95), but copper avoidance collapses.
Fitted on real worms, the hazard learns that copper raises reversals mainly by raising
command-neuron activity (its direct copper term turns slightly negative), and in the
closed loop the model's command neurons do not rise near copper the way real ones do.

**Version 4** fits the hazard in two stages: the copper effect on reversals alone first
(as observed overall), then the command neurons set the timing around it with the copper
terms held fixed [A] (`--variants v4`, `docs/figures/closed_loop_v4.csv`). Inside on all
10 pairwise levels and on Level 6 encounter and approach; time near copper 28.7%,
occupancy narrowly outside (0.967 of partitions). Better, not passing.

Why the model brain's command neurons miss copper: in the fitted brain, copper's one-step
effect on AVA, AIB and RIM is almost zero, but its steady-state effect through the brain's
own dynamics is large and positive (AVA +0.68, AIB +0.74 SD at the copper line), and part
of it flows through the brain's reversal channel (+0.34). In hazard mode that channel is
overwritten by the discrete reversal state, which cuts the path.

**Version 5** adds the brain's own one-step prediction of its reversal channel to the
hazard, so that path stays intact (`--variants v5`, `docs/figures/closed_loop_v5.csv`).
Reversal statistics become very close to real (spread of per-worm onset rates, log SD
0.15 vs 0.16; median bout 6.6 s vs 6.6 s on one rotation), but it is no better overall:
9 of 10 pairwise (lead-lag just outside, 1.05), 30.8% near copper, occupancy outside.

**What is still missing is avoidance at a distance.** Checked on the real worms:
- Not speed or exploration: simulated worms move as far per minute as real ones (median
  net displacement over 60 s 1.54 vs 1.44 mm).
- Not an aversive memory: after touching copper, real worms reverse less, not more
  (onset rate per forward frame 0.007 in the next 30 s, 0.038 after 5 minutes).
- Real worms mostly never get there: 33 of 43 thousand frames come from periods with no
  copper contact in the previous 5 minutes, with median distance to copper 2.1 mm, although
  they move far enough to reach it. Simulated worms touch copper about five times as often.
So the real avoidance acts before contact, and the reversal hazard measured near copper
(at most 2.5 times the far rate) does not explain it.

**Version 6: slow steering, and copper as a limit.** Over 20 s windows real worms facing
the copper 0.5 to 2 mm away turn away (cosine to the outward normal drops by 0.6 to 0.8
even without reversing) and end up further from it; frame by frame this is invisible.
v6 adds a steering term, turn rate = k x proximity x sin(angle to the outward normal),
with k fitted on training worms (indirect inference on simulated training worms confirms
the fitted gain reproduces the real slope, 0.019 vs 0.019 rad per frame) and its length
scale chosen on validation worms (2 mm). It also exposed a simulation artefact: model
worms that crossed the copper line had no data-driven reason to come back (the sense is
flat beyond the deepest real crossing), and 22% of simulated time was more than 1 mm past
the line (real 0.5%). Copper is now treated as impassable beyond the deepest crossing seen
in training worms (-0.85 mm): there the worm moves whichever way leads back inside [A].
Results (`--variants v6`, `docs/figures/closed_loop_v6.csv`): 10 of 10 pairwise, but time
near copper 27.3%, occupancy and encounter outside.

Every local statistic checked now matches real worms: steering slope, reversal rate,
duration and anatomy near copper (distance gained 9 s after a reversal ends +0.45 vs
+0.41 mm), escape depth. What does not match is how often model worms arrive at the edge.
Model worms also travel straighter over a minute and cover more ground; adding heading
noise calibrated on training worms did not change occupancy (`calibrate_heading`). This
is where arc 5 stands: the brain-behaviour model is complete at the pairwise levels in
closed loop, and the open problem is the arena-scale distribution of where worms go.

Further checks on one rotation (Oct 31): forward runs between reversals (median 12.6 vs
11.4 s), straightness of forward crawling over 3, 10 and 20 s (0.92/0.86/0.84 vs
0.89/0.83/0.82) and per-worm speed (now taken from the tracked plate position, per
training worm, `stage_speed=True`) all match; real worms vary their speed from minute to
minute about twice as much (coefficient of variation 0.12 vs 0.06), and neither shows
dwelling epochs. None of this moves occupancy (29%).

**A data caveat that limits this comparison.** In the copper set, the recorded distance
to the copper centre and the distance computed from the tracked plate position disagree
by -0.72 to +0.75 mm depending on the worm, and some tracked positions lie up to 1.6
times the arena radius from its centre. Measured with the tracked position, real worms
spend 9.1% of their time within 0.5 mm of copper, not 3.2%. The model (27 to 29%) is
outside both, but arena-scale statistics, including the facing directions used for
steering, are only as good as this geometry (about 0.7 mm).

**Resolved: a constant calibration offset.** Fitting candidate corrections per worm, a
single fixed shift of the tracked position, (0.613, 0.462) mm, makes it reproduce the
recorded distance to 0.023 mm rms in every worm (0.54 mm without), and the shift is the
same in all 27 worms to within 0.005 mm; a shift along the body or a different arena
centre does not fit. The loader now applies it (`COPPER_STAGE_OFFSET_MM`), so tracked
paths, the arena circle and the recorded distance agree (the replay lab already fitted
this offset worm by worm, so its copper ring was right; that fit now finds about zero). With corrected geometry v6 is still 10
of 10 pairwise, encounter and approach inside, occupancy narrowly outside (0.969), and
time near copper 33.7% (27.3% before the fix; run-to-run variation at this level is large).

**Level 8 for the closed loop** (`scripts/run_l8_closed_loop.py`, frozen split,
`docs/figures/l8_closed_loop.csv`): AUC 0.952, against 0.94 for the open-loop model and
0.68 for other real worms. Closing the loop does not change how detectable the brain
activity is; the giveaway is still the short-timescale spectrum (arc 1).

**Why real worms take so long to reach copper.** Real worms start a median 1.9 mm from
copper and take a median 393 s to first come within 0.5 mm (8 of 27 never do in 16
minutes); model worms got there in 103 s, all of them. Measuring the drift of distance to
copper over 20 s at each distance shows why: between 0.5 and 2 mm real worms drift away
from copper (+0.22, +0.17, +0.10 mm per 20 s), crossing over at about 2 mm, while v6 model
worms drift slightly toward it. The steering gain fitted to frame-by-frame turning
reproduces that turning but not this drift.

**Version 7** sets the steering gain by indirect inference on a different training-worm
statistic, the outward drift between 0.5 and 2 mm, instead of the turning slope (it needs
about 4 times the fitted gain, so the real drift involves more than the body turning that
can be measured) (`--variants v7`, `docs/figures/closed_loop_v7.csv`). Time near copper
15.3% (v6: 27 to 34%; real 3.2%, or 9.1% by the uncorrected tracked position), **occupancy
inside**, approach inside, encounter just outside (0.962), pairwise 9 of 10 (lead-lag
1.06, just over the line). Closest so far; not yet a full pass.
Over three independent replicates (`--seed-offset 10`, `20`): time near copper 15.3%,
13.6%, 17.2%; occupancy and approach inside every time; encounter outside, outside,
inside (0.962, 0.974, 0.936: borderline); lead-lag outside every time (1.05 to 1.06: a
small but consistent miss).

**Version 8** gives the closed-loop worm the 10-frame brain that passes Level 8 open loop
(`--variants v8`, `docs/figures/closed_loop_v8.csv`): time near copper 11.2% (best so
far), occupancy and approach inside, but encounter now clearly outside (1.0) and lead-lag
still 1.06 (9 of 10).

**What the lead-lag miss is.** Averaged over worms, the closed loop reproduces who leads
whom almost exactly (pattern correlation with real 0.96 at 1.8 and 6 s lags). The pairs
that go wrong all involve ASH, the copper-sensing nociceptor: in real worms ASH leads the
reversal command neurons by seconds (antisymmetric lagged correlation at 6 s: RIM -0.144,
AVE -0.165, AVA -0.167), and in the closed loop that lead is roughly halved (-0.054,
-0.074, -0.104). The reason is the design of v4 to v8: copper raises the reversal rate
through a direct copper term in the hazard, not through ASH. The encounter miss (the
brain's response when the head meets copper) points the same way.

**In real worms, ASH carries copper's effect on reversing.** On forward frames, ASH activity
(drive units) is +1.12 within 0.5 mm of copper against -0.25 beyond 2 mm. Predicting
reversal onsets in held-out worms (two-fold by worm), adding ASH to the command neurons
improves the log likelihood from -3094.5 to -3025.1, and adding direct copper terms on top
of ASH adds nothing (-3026.2) [M].

**Version 9** follows that: the reversal hazard uses the command neurons and ASH with no
direct copper term, so copper can act only through the brain, and the brain's copper
weights may be left unpenalised if validation worms prefer it (they did, in all three
rotations) (`--variants v9`, `docs/figures/closed_loop_v9.csv`):
- **All three Level 6 metrics inside for the first time** (encounter 0.865, approach,
  occupancy), and the lowest time near copper so far, 10.4% (real 3.2%).
- But 8 of 10 pairwise: lead-lag got worse (1.09; the expectation that it would recover
  was wrong) and the activity distribution now misses narrowly (1.06), plausibly from the
  unpenalised copper weights. The steering gain needed rose (6 to 12 times the fitted one).
- Why lead-lag does not recover: the model's ASH learned a phasic copper response (weight
  2.4 on the change in proximity, 0.04 on proximity itself). Driven by real recorded
  copper input it rises by about 0.48 near copper, a third of the real rise (1.37); in
  closed loop, where model worms near copper are rarely approaching it, the rise vanishes
  (-0.11). Real ASH also stays up while the worm is near copper; the model's does not.

**Version 10: a tonic copper input, and a check on v9's distribution miss**
(`--variants v10`, `docs/figures/closed_loop_v10.csv`). Adding proximity smoothed over a
time constant chosen on validation worms (30 s in two rotations, 15 s in one) raises the
model's ASH response to recorded copper from a rise of 0.61 to 0.90 (real 1.37), but in
closed loop it costs the brain's statistics: 6 of 10 pairwise (distribution,
correlation, lead-lag 1.14 and encoding 1.23 outside) and 25% of time near copper. Keeping
v9 but penalising the copper weights like the rest brings the distribution back inside
(1.05; so that miss did come from the unpenalised weights): 9 of 10 (lead-lag 1.06),
occupancy and approach inside, encounter outside, 11.1% near copper.

The pattern across v7 to v10: every way of making the linear brain respond to copper as
strongly and as persistently as real ASH does disturbs its other statistics, and every way
of keeping those statistics leaves ASH's response, and with it the encounter response and
ASH's lead over the command neurons, too weak. No closed-loop variant passes everything:
v9 passes all of Level 6 at 8 of 10 pairwise; v7, v8 and v9 with penalised weights are 9
of 10 with two of three Level 6 metrics. This looks like a limit of linear dynamics with
additive sensory input, a concrete target for a nonlinear sensory stage.

**Version 11: copper enters the brain only through ASH** (`--variants v11`,
`docs/figures/closed_loop_v11.csv`). The brain's copper weights (fast, change and tonic
inputs) are constrained to ASH's row; every other neuron feels copper only through the
brain's own dynamics [A: sensory neurons receive the stimulus], and reversals come from
the command neurons and ASH with no direct copper term. Driven by real recorded copper,
the model's ASH now rises by 1.11 near copper (real 1.37; v9 0.61, v10 0.90). Over the
three pools: **9 of 10 pairwise and all three Level 6 metrics inside** (encounter 0.943,
approach, occupancy), 13.0% of time near copper: the best combined result so far. The
one miss is still lead-lag (1.08), now for the opposite reason: in closed loop the
command neurons lead ASH (antisymmetric correlation at 6 s, AVE to ASH +0.138 against real
-0.165), plausibly because reversals near copper back the worm off and the next approach
raises ASH again, so ASH follows the commands instead of preceding them. Pattern
correlation with real lead-lag falls to 0.77 (v7: 0.96).

**Timing around events shows the actual cause** (all pools, activity aligned to events):

| | ASH peak (rise) | AVA peak (rise) |
|---|---|---|
| encounter (head first within 1 mm), real | +5.4 s (+0.69) | +11.4 s (+0.10) |
| encounter, v11 | +12.0 s (+0.43) | no rise |
| reversal onset within 1 mm of copper, real | +0.6 s (+0.03) | +6.6 s (+0.62) |
| reversal onset within 1 mm of copper, v11 | +11.4 s (+0.17) | +6.6 s (+0.41) |

Real ASH responds within seconds of meeting copper and is already up when a reversal
starts; the model's ASH responds too slowly (its copper input is dominated by the 30 s
tonic term validation chose), peaking seconds after the reversal. So the remaining
lead-lag miss is the speed of the sensory response, not the re-approach guessed above.

**Version 12** (v11 with the 10-frame brain; `docs/figures/closed_loop_v12.csv`): 9 of 10
(lead-lag 1.07), encounter back outside (0.974), 18.7% near copper: worse than v11 on
Level 6. **Fair Level 8 for the closed loop** (`docs/figures/l8_fair_cl11.csv`,
`l8_fair_cl12.csv`; `run_l8_fair.py --models cl11,cl12`): v11 0.816 held-out, 0.787
in-sample; v12 0.665 held-out (0.759, 0.648, 0.587; p 0.02, 0.03, 0.21) and 0.480
in-sample. With the 10-frame brain, a classifier cannot tell the closed-loop worm's brain
from the worms it imitates, while it moves in its own arena and senses copper.

**A correction and a robustness check for v11.** ASH is labelled in 9 of 16 training
worms of rotation 3, under the 60% needed to enter the model's core neurons, so in the
original v9 and v11 runs that rotation had no ASH: no copper input to the brain and no ASH
in the hazard (copper acted there only through steering and the copper limit). The state
space now keeps classes a model depends on (`include=("ASH",)`). Rerun with ASH present in
all rotations, v11 gives the same picture: 9 of 10 pairwise (lead-lag 1.08), all three
Level 6 metrics inside, 16.2% near copper (`docs/figures/closed_loop_v13.csv`).

**Version 13: a separate sensory stage for ASH** (output error). Even driven by recorded
copper, a one-step fit gives ASH an encounter response far too small (rise 0.21, real
0.71), because ASH's own history explains most of each step. v13 instead fits ASH's copper
component directly to its level on training worms, as a sum of exponential kernels of
proximity; the fitted kernels rise fast and adapt (weights +2.73 at about 3 s, -3.46 at
about 30 s), the encounter response doubles (0.33, peak about 5 s after contact), the
brain models the rest of ASH, and the other neurons receive the copper component. In
closed loop this breaks the brain's statistics like v10 did: 6 of 10 pairwise, 28% near
copper, Level 6 inside. Feeding any copper-derived signal to all neurons does this; v11's
constraint (copper only into ASH's own dynamics) remains the best compromise.

**Version 14** adds the fitted ASH copper response to ASH's output only (recorded ASH and
the reversal hazard), with nothing copper-related entering the brain's dynamics
(`docs/figures/closed_loop_v14.csv`): 9 of 10 (lead-lag 1.08), encounter just outside
(0.964), 14.9% near copper. Across five quite different ways of bringing copper in (v7, v9,
v11, v13, v14), lead-lag sits at 1.05 to 1.09, so it is probably not about how copper
reaches ASH but about the closed loop itself (reversals decided by a hazard and written
back into the brain). Arc 5 rests here for now with v11 as the reference closed loop.


## Arc 4: the causal Turing test

**Question.** Do model brains respond to perturbations like real brains? Every level so
far scores spontaneous activity, which a model can match without getting cause and effect
right. In the signal-propagation atlas (Randi et al. 2023), one neuron at a time is
stimulated optogenetically in immobilised worms while the whole head is imaged; the
response of every other neuron is a direct measurement of how activity spreads.

**Data** (`nematica/data/pumpprobe.py`; local only, not redistributed). The Creamer et al.
2025 packaging of the atlas: 110 recordings, a median of 3,800 frames (about 32 minutes at
0.5 s per frame [M: the original atlas files on OSF carry time stamps, 0.5 s apart]), a median of 122 tracked and 62 named neurons per worm, 5,618
stimulations, of which 3,135 hit a named neuron (negative target indices, 1,164 of them,
mark targets that were not tracked; they are dropped). Neurons are pooled into the same
classes as every other level (AVAL and AVAR are AVA; dorsal and ventral members such as
RMDDL and RMDVR are RMD), so models fitted on our other datasets can be scored here.

**Responses.** For each stimulation of class *i* and each other named neuron of class *j*:
the change from its mean over the 5 s before the pulse, in units of that neuron's SD over
the recording, from 0 to 30 s after; averaged per worm over events and over the members of
each class. A worm's *response set* is all its (*i*, *j*) traces. The unit of measurement,
as everywhere, is worm-to-worm variation: how different two real worms' response sets are,
over the pairs both measured.

**Levels** (each a distance between two response sets over shared pairs):

| level | what it asks |
|---|---|
| `C1.pattern` | Which neurons go up, which go down, and by how much relative to each other? 1 minus the correlation of mean responses (0 to 15 s) across shared pairs. |
| `C2.magnitude` | How big are responses overall? Absolute log ratio of the median absolute response. |
| `C3.kinetics` | How fast do responses rise and decay? Distance between the average normalised time courses of the strongest shared responses. |

**Calibrations, with outcomes designed in advance** (real held-out worms, altered):

| calibration | pattern | magnitude | kinetics |
|---|---|---|---|
| real held-out worms, unaltered | inside | inside | inside |
| stimulation times shuffled (responses read at random frames) | outside | either | either |
| stimulated neuron identities permuted within each worm | outside | inside | either |
| responses scaled by 3 | inside | outside | inside |
| responses time-reversed within the window | either | inside | outside |

**Models to test, in order:**

1. Models fitted on the spontaneous activity of other atlas worms (all frames more than
   30 s from any stimulation), stimulated by clamping the target class to its own measured
   response: VAR at class level, pooled and per worm.
2. The same model families fitted on our copper and Atanas datasets (freely moving worms,
   different strain and conditions): does a brain model learned from behaving worms
   predict how signals propagate?
3. Arc 3's connectome versus shuffled wiring as a hard mask and as a prior: does anatomy
   predict causal responses better than random wiring of the same density? Arc 3 could not
   separate them on spontaneous activity; causal data is the direct test.
4. The published Creamer et al. models, which were fitted to this atlas (scored on worms
   they did not see, where that can be determined).

**Expectations, written before any model is scored:** (a) the calibrations hit their
designed outcomes; (b) models fitted on spontaneous activity get the pattern only partly
right (pattern outside or near the edge), because correlation is not causation and
stimulation drives neurons outside their spontaneous range; (c) models fitted on the
behaving-worm datasets do worse than models fitted on atlas worms; (d) the connectome
mask or prior beats shuffled wiring on pattern more clearly than it did on spontaneous
activity.

**A change to the plan, made before any model was fitted.** Stimulations come every 31 s
and each response window is 30 s, so only about a fifth of each recording (a median of 850
frames) is free of stimulation. That is still about 60,000 frames over the training worms,
enough for a pooled model, so "fitted on spontaneous activity" stays as planned. A second
version of the same model is fitted on *all* frames, stimulations included: it can learn
propagation directly from the stimulated neurons' activity, as the published atlas models
do. Expectation, written now: the all-frames model beats the spontaneous-only model on
pattern.

**Calibration results** (`scripts/run_causal_calib.py`, `docs/figures/causal_calibration.csv`;
3 rotating pools of 36 to 37 worms, frozen in `configs/splits/pumpprobe_cv3.yaml`): **31 of
33 designed outcomes hit.** Shuffled stimulation times and permuted targets fail the
pattern level in every pool; tripled responses fail magnitude and pass pattern; time
reversal fails kinetics. The two misses are both "time reversed should pass magnitude": it
fails in 2 of 3 pools. That was a design error, not a ruler error: reversing a decaying
response moves its weak tail into the 0 to 15 s window, so its size really changes.

One fix was made after the first run, and is reported: the kinetics level first chose its
"strongest shared responses" by raw size, so tripling a worm's responses changed which
pairs were compared and failed kinetics in one pool (30 of 33). It now chooses by rank
within each set, which no scaling can change.

What the calibrations also show, plainly:

- **Worms agree only weakly on the pattern.** Two real worms' response patterns correlate
  at about 0.12 (pattern distance 0.85 to 0.88), against about 0 for shuffled times. Each
  worm measures each pair from only a few stimulations, so single-worm patterns are noisy;
  the atlas papers pooled worms for this reason. The level still separates real responses
  from noise in every pool, but the band of "inside" is wide.
- **Kinetics cannot tell responses from noise.** Responses read at random frames have the
  same average normalised time course as real ones; only time reversal is caught. It is
  kept as a weak level and not used for claims on its own.

**A note on scoring models fairly.** A model's *expected* response is noise-free, while
each real worm's responses are averages of a few noisy stimulations. A model scored on
expected responses would look too typical for that reason alone. So models are scored the
way worms are measured: each model runs the whole recording with its own noise, is
stimulated on the worm's own schedule, and its responses go through the same pipeline.

**First baseline: the atlas average.** Each worm's responses predicted by the mean response
of each pair over the *training* worms (the other two pools): what any model that learned
the average atlas perfectly would say. Expectations, written before it was run: too typical
on pattern (an average correlates with each worm better than worms do with each other);
outside on magnitude (averaging over worms shrinks responses).

Result (`docs/figures/causal_baselines.csv`): both expectations met in all three pools.
The atlas average correlates with each held-out worm at about 0.31 (pattern distance 0.68
to 0.71, at the 14th to 17th percentile of real pairs: too typical), and its responses are
too small (magnitude outside). So the target is clear: a good model is not one that
reproduces the average atlas, but one whose simulated worms differ from real worms as much
as real worms differ from each other.

**First models: VAR(3) at class level** (`nematica/systems/causal_models.py`,
`scripts/run_causal_models.py`, `docs/figures/causal_models.csv`). A pooled ridge VAR(3) on
class activity of the atlas training worms, one fitted on spontaneous frames and one on all
frames; each pool worm simulated with the model's own noise and stimulated on its own
schedule (the stimulated class follows its neuron's measured response). Two assumptions
had to be added, both stated in the code: classes a worm does not show stay at zero in
simulation, as missing classes did in training; and the fitted dynamics, slightly
explosive (spectral radius 1.07 to 1.13, from slow drifts in the recordings), are scaled to
radius 0.99 where needed.

| model | pattern (distance; real pairs 0.85 to 0.88) | magnitude | kinetics |
|---|---|---|---|
| VAR(3), spontaneous frames | outside in 3 of 3 pools (0.96 to 0.97) | outside in 3 of 3 | inside 1, too typical 2 |
| VAR(3), all frames | outside in 3 of 3 (0.96 to 0.97) | outside in 3 of 3 | inside 2, too typical 1 |

Against the expectations: (b) met, and more strongly than "partly": both models' simulated
responses correlate with real worms at only 0.03 to 0.04, against 0.12 between real worms.
The all-frames model is closer than the spontaneous one in every pool, as expected, but by
a hair (0.004 to 0.011). Magnitudes are too large: model worms respond about twice as
strongly as real worms in units of each neuron's own variability. A linear model of
spontaneous class activity, even one that has seen the stimulations, does not know how
signals spread through this brain. That is the causal Turing test's first answer, and the
reason the test is needed: these same model families pass most spontaneous levels.

**The published atlas models, expectations written before scoring.** The three linear
dynamical systems of Creamer, Leifer and Pillow (2024: connectome-constrained, fully
connected, and constrained to a shuffled connectome), 154 named neurons, fitted to this
atlas, put through the same stimulation protocol at neuron level. They were fitted to atlas
worms, probably including the ones scored here, so this is in-sample. Expectations: much
closer to real worms than the class VARs on pattern (inside or near the edge); the
connectome-constrained model closer than the shuffled one in every pool.

Result (`scripts/run_causal_models.py --models creamer2024_...`,
`docs/figures/causal_models_creamer.csv`):

| published model | pattern (real pairs 0.85 to 0.88) | magnitude | kinetics |
|---|---|---|---|
| connectome-constrained | outside in 3 of 3 (0.97 to 0.98) | outside 3 of 3 | inside 3 of 3 |
| fully connected | outside in 3 of 3 (0.93 to 0.95) | outside 3 of 3 | outside 2, inside 1 |
| shuffled connectome | outside in 3 of 3 (0.98 to 0.99) | outside 3 of 3 | inside 3 of 3 |

The connectome-constrained model is closer than the shuffled one in every pool (met), but
none is near real worms: simulated worms' patterns correlate with real worms at 0.01 to
0.07, against 0.12 between real worms. The "inside or near the edge" expectation is not
met. Two cautions before reading this as "the published models fail": the protocol here
clamps the stimulated neuron to its measured response, while the authors model
stimulation as an input and infer hidden states; and the magnitude level may penalise any
stationary model, because real neurons' SDs include slow drifts that models do not have.
Both are being checked.

**Two more pieces of the original atlas archive** (Randi et al. 2023, OSF e2syt; local
only). (1) 18 recordings of *unc-31* mutants, which cannot release neuropeptides from dense
core vesicles, stimulated with the same protocol: 15 have neuron identities and are used.
(2) 2 recordings of unstimulated immobilised worms (10 minutes each); too few to fit a
model on, kept for later.

**unc-31 against wild type, written before running:**

1. *Through the ruler.* unc-31 worms' response sets, scored as a "system" against each
   wild-type pool. Expectation: inside on pattern and kinetics (they are real worms, and the
   mutation changes a minority of pairs while single-worm patterns are noisy); no prior on
   magnitude. If unc-31 worms are inside, the ruler cannot see the mutation one worm at a
   time, which says something about its resolution.
2. *Does anatomy predict responses?* For each worm, how well class-level wiring (Kunert et
   al. 2014, chemical or electrical, as in arc 3) separates responding pairs: the AUC of
   response size for wired against unwired pairs, minus the mean AUC over 20 shuffled
   wirings with the same number of inputs per class. Expectations: (a) the excess is above
   zero in wild type, but small; (b) it is larger in unc-31 worms than in wild type, as the
   atlas paper reported that anatomy predicts responses better without neuropeptides.

**unc-31 results, and a lesson about preprocessing** (`scripts/run_unc31.py`,
`docs/figures/unc31_vs_wt.csv`, `docs/figures/wiring_predicts_responses.csv`). The first run
compared unc-31 worms (from the original archive) with wild-type worms from the Creamer
packaging, and unc-31 came out *outside* on magnitude and kinetics in every pool. That was
not biology: the two packagings hold the same raw values, but the Creamer version blanks
18 to 50% of each neuron's frames (low-confidence tracking) and some uncertain labels,
while the original archive keeps them. With wild type taken from the same original
archive (113 worms, converted the same way), the comparison is like for like:

- unc-31 worms are **inside on all three levels** in every pool (kinetics too typical in
  one). Expectation 1 met: one worm at a time, the ruler cannot tell a neuropeptide-release
  mutant from wild type. That is a statement about resolution: single-worm response sets
  are noisy, and the mutation's effects are on a minority of pairs.
- Wiring predicts response size slightly better than shuffled wiring in wild type (median
  AUC excess +0.014, above zero in 73 of 105 worms, Wilcoxon p = 1e-5): expectation 2a met.
  In unc-31 the excess is +0.010 (9 of 15, p = 0.02): **not larger** than wild type
  (p = 0.48). Expectation 2b not met at this resolution (class level, AUC per worm, 15
  mutant worms).

The model scores above use the Creamer packaging throughout (real and simulated worms on
the same recordings), so they are internally consistent; they will be repeated on the
original archive.

**The headline test: same models, same worms** (`scripts/run_same_worms.py`). The claim
"a model can look right at rest and still be wrong about cause and effect" needs both
verdicts on the same recordings. Here everything uses the original archive (wild type, 113
worms, frozen pools): models fitted on training worms; each pool worm and its simulated
twin stimulated on the same schedule; the simulated worm then scored on the ordinary
activity levels (distributions, timescales, correlations, dimensionality, lead-lag, AVA
bouts) *and* on the causal levels. Expectation, written before running: the atlas-fitted
VAR(3) and the published fully connected model pass at least half of the activity levels
in most pools, while failing causal pattern in every pool. If they fail the activity levels
too, the headline is not supported in this form and will not be claimed.

**Result** (`docs/figures/same_worms.csv`; activity levels: distribution, timescale,
correlation, dimension, lead-lag, AVA bouts):

| model | activity levels inside (pools 1, 2, 3) | causal pattern | causal magnitude |
|---|---|---|---|
| VAR(3), spontaneous frames | 5, 5, 5 of 6 (only dimension misses) | outside in 3 of 3 | outside in 3 of 3 |
| VAR(3), all frames | 4, 4, 3 of 6 | outside in 3 of 3 | outside in 3 of 3 |
| published, fully connected | 2, 2, 3 of 6 (too typical on timescale and correlation) | outside in 3 of 3 | inside in 2 of 3 |
| published, connectome-constrained | 3, 2, 3 of 6 | outside in 3 of 3 | inside in 2 of 3 |

**The headline holds for the VAR fitted on spontaneous activity:** on the same worms, under
the same stimulations, it is indistinguishable from real worms on five of six ordinary
activity statistics in every pool, and wrong about how stimulation spreads in every pool.
A brain model can look like a real brain at rest and still be wrong about cause and
effect; the causal levels catch what the activity levels cannot. The published models do
not meet the "look right at rest" half (their spontaneous activity is too regular: too
typical), so for them the expectation is not met. On this archive's preprocessing the
published models' response *sizes* pass in two pools; the magnitude failures on the
Creamer packaging were at least partly a normalisation effect, as suspected.

## Can you verify a brain copy by watching it?

The headline result raises a sharper question, which matters well beyond worms: **does a
brain model's realism at rest tell you anything about whether it gets cause and effect
right?** If not, no amount of watching can certify a copy of a brain; you have to
intervene. Three experiments, all on the original archive (113 wild-type worms, frozen
pools), with expectations written before any of them ran.

**A. Two checks on the headline.**
- *Units.* Response sizes have been in units of each neuron's SD over the whole recording,
  which slow drift inflates in real worms but not in models. Rerun with units of each
  neuron's fluctuation size just before stimulation (`norm="fluct"`). Expectation: the
  VAR's magnitude distance shrinks; pattern verdicts do not change.
- *Protocol.* Besides clamping the stimulated neuron to its measured response, stimulate by
  a one-frame input pulse sized to the neuron's measured peak, after which the model's own
  dynamics run (`@pulse`), for our models and the published ones. Expectation: pattern
  stays outside for every model under both protocols.

**B. Rest against poke, across many artificial brains.** Sixteen brains: VAR with 1, 3, 6
and 10 frames of memory, each fitted on spontaneous or on all frames; the three published
models under both protocols; and a deliberately causal-blind control, a VAR in which each
class is driven only by its own past (`diagonal`), which can reproduce single-neuron
statistics but propagates nothing. For each: a rest score (median absolute log ratio of
model-to-real over real-to-real distance across the six activity levels) and a poke score
(pattern distance). Expectation: the rank correlation between rest and poke scores across
brains is weak (|Spearman rho| < 0.4), and the diagonal control is not the worst at rest.
If rest realism does predict poke realism, watching is a usable proxy and that will be
reported.

**C. Does a worm's own resting activity reveal its own wiring?** For each worm, a VAR(2)
fitted only on its own stimulation-free frames, simulated under its own stimulations, and
compared with the same worm simulated by five other worms' own models. Expectation: a worm's
own model is no closer to its real echoes than other worms' models are (paired difference
within 0.01 of pattern distance, Wilcoxon p > 0.05). Alongside, the *causal fingerprint*:
each worm's stimulations split into odd and even events; is a worm's odd-half echo pattern
closer to its own even half than to other worms' even halves? Expectation: yes, modestly
(within-worm distance smaller in most worms), so worms have individual causal signatures
that a faithful copy would need, and that watching does not reveal.

**A, results.** *Units:* measuring responses in units of each neuron's pre-stimulus
fluctuations instead of its whole-recording SD shrinks the VARs' magnitude distance by a
third to a half (VAR(3) from rest: 0.55 to 0.66 down to 0.34 to 0.38), as expected, but
magnitude stays outside; pattern verdicts do not change for any model (met). *Protocol:*
stimulating by a one-frame pulse instead of clamping makes every model worse on pattern
(published fully connected 0.92 to 0.94 with the clamp, 0.99 with a pulse); pattern is
outside for every model under both protocols (met). The clamp, which feeds models the
stimulated neuron's real response, is the kinder of the two.

**B, results** (`scripts/analyse_rest_vs_poke.py`, `docs/figures/rest_vs_poke.csv`). Across
the 16 pre-registered brains, the rank correlation between rest score and poke score is
+0.07, -0.47 and -0.30 in the three pools, -0.21 pooled (48 brain-pools, p = 0.15); with the
ingredient-hunt brains added, -0.03, -0.18 and -0.02, -0.06 pooled (88 brain-pools, p =
0.56). **How real a brain model looks at rest says nothing about whether it answers a poke
correctly.** If anything the sign leans the wrong way (better at rest, slightly worse when
poked), most visibly in pool 2. Expectation: met pooled and in 2 of 3 pools (pool 2 at -0.47
crosses the 0.4 line). The causal-blind control (each class driven only by its own past)
*is* the worst or nearly the worst at rest in two pools (16th and 15th of 16) but mid-table
in the third: the "not the worst at rest" half of the expectation is not met, so the rest
levels do notice a brain with no coupling at all. They just cannot tell a brain with the
wrong coupling from one with the right coupling.

**C, results** (`scripts/run_own_rest.py`, `docs/figures/own_rest_fingerprint_fluct.csv`).
44 worms have enough stimulation-free activity (at least 300 frames) for a model of their
own; 43 have enough stimulations for the split.

- *Own rest does not reveal own wiring.* A worm's own model is no closer to its real
  echoes than other worms' models (pattern distance 0.931 against 0.946; own closer in 26
  of 44; median paired difference -0.008, Wilcoxon p = 0.11). Expectation met: watching a
  worm's brain at rest does not tell you how *that* brain answers a poke, beyond what any
  worm's brain tells you.
- *But worms do have causal fingerprints.* A worm's odd-half echoes are closer to its own
  even half than to other worms' (0.853 against 0.922; 36 of 43 worms; p = 5e-6).
  Identification from echoes alone is weak (own half ranked first in 2 of 43, median rank 8
  of 42, where chance would be 21). It is not a recording-day effect: other worms recorded
  the same day are no closer than worms from other days (0.919 against 0.933; p = 0.18),
  and both are further than the worm itself (p = 7e-5). One alternative cannot be ruled out
  here: worm-specific measurement quirks (a consistently mislabelled neuron, say) would also
  look like a fingerprint.

Together: each worm's brain answers pokes in its own, repeatable way, and that individual
causal signature is invisible in its resting activity, as far as a linear model fitted to
that activity can see. A copy built by watching would miss it.

**D. The ingredient hunt: what would it take to pass the poke test?** Every brain so far
fails it. Rather than stop at a negative result, add one candidate ingredient at a time to
the VAR and see which, if any, brings the echo to real. Candidates (all fitted on training
worms only, scored on the same held-out worms, with perturbational complexity added):

| model | ingredient |
|---|---|
| `var3_stim` | learns only from the 30 s after stimulations: cause and effect, not rest |
| `var3_all_relu` | nonlinear propagation: a class's influence changes once it is strongly active (rectified copies of the last frame beyond 1 SD) |
| `var3_all_lasso` | sparse coupling: most neuron pairs do not influence each other at all |
| `var3_stim_relu` | the first two together |
| `var10_stim` | learning from stimulation with 5 s of memory |

Expectations, written before running: learning from stimulation improves pattern the most
(closer to real worms than every rest-fitted model, in every pool) but stays outside;
nonlinearity and sparsity each shrink spread toward real (3 to 4% of the brain); no single
ingredient passes pattern. **Passing the poke test** is defined now, in advance: pattern
inside in at least 2 of 3 pools *and* spread inside in at least 2 of 3. If something passes,
it is then checked at rest too: a model that passes the poke test but fails at rest would
be the mirror image of the headline.

**D2. Watching plus poking (written before running).** If watching teaches the ongoing
dynamics and only poking teaches cause and effect, a brain model may need both, learned
separately. `hybrid_kernels`: the VAR fitted on stimulation-free frames supplies ongoing
activity, and causal kernels learned from the training worms' stimulations (each pair's
mean echo, shrunk toward zero when rarely measured) supply the echoes. Two anatomical
versions test the wiring question with causal data: kernels allowed only between classes
the connectome connects (`_connectome`), or only along a shuffled wiring of the same
density (`_shuffled`). Expectations: the hybrid passes the poke test as defined above
(pattern and spread inside in at least 2 of 3 pools) while keeping the VAR's rest score (5
of 6); the connectome-restricted kernels beat the shuffled ones on pattern in every pool.
If the hybrid passes, the lesson is constructive: a faithful brain copy needs two kinds of
knowledge, and only one of them can be had by watching.

**D and D2 results so far** (`results/same_worms_pci`, to be gathered into
`docs/figures/ingredients.csv` when all pools finish; original archive, response units of
pre-stimulus fluctuations; real echoes reach a median of about 16% of the brain in these
units):

| model | rest (of 6) | pattern (real 0.89 to 0.91) | spread |
|---|---|---|---|
| VAR(3) from rest | 5 | 0.99, outside | 26%, outside |
| VAR(3) from pokes | 2 to 4 | 0.98 to 0.99, outside | 17 to 30%, outside |
| VAR(3), rectified features | 4 | 0.99, outside | 27 to 28%, outside |
| VAR(3), sparse coupling | 2 | 0.99, outside | 32%, outside |
| **hybrid: rest dynamics + causal kernels** | 4 | **0.909, 0.919, 0.924: inside in 2 of 3** | 26%, outside |
| hybrid, kernels only along the connectome | 3 to 5 | 0.98, outside | 24 to 25%, outside |
| hybrid, kernels along shuffled wiring | 3 to 5 | 0.99 to 1.00, outside | 24 to 25%, outside |

- **The first artificial brain whose echoes have a real worm's pattern**: the hybrid sits at
  the real worm-to-worm median in pools 1 and 3 (52nd percentile in pool 1). None of the
  dynamical ingredients (nonlinearity, sparsity, learning from pokes) came close: a model
  trained to predict the next half-second does not learn where a poke's echo goes, even
  when it is trained on pokes. Causal structure had to be learned *as* causal structure.
- **It does not pass the poke test as defined in advance**: its echoes still spread too far
  (26% against 16%), in every pool. The excess comes from the ongoing dynamics (it is the
  same in the VAR alone): over 30 s, the model's activity wanders further from its starting
  point than real activity does.
- **Anatomy, with causal data:** kernels restricted to connectome edges beat kernels along
  shuffled wiring in every pool (expectation met), but both are far worse than unrestricted
  kernels. Most of the echo travels between classes that are not directly wired together:
  at class level, the wiring diagram is a poor map of where signals go.
- Expectations: learning from pokes did not beat every rest-fitted model on pattern (not
  met); nonlinearity and sparsity did not shrink spread (not met); the hybrid kept the
  VAR's rest score only partly (4 of 6, not 5: timescale fails).

**Next ingredient (written before running): the hybrid with its ongoing dynamics learned
from the stimulation windows** (`hybrid_kernels_bgstim`), whose VARs had realistic spread
levels (17%). Expectation: pattern stays inside in at least 2 of 3 pools and spread comes
inside in at least 2 of 3, which would be the first pass of the poke test.

Result: pattern inside in 2 of 3 pools (0.906, 0.919, 0.922), spread outside in all 3 (25%):
the expectation is not met, and the hybrid with measurement noise behaves like the hybrid
without it. A further check with heavy-tailed shocks in the dynamics (Student-t, fitted to the
residuals' kurtosis) did not change spread either.

**What the spread level is really measuring.** Reading "responses" at random moments, with
no poke at all, gives the answer: real brains score a median of 14% (5th percentile 6%),
model brains 25% (5th percentile 18%). Real poke echoes score 16%, so most of the spread
level is not the echo; it is how ongoing activity evolves over 30 s compared with its jitter
just before. **Real worm brains are often quiet over half a minute and sometimes eventful;
every model brain tested is always busy.** That is a property of ongoing activity that the
six ordinary activity levels do not catch (they look at distributions, correlations and
timescales, not at how calm or eventful a stretch of activity is), and it connects directly
to the next measures below: a brain that is "always busy" is a different kind of system from
one that settles and wakes.

So far, then: cause and effect can be given to a model (the hybrid's echo patterns are
real-like), but a real brain's way of being quiet cannot yet, by any ingredient tried.

**Two more ingredients for calm (written before scoring).** Both are calibrated on training
worms only, to match their "spread at random moments" (5th, 50th and 95th percentiles: 6%,
17% and 28%):
- `hybrid_kernels_regimes`: the dynamics' driving noise switches between a quiet and an
  active gain (hidden two-state chain; share of quiet time, dwell and gain chosen on training
  worms). On calibration it reaches 4%, 26%, 33%: it widens the low end but cannot bring the
  median down.
- `hybrid_kernels_obsfit`: a single share of white measurement noise for all classes, chosen
  the same way: 10%, reaching 11%, 18%, 24% on calibration (median right, range too narrow).
- `hybrid_kernels_regimes_obsfit`: both.

Expectation for the poke test on held-out worms: `obsfit` brings spread inside in at least 2
of 3 pools with pattern still inside in at least 2 of 3, which would be the first full pass
of the poke test; the combination does at least as well. Calibration shows the median of
"calm" is set by how much fast, non-propagating noise sits on top of the slow dynamics,
which the autocovariance estimate (6%) understated.

**Result: the first artificial brain to pass the poke test** (`docs/figures/ingredients.csv`):

| model | rest (of 6) | pattern (real 0.89 to 0.91) | spread | magnitude | kinetics | perturbational complexity |
|---|---|---|---|---|---|---|
| hybrid + measurement noise | 3, 4, 4 | 0.892, 0.909, 0.907: inside 3 of 3 | 19 to 20%: inside 1 of 3 | outside 2 of 3 | inside 3 of 3 | outside 3 of 3 |
| **hybrid + measurement noise + quiet/active regimes** | 3, 3, 4 | **0.884, 0.912, 0.910: inside 3 of 3** | **20 to 21%: inside 3 of 3** | inside 2 of 3 | inside 3 of 3 | outside 3 of 3 |

By the definition written before any of these ingredients was tried (pattern and spread
inside in at least 2 of 3 pools), **the hybrid with measurement noise and quiet/active regimes
passes the poke test, in all three held-out pools**, and passes magnitude and kinetics too.
(An earlier version ignored the regimes whenever measurement noise was on; it was fixed and
rerun, and only the fixed results are shown.)

What it took, in order of discovery: causal links learned *from pokes*, as links rather than
as one-step dynamics; ongoing dynamics learned *by watching*; fast noise that does not
propagate; and a brain that alternates between calm and active stretches. No single
ingredient was enough.

What it still fails, honestly: perturbational complexity (the PCI distribution of its echoes
is outside in every pool), and it is weaker at rest than the plain VAR (3 or 4 of the 6
activity levels, against 5). So it is the mirror image of the headline only in part: the
first model that answers a poke like a real worm is not yet the one that looks most like a
real worm at rest. One brain model that does both is the next target.

**Merging rest and poke (written before running).** The passing hybrid's rest failures are
mostly dimensionality (outside in every pool, model activity spread over 1.6 to 2.1 times
too many dimensions), inherited from the class-level VAR, which fails it too. Real worm
brains are low-dimensional: on the stimulated worms, participation ratio 16 for real worms
against 25 for the class VAR. New background, `LowRankVAR`: a few shared brain-wide modes
(top 6 principal directions of training activity, their own VAR) plus private per-class
activity; on a check with 8 pool worms it gives 18. Model `hybrid_kernels_regimes_obsfit_lowrank6`.
Expectation: dimension comes inside, rest reaches at least 5 of 6 in at least 2 of 3 pools,
and the poke test is still passed (pattern and spread inside in at least 2 of 3): one brain
that is real-like both watched and poked.

Result (`results/same_worms_pci`, gathered in `docs/figures/ingredients.csv`): the poke test
is still passed (pattern inside 3 of 3, spread inside 2 of 3) and dimensionality improves
(ratio to real 1.3 to 1.4 instead of 1.6 to 2.1; inside in 2 of 3), but rest stays at 3 of 6:
correlations become too typical in every pool (0.89 to 0.94 of the real spread) and lead-lag
falls outside in every pool. Expectation not met. A few shared modes make every simulated
worm's correlations the *average* worm's correlations: the low-rank brain is too typical,
arc 1's lesson again. The next ingredient is individuality: each simulated worm's background
its own, as in the per-worm VARs that pass all 10 levels on the copper data.

Result, pool 1: pattern inside again (0.916, 54th percentile), but spread *worse* (30%):
expectation not met, and the remaining pools are not needed to see it. Looking at why: the
spread level counts responses above 3 times each neuron's fluctuation size just before the
poke, and a VAR turns all of its noise into slow wandering, while real recordings also
contain fast measurement noise that does not propagate. A model without measurement noise
wanders too far relative to its own jitter.

**Next ingredient (written before running): measurement noise** (`hybrid_kernels_obs`). The
share of each class's variance that is white measurement noise is estimated from real
stimulation-free activity (autocovariance at lags 0 to 2: a median of 6%), removed from the
dynamics' driving noise and added back as white noise on the output. Expectation: spread
comes inside in at least 2 of 3 pools while pattern stays inside in at least 2 of 3: the
first pass of the poke test.

**Why does echo complexity still fail? (hypothesis written before computing).** The passing
hybrid gives every poke of the same neuron class the same average echo (its kernel) on top
of background activity, while a real brain answers the same poke differently each time.
Prediction: (1) the hybrid's echoes are *less* complex than real ones (lower median PCI);
(2) real echoes to repeated pokes of the same class differ more from each other than the
hybrid's do (lower correlation between repeats in real worms). If both hold, the missing
ingredient for complexity is trial-to-trial variability in the causal response itself.

Result (`scripts/run_pci_why.py`, pool 1): **the hypothesis is wrong, in the opposite
direction.** The hybrid's echoes are *more* complex than real ones (median PCI 0.89 against
0.67), and repeated pokes of the same class are about as dissimilar in the model as in real
worms (correlation between repeats 0.11 against 0.09; p = 0.15). Real echoes are more
compressible: when a real neuron responds, it stays responding for a stretch, and neurons
respond together, so the significance pattern comes in coherent blocks. The model's pattern
is speckled, most likely by the very ingredient that fixed spread: white measurement noise
crosses the threshold at isolated moments. Next (to be pre-registered): measurement noise
that is smooth in time, or a threshold that requires a response to last.

**Smooth measurement noise (written before running).** `hybrid_kernels_regimes_obsfit_smooth0.8`:
the same model, with its measurement noise correlated over about 2.5 s (AR(1), coefficient
0.8, same variance; the share is recalibrated on training worms as before). Expectation:
echo complexity moves toward real (median PCI below the white-noise version's 0.89), and the
poke test stays passed; complexity inside in at least 2 of 3 pools would make it the first
model to match a real brain's perturbational complexity.

Result: no change (pool 1 PCI distance 0.907, as with white noise). The cause is elsewhere.
A diagnostic (`scripts/diag_echo_structure.py`, pool 1, not pre-registered) finds it:

| | median length of a response (frames) | steps where the responding set changes | classes that respond at all in 30 s |
|---|---|---|---|
| real worms | 3 (mean 6.5) | 85% | 66% |
| VAR(3) | 2 (mean 5.2) | 97% | 93% |
| passing hybrid | 1 (mean 3.4) | 98% | 95% |

**In a real brain, a third of the neuron classes never cross the threshold in the 30 s after
a poke, and the ones that do stay responding; in every model, almost every class flickers
across it at some point, briefly.** Real echoes are complex but structured because most of
the brain stays out of them. This is the same theme as the calm finding, at the level of
single neurons: real brains have neurons that are quiet for long stretches while others are
active, and every model gives every neuron the same restlessness. The next ingredient is
per-class quiet and active states (each class with its own share of quiet time), to be
pre-registered.

**Per-class quiet states (written before scoring on held-out worms).** A decomposition on
pool 1 (diagnostic, not pre-registered) located the restlessness: it is the ongoing dynamics,
not the causal kernels (background alone: 93% of classes cross the threshold in 30 s, PCI
0.81; real 65%, 0.67), and the white measurement noise that fixed spread *raises* PCI (0.89),
so spread and complexity pull against each other. New ingredient: each class has its own
quiet and active stretches; in a quiet stretch it decouples from the rest and settles. Each
class's share of quiet time starts from how often it stays out of a random 30 s window in
the training worms, and its scale, how still a quiet class is, and the measurement-noise
share are calibrated jointly on training worms to match three things at random moments: the
share of classes that cross the threshold, the spread, and the PCI
(`hybrid_kernels_quietobsfit`). On calibration without measurement noise it already gives
73% of classes and PCI 0.64 (real 65%, 0.67), with spread too high. Expectation: echo
complexity inside in at least 2 of 3 pools, and the poke test still passed (pattern and
spread inside in at least 2 of 3): the first model to match a real brain's perturbational
complexity.

Result (`docs/figures/ingredients.csv`): **echo complexity moves most of the way toward real
but stays outside** (PCI distance 0.47 to 0.56, against 0.88 to 0.93 for the earlier hybrids
and 0.35 to 0.37 between real worms); pattern stays inside in 2 of 3 pools, spread falls back
inside in only 1 of 3, and rest collapses to 1 or 2 of 6 (distributions, correlations,
dimension and lead-lag all fail): decoupling quiet classes breaks the brain's ordinary
statistics. Expectation not met.

**Where the ingredient hunt stands.** Every property can be reached on its own, but in this
family of models (linear dynamics, Gaussian noise, learned causal kernels) they trade off:

| what the ingredient fixes | what it costs |
|---|---|
| causal kernels learned from pokes: echo pattern | nothing measurable |
| fast measurement noise: spread | echo complexity gets worse |
| calm/active regimes (whole brain): spread distribution | a little rest realism |
| a few shared modes: dimensionality | correlations become too typical |
| per-class quiet stretches: echo complexity, most of the way | rest realism collapses |
| individual backgrounds: correlations no longer too typical | timescale, bouts, lead-lag |
| a learned nonlinear background (GRU): spread and magnitude, with nothing hand-tuned | rest realism; complexity unchanged |

Real brains have all of these at once. A model that does too will probably need what none of
these have: activity that is genuinely nonlinear in time (neurons that switch on and stay on,
others that stay off), learned from the brain itself rather than assembled from parts. That
is the next target, together with individual backgrounds (each simulated worm its own
dynamics), which the copper data showed is what makes a brain model look like a particular
worm rather than an average one.

**Individual backgrounds (written before running).** `hybrid_kernels_regimes_obsfit_indiv`:
the passing hybrid, but each simulated worm's ongoing dynamics come from one training worm's
own VAR (its stimulation-free frames, shrunk toward the pooled VAR with weight 300, as the
per-worm models that pass all 10 levels on the copper data), chosen by worm. Calibrations
(regimes, measurement noise) as before, on the pooled background. Expectation: correlations
are no longer too typical, rest reaches at least 5 of 6 in at least 2 of 3 pools, and the
poke test is still passed (pattern and spread inside in at least 2 of 3).

Result: correlations stop being too typical (inside in 2 of 3), and the poke test is still
passed (pattern inside in 2 of 3, too typical in the third; spread inside in all 3), but rest
falls to 1 or 2 of 6: one worm's stimulation-free frames (about 850) are too few for its own
VAR, whose dynamics come out too slow (timescale 1.4 to 1.7 times real, bout lengths and
lead-lag outside). Expectation not met. Individuality needs more data per worm than the
atlas's stimulation-free stretches give.

**A nonlinear background (written before running).** `hybrid_kernels_gru64`: the causal
kernels on top of a GRU learned from the training worms' stimulation-free stretches, which
predicts both the next frame and how large its fluctuation will be, so calm can be calm
(`AtlasGRU`; no regimes, no measurement noise, nothing calibrated by hand). On a quick check
(pool 1, 6 worms, a shorter training run) its spread at random moments is already real-like
(12% against 13%), with too many classes crossing the threshold (87% against 62%) and echo
complexity still too high (0.88 against 0.67). Expectation: the poke test is passed (pattern
and spread inside in at least 2 of 3) with rest at least 4 of 6; complexity: no strong prior.

Result: **the poke test is passed with nothing calibrated by hand**: echo spread comes out
real-like in all three pools (14 to 15%, against 16% for real echoes in these units) because
the GRU learned when to be calm; pattern inside in 2 of 3 (too typical in the third), and
magnitude inside in all 3, a first. But rest is 0 to 2 of 6 (its activity is too slow,
timescale 1.4 to 1.8 times real, and too regular: distributions too typical, correlations and
lead-lag outside), and echo complexity is as far from real as ever (PCI distance 0.94). Half
of the expectation met. A learned nonlinear brain finds calm by itself, which no linear
ingredient did, but a short training run on about 140 stimulation-free stretches does not
give it realistic ongoing dynamics.

**A better-trained nonlinear brain (written before running).** Two changes to the GRU: twice
the training (3,000 steps), and free-running training (scheduled sampling: by the end, half
of its inputs are its own previous samples rather than the data), so the slow drift that
builds up when it runs on its own is what it learns to avoid. `hybrid_kernels_gru64ss`, and
the same with per-class quiet stretches calibrated as before (`hybrid_kernels_gru64ss_quietfit`).
Expectations: for the first, timescale and distributions come inside and rest reaches at
least 4 of 6 in at least 2 of 3 pools with the poke test still passed; for the second, echo
complexity inside in at least 2 of 3 pools. A brain that does all three (rest at least 5 of
6, poke test, complexity) would be confirmed on a second frozen split before being claimed.

Result for `hybrid_kernels_gru64ss` (pools 1 and 2; pool 3 and the quiet-stretch variant were
stopped once the direction was clear): **worse, not better.** Free-running training makes the
GRU's activity even slower (timescale 1.8 to 2.5 times real) and calmer than real (echo spread
9 to 11%, now *below* real 16%, outside), rest 1 of 6, and complexity unchanged. Expectation
not met. Trained to survive its own errors, the network learns to play it safe: smooth, slow
activity. Getting a learned brain's ongoing dynamics right will need an objective that looks
at the statistics the ruler checks (timescales, correlations), not only next-frame likelihood.

**Confirmation on a second frozen split (written before running).** Every arc 4 result so
far uses one frozen set of three pools. A second set, `configs/splits/pumpprobe_cv3_blocks1.yaml`
(hash b1103bc34a2c6fe8): the same 110 worms in recording order, in blocks of three, with the
pool assignment permuted within each block, so each new pool shares only 8 to 16 worms with
any old pool and stays spread over recording days. Brains: the one that passes the poke test
(`hybrid_kernels_regimes_obsfit`), the plain hybrid (`hybrid_kernels`) and the linear brain
learned from rest (`var3_spontaneous`), scored on all eleven levels (`run_same_worms.py --pci`).
Expectations: the passing hybrid keeps echo pattern and echo spread inside in at least 2 of 3
new pools; the linear brain stays outside on echo pattern in 3 of 3 and inside on at least 4 of
6 activity levels in at least 2 of 3; echo complexity stays outside for all three brains. If
the passing hybrid fails the pattern or spread in 2 or more new pools, the site will stop
calling it a brain that passes the poke test.

Result (`docs/figures/same_worms_recording_blocks1.csv`; new pools 1, 2, 3):

| brain | activity levels inside | echo pattern | echo spread | echo complexity |
|---|---|---|---|---|
| passing hybrid | 4, 5, 4 of 6 | inside 3 of 3 | inside 3 of 3 | outside 3 of 3 |
| plain hybrid | 4, 4, 6 of 6 | inside 2 of 3 | outside 3 of 3 | outside 3 of 3 |
| linear brain from rest | 3, 4, 5 of 6 | outside 3 of 3 | outside 3 of 3 | outside 3 of 3 |

**All expectations met: the poke-test pass replicates on a second split**, in all three new
pools, as does the headline (the linear brain learned from rest is real-like at rest in 2 of 3
pools and wrong about cause and effect in all three). The passing hybrid also looks a little
more real at rest here (4 to 5 of 6, against 3 to 4 on the first split), and in one new pool
the plain hybrid is inside on all six activity levels while its echo pattern is inside too:
the first time any brain has matched real worms on every watching test and on the echo
pattern at once, though its echo spread and complexity are still outside. That combination
is one pool on one split, so it is noted, not claimed.

**Signal or noise? (written before computing it).** A model can fail the poke test in two
different ways: its *average* echo is wrong (it does not know the causal structure), or its
average echo is right but each single echo is buried in the wrong kind of variability.
Diagnostic: for each held-out worm, the model's echo averaged over 10 simulated repeats of
the whole experiment, correlated (across pairs) with the atlas average of the training
worms; compared with how well one real worm's echoes correlate with that average (about
0.31). If a model's averaged echo reaches 0.31, its failure is about trial-to-trial
variability, not cause and effect, and the headline will be restated accordingly.

Result (`scripts/run_signal_noise.py`, `docs/figures/signal_noise_f0.csv`; pool 1, original
archive, response units of pre-stimulus fluctuations, where one real worm correlates with
the atlas average at 0.26):

| brain | single simulated worm vs atlas average | 10 repeats averaged vs atlas average |
|---|---|---|
| VAR(3), learned from rest | 0.04 | 0.05 |
| VAR(3), rectified features | 0.05 | 0.09 |
| VAR(3), learned from pokes | 0.07 | 0.12 |
| published, fully connected | 0.16 | 0.20 |

Averaging away the noise barely helps: even ten repeats of the whole experiment give an echo
that agrees with the atlas less than *one* real worm does. **The failure is about cause and
effect, not trial-to-trial noise**, so the headline stands as stated. The published model,
fitted to the atlas itself, comes closest; learning from pokes helps the VAR (0.05 to 0.12)
but far from enough.

**What does "inside" mean on the poke pattern? (written before computing it).** The
pattern level asks whether a brain's echoes (which neuron answers which poke, and how
strongly) agree with a real worm's about as well as two real worms agree with each other.
Real worms agree only weakly (correlation about 0.1 between two worms, about 0.31 between
one worm and the average of the training worms), so a reader can fairly ask how much true
cause and effect a brain needs before the test notices. Power analysis
(`scripts/run_causal_power.py`): synthetic brains whose echoes are a known blend of the true
average echo (the atlas average of the training worms) and the same echoes reassigned to
random pairs, `f * true + sqrt(1 - f^2) * reassigned`, so that `f` is exactly the brain's
correlation with the true average and every echo keeps its real size and shape. `f` runs
from 0 (no cause and effect, right everything else) to 1 (the average itself), three random
reassignments per value, scored with the same verdict rules on the same three frozen pools
(original archive, 113 wild-type worms). Expectations: `f = 0` is outside in all three
pools; around `f = 0.3`, a real worm's own level, is inside in at least 2 of 3; `f` of 0.6
and above is too typical in all three (the plain average already is); and the inside window
is narrower than 0.3 in `f`. If so, "inside" means "as much causal structure as a real worm
shows, give or take about 0.1 in correlation", and the published fully connected model
(0.16 to 0.20 against the average, above) is predicted outside, as observed.

Result (`docs/figures/causal_power.csv`; `f` in steps of 0.05, three reassignments each,
all three agreeing at every step except one borderline value):

| pool | outside (too little cause and effect) | inside | too typical |
|---|---|---|---|
| 1 | `f` up to 0.25 | 0.30 to 0.45 | 0.50 and above |
| 2 | up to 0.30 (0.35 borderline) | 0.40 to 0.50 | 0.55 and above |
| 3 | up to 0.30 | 0.35 to 0.50 | 0.55 and above |

Three of four expectations met: no cause and effect is outside everywhere, the window is
narrow (0.15 to 0.20 wide in `f`), and the plain average and anything near it is too typical
from 0.5 or 0.55. The fourth missed: `f = 0.3` is inside in only 1 of 3 pools, because the
window sits higher than predicted, centred near 0.4 rather than 0.3. The reason is
instructive. In this run one real worm correlates with the atlas average at only 0.22 to 0.25,
lower than its true causal structure, because the average itself is noisy and incomplete;
a brain whose echoes are noise-free needs `f` near 0.4 to match the agreement real worms show
with each other (about 0.1). So **"inside" on the poke pattern means: the brain's echoes
correlate with the true average echo at about 0.3 to 0.5.** Less is a brain that does not
know enough cause and effect; more is a brain more stereotyped than any real worm. The ruler
resolves a shortfall of about 0.1 in that correlation. On this scale the VAR models (0.04 to
0.12 against the average, above) are nowhere close, the published fully connected model (0.16
to 0.20) is short by about 0.15, and the plain atlas average is too far the other way: a
brain copy has to be right about cause and effect *and* as individual as a real worm.

## Is the wiring diagram enough to copy a brain?

Most attempts to build a whole-brain model start from the wiring diagram: the neurons and the
synapses between them (OpenWorm for *C. elegans*; connectome-constrained models of the fly
brain). The atlas lets us ask directly whether the wiring diagram is enough to build a brain
copy that answers pokes correctly.

**What the atlas says, before any model** (descriptive; class-level wiring from Kunert et al.
2014, a link j to i counted as wired if any member of j makes a chemical synapse onto any
member of i or they share a gap junction; 4,124 poked pairs measured in at least 3 of the 113
worms, both classes in the connectome). 14.5% of pairs are wired. Among the pairs whose echo
is reliable across worms (|t| > 3 over worms, 279 pairs), 16.1% are wired; among the most
reliable (|t| > 4, 101 pairs), 19.8%. **The wiring diagram is barely enriched for the links
that carry a real worm's echoes: 85% of the reliable echo, by size, travels between neuron
classes that have no synapse or gap junction between them.** Nor are those unwired echoes
explained by one intermediate neuron: 57.3% of reliable unwired pairs are two wired steps
apart, the same as for unwired pairs in general (57.0%). This is consistent with the atlas
authors' finding that signals often propagate where no wire exists (Randi et al. 2023); here
it becomes a test of brain copies.

**Can the wiring predict where a poke's echo goes?** (Exploratory, not pre-registered;
`scripts/analyse_wiring_echo.py`, `docs/figures/wiring_echo.csv`.) Split the worms into two
random halves; in one half, mark which poked pairs give a reliable echo (|t| > 2); ask how well
each predictor ranks those pairs, as an area under the ROC curve (0.5 is a coin flip), over 20
random halves. **Whether a wire exists: 0.508 [0.495, 0.520]. The number of synapses: 0.508.
Two wired steps: 0.505. The echoes of the other half of the worms: 0.620 [0.600, 0.638].** At
the level of neuron classes and calcium imaging, the wiring diagram predicts where a poke's
echo goes no better than chance, while other worms' pokes do. Binomial tests for enrichment of
wired pairs among reliable echoes: p = 0.24 (|t| > 3), p = 0.09 (|t| > 4).

**The model test (written before running).** The brain that passes the poke test
(`hybrid_kernels_regimes_obsfit`: causal links learned from pokes, dynamics learned from
watching, measurement noise, calm and active states) is rebuilt with its causal links
restricted, everything else identical:

| brain | causal links kept |
|---|---|
| `..._connectome_...` | only wired pairs |
| `..._shuffled_...` | random wiring with each class's number of inputs kept |
| `..._unwiredn_...` | as many links as the wired version, drawn at random from unwired pairs |
| `..._unwired_...` | every unwired pair (both classes in the connectome), no wired ones |

Every version keeps each class's echo onto its own other members (left-right partners), as
the wiring mask does. (A first launch dropped those for the unwired versions; it was stopped,
its one result deleted, and rerun.)

Scored on all eleven levels on both frozen splits (`pumpprobe_cv3`, `pumpprobe_cv3_blocks1`),
responses in units of pre-stimulus fluctuations as for the ingredient hunt. Expectations:
the full brain passes echo pattern in at least 2 of 3 pools on each split; the wired-only
brain fails it (outside) in at least 2 of 3 on each split; so do the shuffled and the
count-matched unwired brains, with the wired-only brain's echo agreement no more than 0.02
above the count-matched unwired brain's (the wiring is barely better than random links);
and the brain built only from unwired links passes echo pattern in at least 2 of 3 pools on
each split. If the wired-only brain passes, the headline below will say the wiring diagram is
enough at this resolution.

**A flaw in the design above, found before its results were in (written before running the
fix).** 36% of the measured pairs involve a neuron class that this connectome does not
contain (mostly pharyngeal neurons: I1 to I6, M1 to M5, MC, MI, NSM, which the Kunert somatic
matrices leave out; also naming mismatches such as AWCON and AWCOFF). The masks above drop
every such link, so all four restricted brains lose about a third of the echo for a reason
that has nothing to do with the wiring; the first results (all four outside on echo pattern
in the first pool of each split) cannot separate the two. They are kept and reported, but the
wiring question is asked again with versions that keep every link involving an unknown class
and restrict only the links between classes the connectome covers (`wiredk`, `shuffledk`,
`unwiredk`, `unwirednk`; same definitions otherwise). Expectations for these, unchanged from
above: wired-only fails echo pattern in at least 2 of 3 pools on each split, as do shuffled and
count-matched unwired, with wired-only no more than 0.02 above count-matched unwired in echo
agreement; unwired-only passes echo pattern in at least 2 of 3 on each split.

**Result (repaired data, 1 Nov 2026; `results/fixed_cv3`, `results/fixed_blocks1`).** Echo
pattern verdict and agreement with real worms, three pools per split:

| brain | split cv3 | split blocks1 |
|---|---|---|
| full (all links) | inside 0.113, 0.094, 0.088 | inside 0.108, 0.100, 0.090 |
| wired links only (`wiredk`) | outside 0.068, 0.056, 0.041 | outside 0.066, 0.053, 0.047 |
| shuffled wiring (`shuffledk`) | outside 0.060, 0.043, 0.028 | outside 0.052, 0.035, 0.037 |
| as many random unwired links (`unwirednk`) | outside 0.052, 0.044, 0.021 | outside 0.052, 0.035, 0.035 |
| all unwired links (`unwiredk`) | 1 of 3 inside: 0.095, 0.075, 0.070 | 1 of 3 inside: 0.088, 0.072, 0.071 |

Against the expectations: wired-only fails in 3 of 3 pools on both splits (met); shuffled
and count-matched unwired fail everywhere (met); wired-only beats an equal number of random
unwired links by 0.012 to 0.020 (met: no more than 0.02); unwired-only was expected to pass in
at least 2 of 3 on each split and passes in 1 of 3 (not met). **The wiring diagram is not
enough to copy how a worm answers a poke: a copy built only on its links agrees with real
worms about half as well as the full copy, and each wired link is worth only a little more
than a random unwired one. But the unwired links are not enough either: a working copy
needs both.**

## Signatures of a mind: perturbational complexity

Nobody can measure consciousness directly, and whether a worm experiences anything is an
open question; nothing here claims it does. But consciousness science has measuring tools
that work on brains that cannot report, and the most validated one is a perturbation test.
The **Perturbational Complexity Index** (PCI; Casali, Massimini, Tononi and colleagues,
2013) separates conscious from unconscious people: perturb the cortex with a magnetic
pulse, mark where and when the response is significant, and measure how compressible that
pattern is. Awake brains answer with echoes that are widespread *and* differentiated; deep
sleep, anaesthesia and coma give local blips or stereotyped waves. The optogenetic atlas
is the same experiment in a worm, thousands of times over. So the question becomes: **do
artificial brains have a real brain's perturbational signature?**

**Measure** (`nematica/bench/perturbational.py`). Per stimulation: each named class's
response over 30 s, in units of its own fluctuation size before stimulation; significant
where above 3 [A]; PCI = Lempel-Ziv complexity of the significance pattern, normalised by
its length and by how much of it is significant (the standard PCI normalisation). Two
levels, distances between two worms' sets of events: `P1.complexity` (KS distance between
PCI distributions) and `P2.spread` (KS distance between the fractions of the pattern that
responds).

**Calibrations, outcomes designed before running:**

| calibration | complexity | spread |
|---|---|---|
| real held-out worms | inside | inside |
| responses scaled by 3 | either | outside |
| desynchronised (each class's response shifted in time by its own random offset) | outside | inside |
| time reversed | inside | inside |

**Expectations for the models, written before running:** the class VARs and the published
models respond too strongly (magnitude level), so their echoes spread too far (spread
outside); and their noise is unstructured, so their echoes are more complex than real
ones (complexity outside, above real worms). A brain whose echo is "too complex" in this
sense is not more conscious-like; it is noisier. Real brains sit between a blip and noise.

**PCI results** (`scripts/run_pci.py`, `docs/figures/pci.csv`; Creamer packaging). Real
worms: 3,062 stimulations, median PCI 0.86 (interquartile 0.75 to 0.96), and a sparse echo:
a median of 3.4% of the class-by-time pattern responds. Calibrations: 18 of 21 designed
outcomes hit. The 3 misses are all "desynchronised echoes must fail complexity": PCI does
rise (0.86 to 0.91 to 0.93) but stays inside the wide band of real worm-to-worm variation,
so the complexity level is weak at detecting scrambled timing and claims rest mainly on
spread.

| model | spread (real 3.2 to 3.9%) | complexity (real PCI 0.86) |
|---|---|---|
| VAR(3), all frames | 6.4 to 7.3%: outside in 3 of 3 | 0.91, higher: outside in 2 of 3 |
| published, connectome-constrained | 12%: outside in 3 of 3 | 0.82, lower: outside in 3 of 3 |
| published, fully connected | 14%: outside in 3 of 3 | 0.82, lower: outside in 3 of 3 |
| published, shuffled connectome | 12%: outside in 3 of 3 | 0.81, lower: outside in 3 of 3 |

Against the expectations: spread outside for every model, met (echoes reach two to four
times too much of the brain). Complexity outside, met in 11 of 12, but the direction
predicted for all of them (more complex, noisier) holds only for the VAR. **The published
atlas models answer a poke with echoes that are too widespread and too stereotyped**: a
lower PCI over a larger response, the direction consciousness research associates with a
brain whose response is one undifferentiated wave. Real worm brains answer with sparse,
differentiated echoes. To repeat the caution: this says the models lack a measurable
property of the real brain's responses, not anything about experience.

## Signatures of a mind at rest

Perturbational complexity needs a poke. Consciousness research also reads the *ongoing*
activity of brains, and three of its measures can be applied to any whole-brain recording,
so they can be run on every dataset here (`nematica/bench/mind.py`), real and artificial
alike, in 60 s windows:

| level | measure | in people |
|---|---|---|
| `M1.complexity` | Lempel-Ziv complexity of the activity pattern (each class above or below its median) | falls under anaesthesia and in deep sleep |
| `M2.integration` | total correlation: how much the brain's parts share rather than act independently | central to integration theories of consciousness |
| `M3.repertoire` | entropy of coarse whole-brain states (sign pattern of the top 4 principal components) | richer state repertoires in wakefulness |

Distances between worms are KS distances between window distributions, scored with the
ruler as usual. **Calibrations, outcomes designed before running:** classes shifted in time
independently (correlations destroyed): integration outside, complexity either; frames
shuffled (time order destroyed): complexity outside (higher), integration inside;
phase-randomised (spectra and correlations kept): integration inside; Gaussian noise:
complexity and integration outside.

**Expectations for the models, written before running:** on the copper and Atanas datasets,
the per-worm VARs that pass the ordinary activity levels are inside on integration (they
reproduce correlations), but *outside on complexity, above real worms*: linear Gaussian
models driven by noise produce more irregular activity than real brains, whose activity is
structured by discrete states (forward, reverse, turn). Repertoire: no strong prior.

**Results on the copper dataset** (`scripts/run_mind.py`, `docs/figures/mind_copper.csv`):

- Calibrations: 24 of 27 designed outcomes. The misses are all integration: shifting each
  class in time independently lowers total correlation (0.71 to 0.58) but stays inside in 2
  of 3 pools, and shuffling frames falls outside once. Real worms differ from each other a
  lot on integration (median KS 0.5 to 0.6), so that level is coarse.
- Real worms: complexity 0.97 to 0.99 (binarised activity is close to maximally complex at
  60 s), total correlation 0.71 to 0.74 per class, about 3.6 bits of whole-brain state
  repertoire (of 4 possible).
- **The per-worm VARs that pass the ordinary activity levels also pass all three
  consciousness-science signatures of ongoing activity**: VAR(3) inside on all three in every
  pool, VAR(10) on 8 of 9 (integration slightly low in one pool). Expectation (complexity
  outside, above real) not met: the models' ongoing activity is as complex, as integrated
  and as varied in its global states as real worms' activity.

**Results on the Atanas dataset** (`docs/figures/mind_atanas.csv`): calibrations again 24 of
27 designed outcomes (the same integration misses); VAR(3) inside on all three signatures in
every pool; VAR(10) inside on complexity and repertoire everywhere, integration low in 2 of 3.

This sharpens the headline rather than softening it: by every measure of *ongoing* activity
used here, including the ones consciousness science uses, these artificial brains are
indistinguishable from real worm brains, and the poke still shows they are wrong.

## Arc 6: from one brain to a swarm

**Question.** Does the ruler's verdict hold when many model brains share one world? Real
worms on a plate meet, touch, back off and sometimes clump. A model that is right one worm
at a time could still be wrong as a crowd, and the crowd is a new place to ask arc 2's
question: does individuality matter? If every worm in a swarm is the average worm, does
the swarm behave differently from a swarm of distinct individuals?

**What gets built (no new data needed).**

- `nematica/swarm/engine.py`: N closed-loop worms in one copper arena, each a v11 brain
  (`SensoryVAR`) with a motion-matched body, stepped together one frame (0.6 s) at a time.
  The single-worm simulation was split into a per-frame agent (`BrainAgent`: `think` then
  `move`); with no interactions it reproduces the old simulation exactly (same random
  draws, checked to the bit).
- Interactions, all stated assumptions [A] until they can be calibrated against real
  multi-worm tracking (Ding et al. 2019, Level 7):
  - *exclusion*: a head may not move closer to another worm's body than the contact
    distance (0.1 mm, about two body widths); it holds still instead;
  - *touch*: while crawling forward, a frame in which the head is within the contact
    distance of another worm starts a reversal with probability 0.3, on top of the brain's
    own reversal hazard (anterior touch makes real worms reverse);
  - *density* (other heads within one body length) is measured, never fed to the brain.
- Swarm statistics (`nematica/swarm/metrics.py`): time in contact, fraction of worms in a
  cluster (bodies touching, connected components of 2 or more), cluster sizes,
  nearest-neighbour head distance, reversal onsets per minute against local density, time
  near copper, and the spread of each worm's own statistics across the swarm.

**First experiment: twins versus average worms.** For each frozen rotation, models are
fitted on the training worms as in arc 5. Swarms of 32 worms, 16 minutes:

| swarm | brains |
|---|---|
| twins | each training worm's own model, twice (16 worms x 2) |
| average | 32 copies of the pooled model (pooled dynamics, median reversal offsets, pooled speeds) |

each run with interactions on and with interactions off (worms pass through each other:
the chance-encounter baseline), 3 seeds per rotation.

**Expectations, written before any run.**

1. (check of construction) Twins spread more: the between-worm SD of reversal rate is at
   least 1.5 times larger in twin swarms than in average swarms.
2. (check of construction) With interactions on, reversal onsets per minute rise with local
   density; with interactions off they do not (within seed variation).
3. (check of construction) Interactions lower time in contact compared with pass-through
   swarms, because touched worms back off.
4. (the open question, no strong prior) Swarm-level means (time in contact, fraction in
   clusters, nearest-neighbour distance, time near copper) differ between twin and average
   swarms by less than two seed-to-seed SDs, but twin swarms are more heterogeneous: the
   between-worm SD of time in contact is larger for twins. If means also differ clearly,
   individuality changes the collective, not just the individuals.

Nothing here is scored against real swarms yet: these are model-against-model comparisons.
The scored test (Level 7) needs real multi-worm tracking.

**Results** (`scripts/run_swarm.py`, `docs/figures/swarm_twins_vs_average.csv`; 3 rotations
x 3 seeds, twin and average swarms paired on the same starting positions; "seed SD" is the
seed-to-seed SD within a rotation):

| interactions on | twins | average | twins minus average | paired runs in that direction | in seed SDs |
|---|---|---|---|---|---|
| time in contact | 0.056 | 0.066 | -0.010 | 9 of 9 | -2.3 |
| fraction of worms in a cluster | 0.214 | 0.246 | -0.032 | 9 of 9 | -2.1 |
| nearest-neighbour distance (mm) | 0.640 | 0.596 | +0.044 | 9 of 9 | +2.3 |
| time within 0.5 mm of copper | 0.234 | 0.182 | +0.053 | 9 of 9 | +2.6 |
| reversals per minute | 3.10 | 3.03 | +0.07 | 8 of 9 | +0.7 |
| between-worm SD of reversal rate | 0.56 | 0.36 | +0.20 | 9 of 9 | +4.8 |
| between-worm SD of time in contact | 0.017 | 0.018 | -0.001 | 3 of 9 contrary | -0.6 |

Against the expectations:

1. Met: twins spread 1.55 times more in reversal rate with interactions (2.05 times in
   pass-through swarms).
2. Met: with interactions, reversals per minute rise with local density (2.9, 3.9 and 5.1
   at 0, 1 and 2 or more neighbours); in pass-through swarms they are flat (2.95, 2.95,
   2.94).
3. Met: interactions halve time in contact (0.056 against 0.109 for twins).
4. Not as expected, on both halves. The swarm-level means do differ, consistently (every
   paired run, about two seed SDs): twin swarms touch less, cluster less, keep further
   apart and spend more time at the copper edge. And twin swarms are not more
   heterogeneous in contact time. The same differences appear in pass-through swarms
   (contact -0.011, clusters -0.026, copper +0.026), so they come mostly from where the
   worms go, not from how they react to each other: the pooled model spends less time at
   the copper edge than the worms it was fitted on, so a swarm of it crowds the middle of
   the arena and meets more often.

A caveat that applies to every copper number here: like the single closed-loop worm of arc
5, these model worms spend far more time at and over the copper line than real worms (24%
within 0.5 mm or beyond for twin swarms, against a median of 3% for real worms, who mostly
turn back at the line). Swarm worms start uniformly over the arena, nearer the copper on
average than real worms' starting points, which adds to it. So where a worm likes to be is
partly the model's known copper miss, and the swarm results inherit it.

The average worm is not a typical worm (arc 1's lesson, now at the scale of a crowd), so
this experiment cannot yet say whether *diversity itself* changes the swarm or only the
pooled model's bias does. That needs a control with no pooled model at all.

**Second experiment: clones.** For every training worm, a homogeneous swarm of 32 copies of
that one worm's model (seed 0, interactions on and off, all three rotations). Diversity
acts only additively if the mixed twin swarm equals the average over the clone swarms;
any gap is an effect of mixing. Expectation, written before the results were seen: in
pass-through swarms, the mixed swarm has *less* contact than the average clone swarm. By
geometry alone, when worms differ in where they like to be, two different worms overlap
in space less than two copies of the same worm (the overlap of two densities is at most
the mean of their self-overlaps).

**Clone results** (`docs/figures/swarm_clones.csv`; 16 clone swarms per rotation, one seed;
the twin swarm here is seed 0 of the first experiment, reproduced exactly):

| | interactions | twins (mixed) | mean of clone swarms | range over clone swarms | average-worm swarm |
|---|---|---|---|---|---|
| time in contact | off | 0.106 | 0.109 | 0.062 to 0.187 | 0.123 |
| time in contact | on | 0.053 | 0.060 | 0.039 to 0.097 | 0.067 |
| fraction in a cluster | off | 0.303 | 0.308 | 0.203 to 0.465 | 0.345 |
| fraction in a cluster | on | 0.205 | 0.226 | 0.150 to 0.327 | 0.247 |
| nearest neighbour (mm) | on | 0.657 | 0.631 | 0.501 to 0.758 | 0.598 |
| time near copper | on | 0.245 | 0.217 | 0.065 to 0.432 | 0.198 |

- Individual worms make very different crowds: a swarm of one worm's copies can have three
  times the contact of another's (0.062 to 0.187 without interactions). The model worms'
  individuality is large at the scale of a swarm.
- Without interactions the mixed swarm is the average of its members (contact 0.106
  against 0.109; the difference changes sign across rotations). The geometric expectation
  (mixed below clones) is not confirmed: if it holds, the effect is too small to see here.
- With interactions the mixed swarm is less crowded than its members would be alone in
  every rotation: less contact (-0.004, -0.006, -0.012), fewer worms in clusters (-0.013,
  -0.013, -0.038), larger gaps and more time at the copper edge. A mixing effect that
  appears only when worms react to each other. With one seed per clone this is suggestive,
  not established (the contact gaps are one to three seed SDs); more seeds come next.
- Most of the twin-versus-average gap is the pooled model's bias: the average-worm swarm
  is more crowded than the mean clone swarm even without interactions (0.123 against 0.109).

**More clone seeds (criterion written before the runs).** Seeds 1 and 2 of the clone
experiment, merged with seed 0: the mixing effect under interactions counts as established
if the twin swarm's contact and cluster fraction are both below the clone mean in at least
8 of the 9 rotation-seeds; otherwise it is reported as not established.

Result (`docs/figures/swarm_clones_seed1.csv`, `_seed2.csv`): **not established.** With
interactions, the mixed swarm's contact is below the clone mean in 7 of 9 rotation-seeds
(mean gap -0.003) and its cluster fraction in 6 of 9 (mean -0.009). The direction holds on
average, but the gap is small against seed noise and misses the criterion. Without
interactions the gaps are centred on zero (5 of 9 for both), as before. The firm finding is
the additive one: a swarm is roughly the average of its members, and members differ a lot.

**Sensitivity to the assumed interaction rules (expectation written before the runs).**
Twin and average swarms in one rotation (rotation 0, 2 seeds) with the touch probability
at 0.1, 0.3 and 0.6 and the contact distance at 0.05, 0.1 and 0.2 mm, one changed at a
time. Since the twins versus average gap is present even without interactions, it should
survive every setting: twins below average in contact and cluster fraction in all 10 paired
runs.

So far, then: individuality matters at the swarm scale mostly additively, through each
worm's own taste for where to be, and the "average worm" is a poor stand-in for a
population, alone or in a crowd. Whether mixing adds a genuine collective effect under
interactions needs more seeds here, and then real multi-worm data to say whether real
crowds behave like either.


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

**Creamer et al.'s models on the stimulated worms, with their own stimulation (1 Nov 2026,
exploratory: one pool, repaired data; checked by an independent review).** Their own measure
first, recomputed from their published models and their published train and test response
maps (`scripts/creamer_own_metric.py`; `measured_stams.pkl` from their repository, kept
local): correlation of each model's time-integrated response map with the held-out map,
relative to the train-to-test correlation of the maps (0.173). Connectome-constrained 0.81
(an absolute correlation of 0.14), fully connected 0.69, shuffled 0.23. The ordering matches
the paper; the first value does not (their abstract reports 92%), and the gap is not yet
explained.

Reading their code showed our earlier test of these models was not fair: we held the poked
neuron to its measured response, while their models take a learned input filter (45 frames
per neuron, a unit input at each stimulation, as in their `sample()` and `calculate_irfs`).
`CreamerCausal(protocol="native")` now uses that filter. On the ruler (split cv3, pool 0), the
connectome-constrained model is still outside on the poke pattern: simulated worms' echoes
agree with real worms at 0.003, against 0.095 between real worms.

What separates the two evaluations (`scripts/diag_creamer_reliability.py`,
`scripts/diag_creamer_noise.py`, 14 pool worms; the noise-free echo is measured in the noisy
run's units):

| Comparison | Echo agreement |
|---|---|
| real worm with real worm | 0.094 |
| model without its noise, with real worms | 0.126 |
| model with its fitted noise, with real worms | 0.004 |
| two simulated worms with each other | 0.010 |

- **Single echoes are buried in the model's own noise.** The model's noise-free echo is
  about 0.01 of its ongoing fluctuation, so one simulated worm's echo correlates only 0.09
  with the model's own noise-free echo, while one real worm's echo correlates 0.20 with the
  mean of the other real worms. Their measure scores the noise-free response map, so it
  cannot see this; an experiment, which sees one worm at a time, would.
- **The model's average echo is only partly right.** Its noise-free echo map correlates
  0.23 with the real worms' mean echo map. Scaling the noise down shows the same thing:
  if model and real echoes are each a mean echo plus independent noise, the implied
  correlation between the two mean echoes is 0.42 at one fifth of the fitted noise and
  0.49 at one tenth. At one fifth, simulated worms agree with each other as real worms do
  (0.106), but with real worms only at 0.042, which a partly wrong mean echo accounts for.
  These data do not show whether the model also lacks stable differences between
  individual worms; that needs its own test.

Caveats: one pool and 14 worms; their models were fitted on atlas worms that may include
these (only 2 of the 14 are in the held-out list of their example configuration), which
favours them; in the gallery their models take a unit input at every stimulation, while
other copies are given the poked neuron's measured response, which also tells them which
stimulations took.

## Swarm view (arc 6)

`python scripts/export_swarm.py --data <copper folder> --folds configs/splits/copper2026_cv3.yaml`
writes one twin swarm (rotation 0, interactions on) to `lab/public/data/swarm1/`; open the
lab with `?mode=swarm` to watch 32 model worms from above, with reversals in orange, touches
ringed, the copper shaded, and live counts. Click a worm to follow it.

The public site at `web/sim.html#swarm` is a separate, live behavioral sandbox. Run
`python scripts/export_swarm_profiles.py` after exporting a fitted swarm to refresh its
32 speed, reversal and turning priors. The browser advances new trajectories from a
seed, handles head contact and copper steering, and recomputes crowd measures as it runs.
It does not advance the fitted neural state; its contact and copper rules are stated
assumptions, and its numbers are not validation against real multi-worm recordings.

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


**Copper version** (`python scripts/export_virtual_worms.py --closed-loop ...`, then open
the lab at `?mode=which&set=which3`): the model worm is the v11 closed-loop worm, simulated
in the real worm's own copper arena (same radius, same starting distance), and both worms
are shown inside their copper rings. Its brain senses the copper and decides when to
reverse and where to steer; only body shapes are borrowed. The reveal shows the v11
scorecard (9 of 10 pairwise; all three Level 6 metrics inside).

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

NEMATICA's own code is released under the MIT licence (`LICENSE`). The licence covers the
code only: every dataset and third-party model below keeps its own terms, and copies of
third-party data stay local unless their terms allow redistribution.

- Copper-boundary whole-brain recordings: Baskoylu et al. 2026, Dryad
  10.5061/dryad.w9ghx3g4v (CC0).
- Atanas et al. 2023, *Cell*: brain-wide representations of behavior (Flavell lab).
- Kunert, Shlizerman, Kutz 2014 connectome model; matrices from the C. elegans Neural
  Interactome (BSD 3-Clause, `data_assets/kunert2014/LICENSE`).
- Skuhersky et al. 2022 neuron atlas (paper CC BY 4.0), downloaded by script, not
  redistributed.
- Creamer, Leifer & Pillow 2024 trained models (MIT licence, Copyright (c) 2026 Matthew S.
  Creamer), downloaded by `scripts/fetch_creamer_lds.py`, not redistributed.
