# Study 4 notebook: many repeats of a controlled stimulus (Allen OpenScope Barcoding)

Every run, failure, review and decision, with UTC times (from the clock). Strategy behind it:
`docs/STRATEGY_2026-11-17.md`. No registration yet: by the strategy's order, feasibility comes first,
then calibration, then the claims.

## 17 Nov 2026

### Go-ahead and first look (14:51 to 14:54 UTC)

- The user approved the strategy ("yes, go ahead"): option A (this study, gated) and option C (a short
  preprint draft, shown before anything is shared).
- Dataset: DANDI 000563, "Allen Institute Openscope - Barcoding", CC-BY-4.0, 94 files. Per mouse there is
  one `_ogen.nwb` file (units and stimulus tables) and one file per probe. Third-party data stays local;
  only summary numbers are committed.
- First file read (metadata only, sub-692990): `RepeatFFF_presentations` holds 43,200 frames. That is 90
  repeats of 480 frames at 60 Hz (8.007 s), back to back (start gaps 8.0066 to 8.0234 s), in one block.
  The frame sequence is identical between repeats (a binary full-field flicker, values -1 and 1). A 240 s
  non-repeating flicker (`UniqueFFF`) sits in blocks before and after. `invalid_times` holds one empty
  interval.
- Feasibility F1 over all 14 sessions started at 14:54 (`scripts/barcode_feasibility.py`, metadata only).
  Stop rule from the strategy: stop if fewer than 10 mice have at least 50 valid repeats.

### Feasibility F1 passes (15:10 UTC)

All 14 sessions read without error (`docs/figures/barcode/feasibility.json`, metadata only):
- every mouse has 90 repeats of the 8.007 s flicker (480 frames at 60 Hz), all valid (no overlap with
  invalid intervals), the frame sequence identical across repeats, back to back in one block;
- units passing Allen's QC (good, ISI violations < 0.5, amplitude cutoff < 0.1, presence ratio > 0.9): 751
  to 1,158 per mouse; visual cortex 41 to 554 (median 242), thalamus 65 to 317, hippocampus 66 to 357;
- spike-time arrays to download: 14.2 GB in all (0.78 to 1.10 GB per mouse).

The stop rule (fewer than 10 mice with at least 50 valid repeats) is not met: 14 of 14 have 90. Study 4 goes
on to calibration. Next: cache the spikes of the repeated and unique flicker blocks (caching only, no
statistic computed), then write the calibration criteria before any calibration run.

### Calibration criteria written; prefetch running (15:10 to 15:12 UTC)

- Prefetch (`scripts/barcode_prefetch.py`) started at 15:10: repeated and unique flicker spikes, all good
  units with area and QC, running speed; caching only.
- `docs/BARCODE.md` v0.1: calibration v4 criteria (K1 to K4) and the eligibility rule, committed before the
  calibration run (`scripts/barcode_calibrate.py`). A caution is recorded in the draft: through the
  exponential spike model, additive network activity becomes multiplicative firing, so "gain-type" is
  defined on the network's own activity.

### Calibration v4: M1 and M2 are eligible, the drive exponent is not (15:29 UTC)

96 runs (`docs/figures/barcode/calibration.json`, `calibration_runs.jsonl`); criteria as written in v0.1
before the run.
- **K1 passes** at every instrument: Spearman of M1 with the true internal share 0.97, 0.97, 0.97 and 0.92
  (median, fastest, slowest, noisiest).
- **K2 passes** at every instrument: M2 higher at the slower internal timescale in 8 of 8 pairs everywhere.
- **K3 and K4 fail.** The drive exponent b could not be estimated in 33 of 96 runs. Where it could, additive
  systems gave values up to 244, and its ordering with gain size was negative (Spearman -0.88 to -0.24).
  Cause: the 20 windows are 20 bins each, shorter than the internal timescale, and centring within each
  window removes the slow internal part. This was a design error in the criteria; it is not repaired here,
  because a repair chosen after the result would be a forking path. b is not eligible.
- Only 1 of 96 synthetic recordings reached the instrument tolerance (as registered, reach was reported,
  not required).

**By the eligibility rule, M1 and M2 can carry Study 4's claims, and the drive exponent cannot.** Next:
choose the headline claim (at most two), written to M1 and M2. Prefetch of the 14 sessions is still running.

### Headline claim chosen: the hierarchy profile; draft v0.2 (15:30 to 15:40 UTC)

- The user chose the hierarchy claim (internal share rising from thalamus to visual cortex to
  hippocampus, and whether networks show the same rise across depth).
- Metadata only: area names carry cortical-layer suffixes (`VISp5`, `VISpm2/3`), which are now removed
  before assigning levels. QC units per level, before the inclusion rule: visual thalamus 30 or more in 10
  mice, VISp in 9, higher VIS in 12, hippocampus in 14. Mice with 4 levels: 5; 3 levels: 7; 2 levels: 2.
- From calibration v4, the M1 range across the four instruments for the same synthetic system is 0.03 to
  0.29 (0.16 at share 0.4, slow internal state). So a rise across brain regions could partly be an
  instrument effect, and the draft adds two controls: an instrument-only reference R0, and recording each
  network depth at the matching level's instrument.
- `docs/BARCODE.md` v0.2 holds the claims H1 (premise) and H2 (headline), with decision rules. Next: the
  pipeline, a dry run, the clip pilot, then an independent review before freezing.
