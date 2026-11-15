# Study 2: is the difference slow internal state? (registration, v1.0)

**Status: FROZEN** (16 Nov 2026, after feasibility checks F1 to F5, synthetic calibration, and two
independent reviews, S-R1 and S-R2, whose findings and responses are in `docs/SLOW_LOG.md`). The freezing
commit's message says "SLOW registration frozen"; its hash is recorded here: **Frozen at commit 8df8c650b0e0**. From here on any change to this
file, or to code the results depend on, is a numbered amendment (S1, S2, ...), dated and labelled "before any
real data" or "after X was seen". **No mouse activity had been read for any measurement when this was frozen**
(only metadata, stimulus tables, behaviour shapes, and array shapes of one cached session).

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

**Claim under test, four items, each with its own verdict (section 7):**
1. real cortex carries more internal state (activity not locked to its input) than standard artificial
   networks;
2. that internal state is slower relative to the input;
3. a slow internal state closes the gap, and simpler candidates (a fast drive, more noise) do not;
4. scale is not what closes it.

"Internal state" here means activity that differs between repeats of the same input *within* a repeat:
units are centred within each repeat, so change slower than one repeat (30 s), such as drift between the
two movie blocks, is not counted, in mice or in AIs. Mouse internal state includes whatever the animal's
behaviour (running, arousal) adds; items 1 and 2 are also reported with behaviour regressed out (section 7),
and the wording of any conclusion follows what survives that.

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
k0 = 2** (40 ms in spike bins). History: the first draft extrapolated
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
  20- and 60-repeat sessions face the same rule). A mouse with fewer than 30 included units is excluded; a
  mouse with more than 480 keeps a seeded subset of 480 (the AIs have 480 or 512 units). No pooling.
- Behaviour: running speed (all sessions) and pupil area (where tracked) in 20 ms bins on each repeat, for
  the behaviour-removed sensitivity (section 7).
- Repeats: every repeat of natural_movie_one that does not overlap one of Allen's invalid intervals (the
  number varies by mouse: one test session kept 17 of 20). Each AI is given the same number of repeats as
  the mouse it is compared with.

**Real (replication): deferred.** The Allen Visual Coding two-photon dataset was chosen in F3 (271 mice,
natural_movie_one 10 times each), and its loader and pipeline arm exist (`--arm 2p`). Review S-R2 (finding 2)
showed that the lag-2 measures do not remove single-cell spike noise once it is filtered by the calcium
indicator (spike-driven dF/F with no internal state read M1 0.50 to 0.91), and the AI calcium model lacks
that term. The replication is therefore **not part of this registration**. It will be registered separately,
with its own calibration, before any two-photon activity is read.

**Artificial: every standard family**, 3 instances each, each driven by inputs of its own kind with the
same repeat structure:

| family | systems | input and repeat structure |
|---|---|---|
| A1 random RNN | 480 units, g 1.5, noise 0.1 | the movie's 64 principal-component features through a fixed random input matrix; clip repeated back to back after a 2,000-step blank burn-in; input gain on a grid (section 7) |
| A2 trained RNN | the map study's decision-task RNN, 512 units (accuracy at least 0.7; otherwise seed + 3, then seed + 6, is trained instead) | one fixed draw of trials repeated, 5 to 15 random trials before each repeat, one continuous session |
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
(the LIF network) play the movie in real time. A playback sensitivity is run for A1 at gain 0.25, where it
has an internal part (x0.5, x2, and playback from the driven timescale; section 6). A1 activity is kept as
block means of k native steps so that every playback group has about 5 kept samples per 20 ms bin (memory;
at the median this lowers M1 by about 0.01 against full resolution, `SLOW_LOG.md`, "Block means").

*Augmented (H2):* the balanced-gain random RNN with slow drives; negative controls: the same with a fast
drive, and A1 with more network noise; 8 settings each (section 7).

Repeats must differ in internal state, otherwise C_int is zero by construction:
- networks with noise run continuously, with intervening input between repeats, as mice watch movies;
- deterministic networks (language models, trained networks) get different preceding context before each
  repeat.

## 5. Instruments

- Every AI except the spiking network is recorded through the map study's registered spike model at each
  mouse's own single-unit numbers (bins per timescale, spikes per bin, white share, rate spread), measured
  on that mouse's movie repeats (included units, repeats as segments) after freezing.
- The spike model is applied to the whole run at once: each unit is standardised and rate-normalised once,
  and only the bins are laid out from each repeat's own start (`record.spikes_aligned`). (v0.3 recorded each
  repeat separately, which re-standardised per repeat and erased between-repeat gain changes in AIs only:
  review S-R2 finding 1.)
- After recording, the mouse's instrument function is computed on the recorded repeats themselves. If the
  bins per timescale, spikes per bin or rate spread differ from the mouse's by more than 15%, 15% or 20%, or
  the white share by more than 0.05, the mean count, bin width and rate spread are scaled toward the mouse
  and the recording repeated, at most twice (`record.record_checked`). A recording still outside tolerance
  is "not reached": excluded and counted. The numbers measured on the repeats are stored.
- A system with no measurable native timescale is pre-held (each step repeated 4 times) before matching.
- AI units with SD below 1% of the median unit SD are excluded as silent. The recorded units then go through
  the mouse's inclusion rule, and a seeded subset of the mouse's size is kept (the M1 estimate has a
  small-sample bias that depends on the number of units: C4 population, 0.65 at 200 units, 0.70 at 480).
- The spiking network (A4) is recorded like a mouse: its own spikes in 20 ms bins, thinned at random to the
  mouse's spikes per bin (thinning probability from its included neurons), the mouse's inclusion rule, then
  the mouse's number of units.
- Each AI gets the same number of repeats as its mouse. Recorded bins per clip are reported.

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

- **Multiplicative internal state:** a slow per-unit gain on the locked activity (no additive internal part)
  must raise M1 monotonically (Spearman at least 0.9 over 5 levels), so gain changes between repeats are
  seen through the instrument as they would be in mice (review S-R2 finding 1).
- **Bias bounds.** The known mouse-AI biases from these checks set a floor on what counts as a gap (section
  7): spike type (up to 0.075 in M1, up to 0.5 in log M2) and short recorded clips (M1 lower by 0.03 to 0.04
  at about 570 bins; log M2 lower by 0.33 at 218 bins). Bounds: **0.10 for M1 and 0.5 for log M2**. This is
  the registered consequence of the spike-type check failing narrowly (S-R2 finding 9).

After freezing, on the real recordings, before any verdict is read (review S-R1 finding 8):
- **C3, reliability:** split each mouse's repeats into odd and even; Spearman across mice of M1 (and of log
  M2) between halves at least 0.5. A measure that fails is reported as unreliable and not tested.
- **Playback, in mouse-ruler units:** A1 at gain 0.25 under the playback sensitivity (x0.5, x2, driven
  rule). If any variant moves the median of a measure by 0.5 ruler units or more, that measure's test for the
  movie-driven families (A1, A4) is reported but not counted.
- Not repeated after freezing, with reasons: clip length (fixed by design for each family, and C4 covers
  200 to 4,000 bins); pre-hold (only CfC and LIF, and M1 did not move between pre-holds of 2, 4 and 8);
  re-matching (moved M1 by at most 0.03 and M2 by at most 0.25 before freezing).

## 7. Hypotheses and decision rules (to be frozen)

All tests are paired, mouse by mouse: d = mouse minus AI at that mouse's instrument. **The ruler is a
robust SD of the mice's values** (1.4826 x the median absolute deviation). M1 is analysed as it is, M2 on a
log scale. **The margin for a gap is the larger of 0.5 ruler units and the bias bound** (0.10 in M1, 0.5 in
log M2; section 6).

**From several runs to one d (the bracket rule).** Movie-driven families run on a gain grid (0.05, 0.1,
0.25, 0.5, 0.86 balanced, 1, 2, 4); A6 has 4 model sizes and A7 has 2. For each mouse and measure, among the
family's runs that have a value for that measure (on M2, runs with an internal part): d = 0 if the mouse
lies within their range, else mouse minus the nearer end. A pair counts only if every gain or size was
recorded at that mouse with a reached instrument; if more than 25% of mice lack a pair, the family's verdict
is "not testable".

**Codes.** "No shared part": no positive covariance at lag 2 at all; excluded (not counted as 0). "No
internal part" (M1 below 0.05) and "no locked part" apply to M2. If more than half of a family's pairs have
one code, that code is the family's verdict on that measure.

**Ceilings and censoring (M2).** A mouse at internal ceiling against a family with a run at ceiling is a
tie (d = 0). A pair whose nearer AI run is at internal ceiling while the mouse lies above it, or where
either side's locked time is at ceiling, is censored: excluded and counted.

**Dependence.** Pairs that share an AI run (a generator cell: instance, and playback group for
movie-driven families; both stored on every AI row) are not independent. Every interval is a cluster
bootstrap over cells (4,000 resamples), and the one-sided test must hold within each of the 3 instances as
well as overall.

- **H1 (gap), per family and measure:** confirmed if the one-sided Wilcoxon signed-rank test (mouse
  greater) gives p < 0.05 overall and within every instance, the median d exceeds the margin, and the lower
  end of the cluster interval is above 0. Refuted: the same in the opposite direction. Otherwise not
  decided; fewer than 6 pairs: too few pairs. Reported beside every M2 verdict, not counted: the same test
  with the AI's runs restricted to M1 at least 0.2 (in C1, M2 reads low when the internal share is small).
- **Claim 1 (more internal state)** holds if at least 5 of the 7 families are confirmed on M1 and none is
  refuted on M1. Noisy families (A1, A4) and noise-free ones (A2, A3, A5, A6, A7, whose only internal state
  is what the preceding input left) are reported separately.
- **Claim 2 (slower relative to the input)** holds if the shuffled-movie check passes, at least 3 families
  have a testable M2 verdict (confirmed, refuted or not decided), at least two thirds of those are
  confirmed, and none is refuted. If the check fails, claim 2 is "not assessable".
- **Claim 3 (H2).** Three candidates, each tuned on the mice of a seeded half of the generator cells (seed
  2026; tuning and test halves share no AI run) by minimising the sum of the absolute median d on M1 and log
  M2 (ruler units), then tested on the mice of the other cells. 8 settings each:
  - **slow drive** (`inputs.add_slow_drive`: 10 Ornstein-Uhlenbeck drives through a fixed random projection
    added to unit activity of the balanced-gain A1): share 0.1, 0.2, 0.3, 0.5 x time constant 1 or 3 s;
  - **fast drive**, control: the same with a time constant of 1 or 2 movie frames;
  - **more noise**, control: A1 with network noise 0.2, 0.4, 0.8, 1.6 x input gain 0.25 or 0.86.
  - Equivalent: the 90% cluster interval of the median d within plus or minus 0.5 ruler units on both M1 and
    M2. Claim 3 holds if the slow drive is equivalent and neither control is. The drive is added to the
    activity, not built into the dynamics, so a confirmed claim 3 says a slow additive state suffices, not
    which mechanism produces it.
- **Claim 4 (H3, scale):** Pythia 1B is not closer to the mice than Pythia 14M, on M1 (14M has almost no
  internal part, so M2 cannot be compared). For each mouse, closer-by = |d(14M)| - |d(1B)| in ruler units;
  holds if the upper end of the 90% cluster interval of its median is below 0.5.
- **Behaviour (review S-R2 finding 11).** Each mouse's measures are also computed after regressing out
  running speed and pupil area (each signal and its 1 s mean, additive and as gain on the unit's mean
  response; a constant per repeat). Claims 1 and 2 are re-evaluated with these values; each claim is reported
  as holding "with" or "without" behaviour removed. In a synthetic check this regression removed about
  three quarters of running-driven internal state and left unrelated internal state untouched (0.34 to 0.34).
- **Validity check of M2: the shuffled movie.** In the 26 functional_connectivity mice, the shuffled movie
  (one fixed permutation of the same frames, 20 times; same units). Passes if the locked time falls
  (one-sided Wilcoxon p < 0.05), log M2 rises (p < 0.05), and the median log change of the internal time is
  smaller in size than that of the locked time.

Every verdict is reported whatever it is, with the numbers of mice, pairs, cells, missing and censored pairs.

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
- **F3:** the Allen two-photon dataset was chosen and its loader written; deferred to a separate
  registration after review S-R2 (section 4).
- **F4:** done as an estimate: about 1,330 recordings with one instance per mouse, about 20 hours.
- **F5:** for the final measures and recording path: C1 passes at four real instruments for M1, M2 and a
  multiplicative internal state (`docs/figures/slow_c1_v4.json`); C4 passes (`slow_c4_v3.json`); the
  spike-type check failed narrowly and became the bias bound (section 6). Earlier versions:
  `slow_c1.json`, `slow_c4.json` (v0.2), `slow_c1_v3.json` (v0.3).

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
- Freezing fixes the whole repository at the freezing commit (the study also depends on the map study's
  `nematica/map` code). Every result row stores the commit and whether the code differed from it. Any
  later change to code the results depend on is an amendment (section 9).
- Seeds: the H2 split 2026; per-run recording seeds from `zlib.crc32` of the run label; instance seeds
  0 to 2.
- Before freezing: every critical and major finding of reviews S-R1 and S-R2 resolved (`SLOW_LOG.md`); C1
  rerun on the final recording path, with the multiplicative case; a check of the tests logic on synthetic
  rows (`scripts/slow_test_logic.py`); a review of the frozen text and code before the first real
  measurement. 

## Amendments

### S1 (16 Nov 2026), before any real data

Labelled **before any real data**: no mouse activity had been measured (the data prefetch downloads and
caches only). Cause: review S-R3 of the frozen version (`SLOW_LOG.md`, "Review S-R3"). Changes:
- **Instrument check (B1).** The AI's instrument numbers and its unit inclusion use the mouse's spike
  minimum scaled to the same movie time (200 x AI bins per clip / mouse bins per clip). Corrections scale
  the bin width by the timescale error, the mean count by the count error divided by the bin change, the
  rate spread by its error and the gain toward the white-share target; at most 3 rounds; the best round is
  kept. "Reached" is judged on the analysed units, and a recording with fewer analysed units than its mouse
  is not reached. A non-finite instrument number is never within tolerance.
- **Disk (B2).** Language models run last, model by model; each large model's download is removed after its
  last use; generation stops with an error if under 3 GB is free.
- A4 rows have no playback group (its 3 instances are its clusters). The shuffled check defaults to "not
  assessable" when no mouse has shuffled data. Behaviour and shuffled steps fail on their own without
  dropping the mouse. Behaviour-removed claims re-apply the registered claim rules and counted flags. H2, the
  playback check and H3 use reached instruments only, and H3 uses the same codes as H1. A family verdict needs
  all 3 instances. Pupil area exists only in the 26 DANDI 000022 sessions (eye tracking); elsewhere behaviour is
  running speed alone. The mouse table (instance, group, group medians) is written once after the mice stage
  covers all 58 sessions, and later runs must agree with it. Code provenance is compared with the freezing
  commit and stored in tests.json. A mouse with fewer than 10 valid repeats is excluded. The slow drive is
  built in place (memory).
- Compute: about 3,000 AI recordings, so the AI stage takes days, not 20 hours (F4 was an underestimate).
