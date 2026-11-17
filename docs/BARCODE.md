# Study 4: many repeats of a controlled stimulus (draft v0.1, 17 Nov 2026, NOT frozen)

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
