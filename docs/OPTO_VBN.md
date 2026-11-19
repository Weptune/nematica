# Study V: does watching predict which way driven inhibitory cells push the brain? (registration)

**Status: FROZEN** (19 Nov 2026, written and frozen before any test-condition response of these mice was
computed; see the time in the commit "Study V: registration").

**Origin.** Study O (`docs/OPTO.md`) failed its primary claim, but an exploratory look found that in all 8
Pvalb and Sst mice a copy fitted to resting activity predicted that driving the tagged inhibitory cells
would raise most brain regions, while most fell; in its one Vip mouse most rose. Study S, meant to test
this on held-out mice, was undecided (no light-responsive units). This study tests it on a new dataset.

**Data.** Allen Visual Behavior Neuropixels (DANDI 000713), the earliest session of each mouse; spike
times cached locally, never committed. Metadata: `docs/figures/opto/feasibility_vbn.jsonl`. Light
protocol: 150 square pulses of 10 ms and 150 half-cosines of 1 s, three levels each; about 5 minutes of
spontaneous activity per session.

**What was looked at before this registration (instrument only).** Units, areas, firing rates and tagging
(`docs/figures/opto/vbn_tagcount.json`, Study O's A11 rule, pulse spikes 2 to 9 ms only). Tagging found 0
units in all 27 wild-type mice. Mice with at least 3 tagged units: Sst 29 of 31, Vip 10 of 23. No response
to the half-cosine, and no non-tagged response to any light, was computed.

**Pipeline.** Study O's code (`nematica/opto/real.py`): QC, A11 tagging, at least 3 tagged units, classes
(area x waveform, at least 5 non-tagged units, no empty/grey/root area), at least 4 classes, test condition
the half-cosine (all levels), A7 baseline (0.24 s), unit response in units of its 1 s spontaneous SD,
profile = class medians, the watching copy W (VAR(1) on spontaneous class rates in per-unit SD units, the
tagged class clamped to its measured test course). Light-only check: the 27 wild-type mice, a class name is
dropped everywhere if its median profile over the wild-type mice that have it exceeds 0.5 in absolute value.
One change, needed because this protocol has no 10 Hz train: the copy fitted to stimulation, P, learns from
the square pulses alone; P is descriptive here.

**Per mouse.** real_up = share of classes with profile above 0; w_up = share with W's prediction above 0;
rest_r = median over classes of the correlation at rest between the tagged class's rate and the class's.

**Claims** (one-sided sign tests, p < 0.05, ties dropped; n reported):
- V1, driving Sst cells lowers most regions: real_up < 0.5 in Sst mice.
- V2, watching predicts the wrong direction: w_up > real_up in Sst mice.
- V3, Sst cells move with the brain at rest: rest_r > 0 in Sst mice.
- V4, driving Vip cells raises most regions: real_up > 0.5 in Vip mice.
- V5, the error is specific to Sst: (w_up - real_up) larger in Sst than in Vip mice, one-sided Mann-Whitney,
  p < 0.05.
If fewer than 8 mice of a line enter, that line's claims are undecided.

**Robustness (reported beside V1 and V2, not replacing them):** visual-cortex classes only (areas starting
VIS); broad-waveform classes only (narrow classes may hold untagged cells driven by the light directly).

**Descriptive:** W, P and between-mouse agreement as in Study O.

**Code:** `scripts/opto_vbn.py`, which refuses to run unless this file's status line says FROZEN. No new
independent review: the pipeline is Study O's reviewed code; the new parts are the counts and tests above.
