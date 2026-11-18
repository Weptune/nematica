# Study O: the stimulation test in mouse cortex (Allen optotagging)

Status: **feasibility (metadata only)**. Written 17 Nov 2026 (UTC) before any optogenetic table or
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
