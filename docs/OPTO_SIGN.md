# Study S: does rest-time co-activity predict the sign of a driven cell's effect? (registration)

**Status: FROZEN** (registration v1, 19 Nov 2026, 19:49 UTC, written before any data of these mice was cached; frozen as written, 19:51 UTC).
Origin: the exploratory follow-up at the end of `docs/OPTO.md` (Study O). There, in all 8 Pvalb and Sst
mice, the copy fitted to resting activity predicted that driving the tagged inhibitory cells would raise
most classes, and most classes fell instead; in the one Vip mouse most rose. That was found after looking,
so it is tested here on mice Study O never used.

**Mice.** The 15 Cre mice with an optogenetic table that Study O did not use (45 trials per condition):
Sst sub-699733573, sub-703279277, sub-734865729, sub-735109599, sub-738651046, sub-744915196,
sub-763236006, sub-763884096; Pvalb sub-707296975, sub-726170927, sub-739783158, sub-757329617; Vip
sub-730760263, sub-732548371, sub-745276220.

**Pipeline: Study O's frozen code, unchanged** (`nematica/opto/real.py` at commit 2f1f92e): QC, tagging by
A11 (odd 10 ms pulses, 2 to 9 ms), at least 3 tagged units or the mouse is left out, classes (area x
waveform, at least 5 non-tagged units, no area/grey/root), Study O's light-only drop list (VISp narrow,
VISmma narrow), test condition the half-cosine, A7 baseline, the watching copy W fitted on spontaneous
blocks.

**Per mouse.** real_up = fraction of classes whose measured profile value is above 0. w_up = fraction of
classes whose W-predicted value is above 0. rest_r = median over classes of the correlation, at rest, between
the tagged class's rate and that class's rate.

**Claims** (over the Pvalb and Sst mice that enter; n reported):
- S1, driving them suppresses: real_up < 0.5 in a one-sided sign test, p < 0.05.
- S2, watching predicts the wrong direction: w_up > real_up in a one-sided sign test, p < 0.05.
- S3, they co-fluctuate at rest: rest_r > 0 in a one-sided sign test, p < 0.05 (the premise of S2).
Ties (exactly zero) are dropped, as in Study O. With 12 possible mice, a sign test needs at least 10 of 12 (p 0.019); 9 of 12 is p 0.073.

**Reported only.** The same three numbers for the Vip mice (expected: real_up above 0.5, from Vip cells'
known inhibition of other inhibitory cells; with 3 mice nothing is claimed). Study O's W, P and gap for these
mice, as a description.

**Caveats fixed in advance.** The light alone moved narrow visual classes upward in wild-type mice (+0.3 to
+0.5 SD below the drop bar), which works against S1, not for it. If fewer than 8 Pvalb and Sst mice enter,
S1 to S3 are reported as undecided.

**Code:** `scripts/opto_sign.py`, which refuses to run unless this file's status line says FROZEN. No
independent review: this test adds three counts to a pipeline that was reviewed and frozen for Study O.

## Result (19 Nov 2026, 20:37 UTC; `docs/figures/opto/sign_result.json`): undecided

Only 1 of the 15 mice had at least 3 tagged units (sub-763884096, Sst: 3 units; real_up 0.43, w_up 0.67,
in the predicted direction, but one mouse decides nothing). The other 14 had 0 or 1. As registered, with
fewer than 8 Pvalb and Sst mice, S1 to S3 are undecided.

**Why, checked afterwards on tagging only (no response read):** with looser tagging windows and thresholds
(2 to 4.5 ms after onset, at least 0.3, 0.2 or 0.1 extra spikes), these 15 mice still give 0 to 2 units
each, while Study O's mice give 3 to 38 and the wild-type mice 0 to 1. In these sessions the light
reached almost no recorded cell, so this dataset holds no second set of mice for the test. A miss in
planning: tagging counts are part of the instrument and could have been checked before registering; they
were not.
