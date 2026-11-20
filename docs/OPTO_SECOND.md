# Study P: does a copy taught by light pulses answer like a second mouse? (registration)

**Status: FROZEN** (20 Nov 2026, 19:39 UTC; written, reviewed and frozen before any agreement between two of these mice,
any direction predicted by P, or anything about X was computed; see the commit "Study P: registration")

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
and dropped class.

**One change to the pipeline (from the review before the freeze).** Units with no spread in their 1 s
spontaneous counts cannot be put in SD units. Study O and V floored their SD at 1e-9, which lets one such
unit swamp its class's mean rate and wreck the copies' predictions for that class (on synthetic mice, one
silent unit took a correct P from 0.96 to 0.99 down to 0.00 to 0.29; with the unit dropped it returned to
0.96 to 0.99). Five mice have such units: two flagged by Study V's check (sub-556021, sub-578257, a driven
unit) and three found now (sub-554013, sub-563323, sub-564012, class units). **The primary analysis drops
every such unit, in every mouse.** A mouse is left out if fewer than 3 driven units remain or a class is left
empty. Rows with the untouched pipeline are reported beside it. Two of the three newly found mice had the
lowest P seen in Study V (-0.30, -0.04), so this change is expected to raise P there; it was decided from
spontaneous spike counts alone, before any outcome of this study existed.

**What has been seen, and what that leaves open.** From Study V: each mouse's share of classes that rose,
the watching copy's predicted share, and the agreement of W and of P with the mouse's own profile over all
its classes (medians: P 0.57 in Sst mice, 0.47 in Vip mice; W -0.06 and 0.05; split-half reliability 0.89 and
0.91). **Not seen:** any agreement between two mice, the direction P predicts, and anything about a copy
taught by other mice. Instruments (classes, units, rates, schedules, spontaneous spike counts) were read to
build the calibration and by the reviewer. Because P's agreement is already known, **S2 in effect asks one
thing: whether Sst mice agree with each other by less than about 0.78.** And because the watching copy is
known to predict a rise in 26 of the 27 unaffected Sst mice, **S3 follows from Study V once S0 holds; it is a
restatement, not a new blind claim.** The blind parts are S0, S1, the yardstick's size, S4 and X.

**Pipeline** (`nematica/opto/second.py`, which reuses Study O and V's reviewed code unchanged).
- A mouse's answer is its class profile to the 1 s half-cosine, as in Study V.
- **P**, the copy taught by pulses: one set of kernels fitted to the mouse's own 10 ms square pulses, driven by
  the driven class's measured course under the half-cosine. **W**, the watching copy, as in Study V. **X**, a
  copy that never saw this mouse's stimulation: per class, the median of the other same-line mice's pulse
  kernels (at least 3 mice), driven by this mouse's driven-class course.
- Agreement is the correlation across classes (Study O's measure). For a mouse and each other mouse of its
  line sharing at least 8 classes: B, the agreement of the two mice's profiles on the shared classes; and the
  agreement of each copy's prediction with the mouse's profile on the same classes. Per mouse, the median over
  its partners (at least 5 partners). Direction: the share of a mouse's classes (all of them, not only shared
  ones; classes without a prediction are not counted) that a copy predicts will rise.
- A line's claims are undecided with fewer than 8 mice. Sign tests drop ties. A mouse left out is also left
  out as a partner and as a source for X and for the average.

**Claims** (Sst mice; one-sided, p < 0.05; `second.claims`, `second.verdict`):
- **S0, there is a yardstick:** Sst mice agree with each other, B > 0 (sign test). If S0 fails, everything
  below is undecided.
- **S1, direction:** P predicts that most classes fall (share predicted to rise < 0.5; sign test).
- **S2, pattern:** P is within a quarter of a second mouse: P's agreement minus 0.75 x B is above 0
  (Wilcoxon signed-rank across mice).
- **Verdict for P.** *Like a second mouse* if S0, S1 and S2 hold. *Not like a second mouse* if S0 holds and
  either P's agreement is below B (Wilcoxon, p < 0.01, the threshold the calibration set) or P predicts the
  wrong direction (sign test, p < 0.05). Otherwise undecided. "Within a quarter" is the worm test's
  tolerance; a copy that passes S2 while also measurably below B still passes, as there.
- **S3, the watcher:** by the same rule, W is not like a second mouse.
- **S4, the stricter bar:** P is within a quarter of the average of the other mice. For each mouse, the
  other mice's profiles are averaged class by class (median, at least 3 mice; at least 8 such classes); A is
  that average's agreement with the mouse, and P's agreement is taken on the same classes. P minus 0.75 x A
  above 0 (Wilcoxon, p < 0.01, set by the calibration), and S0 must hold. S4 does not change the verdict; it
  says whether pulses teach at least most of what the species' typical answer already tells. If S4 fails,
  the write-up says so in the same sentence as the verdict. S4 is not a guard against a poor copy: the
  calibration's wrong copy passed it.

**Reported beside these, not replacing them:** the same on visual-cortex classes only; broad-waveform classes
only; classes that light alone barely moves (median over the 27 wild-type mice within 0.2 SD of zero); the
untouched pipeline on all mice; the untouched pipeline without the five affected mice. The verdict for X, and everything for the 10 Vip mice, are descriptive: in Vip
mice most of the response is the light itself (Study V's control), which a second mouse shares for free.

**What a pass would and would not mean.** P is a copy of the same mouse, read through the same instrument,
handed the driven cells' own measured activity under the slow drive, and tested on how the other classes
follow; a second mouse is another animal through another instrument. A pass says pulses teach the pattern of
this mouse's answer to a slow drive at least three quarters as well as another mouse's actual answer gives
it, and get its direction right. It does not say the copy is close to perfect: the split-half ceiling is
reported next to every number, and the gap between P and that ceiling stays a result in its own right. Where
mice agree only weakly the pattern bar is low; in that case the direction test carries the verdict, as it
did in the calibration.

**Calibration** (`scripts/opto_second_cal.py`; synthetic mice with known truth recorded through the 29 real
Sst instruments; no real response read; `docs/figures/opto/second_cal.jsonl`, `second_cal2.jsonl`; 24 distinct
populations, 20 Nov 2026, 18:57 to 19:25 UTC; numbers below are over both files).
- **A right copy passes.** Links visible and linear, three levels of individual variation: P is called like
  a second mouse in 11 of 11 populations; with a slow shared drive that misleads watching, 5 of 5.
- **A wrong copy is caught, by direction only.** When pulses mostly teach links that the slow drive never
  uses, P is called not like a second mouse in 5 of 5: it predicted that most classes rise, and they fell.
  Its pattern agreement (0.72) stayed above the mice's agreement with each other (0.29), and it passed S4.
- **S0 is a weak guard.** Synthetic mice with no shared links still agreed slightly (0.13), because shared
  instruments and dynamics give a common pattern. S0 passed there, in 3 of 3.
- **Size of the rule.** A second mouse's own profile, blurred to sit exactly on the margin, passed S2 in 2%
  to 7% of draws (nominal 5%). A literal second mouse was called worse than a second mouse in 2.5% to 13% of
  draws at p < 0.05 (14.5% in the reviewer's rerun of the worst population) and in 0% to 3% at p < 0.01 (8
  populations, and 3% in that rerun), hence 0.01. The average of the other mice, blurred to its margin,
  passed S4 in 4% to 13% at p < 0.05 (8 populations) and 1% to 3.5% at p < 0.01 (2 populations, and 1.5% and
  2% in the reviewer's two reruns), hence 0.01.
- **Power.** A copy exactly as good as a second mouse passes S2 in 6% to 81% of draws, least when mice agree
  least. So a miss can be lack of power; that case is the verdict "undecided", not "not like".
- **What these rates are.** Each is over random draws within one fixed synthetic population. The Wilcoxon
  test treats mice as independent although two mice share their pair; the rates above are how that plays out.
- Synthetic recordings are slightly cleaner than real ones (split-half 0.93 to 0.96 against 0.89 to 0.91).

**Independent review before the freeze** (20 Nov 2026; a separate Claude agent given the draft, the code and
the calibration files, forbidden to compute any outcome; it read instruments and spontaneous spike counts
only). Nothing blocking was left open. Its points, each accepted:
1. *Blocking, fixed:* silent class units in three unflagged mice break the copies through the SD floor.
   **Corrected:** the primary analysis now drops silent units (see "One change to the pipeline").
2. *Fixed:* the calibration ranges quoted were from one file and counted 30 populations where 24 are
   distinct; the 0.02 threshold for "worse" was not supported in the worst population. **Corrected:** numbers
   recomputed over both files, threshold set to 0.01.
3. *Fixed:* "at least as well as" overstated a three-quarters margin; S4 does not guard against a poor copy;
   P is handed the driven cells' measured response. **Corrected** in "What a pass would and would not mean"
   and in S4.
4. *Fixed:* S3 is not blind, and S2 reduces to a question about the yardstick. **Corrected:** said so under
   "What has been seen".
5. *Fixed:* S4 ignored S0, its 8-class minimum was unregistered, and classes without a prediction were
   counted as predicted falls. **Corrected** in code and text.
6. *Fixed:* unstated rules (8 mice per line, ties, direction over all classes, left-out mice as partners).
   **Corrected:** stated under "Pipeline".
7. *Noted:* the Wilcoxon test's dependence between mice. **Stated** under "Calibration".
The reviewer found the class indexing, the direction test's orientation for both lines, the verdict rule,
and the absence of leaks from the light schedule, the low-light rule and the dropped class to be correct.

**Code:** `scripts/opto_second.py`, which refuses to run unless this file's status line says FROZEN.

## Result (20 Nov 2026, run once at 19:39 UTC from the freeze commit; `docs/figures/opto/second_result.json`)

All 39 mice entered (no mouse was left out once silent units were dropped). Sst mice, primary analysis, n = 29:

| claim | result | numbers | p |
|---|---|---|---|
| S0, Sst mice agree with each other | **supported** | median agreement 0.36; above 0 in 28 of 29 | 6e-8 |
| S1, P predicts that most classes fall | **supported** | P predicts 31% rise (really 12%); right side of one half in 27 of 29 | 8e-7 |
| S2, P's pattern is within a quarter of a second mouse | **supported** | P 0.60 against a second mouse's 0.36; P above the second mouse in 26 of 29 | 9e-6 |
| **Verdict for P** | **like a second mouse** | | |
| S3, the watching copy is not like a second mouse | **supported** | wrong direction (predicts 77% rise), pattern -0.07 | 6e-8, 9e-6 |
| S4, P is within a quarter of the average of the other mice | **supported** | P 0.58 against the average mouse's 0.52 | 0.0002 |

**Beside it.**
- Every robustness row gives the same verdict for P in Sst mice: visual-cortex classes only (P 0.60 against
  0.20), broad-waveform classes only (0.62 against 0.48), classes light alone barely moves (0.63 against
  0.40), the untouched pipeline (0.60 against 0.36) and the untouched pipeline without the five affected mice
  (0.62 against 0.32, n = 24).
- S4 holds in every row except the untouched pipeline on all mice (p = 0.036, above its 0.01 threshold); it
  holds there once the five affected mice are left out (p = 0.0007). So S4 depends on the silent-unit fix.
- X, the copy taught only by other mice's pulses (descriptive): 0.51 against 0.36, direction right (19%
  predicted to rise); like a second mouse by the same rule.
- Vip mice (descriptive, n = 10): P 0.48 against 0.31, like a second mouse in the primary and low-light rows,
  undecided on visual-cortex or broad-waveform classes alone. The watching copy is undecided there.

**What this says.** In Sst mice, a copy taught by brief light pulses gets right what the watching copy gets
wrong: the direction of the slow drive's effect. Its pattern across brain regions agrees with the mouse
better than a second mouse's own response does, and at least about as well as the average of the other mice.
A copy that never saw this mouse's stimulation, only other mice's pulses, also passes. By the project's
ruler, the question on the home page is answered: a copy taught by stimulation answers like a second mouse.

**What it does not say.**
- The copy is far from perfect. Its pattern agreement is 0.60 where the recording's own reliability would
  allow about 0.97. Two mice agree at only 0.36, so the ruler's bar was low here; the direction test and S4
  are what make the pass more than that.
- As registered, P's agreement was already known from Study V, so S2 only asked whether mice agree with each
  other by less than about 0.78. They do, by a wide margin.
- P is a copy of the same mouse through the same instrument, handed the driven cells' measured activity. It
  predicts how the other regions follow, for one inhibitory cell type, one rig, one session per mouse.
- A second mouse is another animal recorded through other units, which lowers its agreement for reasons that
  are not biology.

**Record keeping.** The commit that added the last calibration records says it includes the reviewer's
reruns; it does not. The reviewer's reruns were not saved to the files, and are quoted in the calibration
section from the review itself.
