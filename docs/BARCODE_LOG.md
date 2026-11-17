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

### Headline claim chosen: the hierarchy profile; draft v0.2 (15:30 to 15:31 UTC)

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

### Pipeline written and dry-run end to end (15:31 to 15:37 UTC)

- `nematica/barcode/inputs.py`: language models read at 4 depths in one pass (the nearest layers to 1/8,
  3/8, 5/8 and 7/8 of the depth; Pythia-14m smoke test: layers 0, 2, 3, 5), and the stacked noisy RNN
  reference.
- The flicker sequence was read from the stimulus tables (metadata). It is identical in the 3 sessions
  checked: 480 frames of luminance between -1 and 1. Saved locally as `data/derived/barcode_flicker.npy`.
- `scripts/barcode_run.py` (stages mice, ais, tests; refuses real data until frozen). The dry run works:
  - synthetic mice with internal shares rising by level gave M1 rising by level;
  - the stacked RNN's M1 rose with depth (0.64 to 0.92 at one mouse);
  - the tests stage produced H1 (holds on the synthetic rise) and H2 ("not testable", because dry
    recordings never reach the instrument).
- One fix to the draft from the dry run: R0 is counted whether or not its recordings reach the instrument,
  since synthetic systems rarely do.

### Feasibility F3, and the pre-freeze review started (15:38 to 15:40 UTC)

- **Independent review B-R1** of the draft and pipeline started at 15:38 (an agent that wrote none of the
  code; read-only; no statistic of the Barcoding spikes).
- **F3, one language model, end to end** (`scripts/barcode_lm_check.py`; Study 2's median NM1 instrument as
  a stand-in, no Barcoding activity):
  - Pythia-410M seed 1, 90 contexts; the clip pilot gave 9 tokens. Generation took 79 s; recording 4 depths
    took 25 s.
  - Peak memory was 5.6 GB, close to the machine's limit, so language models must run alone.
  - M1 by depth was 0.64, 0.75, 0.76 and 0.89. This is an AI result at a stand-in instrument, not a
    finding, and it is noted here only because the draft's claims concern depth.
  - **None of the 4 recordings reached the instrument tolerance** (recorded bins 663 to 853 against 400). If
    that repeats at the Barcoding instruments, H2 will be "not testable" under the 25% missing rule. This
    goes to the review.
- The model download for the check was removed afterwards (the disk had fallen to 1.8 GB free); 3.5 GB
  free now.

### Review B-R1: not ready to freeze (report received 15:59 UTC)

An independent reviewer (an agent that wrote none of the code; read-only; no Barcoding spike statistics, only
unit areas and QC flags, the stimulus file, the calibration, F3 and the dry outputs; scratch simulations in
`/tmp/br1/`, not kept) found six blocking problems. I checked B1 and B3 against the code myself; both are
confirmed. The rest are recorded as the reviewer stated them.

**Blocking**
- **B1. H2 can never be refuted.** The per-instance Wilcoxon test returns NaN below 6 pairs
  (`slow_run._wilcoxon`). With 12 eligible mice split 4/5/3 across instances, every per-instance p is NaN,
  so "differs" is impossible. (Study 2 had about 16 mice per instance.) Confirmed.
- **B2. The equivalence rule is miscalibrated.** With 3 clusters, the "90% interval" is about the range of
  three instance medians. In the reviewer's simulation it declared equivalence 8 to 19% of the time at a
  true offset equal to the margin (nominal at most 5%), and only 28% of the time when the true offset is 0.
- **B3. The networks' inclusion rule is about 3.75 times stricter than the mice's.** Mice need 282 spikes
  over all 90 repeats of 400 bins (about 0.0078 per bin). The recorder's scaled rule needs 200 x n/400
  spikes in the first 17 repeats (about 0.029 per bin), because Study 2's scaling assumed a mouse minimum
  counted over 17 repeats. This cuts low-rate units and pushes count per bin and rate spread out of
  tolerance. It is the likely reason for 1 of 96 calibration recordings and 0 of 4 F3 recordings reaching
  the instrument. Confirmed (`record.scaled_min_spikes`, `stream.record_stream`).
- **B4. H2 is likely "not testable" as coded:** reached points are required at every level, which is
  stricter than the draft's "at least 3"; and reach so far is near zero.
- **B5. Under a fast flicker, M1 at lag 2 confounds internal share with how fast the locked response
  decays.** The flicker's frame autocorrelation is 0.52 at 1 frame and 0.04 at 2. In the reviewer's
  simulation at a true share of 0.25, M1 was 0.33, 0.48, 0.70 and 0.98 for locked timescales of 20, 2, 1
  and 0.5 bins. Calibration v4 covered only slow locked parts, so it does not license M1 in this regime.
- **B6. Both claims are likely to restate known facts.**
  - H1 reads as "stimulus locking falls along the mouse visual hierarchy". Siegle et al. 2021 reported
    this, and hippocampus is barely flicker-driven, so its M1 sits near 1.
  - H2 reads as "language-model context sensitivity rises with depth" (Ethayarajh 2019). F3 already showed
    such a rise at a stand-in instrument, and the stacked RNN rises by construction.
  - Nothing in the design tells these explanations apart.

**Major (summarised).**
- M1: R0 is the configuration with the smallest instrument effect, and the effect depends on share.
- M2: the 0.05 threshold is misderived; the largest range is 0.29, so about 0.10 per level.
- M3: matching each depth to a level's instrument leaks brain properties into the networks.
- M4: level 0 mixes LGd with LP, and level contents vary by mouse.
- M5: mice cover different subsets of levels.
- M6: the reliability check across mice fails when mice agree.
- M7: M1 is set to 0 when there is no shared covariance.
- M8: the clip pilot is weak (9 tokens; silent fallback).
- M9: the bin cap is not applied to the starting knobs, so calibration recordings were 388 to 4,398 bins,
  not about 400.
- M10: memory and disk. Hooks keep full layer widths; the stacked RNN is out of memory at fast
  instruments; models are not cached and need about 5 GB.
- M11: missing-data gaps.
- M12: "internal" means different things in mice and language models.
- M13: instances are confounded with mouse subsets; Mamba's instances share weights.
- M14: thalamic and hippocampal bursting and theta enter C_same(2).

Minor items: layer rounding, "binary" flicker (it is continuous), area-parsing edge cases, an unpinned
DANDI version, NaN handling, pilot timing, and running speed only in the behaviour removal.

**My reading.** The study is not ready to freeze. B6 is the decisive point. By the strategy's own rule (a
novelty check before a lead becomes a study), the hierarchy claim fails: its likely answer is known on
both sides, and B5 means the measure may report response speed rather than internal state in this
regime. Fixing B1 to B5 would take a new calibration (v5), new statistics and new controls, a day or more,
to test a claim the literature probably already answers. The next step is the user's decision. No
Barcoding activity has been measured; the cache stays local.

Two lessons for the record:
- **The inclusion-rule scaling (B3) is a trap shared with earlier work.** It is correct only when the
  mouse minimum is counted over the same repeats as the AI's. For Study 3's calibration, a check shows the
  scaled rule was looser, not stricter, so it does not explain that study's low reach.
- **This is the second time an idea passed my own drafting and failed a novelty check at review.** The
  novelty search belongs before drafting claims, as the strategy note says.
