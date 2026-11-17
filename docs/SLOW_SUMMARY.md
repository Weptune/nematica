# Study 2, start to finish: is the difference slow internal state? (15 to 17 Nov 2026)

This is the readable account of Study 2. The full, dated record is `docs/SLOW.md` (the registration, frozen
15 Nov 2026 at 19:27 UTC, commit 8df8c650b0e0, with amendments S1 to S9) and `docs/SLOW_LOG.md` (the notebook: every
run, crash, review and decision, with UTC times). Where this file and those disagree, they are the record.

## The question

The project asks what differentiates real neural networks from artificial ones. Before this study, every
difference that held up pointed at one thing: **slow internal state**, meaning activity that is not set by
the current input and changes slowly. The worm emulator needed slow brain-wide states. Watching a brain
missed influence carried by state that rest activity does not show. In the map study, a random RNN had less
slow memory than 33 of 35 mice. Study 2 tested that thesis directly, across standard artificial network
families, with a measure that does not depend on any system's own clock.

Four claims were registered, each with its own verdict:
1. real cortex carries more internal state than standard artificial networks;
2. that internal state is slower relative to the input;
3. a slow internal state closes the gap, and simpler candidates (a fast drive, more noise) do not;
4. scale is not what closes it.

## How

- **The measure.** Every system sees the same clip many times. What repeats is driven by the input; what
  differs between repeats is internal state. Units are centred within each repeat, so drift slower than one
  repeat (30 s) is not counted. Two numbers, each a ratio inside one system, so no clock conversion is
  needed:
  - **M1**, the internal share: the part of activity that differs between repeats, as a share of all
    activity at a lag of 2 bins (40 ms; starting at lag 2 removes single-spike structure);
  - **M2**, how long the internal part lasts compared with the input-locked part (above 1 means the
    internal part is the slower one).
- **Real brains.** 58 mice from the Allen Brain Observatory Neuropixels sessions (visual cortex units that
  pass Allen's quality checks), watching natural movie one (30 s) 20 to 60 times. 49 mice are used for the
  comparisons (amendment S6: 9 had no measurable timescale on the movie, so there was no instrument to record
  an AI at).
- **Artificial networks**, 3 instances each: A1 random RNN (movie-driven, 8 input gains), A2 task-trained
  RNN, A3 GRU and A5 CfC (character networks), A4 spiking network (movie-driven, 8 gains), A6 Pythia
  transformers (14M, 160M, 410M, 1B), A7 Mamba (130M, 370M). Noise-free networks get a different preceding
  context before each repeat, which is their only possible internal state.
- **Fair recording.** Each network was recorded through a simulated spike instrument set to each mouse's
  own numbers (bins per timescale, spikes per bin, white share, rate spread), checked on the recorded repeats
  and corrected up to 5 times (one retry of 10 for misses), and compared with that mouse. The spiking network
  is recorded like a mouse (its own spikes, thinned).
- **Decision rules,** written before any comparison: paired tests mouse by mouse; a ruler equal to the
  spread between mice (robust SD); a gap must exceed the larger of half a ruler and a measured bias bound;
  for families with several gains or sizes, a mouse inside the family's range counts as no difference (the
  bracket rule); tests must hold overall and within each of the 3 instances.

## What happened, in order

| when (UTC) | step | outcome |
|---|---|---|
| 15 Nov | Registration drafted | reviews S-R1 (23 findings) and S-R2 (19) before freezing; measures moved to lag 2; recorder applied to the whole run; two-photon replication deferred to its own registration |
| 15 Nov | Calibration, freeze | C1 and C4 pass on synthetic systems; a spike-type check failed narrowly and became a registered bias bound; frozen at 19:27 UTC, 8df8c650b0e0 |
| 15 to 16 Nov | Review S-R3, amendment S1 | instrument check fixes, disk rules, many small fixes, before any real data |
| 16 Nov | Mice stage | 58 of 58 mice; C3 reliability 0.96 (M1) and 0.83 (log M2); behaviour explains about 2.5% |
| 16 Nov | Amendments S2 to S5 | memory: analytic hold, streaming recorder (checked equal to 3e-15), knobs from timescales, instrument numbers from all units |
| 16 Nov | Amendment S6 | 9 mice without a movie timescale left out of AI comparisons (after the mice were seen) |
| 16 Nov | Amendment S7 | one retry for recordings that miss the instrument tolerance |
| 16 to 17 Nov | AI stage | 2,548 recordings for the 49 mice, with several machine restarts (resumed each time) |
| 17 Nov | Amendment S8 | Pythia-1B killed for memory; truncated model path, bit-for-bit identical on four models |
| 17 Nov | Retry | 165 of 200 missed recordings reached the instrument |
| 17 Nov, 07:02 | Registered tests | run once on a clean tree |
| 17 Nov | Review S-R4 | every result reproduced independently; no verdict changes; the reading corrected; amendment S9 |

## Results

**Checks first.** Both measures are reliable across mice (split-half rho 0.96 for M1, 0.83 for log M2). The
shuffled-movie validity check passed (24 mice): with the same frames in scrambled order, the locked time
collapses (about 37-fold) and the internal time barely moves. The playback check moved the movie-driven
random RNN by about one ruler unit, so the two movie-driven families (A1, A4) are reported but not counted.

**Mice.** Median M1 0.59 and M2 0.69. M2 is below 1 in 48 of the 49 mice: watching this slow movie, the
part that differs between repeats changes faster (about 0.5 s) than the part locked to the movie (about
0.8 s).

**Verdicts** (d = mouse minus network, in ruler units; margins 1.15 on M1 and 2.12 on log M2):

| family | M1 (internal share) | M2 (relative slowness) | counted |
|---|---|---|---|
| A2 task RNN | refuted: network has more (d -2.49) | not decided (+0.95) | yes |
| A3 GRU | confirmed: mice have more (d +5.20) | refuted: network slower (-2.44) | yes |
| A5 CfC | confirmed (d +4.95) | not decided, network slower (-1.57) | yes |
| A6 Pythia 14M to 1B | not decided: sizes bracket the mice (d 0) | not decided, network slower (-0.72) | yes |
| A7 Mamba | refuted: network has more (d -2.72) | not decided, network slower (-0.84) | yes |
| A1 random RNN | not decided: gains bracket every mouse (d 0) | not decided (0) | no |
| A4 spiking | not decided (+0.46) | confirmed (+8.30), but at a mismatched instrument | no |

**The four claims.**
1. **More internal state: does not hold.** Two families carry far less than the mice (GRU, CfC), two carry
   more (task RNN, Mamba), and the range of Pythia sizes contains the typical mouse.
2. **Slower relative to the input: does not hold.** No family is confirmed; the GRU is refuted, and CfC,
   Pythia and Mamba go the same way (network internal state slower) in all three instances, inside the known
   measurement bias.
3. **A slow drive closes the gap, controls do not: does not hold.** The best slow drive (share 0.5, 1 s)
   overshoots on both measures; the registered grid could not land on the mice on M2, because the slowest
   setting's 1 s is already slower than the mice's own internal time. The fast-drive control is too fast; the
   more-noise control matches on M2 but overshoots on M1.
4. **Scale does not close it: does not hold.** Pythia-1B is closer to the mice than Pythia-14M by a median
   1.95 ruler units [1.37, 3.19]. The pattern across sizes is not monotone (M1 0.33, 0.51, 0.46, 0.60), so
   this says the largest is closest, not that closeness grows steadily with size.

Removing running and pupil effects changes no claim.

**Main conclusion** (wording checked by review S-R4). Measured as the share of activity that differs between
repeats of the same input, within each 30 s repeat, mouse visual cortex watching a natural movie did not
carry more internal state than standard artificial networks as a group, and it was not slower relative to
its input. None of the four registered claims held. In the noise-free networks this internal state is the
trace of the preceding context, and it fades within a short clip of about 20 tokens or characters; in the
mice it does not fade along the clip. Whether the mice's internal state counts as "slow" depends on the
input: faster than the response locked to this slow movie, far slower than the input when the same frames
are scrambled. Adding a slow drive to a random network did not reproduce the mice.

## What it means for the project

The thesis that the difference is "more, slower internal state" is not supported in the form registered.
Two descriptive patterns, seen after the data and therefore leads rather than findings, are the most
promising next questions:
- **Persistence along the clip.** First-half against second-half M1: mice 0.58 and 0.66 (holds up); GRU 0.21
  and 0.01, CfC 0.31 and -0.02, Pythia-14M 0.40 and 0.06, Pythia-1B 0.66 and 0.25, Mamba about 0.89 and 0.65
  (fades); the task RNN 0.82 and 0.80 (holds up). Mice keep generating internal variation; most context-driven
  networks only carry what came before.
- **Noise-like variability.** On M2, only networks with internal noise (the random RNN at higher gains, the
  more-noise control) come near the mice; every noise-free network's internal state is relatively slower.

Either would need its own registration before it is tested.

## Limits

- One species and region (mouse visual cortex), one stimulus (natural movie one), 49 of 58 mice; the 9
  excluded mice had lower M1.
- Only internal state within a repeat (up to a quarter clip, 7.5 s) is measured; slower drift across minutes,
  part of the original thesis, is not tested here.
- Networks other than the spiking one are seen through a spike model fitted to each mouse's instrument; the
  spiking network is not matched to the instrument.
- For the noise-free networks, the M1 verdicts depend on the registered clip length (about 20 tokens).
- The 90% intervals for A2 to A7 and the scale test rest on 3 instances each, so they show agreement across
  instances, not population intervals.
- The movie-driven families are not counted (playback sensitivity), and the random RNN's gain grid brackets
  every mouse, so it can never be confirmed or refuted on M1.

## Deviations, in one place

| what | when labelled | effect |
|---|---|---|
| S1: instrument check, disk rules, many fixes after review S-R3 | before any real data | design |
| S2 to S5: analytic hold, streaming recorder, analytic starting knobs, instrument numbers from all units | after the mice stage, before any AI-mouse comparison | operational; rows written before each change set aside and recomputed |
| S6: 9 mice without a movie timescale left out | after the mice were seen | 49 mice compared |
| S7: one retry for missed recordings | before any comparison | 165 of 200 reached on retry |
| S8: truncated language-model path | before any comparison | bit-for-bit identical |
| S9: A2 clips about 9 times longer than registered; readings made explicit | after the tests | no verdict changed |
| Code stamp empty on every pre-retry row (bug, fixed) | found 17 Nov | provenance bracketed by commit times |
| One retry MemoryError (Pythia-1B, one mouse) | logged | that pair missing |

## Where things are

- Registration and amendments: `docs/SLOW.md`. Notebook and reviews S-R1 to S-R4: `docs/SLOW_LOG.md`.
- Code: `nematica/slow/` (measures, recorder, streaming recorder, inputs, data), `scripts/slow_run.py`
  (stages mice, ais, retry, tests), `scripts/slow_test_logic.py` (decision rules on synthetic rows),
  `scripts/slow_lm_trunc_check.py` (amendment S8 check).
- Results (summary numbers only; Allen data stays local): `docs/figures/slow_runs/` (`mice.jsonl`,
  `mice_table.json`, `ais_shard*.jsonl`, `ais.jsonl`, `ais_retry.jsonl`, `tests.json`).
