# What makes artificial networks different from biological ones: the answer so far

Draft, 6 Nov 2026. This file turns the experiments into answers to the project's question. Each row
is a property that could separate a biological network from an artificial one. Numbers come from the
README sections named in the last column; every number there has its caveats.

Systems compared:
- **Worm**: *C. elegans*, the only animal where we have single-neuron pokes at scale (atlas: 113
  worms; a replication set of 15 unc-31 worms).
- **Recurrent nets**: the lab's random tanh networks, and the same networks trained on memory and
  decision tasks.
- **Lab + biology**: the lab networks with biological ingredients added (shared slow drives that no
  recording sees, links silent at rest, stimulation spread, modules).
- **Transformer**: small trained transformers on a synthetic language, and real language models
  (Pythia-14m and 70m).

## The table

| Property | Worm | Recurrent nets | Lab + biology | Transformer | Verdict |
|---|---|---|---|---|---|
| **Copyable by watching** (recorded activity predicts poke responses) | No: 4 to 16% of worm-to-worm agreement | Yes: random 51 to 82%, trained 75 to 91% | Drives plus silent links: 18 to 19%, near the worm | In time: no, but trivially (effects land in depth, not in later tokens). In depth: partly; correlations recover 0.31 to 0.71 of the residual stream's cause and effect and 0.05 to 0.47 in the computing (MLP) units; training lowers it | **Dissolved as a categorical difference.** Hidden shared signals and training both produce it in artificial networks. It separates worms from the small recurrent nets we tested, not biology from artificial networks |
| **Tiring**: a neuron answers less when poked again (8 Nov: see the late update below) | Yes: about a quarter less (D -0.28 after selection correction) | No (-0.02) | Adding stimulation that weakens with use reaches only -0.13: saturating units hide it | No (-0.002) | **Survives, cause open** (corrected after review 4; it was briefly called "the tool"). Spiking networks (8 Nov): plain spiking, spike-fed adaptation and synaptic depletion do not tire; every neuron-level fatigue tried gives the opposite sign on this measure (+0.13 to +0.75), and only a tiring stimulation channel gives the worm's sign (-0.17; calibration short of its -0.2 rule, so exploratory), which leans back towards the tool. A direct worm test (8 Nov): before a neuron's second poke its resting level does not detectably drop (-0.04 [-0.16, +0.09]) while its response drops (-0.74), the channel's pattern; formally inconclusive (interval wider than +-0.1), but neuron-level fatigue of the size tried in spiking networks is ruled out. Compared with itself, a worm neuron recently driven by other neurons, with no light on it, answers less (-0.09 per SD of drive [90%: -0.16, -0.02], within-neuron shuffle p = 0.026; exploratory), so activity may tire it; the larger drop after being lit could still be partly the channel. Network-level responses decline little: worm echo -0.04 [-0.19, +0.12]; human cortex, channels beyond 10 mm, +0.0004 per pulse [-0.0008, +0.0015] (the stimulated tissue not measured); mouse touch cortex uninformative |
| **State-dependent spread** along the main resting pattern | Yes (-0.049, p = 0.002); replicated in new worms (-0.080, p = 0.033). Matched shams (7 Nov, 3 draws): -0.014, -0.022, -0.003, none significant; with a stricter pseudo-onset pool the real effect is -0.093, p = 0.0008: specific to pokes | Only with strong slow drives | One of two brains (p = 0.0008; p = 0.12) | No on this test (p = 0.39); yes on the language's true hidden state, strongly | **Partly survives.** Artificial networks depend on state too, but not on their main resting pattern; the worm's kind of state dependence is reproduced only with slow drives. Mouse touch cortex leans the same way (S -0.085, 6 of 7 sessions, p = 0.066, inconclusive); human cortex: none detected (S -0.0017 [-0.0046, +0.0015], 54 patients; a different state measure) |
| **Echo breadth**: share of neurons a poke moves | 0.085 | 0.095 to 0.100 | Modules: no detectable narrowing | 0.133 | **Weak.** Close in recurrent nets; transformers wider. Combined with tiring and the rest, no ingredient combination matches all axes at once |
| **Resting structure**: variance in the top 3 patterns | 0.43 | 0.25 to 0.27 | Drives: 0.40 to 0.43 | 0.51 | **Dissolved.** One ingredient (shared slow drives) produces it |
| **Individuality**: each individual has its own causal fingerprint | 0.089 | 0.016 to 0.028 | Silent links raise it; drives erase it | 0.087, but set by the weight noise we chose | **Dissolved, tunable.** It depends on how individuals are made |
| **Reliability**: individuals agree on poke responses | 0.094 | 0.075 | Silent links overshoot, drives undershoot | 0.38 | **Not a difference by itself.** Depends on noise and on how similar individuals are |
| **Echo sparseness**: share of neuron classes a poke reaches (> 3 SD) | 0.65; but sham onsets give 0.70 | Base 0.71 to 0.78 (sham 0.71) | Round 9 setting 0.55 to 0.64 | Paired measure: 0 to 0.05 | **Withdrawn as a poke property (7 Nov sham check).** The per-event measure mostly reads ongoing fluctuations |
| **Echo persistence**: how long a response lasts (mean run, frames) | 6.5; most of it is ongoing activity (first sham check 6.0). Against clean shams pokes lengthen runs by +0.44 to +0.56 (review 6) | Pokes lengthen runs too: base +0.08 against clean shams (+0.14 with the calcium-matched readout) | Drives +0.08 (calcium-matched, clean shams; interval includes 0) | Paired measure: 0 to 1.3 steps (comparison moot, review 6) | **The large contrast is withdrawn; a poke-specific difference is not established.** Worms lengthen more in frames, but relative to their slower ongoing timescale (about 9% against 4 to 6%) the gap may be a matter of scale |
| **Sensory neurons harder to copy** | Not detected | n/a | n/a | n/a | No evidence either way |
| **Keeps the same rules over a recording** (reverse direction: lag-1 structure early vs late, beyond noise) | Drifts: +0.011 (30 s rule), +0.059 (15 s rule); human cortex +0.040 | Plain rate and spiking networks: no drift (intervals include 0) | Slow hidden drives +0.021 without pokes; gated fatigue +0.021 with pokes | Not tested (contexts are independent) | **Candidate, quantitative.** Networks without slow processes keep their rules; slow drives or use-dependent fatigue make them drift, but less than worms under the comparable rule. Human drift may be driven by the stimulation itself |

## What this says, plainly

1. **Being hard to read from the outside is not what makes brains different.** Worms are hard to
   copy by watching, but so are trained transformers in their computing units, and so are artificial
   networks once they have signals no recording sees. This was the project's first headline, and the
   transformer work is what showed it is not a brain-only property.
2. **Tiring with use: still a candidate** (corrected after review 4, which caught that the first reading,
   "it was the tool", rested on a confounded comparison and on a human measure of the network rather
   than the stimulated tissue). Worm neurons answer less the second time, and compared with themselves
   they also answer less after being driven by other neurons (exploratory, shuffle p = 0.026); no artificial network tires on repeat pokes (the driven-by-others design is not tested in them). Network
   responses (the echo) decline little in worms and not at all in human cortex at 5 s.
3. **What survives, shakily:**
   - *The kind of state dependence*: in worms, where a poke spreads depends on the main pattern of
     resting activity; in artificial networks, state dependence exists but follows other variables.
     Beyond the worm it is not established: mouse leans yes, human shows none.
   - *The echo as a whole*: **the large contrast is withdrawn (7 Nov, corrected by review 6).** The
     per-event sparseness measure and perturbational complexity give the same values with no poke
     (not poke-specific); persistence is mostly ongoing activity, and its poke-specific part
     lengthens responses in worms and lab networks alike (worms more in frames, not clearly more for
     their timescale). Perturbational complexity is suspended.
4. **The worm's whole profile is not reproduced.** No combination of five biological ingredients
   matches all six measured properties at once; the closest settings need strong hidden drives,
   large differences between individuals and many units that stay quiet unless strongly driven.
   That shows what is sufficient, not what the worm has.
5. **Mostly one animal.** Human cortex adds three results on (mostly) artefact-free data: network responses
   do not tire at 5 s, and a linear watching copy predicts responses worse than distance alone (0.30
   against 0.45), as in worms; and no detectable state dependence (calibration check failed as worded).
   Mouse hippocampus was inconclusive; mouse touch cortex leans towards state
   dependence but cannot separate watching from poking and its tiring test is uninformative.

## What would settle the surviving differences

- **Tiring:** a worm test with the same neuron driven by others at matched strength, and a human test
  on the stimulated tissue itself (needs a cleaner way round the stimulation artefact near the pair).
- **The echo as a whole**: which mechanism gives lasting responses without broadening them (slow
  synapses on a few links rather than slow units everywhere; neuromodulated gain).
- **The worm kind of state dependence beyond the worm**: mouse touch cortex leaned yes (inconclusive);
  human cortex showed none (with a different state measure and short blocks). Settling it needs
  repeated pokes of the same target across long recordings with states measured the worm's way.

The transformer programme is closed after its current reruns (corrections of published claims).
New work goes to the rows that survive.

## Update, 7 Nov 2026: the watching limit, and what the table does not cover

**Watching, row 1, now has a mechanism-level reading** (README "The watching limit"). Watching can fail
for three different reasons, each with its own fingerprint: the watcher's model is wrong, the data is
too short, or the information is not in rest activity at all. The three show up in different systems:

- *Transformers: structural.* Watching gains nothing from 24 to 96 contexts in any of six networks;
  every unit shares the same token input.
- *Human cortex: data-limited.* Watching improves with more rest data (0.229 / 0.248 / 0.285 from a
  quarter / half / all of a session; 28 of 32 recordings improve). Plateau prediction refuted.
- *Worms: partial by the pre-registered rule, leaning structural.* The best watcher (latent linear,
  maximum likelihood) predicts worm pokes at about zero in all three pools while the data check is 0.59
  to 0.69; exploratory checks (hidden units carry 12 to 19% of rest variance; a lab brain with the same
  data sufficiency is readable) lean structural.

The row's verdict does not change (dissolved as a categorical difference), but the reason watching
fails is itself a property that differs between systems, and in worms it points at influence that
rest activity does not express, the property silent links produce.

**What the table does not cover (gaps in answering the project's question):**

1. *Two meanings of "different" are not separated in the verdicts.* "Dissolved" means an artificial
   network can be built to have the property; ordinary networks mostly still lack it. Both answers
   belong in every row.
2. *Coverage holes.* Echo sparseness and persistence are untested in transformers; human and mouse data
   cover only watching, tiring and state dependence (and partly individuality); only the worm has
   single-neuron pokes at scale.
3. *The artificial side is small:* recurrent networks of about 120 units, transformers up to 70M
   parameters, no spiking networks.
4. *One direction only:* every candidate is something worms do; nothing systematically asks what
   artificial networks do that brains never do.
5. *Unmeasured candidates:* change during a recording (plasticity), sparsity and energy, noise
   structure.

These are the next steps for the project's question, ahead of further work on watching.

## Update, 7 Nov 2026 (evening): one survivor withdrawn

Filling the transformer hole in the echo rows led to a sham check of the echo measures themselves
(README "Does a transformer have the worm's narrow, lasting echo?"). The per-event echo measures
(sparseness, persistence, perturbational complexity, spread) are not specific to pokes: they give
nearly the same values at moments with no stimulation, in worms and in lab networks. So "an echo that
is narrow and lasting at once" is withdrawn as a surviving difference; what it measured is the slow
timescale of worm ongoing activity. **What survives is now: tiring with use (cause open), and the
worm's kind of state dependence (a sham check of it was biased and is uninformative; a matched sham is
needed).** Everything built on responses averaged over pokes is unaffected.

Next for the project's question: a poke-specific echo measure (real minus matched sham), applied to
worms and every artificial system, to see whether any echo property separates them once ongoing
activity is removed; and a matched sham for the state-dependence test.

## Update, 7 Nov 2026 (night): matched shams, corrected by review 6

The worm's **state dependence is specific to pokes** (matched shams null in 2 of 3 draws, the third
-0.014, p = 0.08; with a stricter pseudo-onset pool the real effect is -0.093, p = 0.0008). The echo
comparison against matched shams was confounded (the shams contained the next poke): against clean
shams, pokes lengthen responses in worms (+0.44 to +0.56 frames) and in lab networks (+0.08 to +0.14),
so **no poke-specific echo difference is established**. Survivors now: **tiring with use** (cause open)
and **the worm's kind of state dependence**. The spiking runs' echo excesses used the confounded sham
and carry that caveat.

## Update, 8 Nov 2026: spiking networks and the reverse question

- **Spiking networks** join the artificial side. Plain spiking networks are readable by watching and do
  not tire, like the rate networks, and as built they are less worm-like on echo breadth, resting
  structure and individuality. For tiring, every neuron-level fatigue tried gives the opposite sign on
  the worm's measure; only a tiring stimulation channel gives the worm's sign (exploratory: the
  calibration missed its registered threshold). The question "neuron or tool" leans back towards the
  tool, against the within-neuron worm result.
- **The reverse question** gets its first answer: networks without slow processes keep exactly the same
  rules over a recording, while worms and human cortex drift. Slow hidden drives or use-dependent
  fatigue make networks drift too, but less than worms under the comparable rule.

Survivors now: **tiring** (cause open, leaning tool; a direct worm test shows the channel's pattern), **the worm's kind of state dependence**, and a
reverse-direction candidate, **drifting rules**, quantitative rather than categorical.

## Update, 8 Nov 2026 (late): tiring, hidden state, and the conclusion

**Tiring, settled as far as the atlas allows** (README "Light or activity: what tires a worm neuron?",
corrected by review 7). A neuron poked again 0.6 to 2 minutes later answers at about half its previous
response (-0.76 [-1.08, -0.44]); after 2 to 5 minutes about two thirds; after 5 to 10 minutes it is not
detectably weaker. The decline persists in unc-31 mutants. Two pre-registered ways of splitting light
from activity failed on synthetic worms where the cause was known, so the split is not measurable in
this atlas: every direct poke delivers both. Activity caused by other neurons, with no light, is
followed by a slightly smaller response (-0.10 per SD, beyond the range of synthetic worms without
neuron fatigue), so a modest neuron component is likely but not established. **The tiring row stays
"survives, cause split"**: a short-lived decline that follows light, plus probably a smaller part that
follows activity.

**Invisible machinery: no answer.** A cheap measure of slow hidden state from rest failed its
calibration (at worm recording length, neither model predicts 20 to 40 s ahead on held-out data), so
the test stopped before any brain data was read, as registered.

## Update, 8 Nov 2026 (night): a model that passes on the atlas, and what it does not show

The question was turned around: build one artificial network that held-out real worms cannot be told
apart from, at rest and when single neurons are poked, then remove one part at a time (README "A worm
emulator"). Corrected by review 8 and a bug fix:

- The registered attempt **failed narrowly** on the independent split (rest 4 of 6, pokes 3 of 3).
- The *minimal* model (two unneeded parts dropped, plus each neuron class's own degree of slow
  participation), with a corrected neuron-level readout, passes the rule in **10 of 10 runs** on the atlas
  (two splits of the same 113 worms, five noise draws; fitting is the same in each draw). But several
  passes are within worm-to-worm variation rather than exact: echo size sits further from real worms
  than real worms sit from each other in 30 of 30 pool-runs, and so does lead and lag.
- **On worms it was not built on, it does not hold up.** Refitted from scratch on unc-31 mutants it
  passes in 3 of 5 seeds (the registered bar was 4 of 5). On freely moving worms from another lab it
  fails clearly; there, coupling between neuron types (dropped as unnecessary in the atlas) is needed,
  and real activity is skewed in a way no Gaussian model reproduces.

What the ablations on the atlas say a passing model needs (`docs/figures/emulator_ablations.png`):
- **slow, brain-wide states that interact**: about 70% of real activity is slow, timescale about 40 s.
  This is the most robust gain: on dimensionality, earlier models sat 74 to 85% further from real worms
  than real worms sit from each other (excess distance; their activity spread over far too many
  dimensions), the emulator within 9 to 16% (median excess -0.09 on one split, +0.16 on the other).
- **individual variation between animals**: without it, timescales and correlations are too typical.
- **causal links learned from pokes**: without them the echo pattern fails in every pool.
- **being observed neuron by neuron**, as real neurons are.

A neuron's timescale agrees more within a recording than across worms, but that cannot be separated
from recording conditions (review 8).

## Conclusion: what separates real neural networks from artificial ones

This is the project's answer to its main question, as of 8 Nov 2026, with how strong each part is.

1. **No difference in kind was found.** Every property that first separated worms from artificial
   networks either dissolved when a network was given the right ingredient (hidden slow drives, links
   silent at rest, calm and active regimes, non-propagating noise, individual variation) or turned out
   to be a measurement of ongoing activity rather than of the brain's response. *Strong for the
   properties tested; limited to one animal with single-neuron pokes and to small artificial networks.*
2. **The difference is in what the system carries outside its units' activity.** Every surviving or
   dissolved-but-real difference traces to state that a recording of activity does not show: slow
   hidden drives (why watching fails and why rules drift), use-dependent change (tiring), and
   switching between calm and active regimes. An ordinary artificial network's state is its units'
   activity; a brain's state is more than its neurons' activity. Artificial networks can be given such
   state, and when they are, they acquire the brain's properties. *This is a synthesis across results,
   not a single test; it fits every row of the table and was not predicted in advance.*
3. **The consequence that matters most in practice:** realism at rest does not predict realism under
   perturbation (rho -0.12 across 30 models, recomputed per model after review 7), and individual worms
   appear to have causal fingerprints invisible at rest (*downgraded 8 Nov: possibly partly off-target
   stimulation of neighbouring neurons; see README "Do worms with the same wiring route signals
   differently"*). A copy of a brain cannot be certified by watching it. *Strong, pre-registered,
   checked by reviews; the independence caveat in review 7 does not change a null.*
4. **What survives as a measured difference, by degree:** tiring with use (part probably the tool,
   part probably the neuron), the worm's kind of state dependence (poke-specific, -0.093, p = 0.0008),
   and drifting rules over a recording (worms and human cortex drift, networks without slow processes
   do not). *Each is moderate evidence from mostly one species.*

5. **Constructive answer (8 Nov, night), limited:** on the immobilised, light-stimulated atlas worms, an
   artificial network passes this benchmark once it has slow interacting brain-wide states, individual
   variation and causal knowledge from perturbation; fast coupling between neuron types was not needed
   there. This fits point 2 (the decisive state is slow and not visible in moment-to-moment activity).
   *It did not transfer: 3 of 5 seeds on unc-31 worms (bar 4 of 5), a clear fail on freely moving worms
   where fast coupling matters. Tuned and evaluated on worms already seen; several passes are within
   worm-to-worm variation rather than exact.*

**Is any of this noteworthy?** Two things are, modestly: the benchmark result that looking right at rest
says nothing about being right under perturbation (packaged as a preprint draft), and the repeat-
stimulation decline in the field's main perturbation atlas (a practical caveat, not reported before as
far as we found). The main question's answer, "the difference is state outside the activity", is a
coherent reading, not a discovery: it would need a test designed for it (measuring hidden state
directly, which the atlas and our cheap measure cannot do) before it is more than that.

**What would move it further:** the light-free tiring experiment (draft email to the atlas authors,
not sent); a perturbation dataset with repeated pokes of the same neurons at controlled intervals; and
recordings long enough to measure slow hidden state from rest (our calibration says 16 minutes is too
short).
