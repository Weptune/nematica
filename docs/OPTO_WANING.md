# Study W: asked again and again, does a mouse neuron's answer fade? (registration)

**Status: FROZEN** (21 Nov 2026, 05:29 UTC; written, reviewed and frozen before any response of any unit was looked at as a
function of trial order)

**Why.** The Waning, question VI on the home page: in the worm atlas a neuron poked a second time, 0.6 to 2
minutes after the first, answers at about half its first answer (0.47, interval 0.34 to 0.64; 56 pairs in 37
worms; README "Light or activity: what tires a worm neuron?"). The atlas cannot say whether the neuron tires
or the light tool does: every poke delivers both, and the answer is read through calcium. The mouse
recordings of Study V (`docs/OPTO_VBN.md`) differ in the one way that matters here. The driven cells' own
spikes are recorded, so their answer to the light (tool and cell together) can be read apart from what
happens in their neighbours. This study asks the worm's question of a second
animal and uses that handle. It cannot explain the worm's fade and does not try to.

**Novelty check (21 Nov 2026, before design; three searches).** That channelrhodopsin tires is textbook: peak
currents fall with repeated light and recover in the dark over about 5 s (Boyden et al. 2005), and one study
reports optogenetic response amplitude falling within the first 5 minutes of a session, attributed to the
channel (eNeuro 2019, 10.1523/ENEURO.0229-18.2019). No trial-by-trial analysis of the Allen optotagging block
turned up: the Allen tutorial averages over trials, and arXiv 2611.15606 counts modulated units. So W1 checks
something expected of the tool, in this dataset. W2, whether the neighbours' answer fades faster than the
driven cells' own, was not found. Both are narrow and descriptive.

**Data.** The 39 mice of Study V (29 Sst, 10 Vip), the same cached spike times, tagging rule (A11: odd-numbered
10 ms pulses, spikes 2 to 9 ms after onset) and classes (area by waveform). Every mouse has at least 3 driven
units (twelve have 3 to 7). In every one of them the light
block is 300 trials, 1.68 to 2.19 s apart, 9.5 to 9.7 minutes long: 150 pulses of 10 ms and 150 half-cosines
of 1 s, interleaved, each at three light levels with 50 trials per level (the levels differ between mice).

**What has been seen.** The trial tables (times, kinds, levels). From Study V and P: which units are driven,
every mouse's class profile over all 150 half-cosines, its split-half reliability (medians 0.89 and 0.91),
and the copies' agreement. **Not seen:** any unit's response as a function of its place in the block, in any
form. The calibrations below read no response to light.

**Measures** (`nematica/opto/waning.py`). Thirds are taken within each light level, so both ends of the block
hold the same mix of levels.
- **The driven units' answer to a brief pulse.** Per mouse, the driven units' summed extra spikes 2 to 9 ms
  after a 10 ms pulse (minus the 7 ms before), on the even-numbered pulses only, because the tagging rule
  chose the units on the odd-numbered ones. *Fade:* the last third of those trials over the first third
  (23 to 25 trials each).
- **The split, on the 1 s half-cosines** (`waning.split`). *Driven:* the driven units' summed spikes in the
  1 s minus their rate in the 0.24 s before, last third over first third (48 trials each). *Neighbours:*
  the class profile of the first and of the last third, each projected on the profile of the middle third
  (54 trials), which shares no trial with either; last over first. *Beyond:* the neighbours' ratio over the
  driven ratio, below 1 when the neighbours' answer fades faster than the recorded driven units' own.
  **Two versions of the profile, both required** *(from the review)*: Study V's, per class the median over
  its units of the mean response in spontaneous SD units; and per class the summed change as a fraction of
  the class's own summed rate just before the trials of that third. If the neighbours' resting rate drifts
  over the block, a steady push by a fixed fraction reads as a fade in the first version and not in the
  second; a steady push by a fixed number of spikes does the reverse. Units with no spread in their
  spontaneous counts are dropped from the first version, as in Study P.
- A mouse has no ratio when its early answer is not positive (or, for *beyond*, when the driven ratio is not
  positive); it is left out of that measure and counted. A late answer that has reversed gives a ratio at or
  below 0 and counts as below 1.

**Claims** (all 39 mice together, not either line alone; one-sided sign tests over mice, p < 0.05, ties
dropped, no correction across the three claims; undecided with fewer than 20 mice defined;
`scripts/opto_waning.py`, run once).
- **W1a, the answer fades:** the driven units' fade to brief pulses lies below 1.
- **W1b, the late third stays above 0.64 of the early third.** 0.64 is the top of the worm's interval, which
  is a second answer over a first, so the two numbers are neighbours and not the same quantity; a steady
  fall to half by the end of the block would read 0.64 here. If W1b fails, that is not evidence of a fade
  like the worm's.
- **W2, the neighbours' answer fades faster than the recorded driven units' own:** *beyond* lies below 1 in
  both versions. If only one version says so: undecided, a fade cannot be told from a drift in the
  neighbours' resting rate. If neither: "no sign of it", next to how often the calibration caught a planted
  fade; and "follows the driven units within a quarter" only if the 95% intervals of both medians
  (resampling mice) lie inside 0.8 to 1.25 and that of the neighbours' resting rate, late over early, inside
  0.9 to 1.1. **If W2 holds while the driven units are at their ceiling** (median over mice of their answer
  at the lowest light level over that at the highest above 0.9), it is reported with the rider that a
  weakening of the light's effect, hidden by the ceiling, cannot be excluded.

**Reported without a claim.** Each line on its own (Sst, Vip). The pulse fade at each light level. The driven
units' fade on the half-cosines measured from spike times. The neighbours' ratios alone. The neighbours' and
the driven units' resting rates before the trials, last third over first. The driven units' answer at the
lowest light level over the highest, for pulses and half-cosines (the ceiling check; it uses no trial
order). The first two even-numbered pulses against what the next thirteen say to expect at the same light
levels, pooled over mice, with an interval: the thirds are blind to a drop that is over within a few trials
(one doubled first answer moves the fade from 1.00 to 0.96).

**Limits written now.**
- A different animal, a different light tool (channelrhodopsin, not GUR-3/PRDX-2), light every 2 s and not
  every 0.6 to 2 minutes, spikes and not calcium. Nothing here can say why the worm's answer halves.
- In the mouse the driven unit's own answer still mixes tool and cell. The split is between that mix and
  everything after it.
- *(Review.)* **The recorded driven units are a chosen sample of the lit cells.** The neighbours hear every
  cell that carries the channel; the driven ratio comes only from units that answered strongly enough to be
  tagged, the ones most likely to be at their ceiling. If the light's effect weakens in all lit cells while
  the tagged ones stay saturated, W2 would read "fades faster" with nothing after the driven cells having
  changed (reviewer's synthetic case: *beyond* 0.74, called 8 of 8). A step from driven spikes to neighbours
  that is steeper than proportional does the same. Hence the ceiling check and the wording "the recorded
  driven units".
- *(Review.)* **W1 describes units that answered across the whole block.** A unit that stopped answering
  early is less likely to be tagged at all, which leans the fade towards 1 (reviewer's synthetic case: 0.72
  measured on tagged units against 0.64 over all lit units). And with roughly one spike fitting in the 7 ms
  window, a saturated unit cannot show how much the light's effect has weakened.
- Place in the block is also time. A slow change in the animal's state over these ten minutes, at the end of
  a long session, or a loss of spikes as the probe drifts, would read as a fade or as its opposite, with no
  use involved. These mice have no unlit control; the resting rates are a partial check, and they are not
  free of light themselves (the window starts 0.44 s or more after the light before it).
- Every answer but the very first follows other light by 2 s, and the very first answer to light is in no
  measure: the first pulse is odd-numbered and spent on choosing the units, the block opens with a
  half-cosine in 15 of 39 mice, and 1 to 9 light trials come before the first even-numbered pulse.
- A fade that only delays spikes past 9 ms would read as a fade in W1.
- The split's calibration plants effects into 4.8 minutes of spontaneous activity recorded 66 minutes before
  the light block, with other stimuli in between; the real block lasts 10 minutes. Every calibration run
  reuses the same 39 backgrounds, so its runs share one draw of the slow background.

**Calibration** (before the freeze).

*The fade of the driven cells* (`scripts/opto_waning_cal.py`, `docs/figures/opto/waning_cal.json`). Synthetic
driven units with a known fade, on each mouse's own light schedule, levels, number of driven units and their
resting rates; then the tagging rule and the measure, unchanged. Two sizes of answer, 20 runs each, so 40 runs
per row; 35 to 39 synthetic mice kept at least 3 tagged units.

| planted (late third over early) | measured, brief pulses | measured, half-cosines | "fades" called | "above the worm" called |
|---|---|---|---|---|
| none (1.00) | 0.99 to 1.00 | 1.00 | 0 of 40 | 40 of 40 |
| falls to 0.8 by the end (0.86) | 0.86 | 0.86 to 0.87 | 40 of 40 | 40 of 40 |
| falls to 0.5 by the end (0.64, the worm's top) | 0.64 | 0.64 | 40 of 40 | 1 of 40 |

*The split* (`scripts/opto_waning_cal2.py`, `docs/figures/opto/waning_cal2.json`; rerun in full with the final
code after the review). A known effect planted into each mouse's own spontaneous recording, where no light
was shown: 150 pretend trials 1.9 s apart with the mouse's own sequence of levels. Driven units gain spikes,
each class of neighbours is pushed down or up by its own link, the driven answer falls to `fd` of its start
and the links to `fn` of theirs; then `waning.split` and the registered rule, unchanged. Three link sizes;
the faintest gives class profiles less steady (split-half 0.72 to 0.84, medians per row) than the real ones
(0.89 and 0.91), the other two as steady or steadier (0.91 to 0.98). 6 runs of 39 mice per link size, so 18 per row.

| driven falls to | links fall to | true *beyond* | measured, first version | measured, second version | "fades faster" | "follows within a quarter" |
|---|---|---|---|---|---|---|
| 1.0 | 1.0 | 1.00 | 0.98 to 1.01 | 0.99 to 1.01 | 0 of 18 | 18 of 18 |
| 0.6 | 1.0 | 1.00 | 1.01 to 1.03 | 1.00 to 1.02 | 0 of 18 | 18 of 18 |
| 1.0 | 0.8 | 0.86 | 0.84 to 0.88 | 0.84 to 0.86 | 18 of 18 | 0 of 18 |
| 1.0 | 0.6 | 0.71 | 0.71 to 0.72 | 0.71 to 0.72 | 18 of 18 | 0 of 18 |
| 0.6 | 0.6 | 0.71 | 0.70 to 0.74 | 0.70 to 0.71 | 18 of 18 | 0 of 18 |

(Measured: the median over runs, at each of the three link sizes.) Rows added by the review, middle link size,
6 runs each. *Drift* is the neighbours' resting rate at the end of the block over its start, with nothing
fading unless said; a *fixed-fraction* link removes or adds a share of the spikes there are, a *fixed-number*
link a set number whatever the rate.

| case | first version | second version | resting rate reads | "fades faster" | undecided | "follows" |
|---|---|---|---|---|---|---|
| drift to 0.8, fixed-fraction links | 0.88 | 1.03 | 0.86 | 0 of 6 | 6 | 0 |
| drift to 1.2, fixed-fraction links | 1.12 | 0.97 | 1.13 | 0 of 6 | 0 | 0 |
| drift to 0.8, fixed-number links | 0.94 | 1.10 | 0.86 | 0 of 6 | 2 | 0 |
| drift to 1.2, fixed-number links | 1.04 | 0.89 | 1.13 | 0 of 6 | 6 | 0 |
| links fall to 0.8 while the rate drifts to 1.2 | 0.98 | 0.85 | 1.13 | 0 of 6 | 6 | 0 |
| links fall to 0.8, fixed-number links, no drift | 0.86 | 0.85 | 1.00 | 4 of 6 | 2 | 0 |
| nothing fading, background played backwards | 0.99 | 0.98 | 1.00 | 0 of 6 | 0 | 6 |

So: the measures return what was planted. A fade of the driven units alone is not mistaken for a fade of the
links. Links that lose a fifth by the end of the block are caught in 18 of 18 runs when they act by a fixed
fraction and in 4 of 6 when they act by a fixed number. **A drifting resting rate with nothing fading fools
one version or the other, as the review said, and never both: "fades faster" was called in 0 of 24 such
runs, and a real fade hidden by an upward drift came out undecided, not as "follows".** At the faintest
size a mouse had no ratio in at most 3 of 234 mouse-runs per row. The planted links are the same for every
unit of a class; real links need not be. No saturation of the driven units is planted: that case rests on
the ceiling check and its rider.

## Review before the freeze (independent agent, 20 Nov 2026; it read no response by trial order)

1. **Blocking, accepted.** The neighbours' answer was a spike difference over a fixed spread, so a steady
   fractional push on a resting rate that drifts down read as a fade while the driven measure stayed at 1
   (reviewer's synthetic: *beyond* 0.86, "fades faster" called 8 of 8), and an upward drift could hide a real
   fade. **Fixed:** W2 now needs two versions of the profile that fail in opposite directions under drift,
   the neighbours' resting rate is reported and gates "follows", and the calibration has drift rows.
2. **Accepted.** The tagged units are a chosen sample of the lit cells and the likeliest to be at their
   ceiling. W2 is worded for "the recorded driven units", a ceiling check that uses no trial order is
   registered with its rider, and the limit is stated.
3. **Accepted.** Tagging over the whole block favours units that kept answering. Stated as a limit; W1b is
   retitled to what it tests, and a failed W1b is said not to be evidence of a worm-like fade.
4. **Accepted.** The first pulses held a different mix of light levels from the rest. They are now compared
   with what later pulses at the same level say to expect, and the text says the very first answer to light
   is in no measure.
5. **Accepted.** A late answer that has reversed counts as below 1 and is no longer dropped; W2 has one
   outcome, not two flags that could both be set.
6. **Accepted.** The limits now say that every calibration run shares the same 39 backgrounds, recorded 66
   minutes before the light. Drift, fixed-number links and a reversed background were added, and the whole
   split calibration was rerun with the final code (6 runs per link size where the first pass had 20).
7. **Accepted.** 23 to 25 trials, not 24; "the pulse fade at each light level"; the claims are about the
   pooled set, with no correction across the three. The pulse calibration leaves out synthetic mice with
   fewer than 3 tagged units; the registered run needs no such rule, since every real mouse has at least 3.
8. **Accepted.** The run script prints nothing until the result file is written, and was dry-run end to end
   on three synthetic mice that share only trial tables, unit lists and resting rates with real ones
   (`scripts/opto_waning.py --dry`). Probe drift and the light before the resting window are in the limits.

Checked by the reviewer with no defect found: the thirds, the even-numbered rule against the tagging rule,
the trial order passed to the split, the trial tables of all 39 mice, the baseline windows, and that the
sequence of levels and kinds differs in every mouse.

## Result (21 Nov 2026; the registered run, once)

`docs/figures/opto/waning_result.json`. All 39 mice have every ratio.

- **W1a holds: the answer fades, a little.** The driven units' answer to a brief pulse in the last third of
  the block over the first third: median 0.978 (95% interval 0.954 to 0.995); below 1 in 27 mice, above in 9,
  exactly 1 in 3 (sign test on the 36, p 0.002). The lowest mouse reads 0.78.
- **W1b holds.** The ratio is above 0.64 in 39 of 39 mice.
- **W2 holds, in both versions, and the ceiling rider does not apply.** The neighbours' ratio over the driven
  units' own: 0.90 (0.82 to 0.97), below 1 in 27 of 39, p 0.012; as a fraction of the resting rate 0.91
  (0.87 to 0.96), below 1 in 31 of 39, p 0.0001. The driven units answer the lowest light level at 0.42 of
  the highest (0.47 for pulses) while the light itself is at 0.59, so they are not at their ceiling.

Reported without a claim: the driven units on the half-cosines, 0.99 (0.97 to 1.01); the neighbours' ratio
alone, 0.89 in both versions; the neighbours' resting rate, late over early, 1.00 (0.99 to 1.02); the driven
units' resting rate 0.97 (0.92 to 1.04); the first two even-numbered pulses against the next thirteen at the
same levels, 1.01 (0.96 to 1.06); the pulse fade by light level, 0.99, 0.98, 1.00. By line: Sst (29 mice)
pulses 0.98, *beyond* 0.91 and 0.95 (p 0.031 and 0.001); Vip (10 mice) pulses 0.96, *beyond* 0.68 and 0.71
(below 1 in 7 and 8 of 10; p 0.17 and 0.055).

## After the result (21 Nov 2026; not registered)

`scripts/opto_waning_control.py`, `docs/figures/opto/waning_control.json`. These were thought of only once the
result was in, and the first of them should have been in the registration: Study V had already shown that
the light alone moves the cortex of mice that carry no channel.

1. **The light alone.** The neighbours' measure in the 27 wild-type mice, where nothing is driven. The
   response to the light alone is less than half the size (0.17 SD per class against 0.41 in Sst and 0.43 in
   Vip mice), far less repeatable (split-half 0.60 against 0.89 and 0.91), and mostly a rise (66% of classes,
   against 12.5% in Sst and 73% in Vip mice). Late third over early third: 0.86 (0.62 to 1.10) and, as a
   fraction of the resting rate, 0.76 (0.64 to 0.99); below 1 in 16 and 18 of the 27 mice (p 0.22 and 0.06;
   the two mice with no ratio are ones whose response grew, and are counted as not below 1).
2. **The class Study V and P leave out** because the light alone moves it (VIS|n) exists in 2 of the 66 mice
   here; leaving it out changes no number above.
3. **Falling and rising classes apart** (chosen by the middle third). In the 39 mice the falling classes read
   0.89 (0.80 to 0.99; below 1 in 24 of 36, p 0.033), the rising ones 0.86 (0.65 to 1.03; 17 of 27, p 0.12).
4. **The very first flash** (found by the independent check, reproduced here). No registered measure holds
   the first answer to light. In the 24 mice whose block opens with a pulse, the driven units' answer to that
   first pulse is 1.22 times (1.17 to 1.29; larger in 21 of 24 mice) their answer to later odd-numbered
   pulses at the same light level; the second pulse reads 1.13 (1.04 to 1.21), the third 1.02 (0.96 to 1.09).
   Put the worm's way round, later answers are 0.82 of the first. In the 15 mice whose block opens with a
   half-cosine, the first pulse reads 0.97 (0.88 to 1.06). One trial per mouse.

## Independent check (separate agent, 21 Nov 2026, after the result; own code from the cached spike times)

Its scratch code is not in the repository; item 4 above reproduces its one new finding.

1. **W1 reproduced exactly** in all 39 mice. *Correction accepted:* say 27 below, 9 above, 3 ties.
2. **W2 reproduced** (0.903 and 0.911; largest per-mouse gap 0.007, from spikes that fall exactly on a bin
   edge). With windows starting at the true onset: 0.92 (p 0.027) and 0.90.
3. **How sturdy W2 is.** *Correction accepted: the fractional version passes every variant tried; the SD
   version fails 2 of 6, and the pooled effect leans on the 10 Vip mice.* With a template from every other
   trial, the neighbours' answer reads 0.95, 0.87, 0.89 over the three thirds: the fall comes between the
   first and the middle third and does not go on. First 36 trials against last 36: 0.84 and 0.87. Leaving out
   the highest light level: 0.94 (p 0.37) in the SD version, 0.89 (p 0.005) in the fractional one.
4. **The light-alone control.** Computed as the script says. *Corrections accepted:* the first interval's
   upper end was 1.03 by an accident of the resampling seed and is 1.10; the two mice without a ratio must be
   counted, which takes p from 0.038 to 0.06; Vip profiles have the sign of the light-alone response, Sst
   profiles the opposite, so in Sst mice a shrinking response to the light itself would deepen the falls, not
   lift them. The control works as a control for time only.
5. ***"Shrinks at least as much" was an overstatement* (my draft reading).** The wild-type ratio cannot be
   told apart from the neighbours' tenth, nor, in one of the two versions, from no change.
6. ***"Keep 98% of their answer, so do not tire the way the worm's does" was an overstatement.*** The 98% is
   fair for the steady state: choosing the units on any third of the block gives 0.97 to 0.98. But the first
   flash is larger by a fifth (item 4 above), and W1a itself says the answer fades.

**Reading (as corrected).** In the mouse, cells driven by light 300 times, two seconds apart, give 98% as
many spikes to a brief pulse in the last third of the block as in the first: a small, reliable fade, far from
the worm's halving. That measure leaves out the first flashes. In an unregistered look at the 24 mice whose
block opens with a pulse, the very first answer is about a fifth larger than later ones, and the drop is over
by the third pulse. Their neighbours' answer is about a tenth smaller in the last third than in the first
(more in the 10 Vip mice), gone by the middle third, while the driven units' own answer on the same trials
is 1% smaller and resting rates do not move. That tenth cannot be pinned on anything after the driven cells
tiring with use: in mice with no channel the response to the light alone also tends to shrink over the block,
by an amount these data cannot tell apart from it. The cortex may simply answer less as the ten minutes pass.

**Where this leaves The Waning.** The worm's question is not answered: nothing here can say whether the worm's
neuron or its light tool tires. What is added is a second animal. With a different tool and spikes read
directly, a mouse's driven cells lose about a fifth of their answer within three flashes and then hold it
for ten minutes; the worm's answer halves and takes minutes to come back. In the mouse, too, the early drop
could be the channel or the cell.
