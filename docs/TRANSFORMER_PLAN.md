# Transformers through the worm measurements: a timeline (started 6 Nov 2026)

**Why.** The project asks what makes biological neural networks different from artificial ones. The
artificial networks tested so far are small recurrent networks. The networks people mean by "AI"
today are transformers. Two pilots failed: poking one hidden unit of a small transformer gave echoes
far too weak to measure, so no reading was possible. This plan fixes the design first, then asks
the project's questions of transformers.

**Constraints.** Hugging Face is blocked from the sandbox and the laptop, so pretrained models
(GPT-2, Pythia) can only be used if downloaded by hand (phase 8). Everything else uses small
transformers trained here on CPU. Every phase is pre-registered in the README before it runs; every
result, including failures, is kept.

## Phase 0. Make pokes measurable (diagnostic)
What unit to poke, how hard and how long, so that echoes are measurable. Candidates: one MLP hidden
unit; one attention head's output; a random direction in the residual stream; the residual stream's
main directions. For each: the size of the exact echo (noise-free paired runs) against natural
fluctuations, and how consistent it is across contexts. Target: an evoked share near the worms' (about
0.4) and individuals' agreement above 0.05. Exploratory; it only chooses the design.

## Phase 1. The worm test in token time (pre-registered)
Frames are tokens; the chosen units are the "neurons"; individuals are noisy fine-tuned copies of a
trained base. Recorded and poked like the atlas, measured on the ladder's six axes and the full
ruler. Question: is a transformer copyable by watching, like the recurrent networks, or not, like
the worm?

## Phase 2. The test in depth (pre-registered, with known truth)
In a transformer most cause and effect runs through depth, layer to layer, in one forward pass.
Watching: linear maps between layers fitted on natural activations (half the units seen, as in the
atlas). Poking: activation patching. Score: correlation with the true patching effects, known
exactly, as in the artificial lab. This is the interpretability question "can correlations stand in
for interventions?" asked with the project's ruler.

## Phase 3. Does training matter?
Untrained, trained, and trained far past fitting (on a task that shows sudden generalisation,
modular addition), on phases 1 and 2.

## Phase 4. Does scale matter?
Width 32 to 256, depth 2 to 8, on the synthetic language. Trend of watchability with size.

## Phase 5. State dependence
The worms' replicated finding: the same poke spreads differently depending on the brain's state.
Transformers route information by context through attention, so the prediction is strong state
dependence. Same test as the worms (sign-aligned first component), plus the language's own hidden
state as a known-truth state.

## Phase 6. Silent links, transformer version
Interpretability work reports "dormant pathways" that patching can wake. Measure how much of each
patching effect lies in directions that carry little natural variance, by training stage and size.

## Phase 7. Does a transformer tire?
Repeated patches of the same unit within one context, the worms' tiring test. Expected: no tiring
(weights do not change), which makes tiring a worm property transformers lack by construction;
checked, not assumed.

## Phase 8. Real language models (needs the user)
If GPT-2 small or Pythia models (ideally several training seeds) are downloaded by hand into the
project folder, phase 2 is run on them.

## Phase 9. The interpretability bridge
Watching copies against attribution patching (a gradient, local-linear stand-in for patching) and
true activation patching, on the same networks: where does each fail, and does it fail where the
worm test does?

## Phase 10. Review and write-up
An independent review of every phase, then the README, the website (a "language models" entry) and
the paper.
