# Study 2: is the difference slow internal state? (draft registration, v0.2)

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

Spike noise is independent from bin to bin and from repeat to repeat, so it sits only at lag 0 of C_same.
**The primary measures therefore start at lag 1 and need no extrapolation** (changed 15 Nov during F5,
see `SLOW_LOG.md` 18:30 to 19:05: the lag-0 extrapolation read an internal share of 0.07 to 0.12 in systems
with none, and that bias also dragged the timescale ratio).

- **M1, internal share** = C_int(1) / C_same(1): the fraction of the one-bin covariance that is not set by
  the input. (Reported, not tested: the lag-0 version with the extrapolated noise-free variance.)
- **M2, internal slowness** = T_int / T_lock, where each T is an integrated autocorrelation time summed
  from lag 1 and normalised by lag 1: T = sum over k >= 1 of C(k) / C(1), up to the first lag where C
  falls to zero or below. It asks how much slower the internal state moves than the input-driven activity.
  Both times are in the same system's samples, so the ratio has no clock. (Reported, not tested: the
  half-life ratio and the lag-0 integral ratio.)
  - M2 exists only where there is an internal part to time: it is computed only when M1 is at least 0.05
    (draft threshold; at true share 0, M1 read 0.00 in every calibration run, and 0.06 to 0.08 at true
    share 0.05). A system below the threshold has M2 "absent", which is reported as such.
- *Reported for every AI, not tested:* the internal share weighted by unit variance (native activity, no
  instrument), and the fraction of units whose own internal share exceeds 0.5. Both were added after the
  GRU probe (`SLOW_LOG.md`, "GRU through the median instrument"), where a quiet minority of latching
  units carried the internal state.
- *Secondary:* **M3, carry-over** = the correlation of a unit group's internal component between the end
  of one repeat and the start of the next. It asks whether internal state outlasts the clip.

Brains adapt across repeats. Adaptation enters C_int as slow internal change, which is part of the
property, not a nuisance; it is reported separately (the repeat-by-repeat trend of the stimulus-locked
response).

## 4. Systems

**Real (primary): Allen Brain Observatory Visual Coding Neuropixels** (DANDI 000021 and 000022), one
session per mouse, natural-movie blocks. In brain_observatory sessions these are "natural movie one" (30 s,
900 frames at 30 Hz) shown 20 times in 2 blocks, and "natural movie three" (120 s) shown 10 times in 2
blocks. The functional_connectivity sessions show "natural movie one" 60 times in 2 blocks, plus a
*shuffled* version of the same frames 20 times. The shuffled movie is a built-in control: the same images
with a shorter input timescale. F1 (below) found the movie in all 58 sessions.
- Individuals: mice.
- Units: Allen `good` units, the map study's subset (at most 2,400 per session, seeded) and its QC mask
  (amendment 25). No pooling (F5: repeats already average out spike noise).
- Repeats: every repeat of natural_movie_one that does not overlap one of Allen's invalid intervals (the
  number varies by mouse: one test session kept 17 of 20). Each AI is given the same number of repeats as
  the mouse it is compared with.

**Real (replication): Allen Brain Observatory Visual Coding two-photon** (chosen in F3; `SLOW_LOG.md`,
entry "F3: the two-photon replication is feasible"): 271 mice, each with a "session A" in which natural_movie_one is shown 10
times. One experiment per mouse: the mouse's VISp experiment if it has one, else its lowest experiment id.
Calcium imaging (GCaMP6f, 30 Hz), so the AIs are recorded through the map study's calcium model, matched
to each mouse. The same tests as for the primary dataset, run separately.

**Artificial: every standard family**, 3 instances each, each driven by inputs of its own kind with the
same repeat structure:

| family | systems | input and repeat structure |
|---|---|---|
| A1 random RNN | 480 units, g 1.5, noise 0.1 | the movie's 64 principal-component features through a fixed random input matrix; clip repeated back to back after a 2,000-step blank burn-in; input gain on a grid (section 7) |
| A2 trained RNN | the map study's decision-task RNN, 512 units | one fixed draw of 100 trials repeated, 5 to 15 random trials before each repeat, one continuous session |
| A3 GRU, A5 CfC | the map study's character networks, 512 units | a 3,000-character held-out clip repeated, each repeat after 200 to 600 characters of other held-out text, one continuous run |
| A4 spiking network | the map study's LIF network, 1,000 neurons | external Poisson rates modulated by the movie features (gain grid); movie in real time (33.3 ms per frame) |
| A6 transformers | Pythia 14M, 160M, 410M, 1B | a text clip after a different context (256 tokens) on each repeat; one forward pass per repeat |
| A7 state-space models | Mamba 130M, 370M | as transformers |

The vision network of v0 is dropped: a feedforward network has no internal state by construction, and no
standard recurrent vision network is part of the map study's families. Language models carry no state
between calls, so their only internal state is the preceding context.

**Instances.** Three instances per family (seeds, or released seeds for Pythia as in the map study). To fit
the compute budget (F4) each mouse is compared with one instance per family: instance = the mouse's rank
(in the map study's order) mod 3.

**Playback speed.** A movie-driven AI sees the clip at the same speed relative to its own undriven native
timescale as the mouse does relative to its movie timescale: native steps per frame = tau_native /
(bins_per_tau x 20 ms / 33.3 ms). To share generation across mice, mice are split into 4 groups by
quartile of bins per timescale and each AI run is generated once per group, at the group median. AIs with
no measurable native timescale (the LIF network) play the movie in real time.

*Augmented:* the random RNN with slow drives (the share to be tuned on half the mice and tested on the
other half), and Pythia with a slow latent.

Repeats must differ in internal state, otherwise C_int is zero by construction:
- networks with noise run continuously, with intervening input between repeats, as mice watch movies;
- deterministic networks (language models, trained networks) get different preceding context before each
  repeat.

## 5. Instruments

- Every AI except the spiking network is recorded through the map study's registered spike model at each
  mouse's own single-unit numbers (bins per timescale, spikes per bin, white share, rate spread), measured
  on that mouse's natural-movie repeats after freezing. Units are recorded 100 at a time with one shared
  random generator (memory; same model).
- The spiking network (A4) is recorded like a mouse: its own spikes in 20 ms bins, thinned at random to
  the mouse's spikes per bin.
- AI units with SD below 1% of the median unit SD are excluded as silent (Allen keeps only firing units).
- The recorded clip length is whatever the matched instrument gives; C4 showed the measures do not move
  between about 280 and 3,400 recorded bins per clip. Bins per clip are reported for every recording.
- Replication: the calcium model, matched to each two-photon mouse's numbers on its movie epochs.

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
the mice's values, and the equivalence margin is 0.5 ruler units. **M1 is analysed as it is; M2 on a log
scale** (it is a ratio), and a value flagged at ceiling enters as the lower bound it is (the tests are
rank-based).
- **H1 (gap):** for each standard family (A1 to A7), M1 is lower in the AI than in the mice, and M2 is
  lower in the AI than in the mice; two separate tests per family.
  - Confirmed: a one-sided Wilcoxon signed-rank test (mouse greater) gives p < 0.05 and the median d
    exceeds 0.5 ruler units.
  - Refuted: the opposite one-sided test (AI greater) gives p < 0.05 and the median d is below -0.5 ruler
    units.
  - Otherwise: not decided.
  - **M2 where the AI has no internal part.** M2 exists only where M1 is at least 0.05. If the AI's M2 is
    absent in more than half of its pairs, the family's M2 verdict is "no internal part" (the gap is then
    carried by M1 alone); otherwise the M2 test uses the pairs where both values exist, and the number of
    absent pairs is reported.
  - The thesis holds if at least 5 of 7 families are confirmed on M1 or M2 and none is refuted on either.
- **Free input strength (added 15 Nov during F2, `SLOW_LOG.md` 18:10).** For movie-driven families (random
  RNN, spiking network) the strength of the movie input is a free parameter, and it sets M1 almost by
  itself (0.91 to 0.04 over gains 0.05 to 4 in the random RNN). So these families are measured on a fixed
  gain grid (draft: 0.05, 0.1, 0.25, 0.5, 1, 2, 4), and the family's d at each mouse is taken at the gain
  that brings it **closest** to that mouse on the measure tested. A gap confirmed this way holds for every
  input strength in the grid. The balanced gain (movie input as strong as recurrent input) is reported.
- **H2 (ingredient):** the random RNN at its balanced gain, with slow drives added (`inputs.add_slow_drive`:
  10 Ornstein-Uhlenbeck drives through a fixed random projection, carrying a share of each unit's variance,
  time constant given in movie time). Share (0.05, 0.1, 0.2, 0.3, 0.5) and time constant (0.5, 1, 2, 5 s)
  are chosen together on a seeded half of the mice (the pair minimising the sum of the absolute median d on
  M1 and on log M2) and tested on the other half. Confirmed if the 90% bootstrap interval of the median d
  lies within plus or minus 0.5 ruler units on both M1 and M2 (equivalence). (The map study's version, 50
  times the network's own timescale, outlasts the clip once the network is driven: `SLOW_LOG.md` 17:45.)
- **H3 (scale):** Pythia 1B is not closer to the mice than Pythia 14M. Confirmed if the 90% interval of the
  difference in absolute median d lies above -0.5 ruler units.

Every verdict is reported whatever it is, with the number of mice and pairs.

## 8. Feasibility checks (before freezing; no activity read for any measurement)

- **F1:** natural-movie metadata in all 58 sessions (repeats, frames, blocks, durations). **Done 15 Nov:**
  - all 58 readable;
  - movie one (30 s, 900 frames at 30 Hz) shown 20 times in 32 sessions and 60 times in 26;
  - movie three (120 s, 10 times) in the 32 brain_observatory sessions;
  - the shuffled movie one (20 times) in the 26 functional_connectivity sessions;
  - 600 to 1,803 s of movie one per mouse;
  - summary in `docs/figures/slow_f1_movie_meta.json`.
- **F2:** an input pipeline for every AI family. Code in `nematica/slow/inputs.py`; probes logged. Done for
  A1, A2, A3, A4 and Pythia-14m; CfC running; larger Pythia and Mamba to download (disk).
- **F3:** done: the Allen two-photon dataset (section 4), C1 passes through the calcium model.
- **F4:** done as an estimate: about 1,330 recordings with one instance per mouse, about 20 hours.
- **F5:** C1 passes at four real instruments (median, fastest, slowest, noisiest mouse) for M1 and M2
  (rho 0.98 each); C4 passes (all ratios 0.06 or less, including short clips); re-matching the instrument
  moves the measures little. Summaries: `docs/figures/slow_c1.json`, `slow_c4.json`, `slow_f3.json`.

## 9. Documentation rules

- `SLOW.md` is the registration. After freezing, changes are numbered amendments (S1, S2, ...), each dated
  and labelled "before any real data" or "after X was seen".
- `SLOW_LOG.md` is the lab notebook. Every job started, finished or crashed, every restart, every decision
  and its reason, written at the time.
- Results files are listed with the commit that made them. Third-party data stays local, and only summary
  numbers are committed.
- An independent review comes before the first real measurement, with its findings and fixes recorded.
