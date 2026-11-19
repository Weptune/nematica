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
