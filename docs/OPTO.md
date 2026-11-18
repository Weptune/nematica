# Study O: the stimulation test in mouse cortex (Allen optotagging)

Status: **feasibility passed (metadata only), narrowly; registration not yet written**. Written 17 Nov 2026 (UTC) before any optogenetic table or
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
