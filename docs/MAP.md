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
| **H5** SSMs closer than transformers | Mamba is more brain-like on slow measurements | Mamba-130M closer to the brain centroid than Pythia-160M by at least 1 BVU summed over M4, M5, M7 *(amendment 4: RMS over the slow set in use, see below)* |
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


## Amendment 2 (12 Nov 2026, answering review 10, before any new brain data was read)

Every point of review 10 is accepted. What changed:

**Measurements** (`nematica/map/measures.py`)
- *Timescale (tau_med):* the half-life is now measured against the signal variance extrapolated from lags
  1 and 2 (an exponential through them), so white measurement noise neither shortens nor biases it
  (synthetic half-lives 1.39 / 3.47 / 13.9 samples read 1.45 / 3.50 / 13.79, the same with noise as SD
  as the signal). Floor: 2 samples. A system whose median falls below it is flagged *resolution-limited*
  and mapped at the floor, with a sensitivity analysis at floors 2, 4 and 8.
- *Shared measurements* are compared with a circular-shift null (shifts of at least 20 tau_med, which keep
  each unit's own timescale and break timing between units). **Shared fraction** uses 5 patterns of the
  other units (fixed) and is reported as observed minus the shifted baseline (independent units: 0.00).
  **Spectrum steepness** replaces the spectrum exponent: the slope over ranks 1 to 3 only, and nan unless
  all three beat the null. **Shared dimensionality is dropped**: it never recovered its property.
- **Slow memory** replaces the spectral slow share (a single fast process already gave it about 0.45):
  the median autocorrelation at 10 x tau_med, relative to the signal variance (about 0.001 for one
  timescale; it rises with the share of much slower components). Whole recording of the drawn units.
- **Drift** is measured inside each 150 tau_med window (8 blocks, slope of dissimilarity on separation),
  never over the whole recording, so it no longer shrinks with recording length.
- Windows never straddle a segment boundary (a language model's context, a gap between rest periods).

**Recording models** (`nematica/map/recording.py`)
- Units are standardised and multiplied by a registered gain before rectification, so a network's
  native activation scale no longer decides how much signal survives.
- **The matching rule**, from each preparation's own summary numbers, computed once it is loaded:
  *calcium:* the indicator's decay relative to the recorded median timescale, frames per recorded
  timescale, and the white-noise share are matched (`match_calcium`; indicator decay from the dataset's
  paper, or the indicator's published value when not stated); *spikes* (all real spike data binned at
  20 ms): bins per recorded timescale, mean count per bin, and white-noise share (through the gain) are
  matched (`match_spikes`). Fractional frames and bins are allowed (interpolated sampling; Poisson counts
  drawn from the rate integrated over each bin).
- **Mismatch budget:** after matching, every matched knob is swept by a factor of 2 each way; a
  measurement that moves by more than 1 BVU over that range is not used for brain vs AI distances in that
  preparation's group (reported).
- No field-potential model: **R8 (human cortex) and H7 move to exploratory.**

**Calibration** (`scripts/map_calibrate.py`, `docs/figures/map_calibration.json`). C1 as before, now also
reporting a cross-talk matrix. **C4, new:** at the default synthetic system, each nuisance knob is swept;
for knobs the matching rule does *not* set (samples per timescale from 1.5 to 30, unit scale x0.01 to x100,
population 60 to 3,000 units) a measurement must move by less than half its C1 range; knobs the rule
sets are left to the mismatch budget. Cells: C1 Spearman / largest unmatched-knob ratio / largest
matched-knob ratio. A measurement is used in a recording type when C1 >= 0.9 and every unmatched ratio
< 0.5.

| measurement | native | calcium | spikes |
|---|---|---|---|
| spectrum steepness | 0.97 / 0.24 / - **used** | 0.95 / 0.45 / 0.16 **used** | nan / nan / nan |
| shared fraction | 0.98 / 0.06 / - **used** | 0.98 / 0.21 / 0.48 **used** | 0.98 / 0.29 / 1.59 **used** |
| slow memory | 0.98 / 0.10 / - **used** | 0.71 / 0.96 / 1.08 | 0.98 / 0.41 / 0.18 **used** |
| timescale spread | 0.98 / 0.07 / - **used** | 0.98 / 0.26 / 0.33 **used** | 0.83 / 3.07 / 3.97 |
| coupling spread | 0.98 / 0.15 / - **used** | 0.97 / 0.06 / 0.34 **used** | 0.94 / 0.53 / 1.16 |
| drift | 0.93 / 0.41 / - **used** | 0.82 / 0.26 / 0.19 | 0.32 / 1.19 / 1.35 |
| sparsity | 0.98 / 0.00 / - **used** | 0.98 / 0.05 / 0.07 **used** | 0.98 / 0.38 / 2.42 **used** |

So: **calcium group** uses spectrum steepness, shared fraction, timescale spread, coupling spread, sparsity; **spike group** uses shared fraction, slow memory, sparsity;
AI-to-AI comparisons in native units use all seven. Slow memory and drift do not survive in calcium
recordings and spike recordings lose most measurements: with 50 units and realistic recording noise, few
measurements are trustworthy. That limits what the map can say, and it is reported as a result.
**C3** (stability under unit subsampling) is now built into the protocol (every system is 50 units); a
measurement whose draw-to-draw variation is not below 0.25 of a preparation group's between-individual
spread after 160 draws is dropped for that group.

**Hypotheses, pinned down**
- *Unit of comparison:* one centroid per real preparation (mean of its individuals; at least 3) and one
  per AI family, at a fixed representative: A1 120 units, gain 1.5; A2 the perceptual-decision task;
  A3 a 256-unit GRU; A4 1,000 plain spiking neurons; A5 CfC on the A3 task; A6 Pythia-410M final
  checkpoint; A7 Mamba-370M; A8 ResNet-18 on natural video; A9 the RL agent. Other variants are
  sensitivity analyses. Augmented AIs are never candidate neighbours in H1.
- *Siblings left out:* when finding a system's nearest neighbour, every system from the same dataset, the
  same species in the same kind of preparation (in vivo, culture, organoid, slice), or the same AI family
  is excluded.
- *Groups:* calcium {R1, R2 (exploratory), R3 zebrafish and Danionella as two species, R5, R11 if
  loaded}; spikes {R4, R6, R7 (whole sessions, flagged as task), R9, R10 (human organoids, mouse organoids,
  mouse slices)}. A group needs at least 4 preparations of distinct species-or-preparation type; otherwise
  it is underpowered and reported, not tested. **H1 holds if it holds in every powered group** (at least one).
- *BVU* per group: the pooled within-preparation SD of each measurement (df = sum of n_i - 1), with a
  90% interval; any measurement's contribution to a distance is capped at 10 BVU. Distances use the
  group's measurements that are finite in both systems (at least 3, else not mapped), divided by the
  square root of their number.
- *H2:* candidates fixed: (a) A1 plus slow hidden drives carrying 40% of variance, time constant 50 x A1's
  native median timescale; (b) Pythia-410M with an Ornstein-Uhlenbeck latent (time constant 200 tokens,
  30% of the residual stream's variance at the recorded layer's input, through a fixed random projection);
  (c) A10 at the joint-search setting of 6 Nov (strong slow drives, weak silent links, spread, 30% quiet
  units, individual weight SD 80%, held pushes); (d) A11. For (c) and (d) the worm preparations are left
  out. **Passes** if its distance to the nearest real preparation is at most the largest real-to-real
  nearest-neighbour distance in the group, *and* at most one standard AI family also passes (otherwise
  the criterion is too loose and H2 is undecided in that group). H2 holds if a candidate passes in any
  powered group; if none does, the measurements on which every AI stays furthest out are reported as the
  candidate differences in kind.
- *H3:* gap = |brain centroid - standard-AI centroid| per measurement in BVU. (a) is reported
  descriptively (with 3 to 5 measurements per group a permutation test has no power): are the slow or
  shared measurements in use the largest gaps? (b) holds if adding slow state ((a) and (b) above) cuts the
  distance to the brain centroid by at least 30% for both, in every powered group. Slow state also raises
  tau_med and so rescales every window; this is part of the effect and is reported.
- *H4 to H6* are equivalence tests with bootstrap intervals (200 resamples over draws and text segments or
  seeds), per powered group: **H4** holds if the 90% interval of d(Pythia-1B) - d(Pythia-14M) lies above
  -1 BVU; **H5** if Mamba-370M is closer than Pythia-410M (summed over the slow measurements in use; *amendment 4: RMS*) with
  a 90% interval excluding 0; **H6** if CfC minus GRU lies within +-1 BVU. PolyPythia seeds are used where
  released.
- *H7* is exploratory (no field-potential model, and watch share is defined only in the worm test).
- *H8* holds if R9 and R10 each have a real nearest neighbour under H1's rule.
- *R3:* DANDI 001453 if its files hold cellular calcium traces for at least 3 zebrafish and 3 Danionella
  with at least 50 cells over at least 150 tau_med; otherwise Chen et al. 2018 (Janelia, zebrafish only).

**Language models:** the full 200k-token sample, segments of 2,048 tokens with the first 128 dropped
(burn-in), windows inside segments; units are MLP neurons (Pythia) and gated SSM channels (Mamba), with
the residual stream at the same layer as a common second unit type, and depths 1/4 and 3/4 as
sensitivity analyses. The amendment-1 pilot numbers are void.

## Review 11 (12 Nov 2026, before any new brain data): not ready for data

A second independent review checked amendment 2 against review 10. **Fixed:** shared fraction now has a
clean null (independent units -0.003 to +0.005); the spectrum statistic is null-controlled; the timescale
bias is gone for single timescales; drift is windowed; R8 and H7 are exploratory; the calibration table
follows from the JSON exactly; Poisson bin integration and the matching bisections are correct.
**Still open (must fix before data):**
1. The matching rule silently misses its targets for fast-timescale networks (every language model):
   frames and bins hit a floor of 1 step, decay saturates; it must report what it reached and a network
   that cannot be matched is reported, not mapped. "Indicator decay" must be defined (1/e constant).
2. Matching per preparation leaves each AI without one position per group, so the map and H1 to H6 are
   undefined; one recording per AI per group (the group's median instrument) is needed, and the
   mismatch budget, BVU, distance and hypothesis code must exist and be tested on synthetic "fake brains"
   before data.
3. Slow memory is not monotone in the slow share once slow activity dominates the median unit (then
   tau_med itself becomes slow); it measures a mixture of timescales, must be restated and calibrated as
   such, pooled over segments, with a minimum length.
4. C1 and C4 for calcium and spikes were run at fixed recording settings, not through the matching rule
   the real pipeline uses; rerun through matching against registered synthetic instrument profiles.
5. nan in a measurement (e.g. steepness when one global mode dominates, as in worms and fish) must have a
   registered value or drop the measurement for the whole group, not shrink a distance.
6. Register now: if the spike group cannot be mapped, H8 and the spike arm of H3 to H6 are undecided and
   H1 is tested in calcium only; the calcium group is powered only with Danionella (DANDI 001453) or the fly.
7. Name the slow set per group; H5 and H3(b) are undecided where it is empty (calcium, as of amendment 2).
**Should fix:** C3 as per-individual SD over unit subsets, no draw-count escape; a cross-talk rule (three
calcium measurements largely read one "sharedness" factor); carry BVU uncertainty into H4 and H6; H4 and
H5 undecided if the conclusion changes across timescale floors; drop dead units before recording; R6 as
whole sessions; 40 draws in calibration; state that PolyPythia has no 1B seeds.

*Status: all accepted; amendment 3 follows. Shape checks so far: DANDI 001453 holds behaviour only (no
neural traces), so by the registered rule R3 is Chen et al. 2018 (Janelia figshare 7272617; 18 zebrafish,
about 80,000 cells each; CC BY-NC 4.0, used locally, summary numbers only). With zebrafish as the only
fish, the calcium group is powered only if the fly (R11) is loaded.*


## Amendment 3 (12 Nov 2026, answering review 11, before any new brain data was read)

All points of review 11 are accepted. Code: `nematica/map/{measures,recording,analysis}.py`,
`scripts/map_calibrate.py`, `scripts/map_fake_brains.py`.

**Matching (must-fix 1, 2).** "Indicator decay" is the 1/e constant of exp(-n/decay) (half-decay times
from papers divided by ln 2). Fast networks are first *held*: each native step repeated for
k = ceil(8 / native tau_med) sub-steps (a convention for how long a token or step lasts; sensitivity at 2k),
so frames and bins finer than a native step can be reached. Calcium decay and frame are refined on the
noisy recording; spike bin and gain are iterated jointly with the timescale measured on the recorded
counts. Both report what they reached and a `reached` flag (within 10%; the noise share within 0.05
absolute); **a network whose targets are not reached is reported, not mapped.** **Each AI is recorded once
per group**, matched to the group's median instrument numbers (per-preparation matching is a sensitivity
analysis). **Mismatch budget:** every matched knob swept by a factor of 1.5 each way (the plausible error in
estimating a preparation's instrument numbers); a measurement that moves any mapped AI by more than 1 BVU
is dropped for the whole group. The budget, BVU, distance, nearest-neighbour and hypothesis code is now
written and frozen (`analysis.py`) and was run end to end on synthetic "fake brains" (below).

**Slow memory (must-fix 3)** is restated as a measure of a **mixture of timescales**: it rises when
components far slower than the median unit are present, and a system dominated by one slow timescale
scores like a fast one (its slow timescale then is the median). Its autocovariance is pooled over segments,
with at least 100 tau_med of data. C1 sweeps the slow share over 0 to 0.4, the range in which the median
unit stays fast.

**Calibration through the matching rule (must-fix 4).** C1 and C4 now record every synthetic system through
`match_calcium` / `match_spikes` against two instrument profiles per type: calcium A (decay 0.3 of the
recorded timescale, 4 frames per timescale, noise share 0.2) and B (0.8, 7, 0.4); spikes A (3 bins per
timescale, 0.5 spikes per bin, noise 0.6) and B (6, 0.2, 0.8). C4 sweeps the knobs matching does not set:
native timescale (1.5 to 30 samples per tau), population (60 to 3,000), and the calcium rectification gain
(0.5 to 4; a first run of the gain sweep had a bug that left the gain unchanged and was rerun). 20 draws,
2 seeds. 80 of the calibration recordings did not reach their targets within tolerance
(mostly at the extremes of the sweeps); they are included, which makes the gate conservative. Cells:
C1 Spearman / largest C4 ratio; "ok" = C1 >= 0.9 and every C4 ratio < 0.5.

| measurement | native | calcium A | calcium B | spikes A | spikes B |
|---|---|---|---|---|---|
| spectrum steepness | nan / 0.25 | nan / nan | -0.24 / 1.64 | nan / nan | nan / nan |
| shared fraction | 0.98 / 0.05 ok | 0.98 / 0.21 ok | 0.96 / 0.21 ok | 0.98 / 0.10 ok | 0.91 / 0.19 ok |
| slow memory | 0.98 / 0.17 ok | 0.98 / 0.08 ok | -0.31 / 0.76 | 0.98 / 0.03 ok | 0.98 / 0.07 ok |
| timescale spread | 0.98 / 0.06 ok | 0.98 / 0.07 ok | 0.91 / 0.86 | 0.94 / 0.47 ok | 0.94 / 0.62 |
| coupling spread | 0.96 / 0.09 ok | 0.98 / 0.03 ok | 0.96 / 0.11 ok | 0.98 / 0.23 ok | 0.96 / 0.30 ok |
| drift | 0.86 / 0.19 | 0.96 / 0.45 ok | nan / 0.17 | 0.62 / 0.42 | 0.17 / 1.72 |
| sparsity | 0.98 / 0.00 ok | 0.98 / 0.13 ok | 0.98 / 0.14 ok | 0.96 / 0.30 ok | 0.30 / 0.88 |

**Provisional measurement sets** (passing under both profiles): calcium: shared fraction, coupling spread, sparsity;
spikes: shared fraction, slow memory, coupling spread; native (AI to AI): shared fraction, slow memory, timescale spread, coupling spread, sparsity. **Final sets per
group:** once each group's median instrument numbers are known (they come from loading the data, before any
measurement), C1 and C4 are rerun on synthetic systems at exactly those numbers and the group uses the
measurements that pass there. This is the last calibration step before brain measurements.

**nan (must-fix 5):** a measurement that is nan in any mapped system of a group is dropped for the whole group
(so nan never shrinks a distance); a value needs at least 80% finite draws.

**Outcomes registered now (must-fix 6, 7).** A group is mapped only with at least 3 usable measurements and
at least 4 distinct preparation types. If the spike group cannot be mapped, H8 and the spike arm of H3 to
H6 are undecided and H1 is tested in calcium only; if neither group can be mapped, the study reports that
brain-AI comparison through matched recordings is not possible with these data and measurements, which is a
result about the question itself. The calcium group is powered only if the fly (R11) is loaded (R3 is
zebrafish only; DANDI 001453 holds behaviour only). **Slow set per group:** {slow memory, timescale spread,
drift} intersected with the group's measurements; **H5 and H3(b) are undecided in a group whose slow set is
empty.**

**H2 (changed):** an augmented AI passes if its nearest neighbour among the preparations and the standard AI
families (siblings and the preparations it was fitted on left out) is a real preparation, the same rule as
H1. The earlier threshold rule (nearest real within the largest real-to-real distance) let every standard AI
pass in the fake-brain test, because real preparations of different species are far apart.

**Should-fix items.** C3 is the split-half standard error (two disjoint unit pools), averaged over a
preparation's individuals, below **0.5** BVU (0.25 dropped every measurement on fake brains whose
individuals differ by 20%; the gate stays, at a level where measurement noise is less than half the
biological spread); no draw-count escape. Cross-talk is reported as ratios to each measurement's C1 range
(`X` in the JSON); the effective number of independent measurements will be reported with the map. H4 and
H6 hold only at both ends of the BVU interval (implemented); H4 and H5 are undecided if the conclusion
changes across timescale floors 2, 4 and 8. Units constant in native activity are dropped before recording.
R6 and R7 use whole sessions, flagged as task. PolyPythia has no 1B seeds, so H4's interval for 1B is over
text segments only. Calibration uses 20 draws (not 40) for time; values used in the map use 40.

**Fake-brain test** (`docs/figures/map_fake_brains.json`): five fake preparations from one region of
parameter space (20% individual variation, 30% between preparations, each with its own calcium instrument)
and four standard fake AIs from another region, plus one augmented AI near the brains. Every AI reached its
matched targets. *With the registered gates on,* the C3 and budget gates dropped every measurement, so no
hypothesis was decidable: on data like these the protocol says "cannot map" rather than guessing. *With the
gates off* (a code-path check only): separated regions give H1 real share 1.0 and AI share 1.0 (holds), and
the largest gaps are timescale spread, coupling spread and shared fraction; when the AIs are drawn from the
brains' region H1 fails (0.0 and 0.0). The decision code does what it should; whether the gates let real
data through is the open question this amendment cannot answer in advance.

## Review 12 (12 Nov 2026, before any new brain data): close for step 1, not ready for brain measurements

A third independent review checked amendment 3. **Fixed:** reporting of what matching reached, the decay
definition, slow memory as a definition, calibration through matching (procedure), the nan rule, the slow
set and undecided outcomes; the BVU interval and cap are correct. **Partly fixed or new, before step 1
(loading instrument numbers only):** (1) the white-noise estimator is biased low on smooth calcium signals
(true share 0.10 reads 0.00 to 0.07) but accurate on held or Poisson signals, so brains and AIs with the same
noise read differently; a shape-robust estimator is needed; (2) a frozen `instrument_numbers` function
(unit inclusion, rest segments, indicator decay table, median over individuals then preparations, no
per-unit timescale output); (3) culture spikes are binned at 50 ms in the loader against the registered 20 ms;
(4) a registered table of preparations and individuals (R10 one or three preparations; R7 is likely one
monkey per dataset; R2's role; R9 sessions; R11 units); (5) a rule for instrument spread within a group
(AIs recorded at the group median make AIs alike and brains different; record each AI at each
preparation's own instrument for AI-to-brain distances, or widen the budget to the group's range).
**Before brain measurements:** spike matching does not converge for slow networks and the hold factor
ignores the target (realistic Neuropixels-like numbers are unreachable); the timescale estimator is 2 to 5
times too short on sparse spikes at real noise levels (0.95 to 0.99), which calibration must cover; the
bootstrap for H4 to H6 resamples single replicates rather than means; H5's code uses RMS while the text says
"summed"; a missing C3 or budget value passes silently; segment boundaries are lost through recording;
**the C3 and budget gates are built to fail** (a 3-df maximum against a 10-df BVU; a budget compared across
different noise seeds, whose floor alone reached 0.5 to 0.8 BVU), so pooled, common-random-number versions
and noise-invariant measures (disattenuated sparsity and coupling) are needed; **no positive control** has
shown the gated pipeline can decide anything; H2 should also require a distance within the median
real-to-real neighbour distance and be undecided unless H1's AI half holds; the hold convention shifts some
measures by 1 to 2 BVU against linear interpolation (register both as sensitivities); unit tests.
Provenance: `map_calibration.json` was produced while `recording.py` was still being edited (the reached
tolerance and the calcium gain changed during the run; the gain sweep was rerun); it is regenerated with the
final code in amendment 4, with the code hash recorded.

*Status: all accepted. Amendment 4 will make these fixes, add a gated positive control on fake brains, and
regenerate both calibration files before step 1.*

## Amendment 4 (12 to 13 Nov 2026, answering review 12, before any new brain data was read)

All points of review 12 are accepted. No brain activity has been measured; the only real data touched so far
are file shapes. Code: `nematica/map/{measures,recording,instrument,analysis,data}.py`,
`scripts/map_calibrate.py`, `scripts/map_fake_brains.py`, `tests/test_map.py` (20 unit tests, F17).

**Estimators (F1, F7, F12).**
- *Signal variance* (the part of a unit's variance that is not white noise) is now a quadratic least-squares
  fit through lags 1 to 3, extrapolated to lag 0 and capped at the total. One estimator serves the timescale,
  the noise share and slow memory. On synthetic tests the noise share is within about 0.02 for smooth
  calcium-like, held and fast signals and within 0.05 for Poisson counts (the old lag-2 exponential read
  0.01 for a true 0.05 on smooth signals), and half-lives are recovered within 8% at a white share of 0.5
  and within 12% at 0.9 (the old estimator: 11% and 14%).
- *The system's timescale* (still called tau_med) is now the half-life of the **population**
  autocorrelation (units standardised, autocovariance averaged over units, divided by the averaged signal
  variance), not the median of per-unit half-lives. On sparse spike counts at a white share of 0.97 the
  per-unit median read 5 to 20 times too short (review 12's finding); the population version is unbiased
  there; on clean data the two agree within 1 to 10% (further apart when unit timescales are widely spread). Per-unit half-lives remain only inside
  timescale spread.
- *Noise-invariant measures:* **coupling spread** divides each unit's coupling by sqrt(1 - its noise
  share); **sparsity** divides excess kurtosis by (1 - noise share)^2 for continuous recordings, and for
  spike counts is the kurtosis of the underlying rate from factorial moments (for Poisson counts
  E[C(C-1)...(C-k+1)] = E[rate^k], so Poisson noise drops out exactly). For continuous recordings both are
  nan when the median noise share is above 0.8.
- *Segments (F11):* autocovariances are pooled over segments and recordings are made segment by segment
  (kernels, interpolation and bins never cross a boundary); recordings return their segment starts.

**Matching (F6, F15).** The hold factor is target-aware: k = ceil(max(8, 2 x target samples per tau) /
native tau_med), for slow networks too, and it is raised whenever the frame or bin would fall below one
sub-step. Calcium decay is the *smallest* decay that reaches its target (a log grid, then bisection): the
decay ratio is not monotone once a slow component takes over the recorded timescale. Then up to 8 rounds of
noise bisection and multiplicative frame, decay and bin updates on the achieved values, with common random
numbers (the same noise seed in every evaluation, so the search is deterministic), returning the best round.
The registered call (`recording.match`) uses at most 200 units and at least 400 recorded timescales (at 60
units and 100 timescales the timescale on sparse counts varies by about 40%; at this size about 10%).
Realistic targets are now reached for fast (1 step), medium and slow (30 steps) networks, including
Neuropixels-like spikes (10 bins per timescale, 0.1 spikes per bin, noise share 0.97) and noisy calcium
(decay 0.5 of the timescale, 3 frames per timescale, noise 0.6); unit tests cover the slow case.
Sensitivities registered: linear interpolation instead of the hold, and a hold of 2k
(`record_matched(..., interp=True)`).

**Instrument numbers (F2, F3)** are a frozen function, `instrument.instrument_numbers`, the only code step 1
runs on real data. It outputs aggregates only (timescale in seconds, samples per timescale, noise share,
decay ratio or count per bin, units, duration), never per-unit timescales or any measure. Unit inclusion:
calcium units with a noise share below 0.99; spike units with at least 200 spikes and 0.05 Hz. Rest
stretches only where a preparation marks them. All spikes are binned at 20 ms (`data.bin_spikes`; the
culture loader's 50 ms is fixed). Indicator decay is the half-decay time over ln 2, from a table filled at
step 1 with a citation per indicator (the in vivo single-spike value from the indicator's characterisation
paper where reported, else the dataset paper), before any matching. Aggregation: median over individuals
within a preparation, then over preparations.

**Instrument spread within a group (F5).** Every AI is recorded at **each preparation's own instrument
numbers**. An AI-to-preparation distance uses the AI recorded at that preparation's instrument; an
AI-to-AI distance is the mean over the group's preparations of the distance between the two AIs recorded at
the same instrument; an AI's position for centroids is its mean over the instruments. An AI is mapped only
if matching is reached at every preparation of the group. (Amendment 3's single recording at the group
median is withdrawn: it made AIs alike and brains different by construction.)

**Gates (F10, F12).**
- *C3* is the pooled split-half SE: for each individual, SE^2 is the mean over 5 random splits of
  (a - b)^2 / 4, with two disjoint unit halves when there are at least 100 units, otherwise the first and
  second half in time; a preparation's SE is the root mean SE^2 over its individuals; it must be below 0.5
  BVU in every preparation. A missing value fails.
- *Mismatch budget:* each matched knob is swept x/÷1.5 with common random numbers (the same recording seed
  and unit draws for the base and the swept recording, so seed noise does not count as sensitivity), mean
  over 2 seeds of the largest change; the group's budget is the median over mapped AIs of each AI's largest
  change over the preparations, and must be at most 1 BVU. A missing value fails.

**Analysis (F8, F9, F14, F16).**
- *Bootstrap for H4 to H6:* each resample draws each AI's replicates at every instrument (as many as it has,
  with replacement) and averages them, and draws each preparation's individuals for the brain centroid;
  BVU is held fixed and the test is run at both ends of its interval. At least 20 replicates per AI per
  preparation, else undecided.
- *H5:* RMS over the slow set in use, like every distance (the text said "summed").
- *H2:* undecided in a group unless H1's AI half holds there (standard AIs keep to themselves, so the
  rule is not loose). An augmented AI passes if its nearest neighbour among the preparations (those it was
  fitted on left out) and the standard AIs is a real preparation **and** that distance is at most the
  median real-to-real nearest-neighbour distance in the group. Augmented AIs are not siblings of their
  base model (two AIs are siblings when they share family *and* role).
- *Robustness:* a verdict counts only if it is the same at timescale floors 2, 4 and 8 and under the hold,
  linear interpolation and a hold of 2k; otherwise it is reported as undecided, with each variant's verdict.
- Centroids need at least 3 finite individuals (the mapping rule); BVU uses the same preparations;
  systems without a candidate neighbour make H1 and H8 undecided rather than failing; H8 needs a powered group.

**Preparations and individuals (F4)**, registered now, before step 1. A preparation is mapped with at least
3 individuals; "type" is species plus kind of preparation (in vivo, culture, organoid, slice); same dataset
or same type are siblings.

| id | group | type | individual | units | role |
|---|---|---|---|---|---|
| R1 | calcium | *C. elegans*, in vivo | worm | identified neurons (dataset ROIs) | mapped |
| R2 | calcium | *C. elegans*, in vivo | worm | dataset ROIs | exploratory, not counted (sibling of R1) |
| R3 | calcium | zebrafish larva, in vivo | fish (Chen et al. 2018) | dataset cells | mapped |
| R5 | calcium | mouse cortex, in vivo (2-photon) | mouse (recordings of one mouse pooled) | dataset cells | mapped |
| R11 | calcium | *Drosophila*, in vivo | fly | dataset ROIs or supervoxels; not loaded if only raw volumes exist | mapped if loaded |
| R4 | spikes | mouse, in vivo | mouse | sorted units | mapped |
| R6 | spikes | mouse, in vivo | mouse | sorted units, whole sessions (task flagged) | mapped (sibling of R4) |
| R7 | spikes | macaque, in vivo | MC_Maze and MC_RTT are likely one monkey each | sorted units | exploratory unless 3 monkeys are found |
| R9 | spikes | rat cortical culture | culture (its last-day session) | electrode (detected spikes) | mapped |
| R10a | spikes | human brain organoid | organoid | as in the dataset | mapped |
| R10b | spikes | mouse brain organoid | organoid | as in the dataset | mapped |
| R10c | spikes | mouse neonatal slice | slice | as in the dataset | mapped |
| R8 | (none) | human cortex | patient | field potentials | exploratory (no recording model) |

So the calcium group has at most 4 types (worm, zebrafish, mouse, fly) and is powered only if all four
load with at least 3 individuals; the spike group has up to 5 (mouse in vivo, rat culture, human organoid,
mouse organoid, mouse slice).

**Calibration, regenerated with the final code (F7, provenance).** `docs/figures/map_calibration.json`,
code hash 539cc49115ea3f64 (the measurement, recording, analysis and calibration files as committed in
4fb8ee9; the run started from the working tree on top of 4f84743, and the only file changed during it was
the indicator table in `instrument.py`, which calibration does not use). Profiles: calcium A (decay 0.3 of
the recorded timescale, 4 frames per timescale, noise share 0.2) and R (0.5, 3, 0.6); spikes A (3 bins per
timescale, 0.5 spikes per bin, noise 0.6) and R, Neuropixels-like (10, 0.1, 0.97). Amendment 3's profile B
is replaced by the realistic R profiles. 20 draws, 2 seeds; 7 of 360 matches did not reach their targets
(included). Cells: C1 Spearman / largest C4 ratio; "ok" = C1 >= 0.9 and every C4 ratio < 0.5.

| measurement | native | calcium A | calcium R | spikes A | spikes R |
|---|---|---|---|---|---|
| spectrum steepness | 0.96 / 0.25 ok | nan / nan | nan / nan | nan / nan | nan / nan |
| shared fraction | 0.98 / 0.04 ok | 0.98 / 0.20 ok | 0.94 / 0.18 ok | 0.98 / 0.13 ok | 0.25 / 1.19 |
| slow memory | 0.98 / 0.14 ok | 0.98 / 0.09 ok | 0.94 / 0.18 ok | 0.98 / 0.05 ok | 0.71 / 0.65 |
| timescale spread | 0.98 / 0.10 ok | 0.98 / 0.03 ok | 0.94 / 0.27 ok | 0.94 / 0.17 ok | -0.34 / 0.58 |
| coupling spread | 0.96 / 0.06 ok | 0.96 / 0.03 ok | 0.94 / 0.11 ok | 0.98 / 0.09 ok | nan / nan |
| drift | 0.84 / 0.23 | 0.74 / 0.15 | 0.89 / 0.41 | 0.47 / 1.23 | 0.54 / 0.41 |
| sparsity | 0.98 / 0.00 ok | 0.98 / 0.12 ok | 0.98 / 0.12 ok | 0.98 / 0.04 ok | -0.32 / 0.77 |

So calcium keeps five measurements under both profiles (amendment 3 kept three), and so do moderately
noisy spikes. **At Neuropixels-like noise no measurement survives** with 50-unit draws: each unit is about
97% Poisson noise. A one-seed check (not part of the gate; `data/cache/spikeR.py`) of draws of 200 units
and windows of 600 timescales did not rescue it: slow memory stayed monotone in its property under both
protocols, shared fraction stayed at zero, timescale spread and sparsity did not track theirs, and
coupling spread is undefined above a noise share of 0.8. No fallback protocol is registered. If the spike
group's step-2 calibration at its real instrument numbers keeps fewer than 3 measurements, the spike group
is not mapped, and by amendment 3 H8 and the spike arm of H3 to H6 are undecided.
*Timescale recovery:* the recorded timescale in native steps over the true one is 1.0 in native units,
1.1 to 1.5 (calcium A) and 1.8 to 2.4 (calcium R; the indicator lengthens the timescale, which is part of
the recording, not an estimator bias), and 0.66 to 1.03 for spikes. Drift fails everywhere except native
units (0.84); spectrum steepness never beats its null once recorded.

**Gated positive and negative controls (F13)** (`docs/figures/map_fake_brains.json`, code hash 203b0300c22ba9db,
every registered gate on). Five fake preparation types, four individuals each, each with its own calcium instrument; instrument
numbers from `instrument_numbers`; every fake AI matched and recorded at each preparation's instrument;
pooled C3 (5 splits); budget with common random numbers.
- *Separated (positive control):* all matches reached; four measurements usable (sparsity dropped by C3 at
  0.58 BVU); C3 0.18 to 0.49 BVU and budget 0.11 to 0.67 BVU for the rest. **H1 holds** (real share 1.0,
  AI share 1.0); **the augmented AI passes H2** (nearest P2 at 0.74 BVU, limit 0.83); the paired bootstrap
  decides (two standard AIs 3.13 and 3.01 BVU from the brains: the H6 equivalence rule holds and the H4
  rule holds, both at both BVU ends); the largest gaps are slow memory, timescale spread, shared fraction,
  coupling spread. So the gated pipeline *can* decide when the answer is clear, which amendment 3's could not.
- *Mixed (negative control):* AIs drawn from the brains' region. Only two measurements survived (slow
  memory and timescale spread failed the budget at 1.3 and 2.0 BVU: brain-like AIs with slow components are
  more sensitive to recording knobs), so the group is not mapped and every hypothesis is undecided. The
  pipeline made no false claim, but this control did not show a correct rejection under the gates; that
  remains untested, and the gates' sensitivity to slow, brain-like systems is a limitation to watch.

**Power, stated before data (F12).** With the minimum powered group (4 preparation types, 3 individuals
each) the BVU has 8 degrees of freedom and its 90% interval runs from 0.72 to 1.71 times the estimate;
H1's 80% rule then means every preparation's neighbour must be real (4 of 4). Paired tests use at least 20
replicates per AI per preparation. The positive control (5 types, 4 individuals, df 15) is about the
smallest world in which the pipeline decided; real groups with fewer types or more instrument noise are
expected to be undecided, which will be reported as such.

**Code hashes.** Both JSON files record a hash of the files they ran; both match the committed files.
Two docstrings in `measures.py` state accuracy loosely ("within a few percent", "0.02 to 0.04"); they are
left unedited so the hashes stay valid, and the figures in this amendment govern.

**Text corrections marked in place:** H5 in the hypothesis table and in amendment 2 ("summed") now reads
RMS; README's hypothesis table is updated to the rules as amended.

*Status: amendment 4 complete. Next: independent review 13 of amendments 3 and 4 and the code; if it
clears, step 1 (instrument numbers only) runs on the real datasets.*

## Review 13 (13 Nov 2026, before any new brain data): ready for step 1 with fixes, not ready for brain measurements

A fourth independent review checked amendment 4 against the code and JSON. **Confirmed:** both code hashes
match the committed files (the calibration cache tag confirms the provenance note); the calibration table and
fake-brain numbers match the JSON; the 8-df BVU interval is right; F3, F9, F10, F14, F16 are fixed; F6 holds
(a fast network reached calcium R, Neuropixels-like spikes and a worm-like profile); `instrument_numbers`
outputs aggregates only. **Before step 1:** (1) the timescale uses only the longest segment (`_acov_seg`
keeps segments of at least 4 x max_lag with max_lag from the longest one), so a preparation with unequal
rest stretches is timed from one stretch (3,000 samples at half-life 8 plus nine of 2,900 at half-life 2
read 7.82; pooled, 2.06); (2) F1 is only partly fixed and the text overstates it: on calcium-shaped signals
(decay 1.1 to 8 steps) a true white share of 0.10 reads 0.043 to 0.076 and 0.30 reads 0.25 to 0.28, and the
fake brains' instrument numbers read low in all 10 preparations; (3) step-1 inputs are not registered: trace
type per dataset (raw, dF/F, neuropil-corrected, deconvolved), the rest definition for R1 (its dataset marks
stimuli, not rest), an indicator rule for nuclear GCaMP and non-mammalian temperatures, and a hash of the
loaders in step 1's output. **Before brain measurements:** (4) one AI's value moves across the five similar
fake instruments by 0.9 to 3.8 BVU on some measures, while real-to-real distances are not instrument-matched,
which inflates them in the direction of the worm prediction (an instrument-transfer gate is needed);
(5) factorial-moment sparsity on counts is unusable at 0.1 to 0.5 spikes per bin and depends on the spread of
rates, which AI recordings do not reproduce (every AI unit gets the same mean count); (6) the budget takes the
median over AIs where the max is needed, CRN is not exact for the frame knob, and the "floor removed" is not
implemented; (7) the bootstrap's replicates are recording seeds of one network, not instances; (8) the
robustness rule cannot run as written (hold 2k unimplemented; interpolation reuses hold-matched knobs; floors
would rescale brain windows; whether gates rerun per variant is unspecified); (9) the C3 time-half fallback
fails for preparations under 300 timescales (the worms); (10) the positive control is too favourable (same
generator, noise 0.02 to 0.23, 5 x 4, all parameters separated, calcium only); graded controls at realistic
noise and the minimum group size are needed. **Minor:** slow memory turns down above a slow share of 0.6;
a bleaching-like trend in 30% of units raises the population timescale by 27% (register detrending); the
measures.py module docstring describes the old tau_med; `match()` takes no segments; spike timescale
recovery of 0.66 at 1.5 samples per tau contradicts "unbiased"; `h2` can return decided with no verdict.

*Status: all accepted. Amendment 5 fixes items 1 to 3 (and the minor ones that touch step 1) before step 1;
items 4 to 10 are fixed before any brain measurement.*

## Amendment 5 (13 Nov 2026, answering review 13's step-1 items, before any new brain data was read)

Review 13's items 1 to 3 and the step-1 minor items are fixed; items 4 to 10 are fixed before any brain
measurement (a later amendment). Code: `nematica/map/{measures,recording,instrument,analysis}.py`; 24 unit
tests (4 new).

- **Every stretch counts (item 1).** Autocovariances are pooled over all segments: lag products are summed
  over every segment longer than the lag and each lag is divided by its own number of pairs (so lags never
  cross a boundary and short stretches are no longer discarded). The reviewer's case (one 3,000-sample
  stretch at half-life 8, nine of 2,900 at half-life 2) now reads 2.7 (amendment 4: 7.8). Unit test added.
- **Noise share (item 2).** The signal variance is now the cubic through lags 1 to 4 extrapolated to lag 0
  (amendment 4: a quadratic through lags 1 to 3). On calcium-shaped signals (indicator decay 0.3 to 8
  native steps, true white share 0.1, 0.3, 0.6), AR signals and Poisson counts the error is at most 0.033
  (worst: decay comparable to the native timescale, read low; amendment 4's estimator: 0.05 there).
  *(Corrected after review 13's follow-up: with fractional frames the worst case is 0.041, decay 1.13 and
  frame 1.08; read "at most about 0.04".)* This
  residual bias is registered, not hidden: it applies equally to brains and AIs recorded through the same
  model, but not to brains whose real signal shape differs from the model's; step 2 reports it at each
  group's numbers. Amendment 4's "within about 0.02" was wrong for calcium and is corrected here. Unit test
  on calcium-shaped signals added. Spike timescale recovery is 0.66 at 1.5 samples per timescale, rising to
  0.92 at 30 (amendment 4's word "unbiased" applied only to the high-noise comparison with the per-unit median).
- **Detrending (minor item, registered now).** In the calcium group every recording, brain and AI alike,
  has each unit's linear trend removed within each segment before instrument numbers and measures
  (bleaching raised the population timescale by 27% in the reviewer's test).
- **Segments in matching (minor item).** `match` and both matchers take segments; recordings inside
  matching are made and timed segment by segment.
- **`h2`** now returns undecided when no candidate could be decided.

**Step-1 inputs, registered now (item 3).**
- *Trace type.* Calcium preparations use fluorescence (F or dF/F as shipped, neuropil-corrected where the
  dataset provides it; the noise share and timescale do not depend on per-unit scale). Deconvolved or
  inferred-spike traces are not modelled: a dataset that ships only those is not used. If R5 (Stringer et
  al. 2019) ships only deconvolved activity, R5 is replaced by the Allen Brain Observatory Visual Coding
  two-photon dataset (de Vries et al. 2020), spontaneous-activity epochs, dF/F traces, one individual per
  mouse; this is decided at step 1 from the files' contents and reported.
- *Rest for R1.* Its dataset marks stimulation, not rest. Rest = everything except the 30 s after each
  stimulation onset (sensitivity: 15 s); stretches shorter than 20 s are dropped. R6 and R7 keep whole
  sessions (task flagged), as registered in amendment 3.
- *Indicator rule.* The half-decay comes from the dataset paper if it states one for its own preparation;
  otherwise from the table in `instrument.py` (Chen et al. 2013 in vivo 1-AP values, about 0.1 s for
  GCaMP6f, 0.2 s for 6m, 0.5 s for 6s; Dana et al. 2019 for jGCaMP7f, cultured neurons). For
  nuclear-localised indicators and preparations imaged below 30 C (worm, fish, fly) the table value is a
  convention: step 1 reports the decay ratio at the table value and at twice it, and step 2 calibrates at both.
- *Provenance.* Step 1's output stores `instrument.code_hash` over `instrument.py`, `measures.py`,
  `data.py` and the loader script it runs, plus the dataset identifiers and versions.

**Before brain measurements (registered as open):** review 13's items 4 (an instrument-transfer gate:
each AI's range across the group's actual instruments under 0.5 BVU), 5 (sparsity on counts: dropped or
re-estimated, and AI recordings given the brain's distribution of rates and noise shares), detrending wired
into `measure_matched`, `match` and `record_matched` for the calcium group (in code it is so far applied only
in `instrument_numbers`), 6 (budget as the
max over AIs; CRN for the frame knob), 7 (hierarchical bootstrap over network instances), 8 (robustness
variants re-matched and run in a control; floors applied only to resolution-limited native systems),
9 (an alternative C3 split for short preparations), 10 (graded positive and negative controls at realistic
noise and the minimum group size, several seeds, with decision and false-positive rates), and 11 (slow
memory's turn-down above a slow share of 0.6, which places augmented candidate (a) outside C1's range).
The amendment-4 calibration and fake-brain files remain as evidence for that code version; both are
regenerated with the final estimators at step 2.

*Status: ready for step 1 by review 13's criteria. Step 1 runs only `instrument_numbers` on the real
datasets.*

**Review 13 follow-up (13 Nov 2026):** the same reviewer checked amendment 5. *Step 1 may run.* Item 1 fixed
(2.71 against 7.82; the remainder is the long stretch's real share of variance); item 2 mostly fixed (true
0.10 reads 0.059 to 0.090; worst error 0.041 with fractional frames, corrected above); item 3 registered,
with the caution that the R1 rest construction must be shown in a loader under the step-1 hash; segments in
matching, `h2` and step-1 detrending fixed (trending units no longer move the timescale). Detrending in the
measurement path is added to the open list above.

## Amendment 6 (13 Nov 2026, from file metadata at the start of step 1, before any instrument number or measure was computed)

Opening the worm files for step 1 (stimulus times and recording lengths only) showed that **R1 has
almost no rest under the registered rule**: in all 113 wild-type recordings of Randi et al. 2023 a neuron is
stimulated every 31 s (5th to 95th percentile of gaps 30.5 to 37.5 s), so excluding 30 s after each onset
leaves only the stretch before the first stimulus (median 21 s; at least 100 s in only 2 recordings). That
is shorter than a few timescales, so no instrument number or measure can be taken from it. The two
unstimulated Randi recordings are fewer than 3 individuals. Changes, decided from these metadata alone:
- **R1 becomes exploratory** (whole sessions with stimulation flagged, reported, not counted).
- **R2 becomes the mapped worm preparation:** Atanas et al. 2023 (local copy of the WormWideWeb release;
  30 freely moving worms, NeuroPAL strain, 0.6 s frames, about 16 min each, 121 to 153 neurons, traces
  `trace_original`). Rest: the 13 "baseline" recordings whole (their two halves as segments); for the 17
  "heat" recordings, only the stretch before the heat pulse (first range, about 8 min). Individual = worm.
  Indicator: NLS-GCaMP7f (nuclear); by amendment 5 the table value for jGCaMP7f is a convention and
  step 1 reports the decay ratio at it and at twice it. R2 is freely moving, so its activity includes
  locomotion; that is a property of this preparation, flagged in the results.
- The calcium group's worm type is therefore *C. elegans*, freely moving, in vivo; the group still needs
  four types (worm, zebrafish, mouse, fly) to be powered.
