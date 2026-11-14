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

## Amendment 7 (13 Nov 2026, from file metadata during step 1, before any zebrafish instrument number or measure)

R3's rest was never defined. The zebrafish files (Chen et al. 2018, figshare 7272617; read for protocol
names, frame rates and stimulus codes only) show that fish 1 to 7 saw visual stimuli throughout (phototaxis
and black/white blocks), while fish 10 and 12 to 18 have a block named *Spontaneous* (stimulus code 4;
for example 517 frames at 2 Hz in fish 16, 640 frames at 2.56 Hz in fish 12). Registered now:
- **R3 rest = the frames of the "Spontaneous" block** (from the file's protocol frame lists; a gap inside
  the block is a segment boundary). Fish without such a block are excluded. Fish whose stated frame rate is
  outside 1 to 5 Hz are excluded (fish 17 states 38 Hz, implausible for this light-sheet protocol).
- Activity = `CellResp` (dF/F, the least-processed trace shipped); all cells pass to the unit-inclusion
  rule of `instrument_numbers`. Indicator: GCaMP6f (nuclear-localised in this line), so by amendment 5 the
  table value is a convention, reported at 1x and 2x.
- Fish 8, 9 and 11 could not be read by streaming (their archives fail at the member header); they are
  attempted by full download, and excluded if still unreadable.
So R3 has at most 8 individuals (10, 12, 13, 14, 15, 16, 18, and 8, 9, 11 if readable and with a
Spontaneous block). The Spontaneous blocks last about 4 to 9 minutes.

## Amendment 8 (13 Nov 2026, from file contents and metadata during step 1, before those preparations' instrument numbers or any measure)

- **R11 (fly) is not loaded.** DANDI 000727 ships imaging volumes only (for example a processed functional
  series of 3,384 x 314 x 146 x 91 voxels and raw series, about 67 GB per fly), no ROI or supervoxel
  traces; by amendment 4's table the fly is then not loaded (this study does not segment volumes).
  **Consequence, registered in amendment 3:** the calcium group has at most three types (worm, zebrafish,
  mouse) and is **not powered**; H1 to H6 are not tested in calcium. Its preparations are still measured and
  shown on the map, described, not tested.
- **R5 is replaced** (rule of amendment 5): the Stringer et al. 2019 spontaneous two-photon files hold only
  `Fsp`, deconvolved activity. The Allen Brain Observatory fallback is loaded for the map if time allows; it
  cannot make the calcium group powered.
- **R4** (Stringer et al. 2019, figshare 7739750, three mice, eight probes each): individual = mouse; units =
  every probe's sorted clusters; spikes binned at 20 ms; the whole recording is spontaneous.
- **Length cap for instrument numbers:** at most the first 20 minutes of each individual's rest are used
  (memory: a mouse has about 2,000 units). Measures later use their own registered windows.
- **R10 from DANDI 001603 (curated spikes):** human organoids (HO1 to HO8), mouse organoids (MO1 to MO14),
  mouse slices (M1S1 to M3S2; individual = mouse, its first slice only, so slices from one mouse are not
  counted twice), and rat planar cultures (PR1 to PR8) as **R10d**, type "rat cortical culture", a sibling
  of R9. For subjects with several sessions the first curated-spikes session is used.
- So the spike group has five types (mouse in vivo: R4, R6; rat culture: R9, R10d; human organoid;
  mouse organoid; mouse slice) and is powered if its measures survive step 2.

## Amendment 9 and step 1 results (13 Nov 2026; instrument numbers only, no measure computed)

**Amendment 9 (made during step 1, mechanical):** instrument numbers use at most 500 randomly chosen units
per individual (seeded; memory; aggregates are pooled or medians, so a random subset is unbiased); a
preparation's numbers are medians over the individuals whose numbers are all finite, with the count of
excluded individuals reported; curated spikes shipped only as a 1 ms binned matrix (four rat planar
cultures) are summed into 20 ms bins; the three zebrafish archives over 4 GB store member offsets 2^32 too
large and a wrong CRC, so offsets are corrected and the CRC check is left to HDF5 (fish 8, 9 and 11 still
failed to open and are excluded). Every individual's numbers equal what the final code
(`docs/figures/map_step1.json`, hash b999b7da794825c2) produces; the cached values were computed before
loader-only changes that do not alter them (checked: the two cultures with over 500 units were recomputed
under the unit cap).

**Step 1 results** (`docs/figures/map_step1.json`; medians over individuals):

| prep | type | individuals usable / tried | units | timescale | samples per timescale | noise share | length in timescales | other |
|---|---|---|---|---|---|---|---|---|
| R2 | worm, freely moving | 30 / 30 | 142 | 4.4 s | 7.3 frames | 0.013 | 157 (baseline 193 to 277; pre-heat 84 to 98) | decay ratio 0.087 (x2: 0.17) |
| R3 | zebrafish | 7 / 18 | 420 | 2.8 s | 5.7 frames | 0.49 | 96 (91 to 242) | decay ratio 0.051 (x2: 0.10) |
| R4 | mouse, Neuropixels | 3 / 3 | 482 (of 1,462 to 2,688) | 47 ms | 2.3 bins | 0.83 | 25,600 | 0.069 spikes per bin |
| R6 | mouse ALM | 9 / 9 | 39 | 1.2 s | 60 bins | 0.91 | 1,000 | 0.055 |
| R9 | rat culture (HD-MEA) | 3 / 7 | 135 | 0.19 s | 9.3 bins | 0.69 | 6,500 | 0.024 |
| R10a | human organoid | 4 / 8 | 23 | 0.36 s | 18 bins | 0.72 | 540 | 0.053 |
| R10b | mouse organoid | 14 / 14 | 76 | 89 ms | 4.5 bins | 0.68 | 6,800 | 0.10 |
| R10c | mouse slice | 3 / 3 | 62 | 83 ms | 4.2 bins | 0.73 | 4,600 | 0.014 |
| R10d | rat planar culture | 7 / 8 | 196 | 51 ms | 2.5 bins | 0.49 | 6,400 | 0.035 |

Not loaded: R1 (no rest, amendment 6), R5 (deconvolved only; Allen fallback not yet loaded), R11 (volumes
only), R7 and R8 (exploratory).

**What step 1 shows, before any measure:**
1. *Recordings shorter than a window.* The registered window is 150 timescales. Zebrafish Spontaneous blocks
   are 91 to 242 timescales (median 96), so at most one or two fish could be measured; the pre-heat worm
   recordings (84 to 98) cannot; the 13 baseline worms can. **The calcium group can be mapped, at best,
   for worms alone**, so the calcium arm is descriptive only (already unpowered by amendment 8).
2. *Too few units.* The protocol draws 50 units. R6 (median 39) and R10a (median 23) fall below it in most
   individuals and cannot be measured as registered.
3. *Where the timescale estimator fails.* In 9 spike individuals (4 of 7 cultures, 4 of 8 human organoids,
   1 planar culture) the population timescale is undefined: either very few units (1 to 14) or a lag-1
   autocovariance below lag 2 (refractoriness or bursts at 20 ms, which the white-noise model does not
   describe), which makes the extrapolated signal variance negative. They are excluded and counted.
4. *The spike group can still be powered*: mouse in vivo (R4), rat culture (R9, R10d), mouse organoid
   (R10b) and mouse slice (R10c) are four types with at least 3 individuals of at least 50 units. Their
   noise shares are 0.49 to 0.83, between calibration profiles A (0.6) and R (0.97), so step 2 decides.
   R4's 2.3 bins per timescale is close to the 2-sample floor.
5. *The worm traces are probably pre-processed:* a white-noise share of 0.013 is far below any raw
   fluorescence; `trace_original` in this release appears to be denoised. This is flagged; an AI matched
   to it will be recorded with almost no noise.

*Next:* step 2 (calibration at each spike preparation's own numbers) and review 13's items 4 to 10, both
before any brain measurement; then an independent review of steps 1 and 2.

## Amendment 10 (13 Nov 2026, review 13's items 4 to 10, before any brain measurement)

Code: `nematica/map/{measures,recording,instrument,analysis,pipeline}.py`, `scripts/map_step2.py`,
`scripts/map_controls.py`; 28 unit tests.
- **Instrument-transfer gate (item 4).** Each AI is already recorded at every preparation's instrument; a
  measurement is now used in a group only if every AI's range of values across the group's instruments is
  below 0.5 BVU (`analysis.transfer_range`). If instruments alone move an AI by more, real-to-real distances
  would partly measure instruments, so the measurement is dropped.
- **Spike recordings (item 5).**
  - *Sparsity is undefined for spike counts* (amendment 4's factorial-moment estimate was unusable at real
    count levels). It remains for calcium.
  - AI spike recordings now give units the brain's spread of rates: a fixed, seeded log-normal set of
    multipliers with median 1 and the preparation's SD of log unit rates, a new instrument number. Step 1
    was rerun for the spike preparations to add it (0.6 to 1.3).
  - The matched count per bin is now the median over units, as in the instrument numbers.
  - **The spike nonlinearity is now exponential (log-normal rates) instead of softplus.** With softplus the
    largest possible rate CV is 1.46, so the white-noise share at m spikes per bin cannot fall below
    1/(1 + 2.13 m). That floor is 0.91 to 0.97 for R4, R9, R10b, R10c and R10d, whose measured shares are
    0.49 to 0.83, so **no real spike preparation could have been matched**. With the exponential, all six
    real spike profiles (R4, R6, R9, R10b, R10c, R10d) are reached on a synthetic network. Calcium keeps
    softplus.
  - Spike matching may take up to 14 rounds.
- **Budget (item 6)** is now the largest change over AIs and preparations (not the median). Each AI's
  change is computed with common random numbers, and the seed floor is subtracted: half the absolute
  difference between two base recordings with different seeds (`pipeline.ai_at_prep`). CRN remains
  inexact for the frame and bin knobs, whose changes realign the samples; the floor subtraction is the
  registered allowance for that.
- **Bootstrap (item 7)** is hierarchical: replicates carry their instance (network seed, checkpoint or
  text segment set). Instances are resampled, then recordings within them. Paired tests need at least
  20 recordings from at least 3 instances at every instrument.
- **Robustness variants (item 8)** are re-matched, not reused: `match(..., hold_mult=2)` for the 2k hold
  and `match(..., interp=True)` for linear interpolation. Timescale floors 4 and 8 apply only to systems
  flagged resolution-limited (below 2 samples per timescale), so they never rescale a brain or a matched
  AI's windows. The measurement set and gates are fixed at the primary variant; only verdicts are
  recomputed under each variant.
- **C3 for short preparations (item 9).** When neither unit halves (at least 100 units) nor time halves
  (at least 1.2 windows each) are possible, two unit halves of h = n/2 units (at least 20) are measured with
  h-unit draws, and the SE is scaled by sqrt(h/50).
- **Graded controls (item 10)**, `scripts/map_controls.py`, set up as follows:
  - the spike group at realistic numbers (each fake preparation takes one real step-1 instrument: R4, R9,
    R10b, R10c);
  - the minimum powered size, 4 types x 3 individuals;
  - separations of 0, 1, 2 and 3 between-preparation spreads, 2 seeds each, with every gate on;
  - the paired test uses 5 instances x 4 recordings;
  - reported: the H1 decision rate and, at separation 0, the false-positive rate.

  Fake brains and fake AIs still share one generator and recording model; that limit is stated, not removed.

## Step 2 results (13 Nov 2026; synthetic systems only, at each preparation's own instrument numbers)

`docs/figures/map_step2.json` (code hash 62b1c7633483ad75). Through the registered matching call, C1 and C4
were rerun at the numbers of the five mappable spike preparations (R4, R9, R10b, R10c, R10d) and of the
baseline worms (R2). All 360 matches reached their targets. *Run notes:* the run was killed for memory three
times on the 3,000-unit systems. Two memory-only changes were made: recording upsamples each block of units
on its own, and autocovariances are computed in blocks of units. Both were checked to give bit-identical
output, so finished jobs were carried over under the new code hash. A third change: 3,000-unit systems
whose recording would exceed 10^8 unit-samples are not measured (nan); this affected only the two
3,000-unit C4 jobs at the profiles with the longest recordings.

| measurement | native | worms (R2) | R4 | R9 | R10b | R10c | R10d |
|---|---|---|---|---|---|---|---|
| shared fraction | ok | ok | 0.37 | 0.12 | 0.71 | -0.47 | -0.76 |
| slow memory | ok | ok | ok | C4 0.55 | ok | C4 1.44 | C4 0.71 |
| timescale spread | ok | ok | 0.12 | 0.12 | -0.49 | -0.49 | 0.30 |
| coupling spread | ok | ok | nan | nan | 0.33 | nan | nan |
| sparsity | ok | ok | (undefined for counts) | | | | |
| drift | 0.86 | 0.57 | 0.15 | -0.22 | 0.02 | 0.07 | |
| spectrum steepness | nan | nan | nan | nan | nan | nan | nan |

(ok = C1 >= 0.9 and every C4 ratio < 0.5; otherwise the C1 Spearman, or the failing C4 ratio.)

**Result.** At the worms' numbers five measurements pass. At every real spike preparation's numbers,
**no more than one measurement passes** (slow memory, at R4 and R10b), and none passes at all five.
- The spike group's measurement set (those passing at every preparation) is empty, so by amendment 3 the
  spike group **cannot be mapped**: H8 and the spike arm of H3 to H6 are undecided.
- The calcium group is unpowered (amendment 8), so H1 to H6 are not tested anywhere.
- By the rule registered in amendment 3: *through matched recordings, with these measurements and these
  data, brain vs AI comparison is not possible for spike data at the quality of these datasets*. Sparse
  counts in 20 ms bins (0.014 to 0.10 spikes per bin), 50-unit draws and heavy-tailed rates leave each unit
  mostly Poisson noise, and what remains does not track the systems' properties.
- This is a result about the question: the commonly reported population statistics of spiking data (shared
  variance, timescale spread, coupling) cannot be compared across brains and AIs at this recording quality
  without matching the instrument, and once the instrument is matched they cannot be recovered.
- The calcium arm at worm-like quality keeps five measurements. **That is where a powered comparison is
  still possible**, if more calcium preparations of distinct types can be added (amendment 11).

## Amendment 11 (13 Nov 2026, after step 2, before any brain measurement): a relaxed spike protocol

Step 2 left the spike group unmappable. On the user's instruction to go for the strongest results that can
still be shown, the spike protocol is relaxed here. This is decided before any brain activity is measured,
and **the rules are weaker than registered, so every spike-group result will be labelled as resting on
amendment 11.**
- *Why windows.* An exploratory check (one seed, not part of any gate) at the R10b and R4 numbers showed
  that 1,500-timescale windows recover what 150-timescale windows lose:
  - R10b: shared fraction 0.9 to 1.0, timescale spread 0.3 to 0.9, coupling spread from undefined to
    1.0, slow memory 1.0;
  - R4: shared fraction 0.8 to 1.0, slow memory 1.0; timescale spread at most 0.8 even with 5,000
    timescales (R4 has 2.3 bins per timescale), and coupling spread undefined (its noise share 0.83 is
    above the 0.8 disattenuation limit).
- **Spike windows are 1,000 timescales** (`measures.SPIKE_WINDOW_TAU`), applied to every spike-count
  recording, brain and AI alike. The rule: the largest round number below 0.9 times the shortest mapped
  spike individual (1,152 timescales, an R10b organoid). That is about 90 to 460 spikes per unit per window.
  Calcium and native windows stay 150.
- **R10c (mouse slices) is not mapped:** only 2 of its 3 slices have at least 50 units. The spike group is
  therefore three types: mouse in vivo (R4), rat culture (R9, R10d), mouse organoid (R10b).
- **For the spike group only, MIN_TYPES is 3 (was 4) and MIN_MEASURES is 2 (was 3).** With three types,
  H1's 80% rule means every preparation's nearest neighbour must be real; with two measurements, distances
  are coarse. Every other gate stands: C1 and C4 at every preparation's numbers (rerun now), C3, the
  maximum budget, instrument transfer, controls.
- The graded controls now use this protocol (3 types x 3 individuals, the spike set from the rerun step 2).

## Step 2 under amendment 11, and amendment 12 (13 Nov 2026, before any brain measurement)

**Step 2 rerun with 1,000-timescale spike windows** (`docs/figures/map_step2.json`, same gates). The
spike group's measurement set is **still empty**:
- R4 keeps slow memory only (shared fraction narrowly misses at C1 0.89);
- R9 keeps shared fraction only (slow memory fails C4, 0.55);
- R10b keeps shared fraction, slow memory and coupling spread;
- R10d keeps none (shared fraction 0.74; slow memory fails C4, 0.71).

No measurement passes at every spike preparation, even with windows 6.7 times longer and the bar lowered to
two measurements. **The spike arm is closed:** at the quality of these datasets (0.06 to 0.5 spikes per unit
per timescale) the comparison cannot be made with any measurement in this set, and each surviving
measurement depends on how fast a network runs relative to the instrument (C4). This is reported as the
study's first main result, with the numbers above. No spike-group test or map will be shown.

**Amendment 12: the worm map (descriptive, registered now, before any worm or AI measure).** Calcium at the
worms' numbers keeps five measurements (shared fraction, slow memory, timescale spread, coupling spread,
sparsity), but with one preparation type no H1 to H8 test is possible. What is registered instead:
1. Every AI (A1 to A7, A10, candidates (a) and (b)) is recorded through the worm instrument (R2's step-1
   numbers), with budget, and measured like the worms.
2. The 13 baseline worms of R2 are measured (the pre-heat recordings are shorter than a window). The
   ruler is R2's own between-worm SD per measurement (BVU, 12 df), with the C3 and budget gates.
3. **Worm envelope:** an AI is "worm-like" if its distance (RMS over the usable measurements, in worm
   BVU, capped at 10) to the worm centroid is at most the largest distance of any single worm to the
   centroid of the other 12 (leave-one-out). Reported for every AI with its interval over instances.
4. **Descriptive questions, each answered by numbers, not a test:**
   - which AIs fall inside the envelope;
   - whether the augmented AIs (slow drives; the OU latent; the lab network) are closer than their bases
     (H3(b)'s 30% rule, applied descriptively);
   - whether bigger Pythia models are closer (H4's rule);
   - whether Mamba is closer than Pythia on the slow measurements in use (H5's rule);
   - whether CfC is closer than GRU (H6's rule).

   Because this is one species and one instrument, nothing here generalises to "brains". It says which
   artificial systems are indistinguishable from worms, as worms are recorded.
5. The A10 lab network was tuned on worms (on R1-like data), so it is reported but marked as fitted.

## Review 14 (13 Nov 2026, before any worm measurement): not ready

A fifth independent review checked amendments 5 to 12, steps 1 and 2 and the code against the files.
**Confirmed:**
- no brain measure exists;
- amendments 6 to 9 rest on metadata, 10 and 11 on instrument numbers and synthetic runs;
- amendment 11 is reported honestly and dropped when its rerun failed;
- the step-2 rerun's claims match the JSON, whose hash (61e367da1247c9c6) matches the current code, with
  all 90 jobs recomputed fresh (so the calcium set did not rely on carried-over results).

**Overreach:** "cannot be recovered" (step-2 section) holds for one synthetic generator, one Poisson
recording model and 50-unit draws, not in general. *(Corrected: read the spike result in that scope.)* The
exploratory checks with 200-unit draws and 600-timescale windows (`data/cache/spikeR.py`, one seed) also
failed to rescue the spike profiles and are reported here.

**Before worm measurement:**
1. The two 800-frame ranges of each baseline worm were treated as segment boundaries, so every worm falls
   short of one 150-timescale window. The timestamps show no gap at frame 800. *(The step-1 sentence "the
   13 baseline worms can" was therefore wrong.)*
2. There are 14 baseline and 16 heat worms, not 13 and 17. The brain script would also measure every
   preparation.
3. Recording length is not matched: AI recordings are 2,400 to 4,000 timescales long against 193 to 277 for
   worms. Slow memory and detrending depend on length (A1-slow: 0.32 whole, 0.19 on worm-length crops). Step 2
   at R2 also used about 1,000-timescale synthetic recordings without detrending.
4. AI values are means over many recordings while each worm is one recording, which favours AIs in an
   envelope rule.
5. Amendment 12 has no code:
   - h1 to h6 need a powered group;
   - a nan in one AI drops a measure for everyone;
   - C3 with unit halves misses temporal sampling error;
   - the envelope rule is noisy (simulated median 1.52 BVU, 90% 1.33 to 1.80) and must be reported with its
     uncertainty and as a percentile.
6. The worm noise target (0.013) is effectively unconstrained by a 0.05 tolerance, and the budget barely
   moves it. The paper keeps the activity channel unfiltered, so "denoised" was not supported. A noise
   sensitivity is needed, and AIs with native timescales below 1.5 steps must be flagged.
7. The committed `map_ais.py` crashed (GROUPS lookup). No code hash is stored in the AI outputs.

**Minor:**
- the step-2 text cited the first run's hash; the match count was hard-coded (540 and 450, all reached);
- the 6e7/N length cap was not memory-only (it touched only 3,000-unit jobs);
- R10d drift is -0.37;
- step 1's hash is 4ff3d00427a81b2c;
- detrending is not applied inside matching;
- candidate (b)'s three instances share one OU realisation;
- A10's instances share a base network;
- A8 and A9 are silently missing.

*Status: all accepted. Amendment 13 follows.*

## Amendment 13 (13 Nov 2026, answering review 14, before any worm measurement)

- **A baseline worm is one continuous stretch** (its two 800-frame ranges have no time gap), detrended as a
  whole: 1,600 frames, 151 to 244 timescales (median 197; *corrected after review 14's follow-up, which
  read the recomputed step 1*). Step 1 for R2 was recomputed. The worm map's
  instrument is the median over the **14** baseline worms: decay ratio 0.079, 8.1 frames per timescale,
  noise share 0.014. Only baseline worms are measured (`map_brains.py` now measures R2 baseline only).
- **Length is matched** (items 3 and 4). Every AI is recorded through the worm instrument, and each
  recording is cut into 1,600-frame crops that never cross a segment boundary (`pipeline.crops`; at most 4
  per recording). Each crop is detrended and measured like a worm (40 draws). **Each crop is an AI
  individual**, compared with single worms, never averaged first. Detrending is now also applied inside
  calcium matching.
- **Step 2 for the worm map** (`scripts/map_step2_worm.py`) reruns C1 and C4 at the baseline worms'
  numbers, on 1,600-frame detrended crops. The worm map uses only what passes there.
- **The worm map's rules** (`scripts/map_worm.py`, written before any measure):
  - BVU from 14 worms (13 df).
  - An AI with a nan in a calibrated measurement is reported unmapped; the measurement is not dropped.
  - C3: pooled worm SE below 0.5 BVU. Unit halves of 71 units share the time window, so this gate is
    lenient about temporal sampling error; the between-worm BVU includes that error.
  - Budget: the largest AI change at most 1 BVU.
  - At least 3 measurements.
  - Envelope: the maximum leave-one-out distance of a worm to the other 13, with a bootstrap interval over
    worms.
  - An AI is "worm-like" if its median crop distance to the worm centroid is at most the envelope. Its
    percentile among the worms' leave-one-out distances and a hierarchical bootstrap interval are reported.
  - Pairs use H3(b)'s 30% rule and H4 to H6's interval rules on the bootstrap of median crop distances.
    This is descriptive.
- **Sensitivities** (item 6): every AI is also recorded at noise shares 0.05 and 0.10, and with linear
  interpolation instead of the hold. AIs whose native timescale is below 1.5 steps (below C4's calibrated
  range) are flagged.
- **Provenance and instances** (items 7 and 10): `map_ais.py` is fixed, and every AI output stores a code
  hash. Candidate (b)'s instances get their own OU realisation. A10's instances remain individuals of one
  base network, as registered for the lab ladder.
- **A8 (vision) and A9 (RL agent) are not run:** no natural-video sample is available in this workspace,
  and the RL agent needs an environment and training this machine cannot give in time. They are listed as
  missing.
- Corrections:
  - the step-2 rerun's hash is 61e367da1247c9c6;
  - the match counts are 540 (first run) and 450 (rerun), all reached;
  - the 6e7/N cap was not memory-only (3,000-unit jobs only);
  - R10d drift is -0.37;
  - step 1's hash is 4ff3d00427a81b2c.

**Review 14 follow-up (13 Nov 2026):** the same reviewer checked amendment 13. Its verdict: *the 14 baseline
worms may be measured* once the following are registered and committed. They are, now, before any worm
measurement:
- step 1 for R2 (hash 0f38591d9991dcf3) and step 2 for worms are committed;
- `map_step2_worm.json` was produced at hash 7a79e8304069d4ab. One line of `recording.py` changed afterwards:
  matching now stops when a timescale is undefined. That can only affect unreached matches, and all of them
  were reached, so the result stands without a rerun;
- C1 for worms averages up to 4 crops per synthetic system, while each worm is a single crop. This is
  accepted and stated, since it makes C1 more lenient; slow memory passes at 0.94, close to the bar;
- **nan rules:** a worm with a nan in a calibrated measurement is left out of the worm map (reported); an
  AI crop with a nan is dropped from its AI (reported); an AI keeping fewer than half its crops is
  unmapped; an AI whose recording is shorter than one worm recording is unmapped as too slow;
- the envelope's bootstrap never puts copies of a worm into its own leave-one-out centroid;
- AI results made before amendment 13 (no code hash, or another crop length) are rejected, and the two such
  files (A1, A1-slow) were deleted and are recomputed;
- each variant reports the noise share it actually reached.

**Worm measurement notes (13 Nov 2026):**
- The 14 baseline worms were measured (`docs/figures/map_brains.json`).
- Their split-half SEs came out nan. A unit half's own timescale can exceed 1/150 of the 1,600 frames, so
  that half had no full window. The fix is mechanical and changes no measured value: **C3's halves now use
  the whole recording's timescale** (`measure_matched(..., tau_fixed=...)`), so their windows are the
  recording's own. The worms' values were recomputed and are identical; only the SEs were filled in.
- AI instances are now each matched to the instrument on their own (A1's seed-1 network runs at half the
  speed of seed 0, and with one set of knobs its crops were shorter than a window).
- Cached AI results are reused only if their code hash equals the current code's.
- The AI job that was running when `measures.py` gained the `tau_fixed` argument (default off) stamps the
  new hash; its computations do not touch that argument.
- *(13 Nov, AI recordings)* For memory, a recording of a fast AI is made from only the native stretch its
  crops need (4 crops plus 20%). Recording r of an instance uses the r-th such stretch, so recordings of one
  instance differ in activity as well as noise. Slow A2 (timescale about 930 steps) is kept every 10th step.
  Matching, the budget and the crop rules are unchanged.

## The registered worm map cannot be drawn (14 Nov 2026), and amendment 14 (exploratory, post hoc)

**Registered result.** The C3 gate depends on the worms alone and is now final. The pooled split-half SE of
each worm measurement, over the between-worm SD (BVU, 14 worms):

| measurement | BVU | SE / BVU | C3 (< 0.5) |
|---|---|---|---|
| shared fraction | 0.031 | 1.01 | fails |
| slow memory | 0.057 | 0.31 | passes |
| timescale spread | 0.094 | 0.47 | passes |
| coupling spread | 0.058 | 0.70 | fails |
| sparsity | 0.43 | 0.56 | fails |

Two measurements remain, against the registered minimum of three, so **the registered worm map is not
drawn**, whatever the AIs show. With 16-minute recordings (about 200 timescales), a worm's own measurement
error is as large as the differences between worms on three of the five calibrated measurements: the
ruler is no longer than its error bars.

Separately, the mismatch budget came out undefined for most AIs. Sweeping the frame by 1.5x pushes a
1,600-frame piece below one 150-timescale window. This is a flaw in the sweep (it is much wider than the
10% frame tolerance of matching) and is not used to decide anything.

**Amendment 14, exploratory and labelled post hoc everywhere it is shown.** It was written after the C3
outcome above, and after some AI values had appeared in run logs (for example A1's shared fraction about
0.56 against the worms' 0.22 to 0.34). It is a like-for-like comparison: every AI piece and every worm
carries the same instrument, the same length and the same noise. So the question "is this network inside
the cloud of worms *as recorded*?" is fair even where C3 fails. What changes from the registered rules:
- all five calibrated measurements are used, and C3 is reported, not applied;
- the budget is reported, not applied. Where the 1.5x frame sweep leaves pieces shorter than a window, it is
  shown as undefined;
- everything else is as registered in amendment 13: envelope, crops, bootstrap, nan rules, pairs, variants.

No claim of a test is made from it.

## Amendment 15 (14 Nov 2026): back to the original question, by replication across species (registered before any mouse number or measure)

The user asked to keep pushing for the original question: what differentiates real from artificial neural
networks in general. The data, not the analysis, has been the limit: a ruler needs recordings long and rich
enough that individuals differ by more than their own recording noise. This amendment changes the design
from one pooled, powered group to **replication across species**, and adds the one public dataset in reach
that has long, many-neuron recordings in several individuals.

**Design.**
- Each species is analysed on its own: its real individuals, every AI recorded through *that species'*
  instrument and cut to *that species'* recording length, the ruler from its own individuals, and the
  gates (C1 and C4 at its numbers; C3; budget).
- **A candidate answer** to the question is a measurement that, in every species where it passes the
  gates, puts every standard AI family outside the real individuals' envelope *on the same side* (all
  AIs above, or all below, the individuals' range), while the individuals of that species fall inside.
- Two species agreeing is the minimum for the word "general"; with one, the result is reported as
  single-species.
- Augmented AIs (slow drives, OU latent, the lab network) are reported against the same envelope.
- The worm data (amendment 13) is species 1. Its registered map failed C3 on three measurements; under
  this design the worm contributes only on the measurements that pass C3 (slow memory and timescale
  spread).

**Species 2: mouse visual cortex**, Stringer et al. 2019 (figshare 6163622), spontaneous activity (gray or
black screen):
- 7 mice, about 10,000 neurons each, 1 to 2 hours; individual = mouse (for MP030, its first recording);
- the files hold `Fsp`, suite2p's OASIS deconvolution of GCaMP6s fluorescence (10 to 12 planes at 30 Hz,
  so 2.5 to 3 Hz per plane).

**The deconvolved instrument (new recording model).**
1. An AI is recorded through the calcium model (softplus, then a GCaMP6s indicator with 1/e decay 1.25 s,
   suite2p's recommended value for GCaMP6s, at the mouse's frame rate, plus white noise).
2. A rolling maximin baseline is subtracted (60 s window, as in suite2p).
3. Non-negative AR(1) deconvolution follows: OASIS (Friedrich, Zhou and Paninski 2017), with the same
   1.25 s decay and no sparsity penalty, as in suite2p. It is implemented here from the paper.

The matched targets, measured on each mouse's `Fsp` with `instrument_numbers` and applied identically to the
AIs' deconvolved output:
- samples per timescale (the frame knob);
- the median fraction of exactly-zero samples per unit, which sets how sparse the deconvolved output is
  (the noise knob);
- the white-noise share (reported).

Sensitivity: an indicator decay of 1.5 s.

**Order (as before):**
1. step 1 for the mice (instrument numbers only);
2. step 2 (calibration of every measurement through the deconvolved instrument at the mouse numbers and
   mouse recording length);
3. AIs recorded through the mouse instrument;
4. an independent review;
5. then the mice are measured and the cross-species rule is applied.

The spike datasets stay closed (step 2).

## Mouse step 1 results and amendment 16 (14 Nov 2026, before any mouse measure and before step 2 for the mouse)

**Step 1 (instrument numbers only), 7 mice**, first 20 minutes of each recording, a 500-neuron subset:

| number | median | range |
|---|---|---|
| samples per recorded timescale | 0.71 | 0.64 to 0.90 |
| white share (noise) | 0.78 | 0.65 to 0.95 |
| fraction of exactly-zero samples | 0.63 | 0.62 to 0.67 |
| frame rate | 2.5 Hz (one mouse 3 Hz) | |

**What step 1 showed about the instrument.** A recorded timescale below one frame means the deconvolved
mouse data is nearly white from one 400 ms frame to the next. The population autocorrelation of one mouse
(MP030, computed for this check only) is 0.11 at lag 1, 0.00 at lag 2, slightly negative at lags 3 to 6,
and a slow positive tail of about 0.008 at lags 10 to 30. Passing white input through the deconvolved
instrument gives the same picture (recorded timescale 0.77 frames, white share 0.76 to 0.81). So at this
frame rate the recorded timescale is pinned near a floor of about 0.75 frames and **cannot set the frame**,
which amendment 15 asked it to do.

**Amendment 16.**
1. *Deconvolution kernel.* The data authors deconvolved with a fixed indicator decay of 2 s (Stringer et
   al. 2019, Methods: OASIS, 60 s running baseline, neuropil factor 0.7). Amendment 15 used 1.25 s, which
   was wrong for this dataset. The instrument now records with the GCaMP6s decay from the same table as
   every other calcium preparation (half-decay 0.5 s, 1/e 0.72 s; 1.8 frames at 2.5 Hz), and deconvolves
   with the authors' 2 s kernel (5 frames). Sensitivity: indicator 1/e 1.25 s (amendment 15's value).
2. *The frame.* It is fixed by physics, not by the floored recorded timescale: one frame spans the frame
   duration (0.4 s) over mouse cortex's own native population timescale, taken from the same lab's
   spontaneous Neuropixels recordings (preparation R4, step 1: median 0.047 s over 3 mice, range 0.036 to
   0.104). That is **8.5 native timescales per frame**; an AI frame spans 8.5 of the AI's own native
   timescales. Sensitivity: 3.85 (R4's slowest mouse).
3. *Matched and reported numbers.* SNR is bisected to the white-share target (within 0.05). Samples per
   recorded timescale and the zero fraction are reported, not matched (no knob sets them once the frame is
   fixed; the zero fraction is set by the network's own activity distribution). Matching uses at least
   1,500 frames.
4. *Recording length.* The mouse "recording" is the first 20 minutes, which is 3,000 frames at 2.5 Hz
   (what step 1 read). AIs are cut into 3,000-frame crops. Sensitivity: whole recordings, mice only.
5. *Step 2 at the mouse numbers.* Same gates as before (C1 rho of at least 0.9; C4 ratio below 0.5),
   with the C4 native-timescale levels 1.5, 3 and 6 steps (memory: one 3,000-frame crop at 8.5 timescales
   per frame needs about 25,000 timescales of native activity). Calibration systems hold at least 2 whole
   crops. Deconvolved data is not detrended (the 60 s baseline already removes slow drift).

A synthetic check while writing this amendment (default system and four variants): matching reaches the
white-share target every time, with samples per recorded timescale 0.95 to 1.38 (mouse 0.71) and zero
fraction 0.79 to 0.81 (mouse 0.63). The mouse is whiter and less often exactly zero than these synthetic
systems; whether AIs also differ there is reported with the AI recordings.

## Step 2 for the mouse (14 Nov 2026): no measurement survives the deconvolved instrument

`docs/figures/map_step2_mouse.json` (amendment 16 profile: 8.5 native timescales per frame, white share
0.78, indicator 1.8 frames, kernel 5 frames, 3,000-frame crops; every match reached its target, 0 of 352
unreached). C1 Spearman (needs at least 0.9): shared fraction 0.69, slow memory -0.98 (inverted), timescale
spread -0.12, drift 0.42; coupling spread and sparsity undefined (most values nan). **No measurement passes,
so by amendment 15 the mouse two-photon arm cannot be mapped**, and the mice are not measured. The
deconvolved recordings are close to white from frame to frame (step 1), so properties that live at the
network's own timescale are averaged away inside each 400 ms frame, and the remaining frame-to-frame
structure is dominated by the noise needed to reach the mouse's white share. The registered sensitivity
(3.85 timescales per frame) is not run: it cannot change the primary verdict.

## Amendment 17 (14 Nov 2026): species 2 becomes mouse Neuropixels with pooled units (registered before any grouped measure of real data)

The mouse two-photon arm failed step 2. The one other species with long, many-unit recordings is the
mouse again, through electrodes: R4 (Stringer et al. 2019, 3 mice, 8 probes each, spontaneous). Single
units failed step 2 there (amendments 11 and 12: sparse counts at a white share of 0.83 hide most
properties). **Exploratory synthetic checks made while drafting this amendment** (no real data read):
summing the counts of 8 randomly chosen units into one "group" before measuring raised the recovery
(one seed, 5 levels, R4's matched numbers): shared fraction, slow memory and timescale spread all rho 1.0,
coupling spread 0.7. With groups of 4 timescale spread fell to 0.8; in the rat planar culture (R10d,
groups of 4) timescale spread failed (-0.1). These checks chose G = 8; they are reported here as such.

**Design (amendment 15's rule unchanged; species 2 replaced):**
1. *Grouped-spike instrument.* Each unit is recorded through the registered spike model, matched to R4's
   single-unit numbers exactly as before (amendment 10). Then units are pooled into groups of **G = 8** by
   a seeded random partition (leftover units dropped) and counts are summed per 20 ms bin. Real R4 units
   (every included unit of all 8 probes, at most 2,400) are pooled the same way. Measures run on groups:
   50-group draws, 1,000-timescale windows (amendment 11), split-half SE over group halves.
2. *Step 2* at R4's numbers with pooling, synthetic systems of 480 units (60 groups); C4 population levels
   480, 960 and 2,400 units. Gates as before.
3. *Recording length.* Every measure is a mean over windows of 1,000 timescales, so its expectation does not
   depend on recording length beyond the window, only its variance does. Mice are measured on their first
   20 minutes (about 25,600 timescales; what step 1 read). **AI individuals are crops of 5,000 recorded
   timescales** (compute), one per recording. Sensitivity: mice measured as the mean of 5,000-timescale
   crops.
4. *AIs need at least 400 units* for 50 groups of 8, so for this arm: random RNN 480 units (A1, A1-slow),
   task RNN 512 (A2, retrained as registered, every 100th step kept), GRU and CfC 512 (A3, A5, retrained),
   language models keep 480 MLP or SSM units, the spiking network keeps 480 of its 1,000 neurons. The lab
   network (A10, 120 units, augmented) is not recorded here. Population size is a C4 knob, so a measure that
   passes is insensitive to it by construction (on synthetic systems).
5. *Power.* Three mice give a ruler with 2 degrees of freedom. The cross-species rule is applied as
   written, and any result from this arm is labelled as resting on three individuals.
6. *Candidate under test.* From the worms (exploratory map, amendment 14), the one measurement where every
   recorded AI sits on one side of the worms is **timescale spread** (AIs lower). It is the measurement this
   arm can confirm or refute in a second species; the others are reported.

## Step 2 under amendment 17 (14 Nov 2026): four measurements survive pooled mouse units

`docs/figures/map_step2_r4g.json` (R4's single-unit numbers, groups of 8, 480-unit synthetic systems; 0 of
336 matches unreached). C1 / largest C4 ratio: **shared fraction 0.98 / 0.03, slow memory 0.94 / 0.26,
timescale spread 0.94 / 0.31, coupling spread 0.96 / 0.14** pass; drift (-0.17) fails; spectrum steepness
and sparsity are undefined on counts. So the pooled mouse arm goes ahead with these four, and the worm's
candidate (timescale spread) can be tested in a second species.

**Code-hash carry-over (mechanical).** Adding the deconvolved and pooled instruments changed
`recording.py`, `pipeline.py`, `zoo.py` and `scripts/map_ais.py`, so the worm AI results (A1, A1-slow, A2,
A3, A6-14m, A6-160m at R2) no longer matched the code hash. A worm-path run with the old and new code
(two synthetic instances, matching, recording, measures and budget) gave bit-identical numbers; the new
branches are inactive for R2 (no pooling key, the calcium dispatch unchanged; `task_rnn` with `every=1` is the
original code path). Their stored hash was updated, with the old hash kept in `hash_carried_from`.

**Why the registered worm map's budget was undefined (found 14 Nov 2026 while preparing the mouse
analysis; no rule changed).** The budget re-records an AI with each knob moved by a factor of 1.5. With
the frame shortened by 1.5, a 1,600-frame worm crop spans about 140 recorded timescales, less than one
150-timescale window, so every measurement is undefined for that recording and the budget is nan for A1,
A2, A3 and Pythia-14M (A1 at R2: 11.4 frames per timescale after the change instead of 8.0). Under the
registered rule (a nan budget fails the gate) this, not C3, is what removed slow memory and timescale
spread from the registered worm map. It is a consequence of worm recordings being barely one window long,
not a code error, and it does not arise for the pooled mouse arm (5,000-timescale crops, 1,000-timescale
windows).

## Amendment 18 (14 Nov 2026): the cross-species rule made exact (before any mouse measure)

`scripts/map_species.py` applies amendment 15's rule. Per species and measurement:
- **Real envelope** = the range (minimum to maximum) of the individuals' values.
- **An AI's value** = the median over its crops (its individuals); its 90% interval is the hierarchical
  bootstrap over instances, then crops.
- **A measurement is usable in a species** if it passes that species' gates: worms, C1 and C4 (step 2 for
  worms) and C3 (amendment 15); mouse (pooled), C1 and C4 (step 2 under amendment 17), C3 (pooled mouse SE
  below 0.5 BVU, BVU = SD over the 3 mice) and the budget (largest AI change at most 1 BVU).
- **Separating side** in a species: "below" if every mapped standard AI's value is below the envelope's
  minimum, "above" if every one is above its maximum, otherwise none. Standard families: A1 random RNN, A2
  task RNN, A3 GRU, A4 spiking network, A5 CfC, A6 Pythia, A7 Mamba. A family with no mapped member in a
  species is listed as missing, and the verdict there is marked incomplete.
- **Candidate answer** = a measurement with the same separating side in every species where it is usable.
  "General (two species)" if usable and separating in both; otherwise single-species.
- Strict version (reported): every standard AI's whole 90% interval beyond the envelope.
- Augmented AIs (slow drives, OU latent, lab network) are reported against the same envelope: whether a
  cheap change moves an AI inside it.

## Review 15 (14 Nov 2026, independent, before any pooled-mouse measure): not ready

A reviewer who had not written the code read amendments 15 to 18 and the code diff since fdcfe95 (no real
data read; only small synthetic checks). Findings, and what was done (all before any pooled-mouse measure;
the AI job that was running was stopped and its results will be redone):

1. *BLOCKING. Language-model crops cannot fit at R4g.* Contexts of 2,048 tokens (1,920 after burn-in) are
   shorter than a 5,000-timescale crop (about 3,000 to 4,500 tokens), and crops never crossed a context
   boundary, so A6 and A7 would all come out unmapped. **Fixed:** at R4g, crops may span context
   boundaries and carry the boundaries inside them to the measures, which keep every 1,000-timescale window
   (about 600 tokens) inside one context. The worm crops are unchanged.
2. *BLOCKING. Timescale spread is confounded with an AI's native speed.* Pre-holding (A4, A5) gives every
   unit the same triangular autocorrelation. AIs whose native timescale is below one step (A3 0.70, A6 0.84
   to 0.92) are held to reach the instrument, and holding compresses their spread: in the reviewer's check,
   a true log-timescale IQR of 0.39 at 0.7 steps reads 0.18, while at 3 or 12 steps it reads correctly.
   Both push AIs toward "lower spread", the candidate's direction, and the worm discovery leaned on A3 and
   Pythia. **Fixed (rule):** for the temporal measurements (timescale spread, slow memory) an AI counts only
   if its native timescale is at least 1.5 steps in every instance and it was not pre-held; the rest are
   reported as outside calibrated speed. This leaves A1 (random RNN) and A2 (task RNN) as the counted
   standard families, so the confirmatory claim is about slow-enough recurrent networks, not about AIs in
   general. A4 (spiking network) has no definable timescale at all in its asynchronous state.
3. *BLOCKING. Recording length is not like for like.* Slow memory is computed over the whole recording, and
   the timescale that sets every window comes from the whole recording, so amendment 17's claim that only
   variance depends on length is false. A synthetic check gave slow memory 0.081 on 5,000 timescales against
   0.107 on 25,600, which is about 40% of the C1 range, in the "AIs lower" direction. The registered
   sensitivity was not implemented either. **Fixed:** each mouse is cut into non-overlapping crops of 5,000
   of its own timescales, and each crop is measured exactly as an AI crop is. The mouse's value is the mean
   over crops; its SE is the RMS crop split-half SE divided by the square root of the number of crops. The
   whole 20 minutes is kept as the sensitivity.
4. *BLOCKING. Discovery data was counted as its own replication, and the worm budget was waived without
   saying so.* **Fixed:**
   - The worms are the discovery set, and every worm verdict is exploratory.
   - The pooled mouse is the only confirmatory test, of one hypothesis fixed now: on timescale spread,
     every counted standard AI lies below the mice.
   - Waiving the worm budget is a stated deviation from amendment 15. Its reason: the budget cannot be
     computed at 1,600-frame crops (see the note under amendment 18).
5. *BLOCKING. Three mice make a bare range envelope too weak.* **Adopted:**
   - (a) An AI counts as below or above only if it lies beyond the envelope edge by more than the larger of
     its own budget and 2 x the pooled real SE.
   - (b) Strict version: the AI's whole 90% interval must lie outside the t(df) 90% prediction interval for
     a new individual.
   - (c) C3 is judged against the lower 90% bound of the ruler.
   - (d) The confirmatory test needs both counted families (A1 and A2) mapped; otherwise its result is
     "incomplete".
6. *A2's two recordings overlapped by about 93%.* **Fixed:** 450,000 trials, and results now carry an overlap
   flag.
7. *A2 was decimated, which aliased the trial structure, and its accuracy went unreported.* **Fixed:** the
   long session now uses means over blocks of 100 steps, and accuracy is reported.
8. *Edge cases in the cross-species script.* **Fixed:** a mapped AI with an undefined value counts as not
   separating; the finite-crop rule is the pipeline's (80%); the worm set comes from `map_worm.worms`;
   error results now carry their crop length.
9. *Every AI recording used the same pooling partition.* **Fixed:** there is now one seeded partition per
   recording.
10. *Step 2 under amendment 17 was not run at the registered crop length.* **Rerun:** synthetic systems are
    now measured in 11,718-bin crops.
11. *Memory and hashing problems in `map_ais_fast.py`.* The hold produced float64 data, and the R2 path was
    untruncated (it would have run out of memory). **Fixed:** data is cast to float32 after the hold, R2 is
    truncated, and the script is now part of the code hash.
12. *A second hand edit of the hash carry-over should be avoided.* **Adopted:** every AI is now recorded
    once, with the same activity used at both instruments (480 or more units; 40,000 tokens per language-model
    instance), and the worm AIs are re-recorded too. The 13 Nov worm AI numbers are superseded. The lab
    network (A10) keeps its own size and is recorded for the worms only.
13. *Note: coupling spread is likely to fail the mouse budget* (A1's budget there was already undefined).
    Reported, not changed.
14. *Note: mouse groups mix probes and areas, while the AIs are one layer.* Registered as a sensitivity
    (pooling within probe), to be run if time allows. It is not part of the confirmatory test.
15. *Note: the worm language-model protocol change* is now covered by item 12.
16. *Note: G = 8 was chosen on synthetic checks.* Listed as a forking path (amendment 17).
17. *Note: unit inclusion and rate-multiplier blocks* are negligible. No change.

## Amendment 19 (14 Nov 2026): the changes above, registered before any pooled-mouse measure

Code: `pipeline.crops_across`, `ai_at_prep(cross_segments=...)` with a per-recording pooling seed and an
overlap flag; `zoo.task_rnn` with block means and accuracy; `scripts/map_ais.py` (shared activity, `CROSS`,
`_a2`, hash includes `map_ais_fast.py`); `scripts/map_ais_fast.py`; `scripts/map_brains.py`
(`measure_r4g`); `scripts/map_species.py` (the rules of items 2, 4, 5 and 8); `scripts/map_step2_r4g.py`
(crop length). **The one confirmatory test:** in the pooled mouse, timescale spread passes its gates (C1
and C4 at crop length; C3 against the ruler's lower 90% bound; budget at most 1 ruler unit), and every
counted standard AI (native timescale at least 1.5 steps, not pre-held; families A1 and A2 required) lies
below the three mice by more than its margin. Possible results are "confirmed", "not confirmed",
"incomplete", or "not testable". Everything else is exploratory.

## Step 2 under amendment 19 (14 Nov 2026): timescale spread fails at crop length, so the confirmatory test is not testable

Rerun at the registered crop length (11,718-bin crops; `docs/figures/map_step2_r4g.json`): C1 / largest
C4 ratio: shared fraction 0.98 / 0.07, slow memory 0.98 / 0.07 and coupling spread 0.98 / 0.11 pass.
**Timescale spread does not pass (0.89, threshold 0.9)**; drift fails (0.64). By amendment 19 the one
confirmatory test (timescale spread, AIs below the mice) is therefore **not testable**. Timescale spread is
still measured and reported, as exploratory. No real mouse data has been read for any measure.

## Amendment 20 (14 Nov 2026, before any pooled-mouse measure): a replacement confirmatory test, non-directional

The worm discovery (amendment 14, exploratory) had a second, non-directional pattern: every AI recorded
was far outside the worms' envelope (3 to 7 ruler units against an envelope of 1.7). That pattern is
registered now as the confirmatory test in the pooled mouse, before any mouse value exists. It answers
whether AIs as recorded are distinguishable from animals, not which property differs. Which measurements
drive the distance stays exploratory. This replacement is itself a forking path: the first confirmatory
measure failed a synthetic gate, and a second test was then chosen. It is reported as such.

- **Measurements:** those usable in the mouse (step 2 under amendment 19, C3 against the ruler's lower 90%
  bound, budget at most 1 ruler unit); at least 2, otherwise "not testable". For an AI outside calibrated
  speed (amendment 19, item 2) the temporal measurements are left out of its distance. If fewer than 2
  remain, that AI is not counted.
- **Distance** of a crop: RMS over the measurements of (value - mouse centroid) / ruler SD, capped at 10.
  An AI's distance is the median over its crops, with a hierarchical bootstrap 90% interval.
- **Envelope:** the largest distance of a mouse to the centroid of the other two, computed on the same
  measurements the AI uses.
- **Confirmed** if every counted standard AI's lower 90% bound exceeds the envelope and at least 5 of the 7
  standard families are counted. **Not confirmed** if any counted standard AI's median is at or inside the
  envelope. Otherwise "unclear"; with fewer than 5 families, "incomplete".

## Review 15 follow-up and amendment 21 (14 Nov 2026, before any pooled-mouse measure)

The reviewer checked the fixes (diff 618f9ab..dc8d5ec). Items 1, 2 and 4 to 11 are fixed in code. Three
problems were left, all biasing toward "confirmed"; they are fixed now:
- *The mouse SE was too small (item 3).* Every crop of a mouse uses the same groups, so dividing the RMS crop
  split-half SE by the square root of the number of crops understated it by up to 2.4 times. **Fixed:** no
  division.
- *The leave-one-out envelope of 3 mice carries almost no information.* It is bounded to about 1.2 to 1.7
  by algebra, and a genuine fourth mouse falls outside it 30 to 50% of the time. **Fixed:** an AI must be
  farther than the **95% quantile of a new mouse's distance** under the 3-individual normal model, simulated
  for its number of measurements: 4.9 for 1 measurement, 5.2 for 2, 5.4 for 3. "Confirmed" needs every
  counted AI's lower 90% bound above it. The leave-one-out envelope is reported only.
- *Noise asymmetry.* An RMS distance on single noisy crops is biased upward, and mice are means over 2 to 6
  crops. **Fixed:** an AI's distance is computed on its mean over all its crops (6 or more), so the AI is no
  noisier than a mouse, which makes the bias conservative. The interval is a hierarchical bootstrap of that
  mean.

Also changed:
- the budget gate now uses only the AIs that are counted for that measurement (item 9);
- the mouse crop length is 5,000 of the mouse's own single-unit step-1 timescales, as for the AIs (Krebs,
  Robbins and Waksman: 11,718, 25,980 and 8,975 bins);
- a mouse value needs 80% of its crops finite.
- One relaxation, stated because it raises the chance of a complete test: **an AI counts with at least one
  usable measurement** within calibrated speed (it was two). Without it, the families outside calibrated
  speed would keep only shared fraction and be dropped, leaving 2 of the 5 required families, and the test
  would be "incomplete" by construction.
- Expected outcome stated in advance: usable mouse measurements are likely shared fraction and slow memory
  (coupling spread may fail its budget). Families A3 to A7 would then be judged on shared fraction alone,
  and A1 and A2 on both.

One edge case is left unfixed on purpose. The overlap flag misses the case where an activity is exactly
two stretches long. Fixing it would change the code hash of the AI job now running, and the case does not
arise with the planned lengths.

## Amendment 22 (14 Nov 2026): the 512-unit task RNN did not learn at the old learning rate

With 512 units and the registered settings (orthogonal init, Adam lr 1e-3, 1,500 steps), A2's first
instance stayed at chance (accuracy 0.50), so it was not a task-trained network. A check with lr 3e-4 or
1e-4 reached 0.80 (the ideal observer is 0.79). A2 at 512 units now trains with lr 3e-4. A recording is
refused if accuracy is below 0.7. The 128-unit default is unchanged. The AI job was stopped and restarted;
A1 is recorded again under the new code hash, and its numbers are unchanged in method.
*Addendum (same day):* the accuracy guard first read accuracy from the continuous session (state carried
across trials), which differs from how the task is trained and from the original accuracy (independent
trials, fresh state). It refused seed 1 (0.65 in the continuous session); on independent trials seed 1
reaches 0.79. Accuracy is now computed on independent trials, as originally. The job was restarted again.
*Second addendum:* A2's third instance ran out of memory (6.2 GB) when generating 6,000-trial chunks of
the long session in one call; chunks are now 1,000 trials (60,000 steps, a multiple of the 100-step
blocks). A1 and A2 are re-recorded at the end of the job under the new code hash; A3 and later AIs do not
touch this code path.

## Execution log, 14 Nov 2026 (after amendment 22): everything that happened while recording, in order

Nothing here changed a registered rule unless it says so. Each item names the file that holds it.

1. **Mice measured** (`scripts/map_brains.py R4g`, `docs/figures/map_brains.json`), after review 15's
   follow-up was answered. The first attempt stopped after Krebs: it was killed for memory while A2 was
   generating at the same time. The two remaining mice were measured alone. Per mouse (pooled groups of 8;
   crops of 5,000 of the mouse's own timescales: Krebs 5, Robbins 2, Waksman 6 crops):

   | mouse | shared fraction | slow memory | timescale spread | coupling spread |
   |---|---|---|---|---|
   | Krebs | 0.072 | 0.139 | 0.508 | undefined (fewer than 80% of crops finite) |
   | Robbins | 0.068 | 0.283 | 0.797 | 0.379 |
   | Waksman | 0.022 | 0.146 | 0.518 | 0.332 |

2. **The registered nan rule dropped Krebs.** `map_species.reals` (committed in cb30186, before any mouse
   value existed) leaves out an individual with an undefined value in any calibrated measurement, as for the
   worms. This leaves 2 mice in the registered analysis. Seeing this, I added **amendment 23 (post hoc,
   written after the mouse values were known):** a sensitivity that keeps all three mice and drops the
   measurement instead (coupling spread). It is reported next to the registered result and never replaces
   it. Both give the same verdicts (below).
3. **The A2 accuracy guard** first refused seed 1 because it measured accuracy in the continuous session.
   It was fixed to use independent trials, as originally (amendment 22, addendum).
4. **A2 ran out of memory** when generating 6,000-trial chunks. Chunks are now 1,000 trials (amendment 22,
   second addendum).
5. **The disk filled up** (1.9 GB free): Pythia-410M's three seeds (5.4 GB) were kept for the OU variant
   while Pythia-1B was about to download. The remaining AIs were reordered so that the OU variant ran
   first, after which the 410M weights are freed by the script's own cache rule (`data/cache/run_ais2.sh`).
   Nothing else was deleted. Old Pythia-14M/70M weights from earlier parts of the project (about 1.4 GB)
   were left alone.
6. **Pythia-1B ran out of memory twice.** The first time, the recording buffer kept all 8,192 MLP units of
   every segment. The second time, loading in float32 needed two copies of the weights. `scripts/map_ais_big.py`
   keeps only the sampled units in the hook (the same seeded units `ai.record` chooses) and loads in float16,
   then converts to float32 (the checkpoint is float16, so the weights are identical). Memory only: the
   activity is the same.
7. **The spiking network (A4) ran out of memory** at the 25,000-step truncation with the x16 hold.
   `scripts/map_ais_fast_lowmem.py` truncates to 8,000 native steps for A4 and 12,000 for A5 (its 7 paired
   recordings then overlap; the result carries the overlap flag). Memory only.
8. **Overlap flags:** A1 at R4g (200,000 steps), A1-slow at R4g, A5 at R4g and A10 at R2 have overlapping
   recording stretches. Their recordings share activity, so their between-recording spread is understated.
   No verdict depends on it.
9. **The task RNN (A2) is fast at 512 units**, which was found only after recording. With the 100-step
   block means of amendment 19 (sized for the 128-unit network, whose timescale was about 1,500 steps), its
   native timescale is 0.6 to 2 samples, so it is outside calibrated speed and not counted on temporal
   measurements. Two attempts to bring it within speed failed:
   - 10-step blocks: native timescale 0.7, and matching failed;
   - every step (4,000 trials): native timescales 1.2, undefined and 2.5, and the mouse recording failed on
     the undefined instance.

   Its worm values from the every-step attempt are kept in `data/cache/A2_R2_everystep.pkl` (local):
   shared fraction 0.44, slow memory 0.00, timescale spread 0.24, coupling spread 0.71. The registered
   100-step-block recording was then regenerated for both instruments (`AIS._record`, the same code and
   seeds), and it is the one analysed. Its units mostly follow the white evidence input, so its population
   timescale is short at any resolution.
10. **Code-hash discipline.** Each fix to a hashed file marked earlier results stale, and they were
    re-recorded rather than carried over: A1 three times, A2 four times. The wrappers in items 6, 7 and 9 are
    separate scripts. They change no hashed file, and each says in its docstring what it changes.
11. **Worm AI numbers superseded.** Every worm AI was re-recorded with the shared activity of amendment 19
    (480 or more units, 40,000 tokens per language-model instance). The exploratory worm map
    (`docs/figures/map_worm.json`) was rerun on them, and the 13 Nov numbers are superseded.

## Results (14 Nov 2026)

`docs/figures/map_species.json`, `docs/figures/map_worm.json`, figure `docs/figures/map/species.png`.

**Registered (confirmatory) results.**
- *Timescale spread in the pooled mouse (amendment 19): not testable.* It failed the synthetic C1 gate at
  crop length (0.89 against 0.9) before any mouse was measured.
- *Distance test (amendments 20 and 21): not testable.* Only one mouse measurement is usable (slow memory).
  Shared fraction fails the budget: AIs move by 7.6 mouse ruler units when a knob changes by a factor of
  1.5. Coupling spread fails C3 and its budget is undefined. Timescale spread is not calibrated. The keep-all-mice
  sensitivity (amendment 23) gives the same answer.
- *Registered worm map: not drawn* (14 Nov, unchanged). The budget is undefined at worm crop length.

So **no confirmatory claim** about what differentiates real from artificial networks comes out of this
study. Every pattern below is exploratory.

**Exploratory patterns** (the worms are discovery data; the mouse rows have 2 registered or 3 sensitivity
mice; "below" uses amendment 21's margin; "not counted" marks a temporal measurement of an AI outside
calibrated speed, or an augmented AI):

**Worms (14, discovery)**

| | Shared fraction | Slow memory | Timescale spread | Coupling spread |
|---|---|---|---|---|
| real range | 0.225 to 0.341 | -0.090 to 0.130 | 0.267 to 0.652 | 0.246 to 0.431 |
| gates | fails (C3 1.32, budget nan) | usable (C3 0.40, budget nan) | fails (C3 0.62, budget nan) | fails (C3 0.92, budget nan) |
| Random RNN | 0.394 (inside) | 0.079 (inside) | 0.224 (inside) | 0.388 (inside) |
| Random RNN + slow drives (aug.) | 0.277 (inside, not counted) | 0.136 (inside, not counted) | 0.349 (inside, not counted) | 0.332 (inside, not counted) |
| Task-trained RNN | 0.928 (above) | 0.011 (inside, not counted) | 0.054 (below, not counted) | 0.667 (above) |
| GRU, characters | 0.062 (below) | -0.013 (inside, not counted) | 0.165 (below, not counted) | 0.208 (inside) |
| Spiking network | -0.003 (below) | -0.067 (inside, not counted) | 0.029 (below, not counted) | 0.186 (inside) |
| CfC, characters | 0.154 (below) | -0.023 (inside, not counted) | 0.077 (below, not counted) | 0.269 (inside) |
| Pythia 14M | 0.109 (below) | -0.024 (inside, not counted) | 0.101 (below, not counted) | 0.295 (inside) |
| Pythia 160M | 0.018 (below) | -0.021 (inside, not counted) | 0.112 (below, not counted) | 0.175 (inside) |
| Pythia 410M | 0.014 (below) | -0.021 (inside, not counted) | 0.105 (below, not counted) | 0.169 (inside) |
| Pythia 410M + slow latent (aug.) | 0.015 (below, not counted) | 0.013 (inside, not counted) | 0.125 (below, not counted) | 0.175 (inside, not counted) |
| Pythia 1B | 0.009 (below) | -0.018 (inside, not counted) | 0.123 (below, not counted) | 0.159 (below) |
| Mamba 130M | 0.015 (below) | -0.016 (inside, not counted) | 0.133 (below, not counted) | 0.177 (inside) |
| Mamba 370M | 0.008 (below) | -0.011 (inside, not counted) | 0.155 (below, not counted) | 0.172 (inside) |
| Lab network (aug., fitted to worms) | 0.572 (above, not counted) | -0.046 (inside, not counted) | 0.309 (inside, not counted) | 0.388 (inside, not counted) |

**Mice, pooled units (registered set: 2 mice, Krebs dropped by the nan rule)**

| | Shared fraction | Slow memory | Timescale spread | Coupling spread |
|---|---|---|---|---|
| real range | 0.022 to 0.068 | 0.146 to 0.283 | 0.518 to 0.797 | 0.332 to 0.379 |
| gates | fails (C3 0.25, budget 7.55) | usable (C3 0.34, budget 0.39) | not calibrated (C3 0.37, budget 0.66) | fails (C3 1.62, budget nan) |
| Random RNN | 0.055 (inside) | 0.061 (below) | 0.397 (inside) | 0.173 (below) |
| Random RNN + slow drives (aug.) | 0.032 (inside, not counted) | 0.261 (inside, not counted) | 0.487 (inside, not counted) | 0.135 (below, not counted) |
| Task-trained RNN | 0.309 (inside) | 0.013 (below, not counted) | 0.310 (inside, not counted) | 0.262 (below) |
| GRU, characters | 0.010 (below) | 0.028 (below, not counted) | 0.186 (below, not counted) | 0.141 (below) |
| Spiking network | 0.005 (below) | -0.055 (below, not counted) | 0.208 (below, not counted) | 0.098 (below) |
| CfC, characters | 0.013 (below) | -0.001 (below, not counted) | 0.176 (below, not counted) | 0.155 (below) |
| Pythia 14M | 0.006 (below) | 0.001 (below, not counted) | 0.179 (below, not counted) | 0.168 (below) |
| Pythia 160M | 0.000 (below) | 0.003 (below, not counted) | 0.170 (below, not counted) | 0.080 (below) |
| Pythia 410M | 0.000 (below) | 0.000 (below, not counted) | 0.162 (inside, not counted) | 0.074 (below) |
| Pythia 410M + slow latent (aug.) | 0.001 (below, not counted) | 0.056 (below, not counted) | 0.194 (below, not counted) | 0.101 (below, not counted) |
| Pythia 1B | -0.000 (below) | 0.002 (below, not counted) | 0.180 (inside, not counted) | 0.075 (below) |
| Mamba 130M | -0.000 (below) | -0.000 (below, not counted) | 0.184 (inside, not counted) | 0.089 (below) |
| Mamba 370M | -0.000 (below) | -0.001 (below, not counted) | 0.157 (below, not counted) | 0.084 (below) |

**Mice, pooled units, all 3 (post-hoc sensitivity, amendment 23)**

| | Shared fraction | Slow memory | Timescale spread | Coupling spread |
|---|---|---|---|---|
| real range | 0.022 to 0.072 | 0.139 to 0.283 | 0.508 to 0.797 |  |
| gates | fails (C3 0.36, budget 8.87) | usable (C3 0.31, budget 0.47) | not calibrated (C3 0.35, budget 0.80) |  |
| Random RNN | 0.055 (inside) | 0.061 (below) | 0.397 (inside) |  |
| Random RNN + slow drives (aug.) | 0.032 (inside, not counted) | 0.261 (inside, not counted) | 0.487 (inside, not counted) |  |
| Task-trained RNN | 0.309 (inside) | 0.013 (below, not counted) | 0.310 (inside, not counted) |  |
| GRU, characters | 0.010 (below) | 0.028 (below, not counted) | 0.186 (below, not counted) |  |
| Spiking network | 0.005 (below) | -0.055 (below, not counted) | 0.208 (below, not counted) |  |
| CfC, characters | 0.013 (inside) | -0.001 (below, not counted) | 0.176 (below, not counted) |  |
| Pythia 14M | 0.006 (below) | 0.001 (below, not counted) | 0.179 (below, not counted) |  |
| Pythia 160M | 0.000 (below) | 0.003 (below, not counted) | 0.170 (below, not counted) |  |
| Pythia 410M | 0.000 (below) | 0.000 (below, not counted) | 0.162 (inside, not counted) |  |
| Pythia 410M + slow latent (aug.) | 0.001 (below, not counted) | 0.056 (below, not counted) | 0.194 (below, not counted) |  |
| Pythia 1B | -0.000 (below) | 0.002 (below, not counted) | 0.180 (inside, not counted) |  |
| Mamba 130M | -0.000 (below) | -0.000 (below, not counted) | 0.184 (inside, not counted) |  |
| Mamba 370M | -0.000 (below) | -0.001 (below, not counted) | 0.157 (below, not counted) |  |

**Worm map, exploratory (amendment 14), all AIs**: envelope 1.67 [1.47, 1.86]

| AI | median crop distance (ruler units) | 90% interval |
|---|---|---|
| Random RNN + slow drives (aug.) | 1.97 | 1.72 to 2.13 |
| CfC, characters | 2.87 | 2.61 to 3.00 |
| Random RNN | 3.13 | 2.99 to 3.22 |
| GRU, characters | 3.99 | 3.92 to 4.03 |
| Lab network (aug., fitted to worms) | 4.66 | 4.61 to 4.81 |
| Pythia 14M | 5.25 | 5.15 to 5.28 |
| Pythia 410M + slow latent (aug.) | 6.02 | 5.95 to 6.10 |
| Mamba 130M | 6.04 | 6.00 to 6.06 |
| Pythia 160M | 6.05 | 5.97 to 6.06 |
| Mamba 370M | 6.08 | 6.07 to 6.09 |
| Pythia 410M | 6.08 | 6.06 to 6.14 |
| Task-trained RNN | 6.10 | 5.61 to 7.06 |
| Pythia 1B | 6.12 | 6.11 to 6.13 |
| Spiking network | 6.33 | 6.30 to 6.35 |

| pair | first | second | 90% interval of difference | rule |
|---|---|---|---|---|
| H3b slow drives (A1-slow vs A1) | 1.97 | 3.13 | -1.40 to -0.91 | holds |
| H3b OU latent (Pythia-410M + OU vs Pythia-410M) | 6.02 | 6.08 | -0.14 to 0.02 | does not hold |
| H4 Pythia-1B vs Pythia-14M | 6.12 | 5.25 | 0.84 to 0.96 | holds |
| H5 Mamba-370M vs Pythia-410M (slow set) | 2.06 | 2.46 | -0.62 to -0.26 | holds |
| H6 CfC vs GRU | 2.87 | 3.99 | -1.37 to -0.96 | does not hold |

Registered worm map: fewer than 3 usable measurements: no map {'shared_fraction': 'C3', 'slow_fraction': 'budget', 'timescale_spread': 'budget', 'coupling_spread': 'C3', 'sparsity': 'C3'}

**What the exploratory results say, in plain words.**
1. *Every AI recorded is far from every real worm* (exploratory worm map). AI distances run from 1.97 to
   6.33 ruler units against a worm envelope of 1.67 (90% interval 1.47 to 1.86). No AI, of 14, is
   worm-like.
2. *What brings an AI closest is slow internal drive.* A random RNN with slow drives is the closest system
   to the worms (37% closer than the same RNN without them). In the mouse it is also the only AI whose slow
   memory falls inside the mouse range (0.26 against 0.14 to 0.28) and whose timescale spread comes near
   the mice (0.49 against 0.51 to 0.80). Adding a slow latent to a language model does almost nothing (1%
   closer to the worms).
3. *In the mouse, nearly every AI sits numerically below the mice on the temporal and coupling measurements* (not all of them by amendment 21's margin):
   - slow memory: all 13 AIs below except the slow-drive RNN;
   - coupling spread: all 13 below;
   - timescale spread: all 13 below, though this measurement is not calibrated for the mouse.

   Only the random RNN and the slow-drive RNN are slow enough to count on the temporal measurements. The
   rest are reported, not counted, because holding fast networks compresses these measurements (review
   15, item 2).
4. *Scale does not help* (worms, H4 rule): Pythia-1B is farther from the worms than Pythia-14M (6.12 against
   5.25). Mamba is closer than Pythia on the slow measurements (H5 rule holds), and the "liquid" CfC is
   closer than the GRU by more than 1 unit (H6's no-difference rule does not hold).
5. *Language models and the spiking network are extreme in sparsity* (worms: 5.7 to 11.3, against 0.5 to
   2.0 in worms), while the random RNN, GRU and CfC are below the worms (the task RNN is inside).

**What limits all of this.**
- The worm recordings are barely one measurement window long.
- There are only three mice, and one has a missing value.
- Single units and deconvolved two-photon data hide most measurements.
- Fast AIs cannot be compared on temporal measurements without holding them, which distorts those
  measurements.

The most defensible single statement is a hypothesis for a properly powered test, not a finding: *real
neurons carry more slow, heterogeneous structure than the artificial networks tested, and slow external
drive is the cheapest change that moves an artificial network toward them.*

## Amendment 24 (14 Nov 2026): a powered confirmatory test in the Allen Neuropixels mice (registered before any Allen spike is read)

The user asked to run the test that would settle the exploratory pattern. The study's limit has been the
number of individuals (3 Neuropixels mice), not the analysis. The Allen Brain Observatory Visual Coding
Neuropixels release (DANDI 000021, brain_observatory_1.1, 32 sessions; DANDI 000022,
functional_connectivity, 26 sessions) has one session per mouse. Each session has 6 probes, about 1,200 to
2,200 units of Allen's `good` quality, and spontaneous blocks: three of about 5 minutes in
brain_observatory, and a 30-minute block plus shorter ones in functional_connectivity. Before writing this,
only file metadata was read (block times, unit counts, quality labels, dataset layout) for 20 sessions,
with a check of read speed. No spike time has been read. The per-mouse metadata (blocks, good units) is
reported with step 1.

**Design (preparation "R4a"; everything not stated here is as for the pooled mouse arm, amendments 17 to
21):**
1. *Individuals:* one per mouse. A session is excluded (and counted) if it cannot be read or holds fewer
   than one 5,000-timescale crop.
2. *Activity:* 20 ms spike counts of Allen `good` units (at most 2,400, seeded subset), in every
   spontaneous block of at least 60 s after invalid intervals are removed. Blocks are concatenated with
   segment boundaries. Then the registered unit-inclusion rule, then pooling in seeded groups of 8.
3. *Step 1:* single-unit instrument numbers per mouse (500 seeded units), with medians over mice; these
   set the AI matching. *Step 2:* C1 and C4 at those numbers with pooling, at crop length (5,000 recorded
   timescales), on 480-unit synthetic systems, with the same gates.
4. *AIs:* the 13 AIs of the pooled arm (not the worm-fitted lab network), regenerated with the same
   builders, matched to R4a's numbers, and cut into 5,000-timescale crops (crops may span contexts).
5. *Mice:* cut into non-overlapping crops of 5,000 of their own single-unit step-1 timescales. Crops may
   span block boundaries, which are passed to the measures, as for the AIs. A mouse's value is the mean
   over crops (80% finite); its SE is the RMS crop split-half SE.
6. *Missing values:* a mouse with an undefined value is dropped **from that measurement only**
   (amendment 23's rule, here registered before the data). With dozens of mice, the two rules differ by at
   most a few individuals.
7. *Gates and counting:*
   - C3 is judged against the ruler's lower 90% bound;
   - the budget must be at most 1 ruler unit, over the counted AIs;
   - the native-speed rule for temporal measurements (an AI counts only with native timescale at least
     1.5 steps and no pre-hold);
   - amendment 21's margin (beyond the edge of the mouse range by more than the larger of the AI's budget
     and 2 SE).
   - With many mice, the range runs from the most extreme mouse at each end, so "below every mouse" is a
     strict criterion.

**The confirmatory tests** (fixed now, from the worm and 3-mouse exploration; each is decided only if its
measurement is usable at R4a):

| test | measurement | prediction | counted AIs | decided "confirmed" if |
|---|---|---|---|---|
| A | coupling spread | every standard AI below the mice | all 11 standard AIs | every counted AI is below by the margin |
| B | slow memory | every counted standard AI below the mice | native speed at least 1.5 (A1 must be counted) | as A |
| C | timescale spread | as B | as B | as A |
| D | slow memory | slow drives move a random RNN into the real range | random RNN with slow drives vs plain random RNN | the slow-drive RNN is inside the range (not beyond it by the margin) **and** test B is confirmed |
| E | distance over the usable measurements | every counted standard AI farther from the mice than a new mouse would be | as amendment 21 (at least 5 families) | every counted AI's lower 90% bound beyond the 95% quantile of a new mouse's distance (simulated for this number of mice) |

- **"Refuted"** if any counted standard AI is inside the range or beyond the opposite edge (for test D:
  if the slow-drive RNN is beyond either edge).
- **"Unclear"** otherwise.
- **"Not testable"** if the measurement fails a gate, or if a required AI is not counted.
- The strict version (beyond the t 90% prediction interval for a new mouse) is reported for every test.
- Five tests are run, and all five verdicts are reported whatever they are.

**The 3 Stringer mice (R4g) are not pooled with these:** their instrument and recording protocol differ.
They stay exploratory.

## Step 1 for the Allen mice (14 Nov 2026; instrument numbers only, no measure)

`docs/figures/map_step1.json`, preparation R4a.
- **Data:** all 58 sessions were read, one per mouse (58 distinct mice), and none was excluded. Spontaneous
  time per mouse runs from 616 to 2,334 s (median 951 s). Good units per mouse run from 1,079 to 2,400,
  after the cap (median 1,729).
- **Instrument numbers** (medians over mice, 500 seeded units each):
  - samples per timescale: 2.60 (range 1.43 to 23.9);
  - spikes per bin: 0.066;
  - white share: 0.90;
  - rate spread (log SD): 1.22;
  - timescale: 52 ms (29 to 478 ms).

  These are close to the Stringer mice (2.34, 0.069, 0.83, 1.28).
- **Crops:** by amendment 24's rule a mouse needs at least one crop of 5,000 of its own timescales. **Seven
  mice have none** (their timescale is too long for their spontaneous time), so **51 mice** enter the
  measurement. The excluded mice: sub-707296975, sub-732548371, sub-733457986, sub-734865729,
  sub-735109599, sub-738651046 and sub-769360771.
- **Download:** about 40 MB per mouse is kept locally in `data/cache/allen` (third-party data, not
  committed): the spontaneous spikes of the selected good units, read once with parallel range requests.

## Step 2 for the Allen mice (14 Nov 2026): two measurements survive

`docs/figures/map_step2_r4a.json`. The settings are R4a's median single-unit numbers, groups of 8,
480-unit synthetic systems and 5,000-timescale crops; 0 matches unreached. C1 / largest C4 ratio:
- **pass:** shared fraction 0.96 / 0.09; slow memory 0.98 / 0.10;
- **fail:** timescale spread 0.69; coupling spread 0.55; drift 0.69 (the Allen white share is higher than
  the Stringer mice's: 0.90 against 0.83).

So, by amendment 24:
- **tests A (coupling spread) and C (timescale spread) are not testable**;
- tests B and D (slow memory) and E (distance over the usable measurements) remain;
- no Allen mouse has been measured.
