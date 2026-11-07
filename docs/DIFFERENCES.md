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
| **Tiring**: a neuron answers less when poked again | Yes: about a quarter less (D -0.28 after selection correction) | No (-0.02) | Adding stimulation that weakens with use reaches only -0.13: saturating units hide it | No (-0.002) | **Survives, cause open** (corrected after review 4; it was briefly called "the tool"). Compared with itself, a worm neuron recently driven by other neurons, with no light on it, answers less (-0.09 per SD of drive [90%: -0.16, -0.02], within-neuron shuffle p = 0.026; exploratory), so activity may tire it; the larger drop after being lit could still be partly the channel. Network-level responses decline little: worm echo -0.04 [-0.19, +0.12]; human cortex, channels beyond 10 mm, +0.0004 per pulse [-0.0008, +0.0015] (the stimulated tissue not measured); mouse touch cortex uninformative |
| **State-dependent spread** along the main resting pattern | Yes (-0.049, p = 0.002); replicated in new worms (-0.080, p = 0.033). A sham check (7 Nov) was biased and is uninformative | Only with strong slow drives | One of two brains (p = 0.0008; p = 0.12) | No on this test (p = 0.39); yes on the language's true hidden state, strongly | **Partly survives.** Artificial networks depend on state too, but not on their main resting pattern; the worm's kind of state dependence is reproduced only with slow drives. Mouse touch cortex leans the same way (S -0.085, 6 of 7 sessions, p = 0.066, inconclusive); human cortex: none detected (S -0.0017 [-0.0046, +0.0015], 54 patients; a different state measure) |
| **Echo breadth**: share of neurons a poke moves | 0.085 | 0.095 to 0.100 | Modules: no detectable narrowing | 0.133 | **Weak.** Close in recurrent nets; transformers wider. Combined with tiring and the rest, no ingredient combination matches all axes at once |
| **Resting structure**: variance in the top 3 patterns | 0.43 | 0.25 to 0.27 | Drives: 0.40 to 0.43 | 0.51 | **Dissolved.** One ingredient (shared slow drives) produces it |
| **Individuality**: each individual has its own causal fingerprint | 0.089 | 0.016 to 0.028 | Silent links raise it; drives erase it | 0.087, but set by the weight noise we chose | **Dissolved, tunable.** It depends on how individuals are made |
| **Reliability**: individuals agree on poke responses | 0.094 | 0.075 | Silent links overshoot, drives undershoot | 0.38 | **Not a difference by itself.** Depends on noise and on how similar individuals are |
| **Echo sparseness**: share of neuron classes a poke reaches (> 3 SD) | 0.65; but sham onsets give 0.70 | Base 0.71 to 0.78 (sham 0.71) | Round 9 setting 0.55 to 0.64 | Paired measure: 0 to 0.05 | **Withdrawn as a poke property (7 Nov sham check).** The per-event measure mostly reads ongoing fluctuations |
| **Echo persistence**: how long a response lasts (mean run, frames) | 6.5; but sham onsets give 6.0 | Base 2.2 to 2.5 (sham 1.8) | Slow units 4.7 to 5.0 | Paired measure: 0 to 1.3 steps | **Withdrawn as a poke property (7 Nov sham check).** What differs is the timescale of ongoing activity (slow in worms, slowed further by calcium imaging), a resting property models can match |
| **Sensory neurons harder to copy** | Not detected | n/a | n/a | n/a | No evidence either way |

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
   - *The echo as a whole*: **withdrawn on 7 Nov.** A sham check showed the per-event sparseness and
     persistence measures give nearly the same values with no poke at all (worms 0.70 and 6.0 sham,
     0.65 and 6.5 real), so they describe ongoing activity, not the echo. Perturbational complexity,
     computed on the same maps, is suspended for the same reason.
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
