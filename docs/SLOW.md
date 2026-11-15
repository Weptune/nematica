# Study 2: is the difference slow internal state? (draft registration, v0)

**Status: DRAFT, not frozen.** Started 15 Nov 2026. Nothing in this file binds until it is frozen. Freezing
means a commit whose message says "SLOW registration frozen", and that commit hash is written here. It
happens only after the feasibility checks and the synthetic calibration below have passed. Until then any
part may change, and every change is logged in `docs/SLOW_LOG.md`. **No real activity is read for any
measurement before freezing.**

The lab notebook for this study is `docs/SLOW_LOG.md`: every run, failure, restart and decision, dated, in
order. The first study (the map, `docs/MAP.md`, summary `docs/MAP_SUMMARY.md`) is closed and is not
amended further.

## 1. The question and the claim under test

The project asks what differentiates real neural networks from artificial ones. Across the worm work and
the map study, every difference that held up traced back to **slow internal state**: state that is not
set by the current input and changes slowly.
- The worm emulator needed slow brain-wide states.
- Watching fails because influence lives in state that rest activity does not show.
- Worms and human cortex drift over a recording, while networks without slow processes do not.
- Compared mouse by mouse, a random RNN has less slow memory than 33 of 35 mice, and a small slow drive
  moves it to the typical mouse.

This study tests that thesis directly, across every standard family of artificial network, with a
measurement that does not depend on any system's own clock.

**Claim under test:**
- real cortex carries more internal state (activity not locked to its input) than standard artificial
  networks;
- that internal state is slower relative to the input;
- a slow internal state is the smallest ingredient that closes the gap;
- scale is not.

## 2. Lessons from the map study, built in from the start

| lesson (map study) | what this study does |
|---|---|
| The instrument moves an AI's values more than animals differ (amendment 25 transfer check: 1.8 SDs) | Every AI is recorded at each animal's own instrument and compared animal by animal |
| Fast networks (language models, GRU, CfC, spiking) cannot be compared on timescales measured in their own steps | The measures are ratios inside one system (internal against stimulus-locked), so no clock conversion is needed |
| Three animals give a meaningless envelope | Dozens of animals; paired tests with an equivalence margin |
| Calibration at the wrong length or instrument failed late | Calibration at each animal's own instrument and recording length, before freezing |
| Chains of amendments created forking paths | One registration, frozen after feasibility and calibration; few amendments, each labelled before or after data |
| Crashes and restarts were logged after the fact | `SLOW_LOG.md` is written as things happen |

## 3. Measurements (clock-free)

The input is a clip repeated R times. Y_r(t) is the activity of a group of units during repeat r. For each
lag k:
- same-repeat autocovariance: C_same(k) = mean over r of cov(Y_r(t), Y_r(t + k));
- cross-repeat autocovariance: C_cross(k) = mean over pairs r != r' of cov(Y_r(t), Y_r'(t + k)).

Activity that follows the input repeats across repeats, so C_cross is the **stimulus-locked**
autocovariance. C_int = C_same - C_cross is the **internal** autocovariance: everything that differs
between repeats of the same input. White measurement noise appears only at lag 0 of C_same, so lag-0
values are extrapolated from lags 1 to 4, as in the map study's `_signal_var`.

- **M1, internal share** = C_int(0) / C_same(0), with lag-0 values noise-corrected. It is the fraction of
  real (non-noise) activity not set by the input.
- **M2, internal slowness** = half-life of the normalised C_int over half-life of the normalised C_cross.
  It asks how much slower the internal state moves than the input-driven activity. Both half-lives are in
  the same system's samples, so the ratio has no clock.
- *Secondary:* **M3, carry-over** = the correlation of a unit group's internal component between the end
  of one repeat and the start of the next. It asks whether internal state outlasts the clip.

Brains adapt across repeats. Adaptation enters C_int as slow internal change, which is part of the
property, not a nuisance; it is reported separately (the repeat-by-repeat trend of the stimulus-locked
response).

## 4. Systems

**Real (primary): Allen Brain Observatory Visual Coding Neuropixels** (DANDI 000021 and 000022), one
session per mouse, natural-movie blocks. In brain_observatory sessions these are "natural movie one" (30 s,
900 frames at 30 Hz) shown 20 times in 2 blocks, and "natural movie three" (120 s) shown 10 times in 2
blocks. The functional_connectivity sessions are pending the metadata survey (feasibility check F1).
- Individuals: mice.
- Units: Allen `good` units. Pooling in groups is decided by calibration, not assumed.

**Real (replication): to be chosen in feasibility check F3** from:
- the IBL brain-wide map (trial-aligned decision task; "stimulus-locked" = per-condition trial average);
- the worm data (no repeated sensory clips; probably unsuitable);
- a second Allen dataset.

**Artificial: every standard family**, 3 instances each, each driven by inputs of its own kind with the
same repeat structure:

| family | systems | input |
|---|---|---|
| random RNN | 480 units | movie frames, downsampled, through a fixed random projection |
| trained RNN | task RNN (decision task) | its task stream, the same trial sequence repeated |
| GRU, CfC | character networks | a text clip repeated, each repeat after different preceding text |
| spiking network | LIF, 1,000 neurons | movie projection as input current |
| transformers | Pythia 14M to 1B | a text clip repeated, each repeat after different preceding text |
| state-space models | Mamba 130M, 370M | as transformers |
| vision network | a CNN plus recurrent readout (to be specified in F2) | movie frames |

*Augmented:* the random RNN with slow drives (the share to be tuned on half the mice and tested on the
other half), and Pythia with a slow latent.

Repeats must differ in internal state, otherwise C_int is zero by construction:
- networks with noise run continuously, with intervening input between repeats, as mice watch movies;
- deterministic networks (language models, trained networks) get different preceding context before each
  repeat.

## 5. Instruments

Each AI is recorded through the registered spike model at each mouse's own single-unit numbers, measured
on that mouse's natural-movie blocks. Pooling in groups follows calibration. The movie and repeat
structure are reproduced: the same number of repeats, and clip length in units of the AI's
stimulus-locked timescale equal to the mouse's.

## 6. Calibration (before freezing, synthetic only)

Synthetic systems with a known stimulus-locked component (a fixed signal shared across repeats) and a known
internal component (an Ornstein-Uhlenbeck process, different on each repeat), with known shares and
timescales, are recorded through each mouse's instrument.
- **C1:** M1 recovers the internal share and M2 recovers the timescale ratio (Spearman of at least 0.9 over
  5 levels and 2 seeds).
- **C4:** neither moves by more than 0.5 of its C1 range under unmatched knobs (native timescale,
  population size, clip length in the allowed range).
- **C3:** split-half precision on real mice is checked only after freezing; it is a gate on the
  measurement, not a reason to change it.

A measurement that fails calibration is dropped before freezing, and that is logged.

## 7. Hypotheses and decision rules (to be frozen)

All tests are paired, mouse by mouse: d = mouse minus AI at that mouse's instrument. The ruler is the SD of
the mice's values, and the equivalence margin is 0.5 ruler units.
- **H1 (gap):** for each standard family, M2 (and separately M1) is lower in the AI than in the mice.
  - Per family: confirmed if a one-sided Wilcoxon test gives p < 0.05 and the median d exceeds 0.5 ruler
    units.
  - The thesis holds if at least 5 of 7 families are confirmed and none is refuted.
- **H2 (ingredient):** the slow-drive strength is tuned on a seeded half of the mice and tested on the
  other half. Confirmed if the 90% interval of the median d lies within plus or minus 0.5 ruler units
  (equivalence).
- **H3 (scale):** Pythia 1B is not closer to the mice than Pythia 14M. Confirmed if the 90% interval of the
  difference in absolute median d lies above -0.5 ruler units.

Every verdict is reported whatever it is, with the number of mice and pairs.

## 8. Feasibility checks (before freezing; no activity read for any measurement)

- **F1:** natural-movie metadata in all 58 sessions (repeats, frames, blocks, durations).
- **F2:** an input pipeline for every AI family. Each produces its activity with repeats that differ in
  internal state.
- **F3:** the choice of replication dataset (metadata and size).
- **F4:** compute budget: per-mouse recording of 13 or more AIs times about 50 mice on this machine.
- **F5:** synthetic calibration (section 6).

## 9. Documentation rules

- `SLOW.md` is the registration. After freezing, changes are numbered amendments (S1, S2, ...), each dated
  and labelled "before any real data" or "after X was seen".
- `SLOW_LOG.md` is the lab notebook. Every job started, finished or crashed, every restart, every decision
  and its reason, written at the time.
- Results files are listed with the commit that made them. Third-party data stays local, and only summary
  numbers are committed.
- An independent review comes before the first real measurement, with its findings and fixes recorded.
