# Study 4: does internal state rise along the hierarchy, in mice and in networks? (draft v0.2, 17 Nov 2026, NOT frozen)

Strategy: `docs/STRATEGY_2026-11-17.md`. Notebook: `docs/BARCODE_LOG.md`. Order of work, each a stop point:
feasibility (passed, 15:10 entry), **calibration before any claim (this draft)**, claims, review, freeze,
run.

## Data

Allen OpenScope Barcoding (DANDI 000563): 14 mice, an 8.007 s binary full-field flicker repeated 90 times
back to back (400 bins of 20 ms per repeat), Neuropixels in visual cortex, thalamus, hippocampus and
other areas. Never analysed in this project. Feasibility: 14 of 14 mice have 90 valid repeats.

## Calibration v4 (criteria written before any calibration run)

Question: at 90 repeats of an 8 s clip, which of Study 2's and Study 3's measures can be measured reliably?
Only measures that pass are eligible for claims.

Code: `scripts/barcode_calibrate.py` (runs saved to `docs/figures/barcode/calibration_runs.jsonl`).
Synthetic systems (`nematica/persist/synthetic.py`, flat envelope, because the flicker's statistics do
not change along the clip) of 300 units, 90 back-to-back repeats, clip length set to record as about 400
bins. Recorded with Study 2's streaming recorder (with the bin cap) through the four Study 2 instruments
used in Study 3's calibration (median, fastest, slowest, noisiest NM1 mouse). No Barcoding activity is
used. Seeds 0 and 1.
- **Additive internal state:** share 0.1, 0.25, 0.4, 0.6, each at internal timescale 1 and 4 times the locked
  timescale.
- **Gain-type internal state:** a slow random gain on the locked latents (before the instrument), log-SD
  0.15, 0.3, 0.6 with timescale a quarter of the clip; log-SD 0.3 with timescale equal to the locked one.

Measures: M1 and M2 over the whole clip (lag 2, as Study 2); b, the drive exponent, from the drive-time fit
over **20 windows** of 20 bins (Study 3's fit, more windows because the clip is short and the drive
varies bin by bin rather than along the clip).

Criteria:
- **K1, internal share:** at each instrument, Spearman of M1 with the true share (additive systems, both
  timescales, both seeds) at least 0.9.
- **K2, relative timescale:** at each instrument, M2 higher at internal timescale 4 than at 1 for the same
  share and seed in at least 7 of 8 pairs.
- **K3, drive exponent separation:** at each instrument and seed, the largest b among additive runs is below
  the smallest b among gain-type runs of log-SD 0.3 or more.
- **K4, drive exponent ordering:** pooled per instrument, Spearman of b with gain log-SD (additive share 0.4
  at timescale 1 counted as 0; then 0.15, 0.3, 0.6) at least 0.8.
- Every run that yields the measure is used; instrument reach is reported but is not required (Study 3: the
  synthetic gain-type systems rarely reach the mice's white share).

Eligibility: M1 is eligible if K1 passes; M2 if K1 and K2 pass; b if K3 and K4 pass. If none is eligible,
Study 4 stops before any Barcoding activity is measured.

A caution recorded before running: through the exponential spike model, an additive fluctuation of an AI
unit's activity becomes a multiplicative change of its firing rate. "Gain-type" here therefore means a
gain on the network's own activity (before the instrument). Whether that matches what "gain fluctuations"
means in a mouse's spikes (Goris et al. 2014) is a question for the claims, not settled by this calibration.


## Claims (v0.2, 17 Nov 2026, written after calibration v4; the user chose the hierarchy claim)

Eligible measures (calibration v4): M1 (internal share) and M2 (relative timescale). The drive exponent is
not eligible. **One headline claim (H2) and its premise (H1); M2 is reported, not tested.**

**Levels** (from each unit's area, its peak channel's location, with the cortical layer suffix removed):
0 visual thalamus (LGd, LGv, LP); 1 primary visual cortex (VISp); 2 higher visual cortex (other VIS areas);
3 hippocampal formation (CA1 to CA3, DG, SUB, ProS, PoST, PRE, POST). A level counts for a mouse if at least
30 QC units pass Study 2's inclusion rule (rate at least 0.05 Hz; at least 200 spikes per 510 s of
stimulus, so 282 over the 90 repeats' 720 s); at most 480 units per level, seeded. A mouse enters if it has
at least 3 levels. Metadata counts before inclusion: 4 levels in 5 mice, 3 in 7 and 2 in 2.

**Per mouse:** M1 at each of its levels, from its 90 repeats, with units centred within each repeat; each
level's instrument numbers measured on the repeats (Study 2's instrument function). The **slope** is the
ordinary least-squares slope of M1 on level index over the mouse's levels.

**Instrument-only reference (R0).** M1 differs between instruments even for the same system: up to 0.16 in
calibration v4. So a fixed synthetic system (additive internal share 0.4, timescale equal to the locked
timescale, seed 0) is recorded at each mouse's level instruments, and its slope is the slope that the
instruments alone would give. R0 counts whether or not its recordings reach the
instrument tolerance, because synthetic systems rarely do (calibration v4: 1 of 96).

**Networks, recorded like a hierarchy:** Pythia-160M and Pythia-410M (released seeds 1 to 3 as the three
instances) and Mamba-370M (three text positions), instance = mouse rank mod 3. (Pythia-1B was dropped
before any run: reading 7/8 of its depth needs nearly the whole model in float32, which this machine's
memory cannot hold, as Study 2's amendment S8 found.) Units are taken at 4 depths, the layers nearest to 1/8,
3/8, 5/8 and 7/8 of the depth (Pythia: MLP activations; Mamba: gated SSM outputs; 480 units per depth,
seeded). A text clip follows a different 256-token context on each of 90 repeats. It is sized so that it
records as about 400 bins at the median visual-cortex instrument (pilot with the streamed recorder). **Depth
point k is recorded at the same mouse's level-k instrument**, so that network and mouse profiles pass
through the same instruments. Points are skipped where the mouse has no level k. The network's slope for
that mouse is the least-squares slope over the same levels as the mouse's.

**Reference, not counted:** a 4-layer stacked noisy random RNN driven by the flicker (layer 1 by the
flicker, each later layer by the one before; g 1.5, noise 0.1 per layer). Its internal share should
accumulate with depth by construction.

- **H1 (premise): internal share rises along the mouse hierarchy beyond what the instruments explain.**
  Per mouse, d0 = mouse slope minus R0 slope. H1 holds if the median d0 > 0.05 per level, with a one-sided
  Wilcoxon p < 0.05 over mice. (0.05 per level is the calibration's largest instrument range, 0.16, spread
  over 3 level steps.) If H1 fails, H2 is reported but cannot be read as "reproducing a rise".
- **H2 (headline): transformers and state-space models reproduce the brain's rise across their depth.** Per
  network and mouse, d = mouse slope minus network slope. The ruler is the robust SD of the mice's slopes.
  A network is **equivalent** if the 90% cluster-bootstrap interval (clusters: instances) of the median d lies
  within plus or minus 0.5 ruler units. It **differs** if the median |d| exceeds the larger of 0.5 ruler
  units and 0.05, with one-sided Wilcoxon p < 0.05 overall and within each instance, and the interval
  excluding 0; the direction is reported. **Claim H2 holds** if at least 2 of the 3 networks are equivalent
  and none differs. **H2 is refuted** if at least 2 of the 3 differ.
- Behaviour: running speed regressed out (Study 2's method); H1 and H2 reported with and without.
- Reliability check: odd against even repeats, Spearman across mice of the mice's slopes at least 0.5;
  otherwise "unreliable, not tested".
- Missing: a network recording that does not reach the instrument is excluded and counted. A mouse with
  fewer than 3 usable network points for a network is missing for that network. More than 25% missing gives
  "not testable".

Before freezing: an independent review of this draft and of the pipeline (`scripts/barcode_run.py`, to be
written), a dry run on synthetic stand-ins, and the clip pilot.
