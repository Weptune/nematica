# Study 2: is the difference slow internal state? (draft registration, v0.3)

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
- a slow internal state closes the gap, and simpler candidates (a fast drive, more noise) do not;
- scale is not.

"Internal state" here means activity that differs between repeats of the same input *within* a repeat:
units are centred within each repeat, so change slower than one repeat (30 s), such as drift between the
two movie blocks, is not counted, in mice or in AIs.

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

The input is a clip repeated R times. Y_r(t) is the activity of a unit during repeat r, **centred within
that repeat** and scaled by the unit's pooled within-repeat SD. For each lag k, averaged over units:
- same-repeat autocovariance: C_same(k) = mean over r of cov(Y_r(t), Y_r(t + k));
- cross-repeat autocovariance: C_cross(k) = mean over pairs r != r' of cov(Y_r(t), Y_r'(t + k)).

Activity that follows the input repeats across repeats, so C_cross is the **stimulus-locked**
autocovariance. C_int = C_same - C_cross is the **internal** autocovariance: everything that differs
between repeats of the same input.

A single unit's own spike-train structure (Poisson noise, refractoriness, bursts) has no cross-repeat
counterpart and sits at lags 0 and 1 of C_same in 20 ms bins. **The measures therefore start at lag
k0 = 2** (40 ms in spike bins; 2 frames, 67 ms, in calcium frames). History: the first draft extrapolated
lag 0 (biased by about 0.1 with no internal state), the second started at lag 1 (driven to -1 by a dead
time and to +0.77 by bursts with no internal state; review S-R1 finding 1). From lag 2 the spike type and
drift between blocks no longer matter (`SLOW_LOG.md`, "Fix for S-R1 findings 1 and 3").

- **M1, internal share** = C_int(k0) / C_same(k0), bounded to [-1, 1]. If C_same(k0) is not positive the
  system has no shared covariance at that lag: M1 is set to 0 and flagged `no_shared`.
- **M2, internal slowness** = T_int / T_lock, each T = sum over k >= k0 of C(k) / C(k0), up to the first
  lag where C falls to zero or below, and at most a quarter of the clip. Both times are in the same
  system's samples, so the ratio has no clock. Analysed on a log scale.
  - M2 needs an internal part (M1 at least 0.05; otherwise "no internal part") and a locked part to time it
    against (C_cross(k0) > 0; otherwise "no locked part").
  - If C_int stays positive to the largest lag, T_int is a lower bound (`int_ceiling`); likewise
    `lock_ceiling`. The largest lag is a quarter of the clip in every system, so the cap is the same
    fraction of the movie for mice and AIs.
- *Reported, not tested:* M1 on each half of the clip separately (internal state carried in from before
  the repeat fades along the clip in text and trial networks); the adaptation trend (Spearman, over repeats,
  of how well each repeat matches the mean of the others); for AIs, the variance-weighted internal share
  and the fraction of units whose own internal share exceeds 0.5 (native activity); the superseded lag-0
  and lag-1 measures.
- M3 (carry-over) of earlier drafts is dropped: it had no version free of the spike-train problem.

## 4. Systems

**Real (primary): Allen Brain Observatory Visual Coding Neuropixels** (DANDI 000021 and 000022), one
session per mouse, natural-movie blocks. In brain_observatory sessions these are "natural movie one" (30 s,
900 frames at 30 Hz) shown 20 times in 2 blocks, and "natural movie three" (120 s) shown 10 times in 2
blocks. The functional_connectivity sessions show "natural movie one" 60 times in 2 blocks, plus a
*shuffled* version of the same frames 20 times. The shuffled movie is a built-in control: the same images
with a shorter input timescale. F1 (below) found the movie in all 58 sessions.
- Individuals: mice.
- Units: Allen `good` units, the map study's subset (at most 2,400 per session, seeded), that also pass
  Allen's default QC (amendment 25: isi_violations < 0.5, amplitude_cutoff < 0.1, presence_ratio > 0.9)
  and sit in **visual cortex** (peak channel in an area whose acronym starts with VIS); then the map study's
  inclusion rule (rate at least 0.05 Hz over all repeats; at least 200 spikes over the first 17 repeats, so
  20- and 60-repeat sessions face the same rule). A mouse with fewer than 30 included units is excluded.
  No pooling.
- Repeats: every repeat of natural_movie_one that does not overlap one of Allen's invalid intervals (the
  number varies by mouse: one test session kept 17 of 20). Each AI is given the same number of repeats as
  the mouse it is compared with.

**Real (replication): Allen Brain Observatory Visual Coding two-photon** (chosen in F3; `SLOW_LOG.md`,
entry "F3: the two-photon replication is feasible"): 271 mice, each with a "session A" in which natural_movie_one is shown 10
times. One experiment per mouse: the mouse's VISp experiment if it has one, else its lowest experiment id.
Calcium imaging (GCaMP6f, 30 Hz), so the AIs are recorded through the map study's calcium model, matched
to each mouse's numbers on its movie repeats (GCaMP6f's registered half-decay); the LIF network too. Clip:
900 frames, 10 repeats. Playback speed: one group, at the Neuropixels mice's median timescale (calcium
timescales are set by the indicator, not the neurons). The same tests as for the primary dataset, run
separately (`scripts/slow_run.py --arm 2p`).

**Artificial: every standard family**, 3 instances each, each driven by inputs of its own kind with the
same repeat structure:

| family | systems | input and repeat structure |
|---|---|---|
| A1 random RNN | 480 units, g 1.5, noise 0.1 | the movie's 64 principal-component features through a fixed random input matrix; clip repeated back to back after a 2,000-step blank burn-in; input gain on a grid (section 7) |
| A2 trained RNN | the map study's decision-task RNN, 512 units (accuracy at least 0.7 or the instance is retrained with the next seed) | one fixed draw of trials repeated, 5 to 15 random trials before each repeat, one continuous session |
| A3 GRU, A5 CfC | the map study's character networks, 512 units | a held-out clip repeated, each repeat after 200 to 600 characters of other held-out text, one continuous run |
| A4 spiking network | the map study's LIF network, 1,000 neurons | external Poisson rates modulated by the movie features (gain grid); movie in real time (33.3 ms per frame) |
| A6 transformers | Pythia 14M, 160M, 410M (released seeds 1 to 3, one per instance), 1B | a text clip after a different 256-token context on each repeat; one forward pass per repeat; units: 480 middle-layer MLP neurons |
| A7 state-space models | Mamba 130M, 370M | as transformers; units: 480 gated SSM outputs of the middle layer |

**Clip length for A2, A3, A5, A6, A7** (review S-R1 finding 12): fixed per instance, the same for every
mouse: the number of trials, characters or tokens that records as about 1,500 bins (Neuropixels) or 900
frames (two-photon) at the median instrument of all mice, from a 3-repeat pilot. Each instance of Pythia
1B and Mamba takes its clip from a different place in the text.

The vision network of v0 is dropped: a feedforward network has no internal state by construction, and no
standard recurrent vision network is part of the map study's families. Language models carry no state
between calls, so their only internal state is the preceding context.

**Instances.** Three instances per family. To fit the compute budget (F4) each mouse is compared with one
instance per family: instance = the mouse's rank in the fixed session order (sorted session paths of DANDI
000021, then 000022) mod 3.

**Playback speed.** A movie-driven AI sees the clip at the same speed relative to its own undriven native
timescale as the mouse does relative to its movie timescale: native steps per frame = tau_native /
(bins_per_tau x 20 ms / 33.3 ms). To share generation across mice, mice are split into 4 groups by
quartile of bins per timescale and each AI run is generated once per group, at the group median. The
undriven timescale of A1 is measured per instance (8,000 steps). AIs with no measurable native timescale
(the LIF network) play the movie in real time. A playback sensitivity is run for the balanced-gain A1
(x0.5, x2, and playback from the driven timescale; section 7).

*Augmented (H2):* the balanced-gain random RNN with slow drives; negative controls: the same with a fast
drive, and with more network noise.

Repeats must differ in internal state, otherwise C_int is zero by construction:
- networks with noise run continuously, with intervening input between repeats, as mice watch movies;
- deterministic networks (language models, trained networks) get different preceding context before each
  repeat.

## 5. Instruments

- Every AI except the spiking network is recorded through the map study's registered spike model at each
  mouse's own single-unit numbers (bins per timescale, spikes per bin, white share, rate spread), measured
  on that mouse's movie repeats (included units, repeats as segments) after freezing. Units are recorded
  100 at a time with one shared random generator; each repeat is binned from its own start, as the mice are.
- A system with no measurable native timescale is pre-held (each step repeated 4 times) before matching.
- The matched knobs, the achieved numbers and whether matching reached its targets are stored for every
  recording. A recording whose match is not reached is excluded and counted.
- The spiking network (A4) is recorded like a mouse: its own spikes in 20 ms bins, thinned at random to
  the mouse's spikes per bin.
- AI units with SD below 1% of the median unit SD are excluded as silent (Allen keeps only firing units).
- Each AI is recorded with the same number of units as its mouse has included units (a seeded random
  subset of its non-silent units, at most all of them): the M1 estimate has a small-sample bias that depends
  on the number of units (C4 population: 0.65 at 200 units, 0.70 at 480), so the pair must match.
- Each AI gets the same number of repeats as its mouse. Recorded bins per clip are reported.
- Replication: the calcium model, matched to each two-photon mouse's numbers on its movie repeats.

## 6. Calibration

Before freezing, on synthetic systems (a locked part identical on every repeat, an internal
Ornstein-Uhlenbeck part continuous through the repeats; known shares and timescales):
- **C1:** M1 recovers the internal share and M2 the timescale ratio (Spearman at least 0.9 over 5 levels and
  2 seeds) at four real instruments (the median, fastest, slowest and noisiest mouse of the map study) and
  through the calcium model. Bias is reported beside rank order.
- **C4:** neither moves by more than 0.5 of its C1 range under unmatched knobs (native timescale,
  population, repeats, clip length from about 200 to 3,400 bins).
- **Spike types and drift:** at true share 0, M1 within 0.05 of 0 for Poisson, dead-time and bursting spike
  trains and for rate drift between blocks; at share 0.3, the three spike types within 0.05 of each other.
  (Run before freezing; it failed narrowly, see `SLOW_LOG.md`, "C4 and spike-type checks for the v0.3
  measures"; the criterion was not changed.)

After freezing, on the real recordings, before any verdict is read (review S-R1 finding 8):
- **C3, reliability:** split each mouse's repeats into odd and even; Spearman across mice of M1 (and of log
  M2) between halves at least 0.5. A measure that fails is reported as unreliable and not tested.
- **Nuisance checks, in mouse-ruler units:** the balanced-gain A1 under the playback sensitivity (x0.5, x2,
  driven rule). If a nuisance moves the family's median value by 0.5 ruler units or more, the M2 test of
  every movie-driven family is reported as "playback-sensitive" and not counted for the thesis.

## 7. Hypotheses and decision rules (to be frozen)

All tests are paired, mouse by mouse: d = mouse minus AI at that mouse's instrument. **The ruler is a
robust SD of the mice's values** (1.4826 x the median absolute deviation); the equivalence margin is 0.5
ruler units. M1 is analysed as it is, M2 on a log scale.

**From several runs to one d (the bracket rule; review S-R1 finding 2).** Movie-driven families run on a
gain grid (0.05, 0.1, 0.25, 0.5, 0.86 balanced, 1, 2, 4), and A6 and A7 have several model sizes. For each
mouse and measure: d = 0 if the mouse's value lies within the range of the family's values over its gains or
sizes at that mouse; otherwise d = mouse minus the nearer end. So a confirmed gap means no gain or size in the
grid reaches the mouse. A pair counts only if every gain or size of the family was recorded at that mouse
with a reached match; missing pairs are counted and reported.

**Ceiling (finding 4).** On M2, a mouse at ceiling against a family with a run at ceiling counts as a tie
(d = 0).

**Dependence (finding 6).** Pairs that share an AI run (a generator cell: instance, and playback group for
movie-driven families) are not independent. Every interval is a cluster bootstrap over cells (4,000
resamples), and the one-sided test must also hold **within each of the 3 instances** separately (pairs
within an instance differ in mice). A sign test over cell medians was considered and dropped: with 3 cells
for most families it can never reach p < 0.05.

- **H1 (gap):** for each standard family (A1 to A7), M1 and M2 are each lower in the AI than in the mice.
  - Confirmed: one-sided Wilcoxon signed-rank (mouse greater) p < 0.05 over all pairs and within every
    instance, median d above 0.5 ruler units, and the lower end of the cluster interval above 0.
  - Refuted: the same in the opposite direction.
  - Otherwise: not decided. Fewer than 6 pairs: "too few pairs".
  - M2 codes: if more than half the family's pairs have no internal part, its M2 verdict is "no internal
    part" (the gap is then carried by M1); if more than half have no locked part, "no locked part".
  - Reported beside every M2 verdict, not counted: the same test with the AI's runs restricted to those
    with M1 at least 0.2. Reason: in C1, M2 reads low when the internal share is small (true ratio 4: 0.9
    to 2.0 at share 0.05, 2.6 to 2.9 at 0.8), which favours the thesis for AIs with little internal state.
  - **The thesis holds** if at least 5 of the 7 families are confirmed on M1 or M2 and none is refuted on
    either. If the validity check below fails, M2 is set aside and the count uses M1 only.
- **H2 (ingredient), with negative controls (finding 7).** Three candidates, each the balanced-gain random
  RNN with one change, each tuned on a seeded half of the mice (seed 2026) by minimising the sum of the
  absolute median d on M1 and log M2 (in ruler units), then tested on the other half:
  - **slow drive** (`inputs.add_slow_drive`: 10 Ornstein-Uhlenbeck drives through a fixed random
    projection added to unit activity; share 0.05, 0.1, 0.2, 0.3, 0.5 x time constant 0.5, 1, 2, 5 s of
    movie time);
  - **fast drive**, control: the same with a time constant of one movie frame (share grid as above);
  - **more noise**, control: network noise 0.2, 0.4, 0.8, 1.6 (from 0.1).
  - Equivalent: the 90% cluster interval of the median d within plus or minus 0.5 ruler units on both M1
    and M2. **H2 is confirmed** if the slow drive is equivalent and neither control is.
- **H3 (scale):** Pythia 1B is not closer to the mice than Pythia 14M, on M1 (Pythia 14M has almost no
  internal part, so M2 cannot be compared). For each mouse, closer-by = |d(14M)| - |d(1B)| in ruler units;
  confirmed if the upper end of the 90% cluster interval of its median is below 0.5.
- **Validity check of M2 (not about AIs): the shuffled movie.** In the 26 functional_connectivity mice the
  shuffled movie is one fixed permutation of the same frames, shown 20 times (Allen staff, community
  forum thread 1010). Same units as the movie. Passes if the locked time falls (one-sided Wilcoxon p < 0.05),
  log M2 rises (p < 0.05), and the internal time moves less than the locked time (median absolute log
  change). M2 rising alone would be mechanical, since it is a ratio with the locked time below.

Every verdict is reported whatever it is, with the numbers of mice, pairs, cells and missing pairs.

## 8. Feasibility checks (before freezing; no activity read for any measurement)

- **F1:** natural-movie metadata in all 58 sessions (repeats, frames, blocks, durations). **Done 15 Nov:**
  - all 58 readable;
  - movie one (30 s, 900 frames at 30 Hz) shown 20 times in 32 sessions and 60 times in 26;
  - movie three (120 s, 10 times) in the 32 brain_observatory sessions;
  - the shuffled movie one (20 times) in the 26 functional_connectivity sessions;
  - 600 to 1,803 s of movie one per mouse;
  - summary in `docs/figures/slow_f1_movie_meta.json`.
- **F2:** an input pipeline for every AI family. Code in `nematica/slow/inputs.py`; probes of every family
  logged (A1 to A7); larger models are downloaded one at a time (disk).
- **F3:** done: the Allen two-photon dataset (section 4), C1 passes through the calcium model.
- **F4:** done as an estimate: about 1,330 recordings with one instance per mouse, about 20 hours.
- **F5:** for the lag-1 measures of v0.2, C1 passed at four real instruments and C4 passed; after review
  S-R1 the measures changed (lag 2, within-repeat centring), so C1, C4 and the spike-type check are rerun
  for them before freezing. Summaries: `docs/figures/slow_c1.json`, `slow_c4.json`, `slow_f3.json` (v0.2
  measures); the reruns are logged in `SLOW_LOG.md`.

## 9. Documentation rules

- `SLOW.md` is the registration. After freezing, changes are numbered amendments (S1, S2, ...), each dated
  and labelled "before any real data" or "after X was seen".
- `SLOW_LOG.md` is the lab notebook. Every job started, finished or crashed, every restart, every decision
  and its reason, written at the time.
- Results files are listed with the commit that made them. Third-party data stays local, and only summary
  numbers are committed.
- An independent review comes before freezing (review S-R1, `SLOW_LOG.md`) and another of the frozen
  version before the first real measurement, each with its findings and fixes recorded.
- `SLOW_LOG.md` entries carry UTC times from the machine clock and are cited by title.

## 10. Code, and what freezing fixes

- Measures: `nematica/slow/measures.py`; recording: `nematica/slow/record.py`; inputs:
  `nematica/slow/inputs.py`; mouse data: `nematica/slow/data.py`; pipeline: `scripts/slow_run.py`
  (stages `mice`, `ais`, `tests`; the first two refuse to run until this file says "Frozen at commit").
- Freezing fixes this file and those five files at the freezing commit. Any later change to them is an
  amendment (section 9), with the reason and whether any real data had been seen.
- Seeds: the H2 split 2026; per-run recording seeds from `zlib.crc32` of the run label; instance seeds
  0 to 2.
- Before freezing: every critical and major finding of review S-R1 resolved (`SLOW_LOG.md`); C1, C4 and
  the spike-type check rerun for the final measures; a second review of the frozen text and code. 
