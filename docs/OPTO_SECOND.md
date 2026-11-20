# Study P: does a copy taught by light pulses answer like a second mouse? (registration)

**Status: DRAFT** (21 Nov 2026 IST; written before any between-mouse agreement of these mice was computed)

**Why.** Study V (`docs/OPTO_VBN.md`) showed that a copy built by watching gets the direction of a driven
inhibitory cell's effect wrong. The home page lists this question, The Push, as open, because "no copy has
yet been shown to answer like a second mouse". This study tests exactly that sentence, with the project's own
ruler: a copy passes when it is no further from an animal than another animal is.

**Novelty check (20 Nov 2026, before design).** That a model fitted with perturbation data predicts held-out
perturbations better than one fitted to ongoing activity is published: O'Shea, Duncker et al. 2022 (monkey
motor cortex, bioRxiv 2022.12.16.520768); "Constraining inference of across-region interactions using neural
activity perturbations" (mouse M1 and M2, bioRxiv 2025.11.20.689584); Sourmpis et al., eLife 2026
(10.7554/eLife.106827) test fitted RNNs on unseen optogenetic perturbations. A reanalysis of the Allen
optotagging epochs exists (arXiv 2611.15606, about how many units the light modulates). None of these, as far
as the search showed, judges a copy against how well a second animal's own response predicts the first, or
tests brief pulses against a slow drive of one inhibitory cell type in this dataset. So the claim here is
narrow: it extends this project's worm result (The Echo) to a second species on the same ruler. It is not a
new kind of finding.

**Data.** The 39 mice that entered Study V (29 Sst, 10 Vip), same cached spike times, same tagging, classes
and dropped class. Two mice flagged by Study V's independent check for a driven unit that is silent at rest
(sub-556021, sub-578257) are left out of the primary analysis and included in a robustness row.

**What has been seen.** From Study V: each mouse's share of classes that rose, the watching copy's predicted
share, and the agreement of W and of P with the mouse's own profile over all its classes (medians: P 0.57 in
Sst mice, 0.47 in Vip mice; W -0.06 and 0.05; split-half reliability 0.89 and 0.91). **Not seen:** any
agreement between two mice, the direction P predicts, and anything about a copy taught by other mice.
Instruments (classes, units, rates, schedules) were read to build the calibration.

**Pipeline** (`nematica/opto/second.py`, which reuses Study O and V's reviewed code unchanged).
- A mouse's answer is its class profile to the 1 s half-cosine, as in Study V.
- **P**, the copy taught by pulses: one set of kernels fitted to the mouse's own 10 ms square pulses, driven by
  the driven class's measured course under the half-cosine. **W**, the watching copy, as in Study V. **X**, a
  copy that never saw this mouse's stimulation: per class, the median of the other same-line mice's pulse
  kernels (at least 3 mice), driven by this mouse's driven-class course.
- Agreement is the correlation across classes (Study O's measure). For a mouse and each other mouse of its
  line sharing at least 8 classes: B, the agreement of the two mice's profiles on the shared classes; and the
  agreement of each copy's prediction with the mouse's profile on the same classes. Per mouse, the median over
  its partners (at least 5 partners). Direction: the share of classes a copy predicts will rise.

**Claims** (Sst mice; one-sided, p < 0.05; `second.claims`, `second.verdict`):
- **S0, there is a yardstick:** Sst mice agree with each other, B > 0 (sign test). If S0 fails, everything
  below is undecided.
- **S1, direction:** P predicts that most classes fall (share predicted to rise < 0.5; sign test).
- **S2, pattern:** P is within a quarter of a second mouse: P's agreement minus 0.75 x B is above 0
  (Wilcoxon signed-rank across mice).
- **Verdict for P.** *Like a second mouse* if S0, S1 and S2 hold. *Not like a second mouse* if S0 holds and
  either P's agreement is below B (Wilcoxon, p below the threshold fixed by the calibration, see below) or P
  predicts the wrong direction (sign test). Otherwise undecided. "Within a quarter" is the worm test's
  tolerance; a copy that passes S2 while also measurably below B still passes, as there.
- **S3, the watcher:** by the same rule, W is not like a second mouse.

**Reported beside these, not replacing them:** the same on visual-cortex classes only; broad-waveform classes
only; classes that light alone barely moves (median over the 27 wild-type mice within 0.2 SD of zero); with
the two flagged mice included. The verdict for X, and everything for the 10 Vip mice, are descriptive: in Vip
mice most of the response is the light itself (Study V's control), which a second mouse shares for free.

**What a pass would and would not mean.** P is a copy of the same mouse, read through the same instrument, and
tested on a different kind of drive; a second mouse is another animal through another instrument. A pass
says pulses teach how this mouse answers a slow drive at least as well as knowing another mouse's actual
answer. It does not say the copy is close to perfect: the split-half ceiling is reported next to every
number, and the gap between P and that ceiling stays a result in its own right.

**Calibration** (`scripts/opto_second_cal.py`; synthetic mice with known truth recorded through the 29 real
Sst instruments; no real response read). Filled in below before the freeze.

**Code:** `scripts/opto_second.py`, which refuses to run unless this file's status line says FROZEN.
