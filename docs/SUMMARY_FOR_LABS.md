# NEMATICA in one page

**Question.** How do you know whether an artificial brain is right? NEMATICA scores whole-brain models
of *C. elegans* (and, in a second arm, mouse cortex) against real animals, with every test measured in
units of **how different real animals are from each other**. A model passes a level when it is as close
to real worms as real worms are to each other: not further ("outside"), and not closer ("too typical").
Each level is first checked on calibration systems with known answers. Its resolution is limited: a pass
means "within about 25% of a real worm on that level", not "faithful". Tests from 2 Nov 2026 onward are
pre-registered, amended only with dated notes, and checked by independent reviews; earlier and
exploratory results are labelled as such below, and failed predictions are reported alongside the rest.

## Main findings so far

1. **Watching a brain does not reveal whether a copy is right; stimulating it does.** On the 113
   stimulated worms of the signal-propagation atlas (Randi et al. 2023), a model fitted to ongoing activity
   passes 3 to 5 of 6 activity tests in each of six held-out pools, yet its response pattern to
   single-neuron stimulation agrees with real worms at 0.004 to 0.014 (real worms agree with each other at
   0.087 to 0.121). A model that also learned from stimulation agrees at 0.088 to 0.113, and its response
   pattern is shown equivalent to real worms' within a tolerance fixed in advance, in all six pools (it
   matches less well on response size and on ongoing activity).
2. **Forecasting is not fidelity** (not pre-registered; 27 worms from one lab). On freely moving worms
   (copper-boundary set, Baskoylu et al. 2026), the model that forecasts best is too typical; letting each
   worm keep more of its own dynamics costs 0.009 R² of forecasting and brings the levels onto the
   real-worm line (7 of 8 levels inside on every held-out pool in a nested check).
3. **A worm emulator, and where it fails.** One model with four ingredients (slow interacting
   brain-wide states, individuality, causal links learned from stimulation, neuron-level observation)
   passes both ongoing activity and stimulation on the atlas worms in 10 of 10 noise draws, with
   knife-edge margins on some levels. Exploratory ablations on an earlier version suggest the first three
   ingredients each matter. But it was built on those worms: on unc-31 worms (13 meeting the test's
   requirements) it passes in 3 of 5 draws (pre-set threshold 4), and on freely moving worms (Atanas et al.
   2023) it fails on ongoing activity.
4. **A closed-loop worm** (not pre-registered; chosen among several versions). A brain model driving a
   body in each held-out worm's own copper arena, with copper entering only through ASH, passes 9 of 10
   pairwise levels and all three arena levels, though model worms still spend about four times as long
   near copper as real worms, which the population-level test is too weak to reject.
5. **Repeat stimulation** (exploratory). In the atlas, a neuron stimulated again 0.6 to 2 minutes later
   responds at about half its previous response (56 pairs, 37 worms, gap-matched controls), about two
   thirds at 2 to 5 minutes, and not detectably less after 5 to 10 minutes; a decline is also seen in
   unc-31 worms. About 9% of the atlas's identified stimulations are repeats within 5 minutes.
6. **Mouse: the recording instrument matters more than mice differ.** Recording one random network
   through five Allen mice's simulated instruments moved its measure by 1.8 between-mouse SDs. Matched
   mouse by mouse, the network has less slow memory than the mouse in 33 of 35 mice (that rule was set
   after the mouse values were known, before the network recordings). A pre-registered test of "cortex
   carries more, slower internal state than artificial networks" (49 mice; seven network families, five
   counted) did not support any of its four claims.

## What is blocked, and why

Every public stimulated worm has been used, so the emulator cannot be confirmed on unseen animals. No
public dataset combines whole-brain imaging, targeted single-neuron stimulation and free behaviour, and I
found no second lab's stimulation data with stimulation times in public archives. The next step in mouse
(the optogenetic blocks of the Allen Neuropixels sessions) has narrowly passed a metadata feasibility
check; its registration will be written before any response is read.

## Practicalities

Code, pre-registrations, amendments, reviews and logs: github.com/Weptune/nematica. Third-party data is
kept local and never redistributed; only summary numbers are published. The work is done by one person
with the help of an AI research assistant. Two preprint drafts exist and are available on request.
Contact: Abhinav Krishna, weptune.dev.
