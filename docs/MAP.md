# A map of brains and AIs (pre-registered 12 Nov 2026)

The project's question is what differentiates real neural networks from artificial ones, in general,
not for one animal. Everything so far rests mostly on one animal (*C. elegans*) and on small artificial
networks. This plan widens both sides at once: many real nervous systems, many families of artificial
network, one set of measurements that all of them can take, judged on one ruler. The output is a map
with every system on it, and a set of registered tests on that map.

This file is the registration. It was written before any of the new data was read. Changes after
reading data are added as dated amendments below the original text; the original text is not edited.

## The question, made testable

Three readings of "what differentiates them", each a test:

1. **Is there a brain profile?** Do real nervous systems, across species, preparations and recording
   methods, resemble each other more than they resemble artificial networks? (H1)
2. **Is the difference one of kind?** Can any artificial network, built from ingredients chosen in
   advance, land among the brains on every measurement? If none can, the measurements where every
   artificial network stays outside are the candidate differences in kind. (H2)
3. **Which dials matter?** Which measurements separate brains from ordinary artificial networks
   most, and does adding slow hidden state (the ingredient the worm work found decisive) move
   artificial networks towards brains on exactly those? (H3, then H4 to H8 on specific families)

The worm work predicts "no difference in kind; the separating dials are slow, shared, hidden state".
That prediction is written down here so it can fail.

## Systems

### Real nervous systems (target: at least 8 preparations; each needs at least 3 individuals)

| id | preparation | data (public) | recording | perturbation |
|---|---|---|---|---|
| R1 | *C. elegans*, immobilised, whole brain | Randi et al. 2023, DANDI 001075 (in hand) | calcium | single-neuron light |
| R2 | *C. elegans*, freely moving, whole brain | copper set (Baskoylu et al.), Atanas et al. 2023 (in hand) | calcium | none |
| R3 | larval zebrafish (and *Danionella*), brain-wide | DANDI 001453 (contents to check; fallback: Ahrens lab spontaneous light-sheet sets) | calcium | none |
| R4 | mouse, 8 Neuropixels probes across the brain, spontaneous | Stringer et al. 2019, figshare 7739750 | spikes | none |
| R5 | mouse visual cortex, about 10,000 neurons, spontaneous | Stringer et al. 2019 (figshare) | calcium | none |
| R6 | mouse premotor cortex (ALM) with photoinhibition | Finkelstein et al., DANDI 000060 | spikes | regional light |
| R7 | macaque motor cortex, reaching | NLB MC_Maze / MC_RTT, DANDI 000128, 000129 | spikes | none |
| R8 | human cortex, intracranial, single-pulse stimulation | van Blooijs et al. 2023, OpenNeuro ds004080 (partly in hand) | field potentials | electrical pulses |
| R9 | rat cortical cultures on HD-MEAs: spontaneous development; repeated stimulation | DANDI 002020; DANDI 001611 | spikes | electrical, repeated |
| R10 | human and mouse brain organoids, mouse neonatal slices | van der Molen et al. 2025, DANDI 001603 | spikes | none |
| R11 (stretch) | *Drosophila*, whole brain | Brezovec et al., DANDI 000727 (very large; streamed subsets only) | calcium | none |

Rest periods are used where a preparation has a task (R6, R7): inter-trial and spontaneous blocks only,
with a sensitivity analysis using whole sessions.

### Artificial networks (target: at least 10 families)

| id | family | sizes / variants | individuals |
|---|---|---|---|
| A1 | random rate RNN (tanh) | 120, 1,000 units | 10 seeds |
| A2 | rate RNNs trained on neuroscience tasks (NeuroGym) | 3 tasks | 10 seeds |
| A3 | GRU / LSTM trained on character-level language | 1 size | 5 seeds |
| A4 | spiking networks (plain, with adaptation) | 1,000 neurons | 10 seeds |
| A5 | "liquid" networks (CfC / LTC, *C. elegans*-inspired) | trained on the A3 task and one A2 task | 5 seeds |
| A6 | transformers, Pythia suite | 14M, 70M, 160M, 410M, 1B; checkpoints at steps 0, 1k, 10k, 143k | deduped vs standard as second individual; seeds where released |
| A7 | state-space models, Mamba | 130M, 370M | 2 sizes |
| A8 | vision networks on natural video | ResNet-18, ViT-tiny | 3 inits / training seeds where available |
| A9 | recurrent reinforcement-learning agent | trained in a navigation task | 5 seeds |
| A10 | the lab networks with biological ingredients | slow hidden drives, silent links, individual variation | 10 seeds each |
| A11 | the worm emulator | as frozen 9 Nov | 5 noise draws |

A1 to A9 with default settings are the **standard** artificial networks. A10, A11 and the
slow-state variants in H3 are the **augmented** ones, fixed now: (a) A1 plus slow hidden drives with a
time constant 50 times the unit time constant; (b) Pythia-160M with a slow latent added to the
residual stream (an Ornstein-Uhlenbeck process, time constant 200 tokens, projected through a fixed
random matrix, scaled to 30% of residual variance); (c) A10 at its best ladder setting; (d) A11.

## Recording matched to each brain

An artificial network is never compared in its own native units. It is **recorded the way the brain it
is compared with was recorded** (the project's rule since the emulator work):
- **calcium:** unit activity rectified, convolved with the preparation's indicator kernel, sampled at its
  frame rate, with matched noise and matched number of recorded units;
- **spikes:** unit activity mapped to firing rates (matched to the preparation's median rate) and drawn
  as Poisson spikes, binned as the preparation is;
- **field potentials (R8):** units mixed into channels by distance-weighted sums, as electrodes do.

**Time.** A brain's clock is seconds; a language model's is tokens. No mapping is assumed. Core
measurements are dimensionless: each system's time is measured in units of its own median unit
timescale (tau_med, the lag at which a unit's autocorrelation falls to 0.5). Results under a declared
step length are reported separately and are not used by the tests.

**Input regime.** Each system is recorded in its natural regime without task structure: brains at
rest or spontaneous behaviour; recurrent networks driven by noise; language models reading natural
text (a fixed 200k-token sample of public-domain books); vision models watching natural video; the RL
agent exploring. Sensitivity analysis: language models on shuffled text, RNNs on structured input.

## Measurements

**Core (every system):**

| # | name | what it measures |
|---|---|---|
| M1 | spectrum exponent | power-law slope of the cross-validated (shared) eigenspectrum of population activity |
| M2 | shared dimensionality | number of reliable shared dimensions, as a share of recorded units (shared variance component analysis) |
| M3 | shared fraction | share of each unit's variance predictable from the rest of the population on held-out time |
| M4 | slow fraction | share of variance at timescales beyond 10 tau_med |
| M5 | timescale spread | interquartile range of log unit timescales |
| M6 | coupling spread | spread of population coupling across units (soloists vs choristers) |
| M7 | drift | change in the covariance structure between early and late thirds of 1,000 tau_med, beyond sampling noise |
| M8 | sparsity | median lifetime kurtosis of unit activity after the recording model |

**Perturbation (where a preparation allows it):** echo breadth (excess over no-push moments), response
decline on repeat (tiring), and watch share (how well a model fitted at rest predicts perturbation
responses, against how well individuals agree). Real: R1, R8, R9 (single-site), R6 (regional,
exploratory). Artificial: all.

## The ruler

Each real preparation's individuals (animals, cultures, organoids, patients) give a between-individual
spread per measurement. The **biological variation unit (BVU)** of a measurement is the median of these
spreads across preparations. Every system becomes a vector of 8 values in BVU. Distances on the map are
Euclidean distances in BVU over the measurements that pass calibration.

## Calibration, before any new brain data is read (a gate)

- **C1, recovery.** Synthetic populations with known spectrum exponent (0.5 to 2), known slow fraction,
  known drift and known coupling spread, recorded through every recording model at 50 to 5,000 units.
  Each measurement must recover the known ordering (Spearman at least 0.9) under every recording model.
- **C2, recording invariance.** The same synthetic systems recorded as calcium and as spikes must
  differ by less than 0.5 of the synthetic between-individual spread. A measurement that fails is used
  only within one recording type, never across.
- **C3, sample size.** Each measurement's value must be stable (within 0.25 of its between-individual
  spread) when units are subsampled to the smallest preparation's count.

Measurements failing C1 are dropped before brain data is read, and the drop is recorded here.

## Hypotheses and decision rules

| | prediction | holds if |
|---|---|---|
| **H1** brain profile | brains resemble brains more than AIs | leave-one-system-out, the nearest neighbour of at least 80% of real preparations is real **and** of at least 80% of standard AI families is artificial |
| **H2** no difference in kind | some augmented AI lands among the brains | at least one augmented AI is inside the brain envelope (range of real preparations, widened by 1 BVU) on every measurement |
| **H3** the dials are slow, shared state | the biggest brain vs AI gaps are on slow and shared measurements, and slow state closes them | (a) at least 2 of the 3 largest standardised gaps between the brain and standard-AI centroids are among M1, M3, M4, M7; (b) adding slow state (augmented a, b) cuts distance to the brain centroid by at least 30%, more on M1/M3/M4/M7 than on the rest |
| **H4** scale does not buy it | bigger transformers are not closer to brains | Spearman between log parameters and distance to the brain centroid across Pythia 14M to 1B is above -0.3 |
| **H5** SSMs closer than transformers | Mamba is more brain-like on slow measurements | Mamba-130M closer to the brain centroid than Pythia-160M by at least 1 BVU summed over M4, M5, M7 |
| **H6** "liquid" is not enough | worm-inspired CfC/LTC networks are not closer than GRUs | difference in distance to the brain centroid below 1 BVU |
| **H7** watching fails beyond the worm | perturbation is needed to copy any real network | watch share in each of R8 and R9 is below every standard AI recorded the same way (holds if both; partial if one) |
| **H8** no body needed | cultures and organoids sit among the brains | R9 and R10 each have a real nearest neighbour (H1 criterion) |

**Training direction** (Pythia checkpoints, A2 trained vs untrained): reported, no prediction.

**Reading the outcomes.** H1 fails: there is no common brain profile even across brains on these
measurements, which is itself an answer. H2 fails: the measurements where every AI stays outside are
the candidate differences in kind, ranked by gap. H3 fails: the separating dials are not the ones the
worm work pointed to, and the worm-based conclusion is revised.

## Rules

- Third-party data is downloaded or streamed by script and never redistributed; only summary
  numbers per system enter the repository.
- Each new preparation's loader is checked on shapes and units only before the measurement code is
  frozen; no measurement is computed on new brain data before C1 to C3 pass.
- An independent review of this plan before data, and of the results after, reported with corrections
  marked in place, as before.
- Compute is a 2-core cloud machine and the laptop: data is streamed and summarised one session at a
  time; nothing requires a cluster. Models up to 1B parameters run on CPU over the fixed text sample.

## Phases

1. Measurement code and calibration C1 to C3 on synthetic systems and AI families only.
2. Loaders for R3 to R11 (shape checks only), then measurements on all real preparations.
3. All AI families recorded through every recording model.
4. Tests H1 to H8, the map, an independent review.
5. Perturbation measurements where possible (R8, R9, R6), H7.
6. Visuals: the map itself (every system as a cloud of its individuals), and each system's activity as
   a rotating shape in the same treatment, side by side.


## Amendment 1 (12 Nov 2026, after the synthetic calibration, before any new brain data was read)

The first calibration run (`scripts/map_calibrate.py`, synthetic systems only) showed three problems,
fixed here before any real data is touched:

1. **Unit count changes the values** (C3 as first worded failed for nearly every measurement: values at
   300 units and at 50 differed by 1 to 16 between-individual SDs). So every system is now measured the
   same way (**the matched protocol**, `nematica/map/measures.measure_matched`): 50 units drawn at random,
   40 draws, values averaged over draws. Time windows are 150 tau_med for the windowed measurements;
   slow fraction (Welch segments of fixed length in tau_med) and drift (a rate) use the whole recording,
   so they do not depend on its length. A recording shorter than 150 tau_med is reported, not mapped
   (by the brain-likeness reference, worm atlas runs are about 170 tau_med; the 16-minute copper runs,
   about 75, so R2 becomes exploratory).
2. **Three definitions changed**, each because a synthetic property was not recovered:
   - *shared dimensionality* is now the participation ratio of the reliable shared spectrum (the count
     above a shuffle null fell, rather than rose, with more dimensions at 50 units);
   - *slow fraction* subtracts the white measurement-noise floor first;
   - *drift* is a rate: dissimilarity of the correlation structure regressed on separation between
     blocks of 25 tau_med, per 100 tau_med.
3. **Recording type matters** (C2 failed for every measurement except the spectrum exponent: calcium and
   spike recordings of the same system differ by 0.6 to 42 between-individual SDs). As registered, those
   measurements are compared only within a recording type. **H1 is therefore tested separately in the
   calcium group (R1, R2, R3, R5, R11) and the spike group (R4, R6, R7, R9, R10), and holds only if it
   holds in both.** Every artificial network is recorded through both models and compared with each
   group in its own type. Human cortex (R8, field potentials) is compared with AIs recorded as field
   potentials only.

**Final calibration** (Spearman for C1, ratio to between-individual SD for C2 and C3):

| measurement | C1 native / calcium / spikes | C2 | C3 native / calcium / spikes | used for |
|---|---|---|---|---|
| spectrum_exponent | 0.98 / 0.94 / 0.94 | 0.11 | 0.26 / 0.64 / 0.79 | native, calcium, spikes |
| shared_dim | 0.83 / 0.91 / 0.62 | 0.57 | 0.18 / 0.07 / 0.34 | calcium |
| shared_fraction | 0.98 / 0.98 / 0.87 | 2.70 | 0.16 / 0.15 / 0.54 | native, calcium |
| slow_fraction | 0.98 / 0.96 / 0.69 | 18.74 | 0.30 / 0.11 / 0.35 | native, calcium |
| timescale_spread | 0.98 / 0.95 / 0.98 | 7.14 | 0.21 / 0.30 / 0.58 | native, calcium, spikes |
| coupling_spread | 0.98 / 0.98 / 0.98 | 4.14 | 0.11 / 0.26 / 0.40 | native, calcium, spikes |
| drift | 0.98 / 0.95 / 0.98 | 4.81 | 0.07 / 0.19 / 0.33 | native, calcium, spikes |
| sparsity | 0.98 / 0.98 / 0.98 | 41.63 | 0.77 / 0.63 / 0.37 | native, calcium, spikes |

**A measurement is used within a recording type where it passes C1** (a refinement of "dropped if it
fails": a measurement that recovers its property in calcium recordings but not in Poisson spikes is used
for the calcium group only). So the calcium group uses all eight; the spike group uses spectrum exponent,
timescale spread, coupling spread, drift and sparsity; shared dimensionality is not used for AI-to-AI
comparisons in native units. H3's slow and shared measurements are, per group, those of M1, M3, M4, M7
that are in use. **C3** compared draw-to-draw variation with an arbitrary synthetic between-individual
spread (10% parameter jitter) and many measurements fall short of 0.25; it is re-evaluated against the
real between-individual spread of each preparation once loaded, and a measurement short of it there gets
more draws (up to 160) before use, never different definitions.

## Review 10 (12 Nov 2026, before any new brain data): not ready for data

An independent review of this registration, the measurement code and the AI pilot (an agent that had not
worked on it; checks on synthetic systems and the cached language-model recordings only). **Verdict:
not ready to read brain data.** The plan's logic holds; these must be fixed first (amendment 2):

**Measurements**
1. *Shared fraction* is mostly an overfitting score: independent units with no shared variance give
   -0.29 to -0.49, and more signal can make it more negative. The language models' negative values say
   nothing about shared state. Fix: small fixed predictor set or nested cross-validation, minus a
   circular-shift null.
2. *Spectrum exponent* is fitted on less than a decade of ranks (25 + 25 units), has a per-draw SD of
   0.7 to 0.9, and returns finite values on data with no shared spectrum (the pilot's negative exponents);
   a rank-window bug keeps ranks past the first non-positive one. Fix: nan unless ranks 1 to 10 beat a
   shift null; a robust shape statistic.
3. *Shared dimensionality* (participation ratio) is 0.40 to 0.45 for independent units, the same as
   systems with 20 to 100 shared dimensions. Fix: only dimensions above a shift null, or drop it.
4. *tau_med* has a +1-sample bias and a floor near 2 samples: the language models' timescales (about 2
   tokens) are set by sampling resolution, and under calcium tau_med is set by the indicator kernel, so
   "each system's own timescale" is not true for the calcium group. Fix: remove the bias; a registered
   minimum (resolution-limited systems reported, not mapped) or a sensitivity sweep.
5. *Drift* regresses over the whole recording, so it shrinks with recording span (about 25,000 tau_med
   for language models against 170 to 1,000 for brains); the language models' zero is likely this. Fix:
   only block pairs within 150 tau_med, inside the same windows as the other measures.
6. *Slow fraction*: the tau_med bias compresses it; segments are not a fixed length in tau_med after
   rounding; the noise-floor estimate removes real signal for slow calcium and near-white recordings;
   recording choices alone move it across its whole calibrated range.

**Recording models (the biggest gap)**
7. No registered rule maps each preparation's instrument (kernel in seconds, frame rate, firing rate,
   bin width) onto an AI's steps, and the arbitrary settings used move several measurements by more than
   their calibrated ranges. Fix: a per-preparation matching rule plus a sweep, and a mismatch budget (a
   measurement that moves more than 1 BVU over the plausible range is not used for brain vs AI).
8. Unit scale before rectification decides how much signal survives the spike model (Mamba's channels
   come out almost pure Poisson noise), which biases H5. Fix: standardise units, registered gain.
9. Spike-train bin width and rest-period selection (task data, R6 and R7) are unregistered; windows
   must not straddle gaps.
10. There is no field-potential model, and watch share is not defined here: R8 and H7 move to
    exploratory unless both are added and calibrated first.

**Calibration**
11. C1 tests each measurement at one point in nuisance space (one timescale, noise level, rate, unit
    count). Fix: add **C4, nuisance invariance** (samples per tau, noise, rate, bin, kernel, unit scale,
    population size), with a cross-talk matrix between measurements; re-run C1 at each preparation's
    matched settings.
12. C3 as coded measures Monte-Carlo noise from averaging, not stability under subsampling; register
    that a measurement still short after 160 draws is dropped for that group.

**Hypotheses**
13. H1: "system" is undefined (counting Pythia variants separately makes the AI half nearly automatic;
    with three calcium brains the brain half needs 3 of 3). Fix: one centroid per preparation and per
    family, leave out all siblings (same species, dataset or family), minimum preparations per group.
14. BVU: statistic unstated and very noisy from 3 individuals. Fix: pooled within-preparation SD per
    recording group, with its interval; cap any measure's contribution (e.g. 10 BVU).
15. H2 is partly circular: the emulator and the ladder setting were fitted on worm data. Fix: name the
    A10 setting now, exclude the preparations a model was fitted on, a joint distance criterion, and a
    limit on how many standard AIs may also pass.
16. H3 is near chance as worded (half the measurements are "slow or shared"), and the slow-state
    amplitude, gap metric and group are unregistered. Fix: register them; a permutation test.
17. H4 to H6 confirm nulls with little power. Fix: equivalence tests with bootstrap intervals, named
    groups, more seeds (PolyPythia).

**AI pilot:** 2,048-token segments reset Mamba's state (and cap its memory, relevant to H5); register a
burn-in and keep windows inside segments; use the full 200k tokens; a common unit type (residual stream)
alongside MLP neurons and SSM channels; a depth sensitivity.

*Status: all accepted. Amendment 2 will fix them and re-run calibration (C1 to C4) before any brain data
is read. The pilot numbers in `docs/figures/map_pilot_ai.json` were produced with the flawed definitions
and are superseded.*
