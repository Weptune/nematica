# Study W: asked again and again, does a mouse neuron's answer fade? (registration)

**Status: DRAFT** (written before any response of any unit was looked at as a function of trial order)

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

*The split* (`scripts/opto_waning_cal2.py`, `waning_cal2.json`, `waning_cal2b.json`). A known effect planted into
each mouse's own spontaneous recording, where no light was shown: 150 pretend trials 1.9 s apart with the
mouse's own sequence of levels. Driven units gain spikes, each class of neighbours is pushed down or up by
its own link, the driven answer falls to `fd` of its start and the links to `fn` of theirs; then
`waning.split`, unchanged. Three link sizes; the faintest gives class profiles less steady (split-half 0.69 to
0.85 over runs) than the real ones (0.89 and 0.91), the other two as steady or steadier (0.88 to 0.98). 20 runs of 39 mice per row
(10 for the faintest).

| driven falls to | links fall to | true *beyond* | measured *beyond* (median; range over runs) | "fades faster" called | interval inside 0.8 to 1.25 |
|---|---|---|---|---|---|
| 1.0 | 1.0 | 1.00 | 0.97 to 1.01; 0.92 to 1.06 | 0 of 50 | 50 of 50 |
| 0.6 | 1.0 | 1.00 | 1.00 to 1.02; 0.96 to 1.13 | 0 of 50 | 49 of 50 |
| 1.0 | 0.8 | 0.86 | 0.84 to 0.88; 0.81 to 0.91 | 50 of 50 | 36 of 50 |
| 1.0 | 0.6 | 0.71 | 0.70 to 0.72; 0.66 to 0.76 | 50 of 50 | 0 of 50 |
| 0.6 | 0.6 | 0.71 | 0.72 to 0.73; 0.65 to 0.79 | 50 of 50 | 0 of 50 |

So: the measures return what was planted; a fade of the driven cells alone is not mistaken for a fade of the
links (a slight lean the other way, up to 1.13 in one run); links that lose a fifth by the end of the block
are caught every time, even at the faintest size. **"Within a quarter" is weak on its own:** a true 0.86 sits
inside 0.8 to 1.25 in 36 of 50 runs, so that phrase will always be given with the median and its interval.
At the faintest size a mouse had no ratio in 10 of 1,950 mouse-runs; at the other sizes, never. The planted effects are multiplicative and the same for every unit of a
class; real links need not be.

**Review before the freeze.**

*REVIEW*
