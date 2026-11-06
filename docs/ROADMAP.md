# NEMATICA roadmap (6 Nov 2026)

The question is what makes biological neural networks different from artificial ones. So far we
have measured one difference carefully. Worms cannot be copied by watching them: watching recovers
4 to 16% of the agreement between worms. The artificial networks we tested can be: 51 to 91%. Part
of the worm gap comes from the experiment itself (stimulation reaching neighbours).

One difference is a finding, not an answer. An answer has three parts:

1. **An atlas of differences.** Several measured axes, each judged on the same ruler (how much real
   individuals differ from each other), not only "copyable by watching".
2. **Causes.** For each axis, which biological ingredient produces it. We find out by adding
   ingredients to artificial networks until they show the worm's pattern.
3. **Generality.** Whether the same differences appear in other brains and in large modern
   artificial networks.

The work below is grouped by which of these it serves. Every test is pre-registered in the README
before it runs, as now. "In hand" means the data is already on the laptop or in the sandbox.

## Status (6 Nov 2026, night): the conclusion and the plan from it

**Conclusion so far.** Watching ongoing activity does not reveal cause and effect in worms, and
(suggestively, on artefact-free data) not in human cortex either; poking does. That is not a brain-only
property: artificial networks with unrecorded slow signals and links silent at rest are as hard to read,
and so are trained transformers (correlations recover 0.31 to 0.71 of the true effects through their
layers, 0.05 to 0.47 in the units that compute; gradients recover 0.99). Most candidate differences
dissolve when one mechanism is added to an artificial network. Three remain open, none settled:
1. **Tiring with use.** A worm neuron answers less the second time and, compared with itself, also
   after being driven by other neurons; network-level responses decline little in worms and not at all
   in human cortex at 5 s gaps. Cause open (neuron, channel, or both).
2. **The echo as a whole.** A worm's echo is narrow, lasting and individual at once. Each part can be
   built into a network, but slow units that make responses last broaden echoes and erase
   individuality; slowing only some units does not escape the trade-off.
3. **State-dependent spread.** Found and replicated in worms; mouse leans yes (inconclusive); human
   cortex shows none (with a different state measure).

**Plan executed (6 Nov):** conclusion written; mouse touch cortex (tiring uninformative, state leaning,
watching versus poking not separable in that design); the echo (matched readout, persistence, slow
units); human state test; paper rewritten around the conclusion; two independent reviews (3 and 4), a
fifth running. The transformer programme is closed.

**Next, only where it would settle something:** a mechanism with its own rationale for lasting but
narrow echoes (slow synapses on specific links); the worm tiring test with the same neuron driven by
others at matched strength; data with repeated pokes of the same target over long recordings (an
experiment, needs a lab, only with your go-ahead).

## Status (6 Nov 2026, evening)

Checked against the README before running anything, several items turned out to be partly done
already: B3 (peptide-reduced worms, 2 Nov, prediction failed), B5 for worms (a worm agrees with
itself about twice as well as with other worms, 1 Nov), C1 in linear form (a connectome-constrained
synthetic worm is copyable by watching unless unrecorded shared drives are present, 1 Nov), and
strong watchers (stitched and latent-ready linear watchers; a GRU used only inside a poke-trained
copy). Run today, each pre-registered:

- **A2, neuron role:** inconclusive; sensory neurons are not the hardest to copy by watching.
- **B1, repeat pokes:** a stimulated neuron responds about a quarter less the second time (after
  correcting for selection); artificial networks do not change. Neuron or light-gated channel: not
  separable here. The change in the spread is lost in noise.
- **B2, behavioural state:** by AVA, no detectable state dependence. By each worm's main resting
  pattern, the spread does depend on state: found after the second review (p = 0.002), then
  replicated as pre-registered in 15 unseen unc-31 worms (p = 0.033) with a positive control that
  passed. The ladder's best network shows it in one of two brains, more weakly.
- **A1, nonlinear watcher:** a GRU trained only by watching fails like the linear watchers (0.004 to
  0.011 against 0.09 to 0.11); on a network where watching works it recovers about half, so the
  failure on worms is real.
- **C2/C3, ingredient ladder, nine rounds:** no single ingredient makes an artificial network look
  like a worm. A joint search over ingredient strengths found a setting (strong slow drives, weak
  silent links, spread, 30% quiet units, connection strengths varying between individuals with an
  SD of 80%, pokes held 3 s) that is within about a fifth of the worm on average over five axes
  (not within 25% on all) and, on the full ruler, watching recovers 11% to 29% (worms 4 to 16%). It
  was chosen after seeing both brains, so it shows what is sufficient, not what the worm has. Dead
  ends, all recorded: private drives and excitability drives did not restore individuality; larger
  individual differences did (poke strength alone did not).
- **Worm individuality** is specific to the poked neuron (not a worm-wide profile).
- **A3, neighbour partners:** no power (its positive control is invisible to the pre-registered
  design); open.
- **D2 and C1, real wiring diagrams (fly, via flyvis; worm, Kunert):** the trained fly models could
  not be downloaded (Google Drive blocked on both machines); the wiring diagrams in the lab's
  dynamics were unusable (pokes do not spread). Needs a proper modelling design, starting from the
  existing Kunert model.
- **D1, transformer:** unusable twice; poking one hidden unit of a small transformer gives echoes
  too weak to measure. Needs a different design (residual-stream directions).
- **Independent reviews:** two, both done; every correction they asked for is in the README.

Next: repeat pokes at matched strength and
stimulation at several strengths (experiments that would say which ingredients the worm has);
the human data with the pulse removed; the Kunert model as a wired network.

---

## A. Close the holes a reviewer will find first

**A1. The strongest possible watcher.** (In hand.) The obvious objection: watching failed because
our watching models were too weak. Answer it directly. Train one large shared model on every worm's
resting activity at once (113 atlas worms, the separate spontaneous-activity recordings, and the
18 peptide-mutant worms), of the kind now used as "foundation models" for neural data, then ask it to
predict echoes in held-out worms. Prediction: it still falls far short of the poke-trained copy.
If it closes the gap, the headline changes, and we say so.

**A2. Split the worm result by neuron role.** (In hand; already proposed.) Sensory, inter and motor
neurons. Prediction: watching fails most when sensory neurons are poked, because at rest they mostly
report the outside world, not the network.

**A3. What causes the neighbour effect.** (In hand.) If a poke truly activates its neighbours, the
neighbours' own wiring partners should also respond more than expected. A recording artefact would
not do that.

**A4. Same neuron, different strengths.** (In hand, partly.) Silent links predict a threshold:
weak pokes look like rest, strong pokes reveal new paths. Pokes vary naturally in strength; the
earlier attempt (T2) had too little range, so redesign around connectome-defined pairs.

## B. New axes of difference (each a separate, measured comparison)

**B1. Does a brain answer the same question twice the same way?** (In hand.) In 36% of cases the
same neuron was poked two or more times in one worm. Compare its first and later echoes, against
worm-to-worm variation. Artificial networks answer identically every time unless built otherwise.
A real change (habituation, sensitisation) would be a clean difference: biological networks are
changed by being asked.

**B2. Does the answer depend on what the brain was doing?** (In hand.) AVA, a neuron that marks
whether the worm is reversing, is identified in 68 worms. Split echoes by the worm's state at the
moment of the poke. If the same poke has different consequences in different states, the worm's
wiring is effectively rewired by state. Measure the same thing in artificial networks.

**B3. Wireless signalling.** (Done 2 Nov.) Worms also signal with neuropeptides, outside the
wiring diagram; that network has been mapped (Ripoll-Sánchez et al., Neuron 2023) and is far
denser than the synaptic one. The 2 Nov test (README "Four tests on the data we have", test 1)
predicted that worms with peptide release reduced would be easier to copy by watching. The
prediction failed: watching was no better (unc-31 minus wild type -0.008, 90% interval -0.027 to
+0.011), and the slow shared activity that defeats watching is present in both strains. What
remains: a slow wireless layer as an ingredient in artificial networks (C2).

**B4. Areas and modules.** (In hand.) Your question. Do echoes stay inside anatomical groups
(ganglia, functional circuits) more than chance? Do modules found from rest activity match modules
found from pokes? Then build modular artificial networks and run the same measures.

**B5. How different are individuals?** (In hand; numbers mostly exist.) Compare worm-to-worm
differences with seed-to-seed differences between artificial networks trained on the same task.
Is biological individuality larger, smaller, or differently shaped?

**B6. Timescales and dimensionality.** (In hand.) How many independent patterns rest activity has,
and how long each neuron "remembers". Both are cheap, standard, and comparable across all our brains.

## C. Causes: the ingredient ladder

This is the part that turns measurements into an answer.

**C1. Real worm wiring.** Build artificial networks on the worm's actual wiring diagram (chemical
synapses and gap junctions), with artificial dynamics. If these copy easily by watching, wiring is
not the difference; dynamics are.

**C2. Add biological ingredients one at a time and in combination:**
- thresholds that keep some links silent at rest (already shown sufficient in simple networks);
- a slow wireless layer built from the peptide map;
- behavioural states that switch the network between modes;
- short-term plasticity, so repeated pokes change the answer (tests B1);
- cell-type diversity (graded and spiking neurons, different time constants);
- modules (tests B4).

**C3. Score every variant on every axis in B**, giving a fingerprint per network. Find the
smallest set of ingredients that reproduces the worm's fingerprint, and how much each contributes
(a fair-share attribution over all combinations). The deliverable is a sentence of the form "the
worm differs from an artificial network mainly because of X and Y, roughly this much each, and not
because of Z."

## D. Generality

**D1. Large language models.** Apply the identical test to a small transformer: build a copy of its
internal units by watching their activity, then compare against direct interventions (activation
patching). Individuals are separately trained seeds. Interpretability researchers have already
found that interventions can wake "dormant" pathways in language models (Makelov, Lange and Nanda,
ICLR 2024), which is our silent-links idea seen from the AI side. This asks whether large trained
networks are moving towards brains on this axis, and it connects the project to a much larger
audience.

**D2. A published connectome model of a real brain.** The fly visual system model of Lappalainen
et al. (Nature 2024) is open source (`pip install flyvis`). Test whether a model built from a real
wiring diagram is copyable by watching. No fly poke data needed for this half.

**D3. Mouse visual cortex.** Chettih and Harvey (Nature 2019) stimulated single neurons in mouse V1
and recorded their neighbours ("influence mapping"). Check whether the data is public; if so it is
the closest mammalian match to the worm experiment.

**D4. Human, done properly.** Re-extract the 74-person recordings with the stimulation pulse
removed (needs the 289 GB re-download).

**D5. Mouse touch cortex.** Data in hand; map trials to targets, score only no-lick trials.

## E. Make it last

**E1. Theory.** For a linear network driven by noise, rest activity fixes the wiring only if the
noise structure is known; unknown noise, hidden neurons and thresholds each leave room for many
different wirings that look identical at rest. Turn this into a formula that predicts the ceiling
on watching from measurable quantities, then check the prediction against worms and every artificial
family. A law that predicts the measurements is much stronger than the measurements alone.

**E2. An open benchmark.** Release artificial brains with hidden ingredients, plus our held-out
split of the public worm atlas (as a list of recordings and code, never the worm data itself), and
let anyone submit a watching model. This turns the project into a shared test bed.
(Nothing is published without you.)

**E3. A prediction for a real experiment.** Name, in advance, the worm neurons whose echoes watching
will get most wrong, and the strength at which silent links should appear. A lab with the
equipment could test it. (Contact only with your go-ahead.)

---

## Suggested order

1. **Week 1, quick and in hand:** A2 (roles), B1 (repeat pokes), B2 (state), B3 (peptide mutants).
   Each is a few hours and each adds an axis or a test of the main result.
2. **Week 1 to 2:** A1 (strongest watcher). This is the biggest robustness risk.
3. **Week 2 to 3:** C1 and C2 (worm wiring, ingredient ladder), then C3 (fingerprints).
4. **In parallel:** D1 (language model) and D2 (fly model), since they need no new data.
5. **Then:** E1 (theory), A3, A4, B4 to B6, D3 to D5, E2, E3.
