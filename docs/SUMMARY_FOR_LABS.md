# NEMATICA in one page

**Question.** How do you know whether an artificial brain is right? NEMATICA scores whole-brain models
of *C. elegans* (and, in a second arm, mouse visual cortex) against real animals, with every test
measured in units of **how different real animals are from each other**. A model passes a level when it
is as close to real worms as real worms are to each other: not further ("outside"), and not closer
("too typical"). Each level is checked first on calibration systems whose outcomes were written down
before running. Every test is pre-registered, amended only with dated notes, and checked by an
independent review; failed predictions are reported alongside the rest.

## Main findings so far

1. **Watching a brain does not reveal whether a copy is right; stimulating it does.** On the 113
   stimulated worms of the signal-propagation atlas (Randi et al. 2023), a model fitted to ongoing activity
   passes 3 to 5 of 6 activity tests in each of six held-out pools, yet its responses to single-neuron
   stimulation agree with real worms at 0.004 to 0.014 (real worms agree with each other at 0.087 to
   0.121). A model that also learned from stimulation agrees at 0.088 to 0.113, and is shown equivalent to
   real worms within a tolerance fixed in advance in all six pools.
2. **Forecasting is not fidelity.** On freely moving worms (copper-boundary set, Baskoylu et al. 2026),
   the model that forecasts best is too typical; letting each worm keep more of its own dynamics costs
   0.009 R² of forecasting and brings the levels onto the real-worm line (7 of 8 levels inside on every
   held-out pool in a nested check).
3. **A worm emulator, and where it fails.** One model with four ingredients (slow interacting
   brain-wide states, individuality, causal links learned from stimulation, neuron-level observation)
   passes both rest and stimulation on the atlas worms in 10 of 10 noise draws. Removing any of the first
   three breaks specific levels. But it was built on those worms: on 13 unc-31 worms it passes in 3 of 5
   draws (pre-set threshold 4), and on freely moving worms (Atanas et al. 2023) it fails at rest.
4. **A closed-loop worm.** A brain model driving a body in each held-out worm's own copper arena, with
   copper entering only through ASH, passes 9 of 10 pairwise levels and all three arena levels.
5. **Repeat stimulation.** In the atlas, a neuron stimulated again 0.6 to 2 minutes later responds at
   about half its previous response (56 pairs, 37 worms, gap-matched controls), about two thirds at 2 to 5
   minutes, and not detectably less after 5 to 10 minutes; also in unc-31 worms. About 9% of the atlas's
   identified stimulations are repeats within 5 minutes.
6. **Mouse: the recording instrument matters more than mice differ.** Recording one random network
   through five Allen mice's simulated instruments moved its measure by 1.8 between-mouse SDs. Matched
   mouse by mouse, the network has less slow memory than the mouse in 33 of 35 mice. A pre-registered test
   of "cortex carries more, slower internal state than artificial networks" (49 mice, seven network
   families) did not support any of its four claims.

## What is blocked, and why

Every public stimulated worm has been used, so the emulator cannot be confirmed on unseen animals. No
public dataset combines whole-brain imaging, targeted single-neuron stimulation and free behaviour, and no
second lab's single-neuron stimulation data with stimulation times is public. The next step in mouse
(the optogenetic blocks of the Allen Neuropixels sessions) has passed a metadata feasibility check; its
registration is being written before any response is read.

## Practicalities

Code, pre-registrations, amendments, reviews and logs: github.com/Weptune/nematica. Third-party data is
kept local and never redistributed; only summary numbers are published. The work is done by one person
with the help of an AI research assistant. Two preprint drafts exist and are available on request.
Contact: Abhinav Krishna, weptune.dev.
