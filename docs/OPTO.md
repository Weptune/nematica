# Study O: the stimulation test in mouse cortex (Allen optotagging)

Status: **registration draft v0.1 (19 Nov 2026); calibration next; no response read**. Written 17 Nov 2026 (UTC) before any optogenetic table or
response was opened. Context: `docs/STRATEGY_2026-11-17.md` and `docs/EMU_R.md` (the worm stimulation data
is exhausted; no public second worm dataset passes; plans must not depend on replies from other labs).

## Question (to be sharpened only after feasibility)

In the worm, a model fitted to ongoing activity looks real but answers stimulation wrongly, and only
learning from stimulation fixes it. Does the same hold in mouse visual cortex, measured animal by animal
against mouse-to-mouse variation? The Allen Visual Coding Neuropixels sessions (DANDI 000021 and 000022,
already in the project's pipeline) are believed to end with an optogenetic block in Cre-line mice (light
that activates one interneuron type). If so, that block is a public perturbation dataset in a second
species. Prior work: Sourmpis et al. (eLife 2026) show that fitted generic RNNs predict optogenetic
perturbations poorly in mouse task data; what would be ours is the calibrated, animal-by-animal version
on public data, in the same framework as the worm.

## Feasibility stop rule (fixed before opening any optogenetic table)

Metadata only: whether an optogenetic table exists, its conditions, number of trials, pulse durations,
light levels, times, and the mouse's genotype. No spike, LFP or response value is read.

The dataset is **usable** if all of these hold:
1. At least 12 mice have an optogenetic block with at least 50 trials of one fixed condition (same pulse
   shape and duration; light levels may vary if each level has at least 50 trials or levels are pooled by
   a rule written before responses are read).
2. Those mice have at least 10 minutes of activity outside any stimulus block, for fitting a model to
   ongoing activity (spontaneous blocks, as in the map study; the movie may serve as a second option).
3. At least two Cre lines are represented, or one line with at least 12 mice (so that a "which
   interneuron type" factor does not hide inside the mouse-to-mouse spread).
4. The block's trials are at least 1 s apart, so that a response window does not overlap the next pulse.

If the dataset is not usable, Study O stops here and the reason is recorded. If it is, the question,
measures, models, calibration systems and claims are written next, reviewed, and frozen before any
response is read.

## Feasibility log

18 Nov 2026, 06:29 UTC. `scripts/opto_feasibility.py`, output `docs/figures/opto/feasibility.jsonl`
(metadata only: genotype, optogenetic table columns and counts, spontaneous block lengths; no responses).

- All 58 sessions read without error. Every session with a Cre line has an optogenetic table at
  `processing/optotagging/optogenetic_stimulation` with three conditions: single square pulses (5 ms and
  10 ms), a 1 s train of 2.5 ms pulses at 10 Hz, and a 1 s half-cosine, each at three light levels.
- Cre mice with a table: 28 (Pvalb 8, Sst 12, Vip 8). 26 wild-type (no ChR2) mice also received the light,
  which gives a **light-only control** (heating, photoelectric artefact, visual response to the light).
- Trials per condition: 45 in 15 Cre mice, 75 in 12, about 150 in 1. **Rule 1** (at least 12 mice with at
  least 50 trials of one fixed condition): **13 mice pass** (Vip 5, Pvalb 4, Sst 4; 10 from 000022, 3 from
  000021). Passes, narrowly. Six wild-type mice also have at least 50 trials per condition.
- **Rule 2** (at least 10 minutes outside stimulus blocks): the shortest spontaneous total among Cre mice
  is 1237 s. Passes.
- **Rule 3** (at least two Cre lines): three lines. Passes as written, but with 4 or 5 mice per line the
  interneuron type will be a large factor; the registration must treat it explicitly.
- **Rule 4** (trials at least 1 s apart): the smallest gap is 1.68 s. Passes; a 1 s train or half-cosine
  leaves under 0.7 s before the next trial, so response windows must be chosen with that in mind.

**Outcome: usable, narrowly.** Next: the question, measures, models, calibration systems and claims,
written and reviewed before any response is read. Status line updated.

## Registration draft v0.1 (19 Nov 2026, 17:11 UTC; written before any response is read)

**Question.** In the worm, a copy fitted to ongoing activity looks real but answers stimulation wrongly,
and a copy that learned from stimulation answers like a real worm. Does the same hold in mouse visual
cortex, scored mouse by mouse against how much mice of the same line differ from each other?

**Mice.** The 13 Cre mice that pass rule 1: Pvalb, Sst and Vip lines (sub-769360771, sub-775876808,
sub-776061236, sub-763808588, sub-774672354, sub-791857600, sub-795770029, sub-803390283, sub-811322604,
sub-813701555, sub-817060743, sub-820866111, sub-821469659). Light-only controls: the 6 wild-type mice with
at least 50 trials per condition (sub-772616820, sub-754477355, sub-769319621, sub-800249582,
sub-800250054, sub-827809879).

**Units and classes.** Allen `good` units passing Allen's default quality control (ISI violations < 0.5,
amplitude cutoff < 0.1, presence ratio > 0.9). A unit's class is its brain area (Allen structure acronym)
crossed with its waveform group (narrow: trough-to-peak < 0.4 ms; broad otherwise). A class is used in a
mouse if it holds at least 5 non-tagged units there.

**Tagged units** (the stimulated population): on the odd-numbered square-pulse trials (5 and 10 ms), spike
count 1 to 11 ms after onset against the 10 ms before onset, one-sided Wilcoxon p < 0.001 and at least
0.3 extra spikes per trial. Tagged units are the input, never part of a response profile. A mouse with
fewer than 3 tagged units is reported and left out.

**Conditions.** Train: square pulses (5 and 10 ms, all levels). Test: the 1 s half-cosine (all three
levels pooled). A unit's response to a trial: spike rate 0 to 1 s after onset minus the 1 s before,
divided by the SD of its spike counts in 1 s windows of spontaneous activity.

**Light-only check.** The same profile is computed in the 6 wild-type mice (all units, no tagging). A class
whose median response across wild-type mice exceeds 0.5 SD in absolute value is flagged (artefact or a
visual response to the light) and dropped everywhere.

**Profile and agreement.** A mouse's response profile: per class, the median response of its non-tagged
units to the test condition. Agreement between two profiles: Pearson r over shared classes (at least 4).
Between-mouse agreement for mouse m: median r between m and the other mice of its line. Ceiling: odd
against even test trials within m.

**Copies of each mouse** (fitted on that mouse alone):
- *W, watching*: a linear dynamical model of class-averaged rates (tagged units as one more class), 20 ms
  bins, fitted to spontaneous blocks only. Stimulation is simulated by adding to the tagged class its own
  measured response time course to the test condition; W's predicted profile is the resulting change in
  each class, scaled to SD units by the same rule.
- *P, poke-learned*: kernels from the tagged class to every class, estimated from the train condition only
  (square pulses), applied to the tagged class's measured test-condition time course.
P never sees non-tagged responses to the test condition; W never sees any stimulation.

**Claims** (per mouse m, d = between-mouse agreement minus a copy's agreement with m):
- O1, watching falls short: median d_W > 0.1 and a one-sided sign test over the 13 mice p < 0.05.
- O2, poking reaches the mouse level: the 90% bootstrap interval of median d_P (mice resampled) lies
  below +0.1.
- O3, poking beats watching: r_P > r_W in at least 10 of 13 mice.

**Calibration before claims** (synthetic networks with known coupling, recorded through three of these
mice's instruments: unit counts, rates, bins; same code). (a) In a linear network whose input-to-network
links are active at rest, W must reach at least 0.8 of the ceiling; (b) in a network whose input links are
silent at rest, W must fall below 0.5 of the ceiling while P reaches at least 0.8; (c) five synthetic
"individuals" with jittered coupling must give between-individual agreement below the ceiling. If any
check fails, the study stops, as Studies 3 and 4 did, and no real response is read.

**Before freeze:** one independent review of this draft and the calibration code.

### Calibration pilot and amendment A1 (19 Nov 2026, after the pilot on a generic instrument; no mouse data read)

Pilot (`scripts/opto_calibrate.py --pilot`, `docs/figures/opto/calibration_pilot.json`): the first synthetic
"silent" network let its links fire at rest (threshold 3 resting SDs); raised to 4, a property of the
synthetic system, not of the test. Then, over five systems each: links visible at rest, W 0.76 to 0.85 and
P 0.90 to 0.97; links silent at rest, W -0.30 to 0.31 and P 0.69 to 0.96; synthetic ceilings about 1.0.
The separation is large, but checks (a) and (b) as written fail by small margins because they are
fractions of a ceiling far higher than real data will give.

**A1.** Checks (a) and (b) are replaced by verdict-level checks, which test what the claims test: two
synthetic populations of 13 individuals each (coupling jittered by 30% between individuals), one with
links visible at rest and one with links silent at rest, scored with the claim rules O1 to O3 unchanged.
Required: silent population, O1 and O3 supported and O2 met; visible population, O1 not supported. Check
(c) is kept. The pilot's synthetic systems are otherwise unchanged.

**A1 result (19 Nov 2026, pilot, generic instrument).** Visible population: O1 not supported, as required.
Silent population: W 0.04 below zero, P 0.93, O2 and O3 met, but O1 not supported (median between-individual
agreement 0.17, so W falls short of it by only 0.05, under the 0.1 margin). Check (c) passed. Reading: when
individuals differ a lot, "a copy falls short of another animal" has little room to show. O1's power depends
on how much individuals agree, which only the data will say.

**A2 (written before running).** A power sweep on the silent population: between-individual coupling jitter
0.1, 0.2 and 0.3 (0.3 already run). Purpose: state, before any mouse response is read, the between-individual
agreement below which O1 cannot be decided; if the real value falls below it, O1 is reported as undecidable,
not as failed. O2 and O3 do not depend on it.

**A2 result and A3 (19 Nov 2026, pilot).** Jitter 0.1 gave between-individual agreement -0.09 and jitter 0.2
gave 0.69: not monotonic, because each synthetic individual drew its own internal network from scratch, so
"individuals" were unrelated animals. That is a fault in the synthetic population, not in the test. A3: a
population now shares one internal network and one coupling, each jittered per individual by the same
fraction. A1's checks and claim rules are unchanged; the A1 and A2 runs are rerun under A3 (written before
running).

**A3 results (19 Nov 2026, pilot, generic instrument; all runs reported, none dropped).**

| run | population | between | W | P | O1 | O2 | O3 |
|---|---|---|---|---|---|---|---|
| A1 rerun, jitter 0.3 | visible | 0.43 | 0.77 | 0.93 | no (as required) | yes | 13/13 |
| A1 rerun, jitter 0.3 | silent | 0.68 | 0.26 | 0.96 | yes | yes | 13/13 |
| A2, jitter 0.1 | silent | 0.62 | -0.15 | 0.66 | yes | no | 13/13 |
| A2, jitter 0.3 | silent | 0.53 | -0.05 | 0.93 | no (p 0.29) | yes | 13/13 |
| A2, jitter 0.5 | silent | 0.08 | -0.10 | 0.93 | no | yes | 13/13 |

The A1 checks pass on the A1 rerun, but that is one draw. Across the four silent populations the full
pattern (O1, O2 and O3 together) is recovered once. O3 (stimulation beats watching, per animal) is
recovered every time; O1 and O2 are not reliable at 13 animals. Verdict of the pilot: as registered, only
O3 has the power to be read; O1 and O2 would be reported as underpowered unless a later amendment, made
before mouse responses are read, fixes that.

**A4 (19 Nov 2026, 17:36 UTC, written before running; no mouse data read).** Where the noise comes from:
each animal's measured profile is already near its ceiling (odd vs even trials about 1.0), so resampling
trials, the fix floated after A3, would not help and is dropped. The noise is that each agreement is a
correlation over only 12 numbers (one per class), so a copy that knows nothing can still score 0.3 by
chance. A4 keeps the time course: the profile becomes class x ten 100 ms bins over the same 1 s window, the
copies' predictions are binned the same way, and agreement is Pearson r over all class-bin cells. Claim
rules O1 to O3 and checks A1 and (c) are unchanged. Rerun on the same five populations and seeds as A3; all
results reported. If A4 does not recover the silent pattern in at least three of the four silent
populations while keeping O1 unsupported in the visible one, O1 and O2 are reported as underpowered.

**A4 result (19 Nov 2026, 17:37 UTC).** Silent pattern recovered in 1 of 4 populations again (O1 failed at
jitter 0.3 and 0.5, O2 at 0.1); visible O1 correctly unsupported. By A4's own rule, O1 and O2 are
underpowered and the class x time profile is not adopted; the registered class profile stays.

A closer look at all A3 and A4 runs shows a second problem: O3 is met in every population, **including the
visible one** (13 of 13 there too). Fitting on stimulation always helps a little, so "P beats W" does not
tell silent links from visible ones. What does separate them is the size of the gap: P minus W was 0.13 to
0.22 with visible links and 0.62 to 1.07 with silent links, in every run.

**A5 (19 Nov 2026, 17:40 UTC, written before running; thresholds chosen from the A1 to A4 pilot runs, so
they are tested on fresh seeds).** New claim O4: per animal, gap = (P - W) / ceiling; supported when the
median over animals exceeds 0.4 and its bootstrap 5th percentile exceeds 0.3. O4 becomes the primary claim;
O3 is kept but reported as non-diagnostic; O1 and O2 are kept as secondary and reported with their power.
Check on fresh seeds 1, 2 and 3 (never used before), jitter 0.1, 0.3 and 0.5 (one per seed), one visible and
one silent population each: required, O4 supported in all three silent and in none of the three visible.
All results reported.

**A5 result (19 Nov 2026, fresh seeds).**

| seed, jitter | population | between | W | P | gap (lower bound) | O4 | O1 |
|---|---|---|---|---|---|---|---|
| 1, 0.1 | visible | 0.99 | 0.82 | 0.95 | 0.13 (0.11) | no | **yes (false positive)** |
| 1, 0.1 | silent | 1.00 | 0.37 | 0.93 | 0.57 (0.49) | yes | yes |
| 2, 0.3 | visible | 0.91 | 0.87 | 0.97 | 0.10 (0.08) | no | no |
| 2, 0.3 | silent | 0.99 | -0.08 | 1.00 | 1.08 (0.93) | yes | yes |
| 3, 0.5 | visible | 0.90 | 0.84 | 0.97 | 0.14 (0.10) | no | no |
| 3, 0.5 | silent | 0.33 | 0.02 | 1.00 | 0.76 (0.56) | yes | no |

O4 passes its check: supported in all three silent populations, none of the three visible. The smallest
silent gap (0.57) and the largest visible gap (0.14) are far apart. O1 also gave a false positive when
individuals were near-identical, which confirms it as secondary. Study O's primary claim is now O4.
Remaining before the real test: the same calibration on three mice's real instruments (their units, rates
and trial counts), then one independent review, then freeze.

### A6: calibration through real instruments (19 Nov 2026, 17:54 UTC, written before running)

Data are being cached locally (`scripts/opto_cache.py`, `data/cache/opto`, never committed): QC units'
metadata and spike times in spontaneous blocks and the optogenetic block only. The instrument of a mouse is
its QC units, its tagged units, its classes, its units' firing rates, its spontaneous blocks and its trial
counts. Finding the tagged units reads spikes 1 to 11 ms around the odd square-pulse onsets, which the
registration already counts as part of the input; no test-condition (half-cosine) response and no
non-tagged response to any light is computed before freeze.

Instruments: the first registered mouse of each line, sub-769360771 (Vip), sub-776061236 (Pvalb),
sub-763808588 (Sst). Through each, two synthetic populations (13 individuals, one shared network and
coupling jittered 30%, trials interleaved at random with 1.7 to 2.5 s between onsets, units at the mouse's
own firing rates) with links visible or silent at rest, scored by `nematica/opto/real.py:analyse`, the code
the real test will use (`scripts/opto_instrument_cal.py`). Pass: O4 supported in the silent population and
not in the visible one, for each of the three instruments. If any instrument fails, the study stops before
any response is read, and that is reported. Seed 20261120, never used before.

**A6 first run (17:55 UTC), instrument sub-769360771 only.** Visible: gap 0.10 (O4 not supported, as
required). Silent: W -0.01 but **P -0.78**, gap -0.48, O4 not supported. Check failed. Cause, found from
the real trial timing (start-to-start 1.69 to 2.18 s; end of one light to the next onset as little as
0.69 s): the registered baseline, the 1 s before onset, often contains the end of the previous trial's
light and its response, so after a half-cosine or a 10 Hz train the baseline is inflated and the
"response" comes out negative. P, learned on these contaminated square-pulse trials, learned the wrong sign.
This is a flaw in the registered response definition, caught by calibration as intended; no real response
was read.

**A7 (17:56 UTC, written before rerunning; no real response read).** (1) Baseline: the 0.24 s before onset
(12 bins), which ends every trial at least 0.45 s after any earlier light, for unit responses, profiles and
the copies' courses; the 1 s response window is unchanged. (2) Synthetic systems use the mouse's own trial
order and timing, including the 10 Hz trains (ten bins at 4 resting SDs), instead of an invented schedule.
A6's pass rule is unchanged and is rerun on all three instruments with the same seed.

**A7 result (18:00 UTC), instrument sub-769360771.** Visible: gap 0.12 (not supported, as required).
Silent: W -0.02, P 0.75, gap 0.54 but its bootstrap lower bound 0.23 is under 0.3, so O4 not supported.
Check failed again, now narrowly: P is right on average but varies between individuals. The square pulse
is brief, so with links silent at rest it barely crosses the threshold and tells P little about a 1 s drive.

**A8 (18:01 UTC, written before running; no real response read).** P learns from all stimulation except the
test condition: square pulses and the 10 Hz trains, one set of kernels fitted to both. P still never sees
the half-cosine. Rerun on all three instruments with a fresh seed (20261121); A6's pass rule unchanged. If
it fails, the study is stopped as registered, and the failure and its causes are what is reported.

**A8 result (18:08 UTC, seed 20261121).** Each instrument was first run alone (sub-769360771, then
sub-776061236; both passed), then all three in one call, which is the record
(`calibration_instruments_A8.json`):

| instrument | tagged / classes | visible: W, P, gap (low) | silent: W, P, gap (low) | pass |
|---|---|---|---|---|
| sub-769360771 (Vip) | 5 / 22 | 0.80, 1.00, 0.20 (0.18) | 0.02, 0.96, 0.87 (0.51) | yes |
| sub-776061236 (Pvalb) | 26 / 23 | 0.84, 0.97, 0.14 (0.11) | 0.05, 1.00, 0.95 (0.56) | yes |
| sub-763808588 (Sst) | 13 / 21 | 0.82, 0.99, 0.17 (0.14) | 0.10, 0.99, 0.84 (0.70) | yes |

The A6 check passes on all three instruments. O1 again gave a false positive on one visible population
(sub-769360771), so it stays secondary.

### A9: run details the registration left open (18:12 UTC, written before any real response is read)

- Light-only check: wild-type mice are classed the same way with no tagging; a class name (area x
  waveform) is dropped from every mouse if the median of its profile value over the wild-type mice that
  have it exceeds 0.5 in absolute value. Classes left with fewer than 4 per mouse: that mouse is reported
  and left out.
- Between-mouse agreement uses the classes two mice share (at least 4); pairs sharing fewer are skipped; a
  mouse with no usable pair is left out of O1 and O2 but kept for O3 and O4.
- O4 uses mice whose ceiling (odd vs even trials) is at least 0.5, since a gap scaled by an unreliable
  ceiling means little; if fewer than 8 mice qualify, O4 is reported as undecidable.
- Everything runs from `scripts/opto_run.py`, which refuses to start until a line starting "Status: FROZEN" (in bold) is added here.

### A10: changes after the independent review (19 Nov 2026, 18:21 UTC, before any real response is read)

Review: `docs/OPTO_REVIEW.md`. Correction to A7: the earliest onset after a previous light is 0.44 s,
not 0.45 s (wild-type sub-772616820).
1. Units: class rates for both copies are built from each unit's counts divided by its 1 s spontaneous SD,
   and the copies' z-unit predictions are rescaled to those units before comparison with the profile.
2. NaN agreements are dropped explicitly and every claim reports its n.
3. O3 needs P > W in at least 10/13 of the mice analysed (rounded up).
4. Ceiling: c is the odd vs even r; the gap is divided by sqrt(2c/(1+c)), the best a perfect copy can reach.
   A9's 0.5 rule applies to c.
5. Classes no wild-type mouse has are kept and listed as unchecked.
6. Units whose area is empty, "grey" or "root" belong to no class.
7. Calibration adds a third population per instrument: links visible at rest but W misspecified (a shared
   slow driver of all classes and the tagged class, two lags of dynamics, and a soft saturating
   nonlinearity). Required: O4 not supported.
8. W positive control at rest: W is refitted on the first half of each spontaneous block and asked to
   predict, on the second halves, the average change of each class in the 1 s after the tagged class rises
   above 2 SD (clamped to its own average course). Rest score = r across classes. Interpretation rule: a
   supported O4 is read as "the copy fitted at rest works at rest but fails under drive" only if the median
   rest score is at least 0.5; otherwise as "W is the wrong model even at rest".
9. Robustness (reported beside O4, not replacing it): O4 without narrow-waveform classes in Pvalb mice.
10. Baseline for P: per mouse, r between the 10 Hz train's own profile and the test profile.
11. Tagging is run on the six wild-type mice now (pulse spikes only); units tagged there are false
    positives and are reported before freeze.
12. False-positive rates: 20 fresh seeds, rotating the three instruments, each with a visible, a silent
    and a misspecified-visible population. Required: O4 supported in at most 1 of 20 visible and at most 1
    of 20 misspecified populations, and in at least 18 of 20 silent ones. If not met, the study stops.
13. Framing: O4 is "the copy fitted at rest fails under drive while a copy fitted to other stimulation
    succeeds". It is not evidence of silent links by itself, and it does not use the between-mouse
    comparison; O1 and O2 carry that, as secondary claims.

**A10 smoke test and revision of A10.8 (18:30 UTC, one synthetic individual per kind, instrument
sub-769360771, seed 1; before the 20-seed run).** Rest score: 0.74 with visible links, 0.31 with silent
links, 0.26 with W misspecified. It is low in both the cases it was meant to tell apart, because with
silent links there is nothing at rest for W to capture. So A10.8's interpretation rule is withdrawn; the
rest score is reported as description only. Also seen: the 10 Hz train's own profile matched the test
profile at 0.996 with visible links, about as well as P. In a network like these, the pattern across classes
barely depends on the light's time course, so P's success is close to "the same pattern as other
stimulation". This is why A10.13 frames O4 as a statement about W (the copy fitted at rest fails under
drive), with P as the evidence that the pattern is predictable from the input at all.

**A10.12 restart (18:31 UTC).** The first 20-seed run crashed at seed 11 (silent population): a strongly
coupled synthetic individual drove a unit's rate past what a Poisson draw accepts. Synthetic firing now
saturates at about 20 times the resting rate (latent capped at 6), and all 20 seeds are rerun from the
start under the same pass rule. The partial logs of the crashed run are kept
(`docs/figures/opto/calibration_A10_prefix_*.log`); the 15 populations they completed (seeds 0 to 2 and 10
in full, seed 3 visible and silent, seed 11 visible) all came out as required: O4 supported in the 5 silent
ones and in none of the 10 visible or misspecified ones.

### A11: tagging screened for light artefacts (19 Nov 2026, 18:52 UTC, before any test response is read)

A10.11 result (`docs/figures/opto/wt_tagging.json`): the registered tagging rule tagged 0 units in five
wild-type mice and **8 units in sub-800250054**, a mouse with no opsin. Their spikes are locked to the
light's onset and to its offset (at 5 ms for 5 ms pulses, at 10 ms for 10 ms pulses), the signature of an
electrical artefact of light on the probe, and both fall inside the registered 1 to 11 ms window. The
same artefact can tag units in Cre mice.

**A11.** Tagging uses the odd-numbered 10 ms pulses only, counting spikes 2 to 9 ms after onset against the
7 ms before (same test and thresholds). This window avoids both the onset and the offset of the light. On
the wild-type mice it tags 0 units in all six. In the Cre mice it tags 4, 1, 11, 7, 28, 0, 2, 17, 28, 1, 13,
29 and 32 units (registered order), so with the rule of at least 3 tagged units, 9 mice enter the test
(sub-775876808, sub-791857600, sub-795770029 and sub-813701555 are left out). The 20-seed calibration (A10.12)
was started with instruments tagged by the old rule; it is finished and reported as is, then rerun with the
A11 instruments (seeds 20261300 + i, fresh) under the same pass rule.

**A10.12 result (old-rule instruments, seeds 20261200 to 20261219, 19:08 UTC;
`calibration_A10_0-9.json`, `calibration_A10_10-19.json`).**

| population (20 each) | O4 supported | gap, range | W, median | P, median | rest score, median |
|---|---|---|---|---|---|
| links visible | 0 | 0.05 to 0.16 | 0.87 | 0.99 | 0.68 |
| links silent | 20 | 0.84 to 1.26 | -0.08 | 0.98 | 0.01 |
| visible, W misspecified | 0 | 0.02 to 0.08 | 0.95 | 0.99 | 0.17 |

Pass (required at most 1, at least 18, at most 1). A limit worth stating: the misspecification built here
(shared slow driver, two lags, saturation) did not hurt W's agreement at all (0.95), so this check shows
that these particular departures from W's model do not produce a false O4; it cannot show that no
departure would. O1 was supported in 1 of 20 visible populations (a false positive) and O2 in all 60, so
O2 does not discriminate either.
