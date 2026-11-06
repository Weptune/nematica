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
| **Tiring**: a neuron answers less when poked again | Yes: about a quarter less (D -0.28 after selection correction) | No (-0.02) | Adding stimulation that weakens with use reaches only -0.13: saturating units hide it | No (-0.002) | **Dissolved: the tool, not the neuron.** In the atlas, being driven by other neurons (no light) does not tire a neuron, only being lit does; human cortex poked electrically does not tire at all (+0.0004 per pulse [-0.0008, +0.0015], 74 patients) |
| **State-dependent spread** along the main resting pattern | Yes (-0.049, p = 0.002); replicated in new worms (-0.080, p = 0.033) | Only with strong slow drives | One of two brains (p = 0.0008; p = 0.12) | No on this test (p = 0.39); yes on the language's true hidden state, strongly | **Partly survives.** Artificial networks depend on state too, but not on their main resting pattern; the worm's kind of state dependence is reproduced only with slow drives |
| **Echo breadth**: share of neurons a poke moves | 0.085 | 0.095 to 0.100 | Modules: no detectable narrowing | 0.133 | **Weak.** Close in recurrent nets; transformers wider. Combined with tiring and the rest, no ingredient combination matches all axes at once |
| **Resting structure**: variance in the top 3 patterns | 0.43 | 0.25 to 0.27 | Drives: 0.40 to 0.43 | 0.51 | **Dissolved.** One ingredient (shared slow drives) produces it |
| **Individuality**: each individual has its own causal fingerprint | 0.089 | 0.016 to 0.028 | Silent links raise it; drives erase it | 0.087, but set by the weight noise we chose | **Dissolved, tunable.** It depends on how individuals are made |
| **Reliability**: individuals agree on poke responses | 0.094 | 0.075 | Silent links overshoot, drives undershoot | 0.38 | **Not a difference by itself.** Depends on noise and on how similar individuals are |
| **Echo complexity**: who joins the echo after a poke | Sparse and sustained: a third of classes never respond, responders keep responding | Fitted worm models: almost every class flickers in briefly | Not tested | Not tested | **Open.** No model matches it yet; the strongest remaining candidate |
| **Sensory neurons harder to copy** | Not detected | n/a | n/a | n/a | No evidence either way |

## What this says, plainly

1. **Being hard to read from the outside is not what makes brains different.** Worms are hard to
   copy by watching, but so are trained transformers in their computing units, and so are artificial
   networks once they have signals no recording sees. This was the project's first headline, and the
   transformer work is what showed it is not a brain-only property.
2. **Tiring with use was the tool.** Worm neurons answer less the second time and no artificial
   network does, but activity alone does not tire a worm neuron (only light does), and human cortex
   poked electrically, 74 patients, shows no tiring at all. So it belongs to the light-gated channel.
3. **What survives, shakily:**
   - *The kind of state dependence*: in worms, where a poke spreads depends on the main pattern of
     resting activity; in artificial networks, state dependence exists but follows other variables.
   - *The sparse, sustained echo*: a third of a worm's neurons stay out of an echo and those in it
     stay in; every fitted model's neurons flicker in briefly.
4. **The worm's whole profile is not reproduced.** No combination of five biological ingredients
   matches all six measured properties at once; the closest settings need strong hidden drives,
   large differences between individuals and many units that stay quiet unless strongly driven.
   That shows what is sufficient, not what the worm has.
5. **Mostly one animal.** Human cortex now adds two results on artefact-free data: no tiring, and a
   linear watching copy predicts responses worse than distance alone (0.30 against 0.45), as in worms.
   Mouse hippocampus was inconclusive; mouse touch cortex is downloaded but not analysed.

## What would settle the surviving differences

- **Tiring: settled for now (6 Nov).** Activity alone does not tire worm neurons; human cortex does
  not tire across 10 pulses 5 s apart. Open only at longer gaps, and in mouse touch cortex.
- **The sparse, sustained echo**: what keeps a third of a worm's neurons out of an echo; whether
  thresholds, silent links or neuromodulation produce it in an artificial network without breaking
  the other properties.
- **The worm kind of state dependence beyond the worm**: the same pre-registered test in mouse
  touch cortex and human data.

The transformer programme is closed after its current reruns (corrections of published claims).
New work goes to the rows that survive.
