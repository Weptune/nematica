# The map study, start to finish (12 to 14 Nov 2026)

This is the readable account of the "map of brains and AIs" study. The full, dated record is
`docs/MAP.md`: every rule written before the data it governs, 23 amendments, 6 independent reviews and
every gate result. This file summarises it, lists every deviation in one place, and says where each result
and script lives. Where the two disagree, `docs/MAP.md` is the record.

## The question and the approach

**Question.** What differentiates real neural networks from artificial ones, in general, not for one
animal?

**Approach.**
- Record many artificial networks the same way real brains are recorded, through a simulated copy of each
  real instrument (calcium imaging, deconvolved two-photon, spike sorting), matched to that instrument's
  measured numbers.
- Measure every system with the same population measurements:
  - shared fraction: how much activity is shared across units;
  - slow memory: how much variance is slow;
  - timescale spread: how much units differ in how long they remember;
  - coupling spread: how unevenly units follow the shared signal;
  - sparsity;
  - drift;
  - spectrum steepness.
- Judge every difference on a biological ruler: the spread between real individuals of one species.

**Discipline.**
- Every rule was registered before the data it governs. Changes are dated amendments, and each says
  whether it came before or after any data was seen.
- Independent reviewers (agents that had not written the code) checked the plan and the code before every
  data step.
- Third-party data stays local; only summary numbers are committed.

## What happened, in order

| when | step | outcome |
|---|---|---|
| 12 Nov | Registration | 8+ real preparations, 10+ AI families, measurements, ruler, gates C1 (recovers its property), C3 (precise enough), C4 (insensitive to unmatched knobs), hypotheses H1 to H8 |
| 12 Nov | Amendment 1 | matched protocol (50-unit draws, 150-timescale windows) after unit count changed values |
| 12 Nov | Review 10, amendment 2 | shared fraction rebuilt (it was an overfitting score); noise-robust timescale |
| 12 Nov | Review 11, amendment 3 | fast networks "held" so instruments finer than one step can be matched |
| 12 to 13 Nov | Review 12, amendment 4 | shape-robust noise estimator; frozen instrument-number function; 20 unit tests |
| 13 Nov | Review 13, amendment 5 | every recording stretch counts; detrending for calcium |
| 13 Nov | Amendments 6 to 8 | from file metadata only: one worm dataset has no rest; zebrafish rest = "Spontaneous" block; fly not loadable (volumes only) |
| 13 Nov | Amendment 9, step 1 | instrument numbers for 9 preparations (no measure computed) |
| 13 Nov | Amendment 10, step 2 | instrument-transfer and budget gates; calibration at each real instrument: spike preparations keep almost nothing |
| 13 Nov | Amendment 11, 12 | longer spike windows (labelled as weaker rules); still no common spike measurement, so the spike arm closed |
| 13 Nov | Review 14, amendment 13 | worms measured in worm-length crops; AIs cut to the same length |
| 14 Nov | Registered worm map | not drawn: fewer than 3 measurements pass (C3 and an undefined budget) |
| 14 Nov | Amendment 14 (post hoc) | exploratory worm map: every AI outside the worm envelope |
| 14 Nov | Amendment 15 | the question again: replication across species; a candidate answer must hold in every species where it can be measured |
| 14 Nov | Mouse two-photon, amendment 16 | 7 mice, step 1; deconvolution kernel corrected to the authors' 2 s; frame fixed from Neuropixels timescale |
| 14 Nov | Mouse two-photon step 2 | no measurement survives the instrument: arm closed, mice not measured |
| 14 Nov | Amendment 17 | species 2 = mouse Neuropixels with units pooled in groups of 8 (chosen on synthetic checks) |
| 14 Nov | Step 2 (pooled) | 4 measurements pass at whole length |
| 14 Nov | Amendment 18 | exact cross-species rule |
| 14 Nov | Review 15, amendment 19 | 5 blocking problems fixed before any mouse value: language-model crops, native-speed confound, recording length, discovery vs confirmation, 3-mouse envelope |
| 14 Nov | Step 2 at crop length | timescale spread fails (0.89 against 0.9): the confirmatory test is not testable |
| 14 Nov | Amendment 20 | replacement confirmatory test: AIs farther from the mice than any mouse (disclosed as a forking path) |
| 14 Nov | Review 15 follow-up, amendment 21 | mouse SE, new-mouse threshold, noise asymmetry fixed before any mouse value |
| 14 Nov | Amendment 22 | 512-unit task RNN retrained (it stayed at chance) |
| 14 Nov | Mice measured; 14 AIs recorded at both instruments | see results |
| 14 Nov | Amendment 23 (post hoc) | sensitivity keeping all 3 mice after one had a missing value |

## Results

**Confirmatory: none.** Every registered test ended "not testable":
- the worm map: too few measurements pass at worm recording length;
- timescale spread in the mouse: it failed calibration at crop length;
- the distance test in the mouse: only one mouse measurement is usable.

No result below is a confirmed finding.

**Exploratory** (figure: `docs/figures/map/species.png`; tables: the "Results (14 Nov 2026)" section of
`docs/MAP.md`):
1. **No AI is worm-like.** All 14 AIs lie 1.97 to 6.33 ruler units from the worms, against a worm
   envelope of 1.67.
2. **Slow drive is the one change that moves an AI toward real brains.**
   - A random RNN with slow external drives is the closest system to the worms: 37% closer than without
     them.
   - In the mouse, it is the only AI whose slow memory falls inside the mouse range.
   - Adding a slow latent to a language model barely helps (1%).
3. **In the mouse, nearly every AI sits below the mice on slow memory, timescale spread and coupling
   spread.** Fast networks (language models, GRU, CfC, spiking) cannot be counted on the temporal
   measurements, because holding them to reach the instrument compresses those measurements.
4. **Scale does not buy brain-likeness.** Pythia-1B is farther from the worms than Pythia-14M.
5. **Architecture matters somewhat.** Mamba is closer than Pythia on the slow measurements, and the CfC
   "liquid" network is closer than a GRU.

**Hypothesis for a properly powered test** (not a finding): real neurons carry more slow, heterogeneous
structure than the artificial networks tested, and slow external drive is the cheapest change that moves an
artificial network toward them.

## Every deviation and forking path

Things a reader should weigh, all also in `docs/MAP.md`:
1. Amendment 11 relaxed the spike protocol after step 2 failed. It still failed, and it is labelled.
2. Amendment 14: the worm map was made exploratory after the registered map could not be drawn.
3. Amendment 15 moved the design from one pooled group to replication across species, on the user's
   request.
4. Amendment 16 corrected the deconvolution kernel to the data authors' value (amendment 15 had a wrong
   value). The frame was then fixed from another dataset's timescale, because the measured one was floored.
5. Amendment 17 chose groups of 8 on synthetic checks, so that the candidate measure would pass
   calibration.
6. The candidate (timescale spread) was found on the worms. After review 15 the worms are labelled
   discovery data only.
7. Amendment 20 replaced the confirmatory test after the first one failed a synthetic gate (before any
   mouse value).
8. Amendment 21 relaxed one rule: an AI counts with at least one measurement. Without that, the test would
   have been incomplete by construction.
9. Amendment 23 (after the mouse values were known): a keep-all-mice sensitivity, reported next to the
   registered 2-mouse result, never replacing it.
10. The worm budget gate was waived in the cross-species rule (it cannot be computed at worm length). This
    is stated as a deviation.
11. The A2 task RNN at 512 units is fast, which was found only after recording. Two attempts to record it
    within calibrated speed failed, and the registered recording is the one analysed.
12. Memory-only workarounds, each checked or argued to leave the activity unchanged:
    - Pythia-1B: buffer and float16 load;
    - spiking network and CfC: shorter truncation;
    - task RNN: 1,000-trial chunks.
13. One hash carry-over (amendment 17's step, checked bit-identical). After review 15 every AI was
    re-recorded instead of carried over.
14. Several runs were killed for memory and restarted. No partial result was kept; each rerun is complete
    under one code hash.

## Data

| arm | data | individuals | result |
|---|---|---|---|
| worm calcium | Atanas et al. 2023, baseline worms | 14 | measured; exploratory map |
| zebrafish calcium | Chen et al. 2018 | 7 usable of 18 | recordings shorter than one window; not measured |
| mouse two-photon (deconvolved) | Stringer et al. 2019, figshare 6163622 | 7 | step 1 only; arm closed at step 2 |
| mouse Neuropixels, single units | Stringer et al. 2019, figshare 7739750 | 3 | step 1; spike arm closed |
| mouse Neuropixels, pooled units | same | 3 (2 in the registered set) | measured; exploratory |
| rat cultures, organoids, slices, mouse ALM | DANDI 001603, 002020, 000060 | 3 to 14 each | step 1 and step 2 only; spike arm closed |

**AIs** (3 instances each):

*Standard:*
- random RNN;
- task-trained RNN;
- GRU and CfC trained on characters;
- spiking network;
- Pythia 14M, 160M, 410M and 1B;
- Mamba 130M and 370M.

*Augmented:*
- random RNN + slow drives;
- Pythia 410M + slow latent;
- the lab network fitted to worms (worms only).

## Where everything is

| what | file |
|---|---|
| the full record | `docs/MAP.md` |
| measurements, recording models, deconvolution, pooling | `nematica/map/measures.py`, `recording.py`, `deconv.py` |
| AI zoo and language-model recording | `nematica/map/zoo.py`, `ai.py` |
| AI recording at an instrument | `nematica/map/pipeline.py`, `scripts/map_ais.py` (+ `map_ais_fast.py`, `map_ais_big.py`, `map_ais_fast_lowmem.py`, `map_ais_a2fine.py`) |
| step 1 (instrument numbers) | `scripts/map_step1.py` -> `docs/figures/map_step1.json` |
| step 2 (calibration) | `scripts/map_calibrate.py`, `map_step2*.py` -> `docs/figures/map_step2*.json` |
| brain measurements | `scripts/map_brains.py` -> `docs/figures/map_brains.json` |
| worm map | `scripts/map_worm.py` -> `docs/figures/map_worm.json` |
| cross-species rule | `scripts/map_species.py` -> `docs/figures/map_species.json` |
| figures | `scripts/plot_map.py` -> `docs/figures/map/` |
| tests | `tests/test_map.py` (32) |
| raw data and AI results | `data/cache/` (local, not committed) |

**Reproducing** (8 GB machine; run heavy jobs one at a time):
1. `map_step1.py`
2. `map_step2_worm.py` and `map_step2_r4g.py`
3. `map_brains.py R2 R4g`
4. `map_ais.py` for each AI, then the low-memory wrappers for Pythia-1B, A4 and A5
5. `map_worm.py`
6. `map_species.py`
7. `plot_map.py species`

## What would make it confirmatory

- More individuals per species. The Allen Brain Observatory Neuropixels sessions have dozens of mice with
  spontaneous blocks.
- Worm recordings several windows long.
- An instrument that resolves timescales without pooling.
- For fast AIs, a definition of temporal measurements that does not need holding.

The current results say where to look. They do not settle the question.
