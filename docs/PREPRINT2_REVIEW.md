# Review P-R1: independent check of preprint draft 2 against the project record

Draft: "Recording networks like brains: an animal-by-animal comparison of internal state in mouse visual
cortex and artificial neural networks" (Claude Doc, https://claude.ai/artifact/SfyEeCsF5JuT7tnAspUTSY,
private). Checked at doc revision 14; corrections applied at revision 46.

Reviewer: an independent agent that wrote none of the draft, read-only on the repository, 17 Nov 2026
(finished about 17:50 UTC). It read the whole draft and both figures and checked them against
`docs/MAP.md`, `docs/MAP_SUMMARY.md`, `docs/SLOW.md`, `docs/SLOW_LOG.md`, `docs/SLOW_SUMMARY.md`,
`docs/figures/slow_runs/tests.json`, `mice.jsonl`, `docs/PERSIST*.md`, `docs/BARCODE*.md` and
`scripts/plot_slow_paper.py`. It opened every related-work link.

**Verdict (reviewer's, paraphrased):** the numbers are largely accurate and the related work is cited
fairly, but before correction the draft was not accurate to the record. It had five errors, dropped caveats
the record carries, and generalised two conclusions beyond what was shown.

**What matched:** every number in the verdict table and the headline statistics: 1.8 SDs, 0.107 in
0.031 to 0.228, 33 of 35, 1.40 [1.24, 1.59], p = 2e-8, 31 mice at 3.3 SDs, 17/18 split, 6%,
+0.03 [-0.08, +0.73], 58 and 49 mice, nine amendments, four reviews, M1 0.59, M2 0.69, 48 of 49, rho 0.959
and 0.830, 24 mice, 37-fold, p = 6e-8, margins 1.15 and 2.12, H3 1.95 [1.37, 3.19], Pythia M1 values,
the Result 4 numbers, and both figures against their data.

## Findings and responses

Each response says what changed in the draft (rev 46). "Fixed" means the draft now says what the record
says.

### Errors

| # | Finding | Response |
|---|---|---|
| 1 | Figure 2 caption said the grey gain medians "bracket every mouse"; the spiking network's run from about 0 to 0.56, below the mouse median. Only the random RNN brackets the mice. | Fixed: the caption says the random RNN's gains bracket every mouse and the spiking network's sit below the median. |
| 2 | Methods said "20 to 60 valid repeats"; the movie was shown 20 or 60 times and valid repeats run from 10 to 60 (S1 excludes fewer than 10). | Fixed. |
| 3 | Methods described only Study 2, so a reader would think Results 1 and 2 used QC units on the movie. The map study used spontaneous activity, `good` units without default QC (at most 2,400), groups of 8, crops of 5,000 timescales, and a different measure (slow memory). | Fixed: a separate "Map study" methods paragraph, and Result 1 now says it concerns spontaneous activity. |
| 4 | Result 2's limit said the per-mouse rule was registered "before any network was recorded per mouse"; the random RNN's values at 5 of these mice (the transfer check) were already known (MAP.md amendment 27). | Fixed with the record's wording: before the other 30 and before the slow-drive network at any single mouse. |
| 5 | "In the noise-free networks, internal state ... fades within a clip"; the task RNN holds up (0.82, 0.80) and Mamba fades only partly (0.89, 0.65). | Fixed: "most context-driven networks", with the half-clip numbers and the task RNN as the exception. |

### Overstatements and missing caveats

| # | Finding | Response |
|---|---|---|
| 6 | Result 2 omitted review 16's QC-drift and excluded-mice concerns (both favour the result; neither check was run for the per-mouse test) and how 58 became 35. | Fixed: added to Result 2's limits. |
| 7 | "Transformer sizes bracket the mice" is stronger than the record (22 of 40 inside, 18 above, 9 unpaired). | Fixed: "the range of sizes contains the median mouse" in table, abstract and discussion, with the counts. |
| 8 | Missing S-R4's M2 reading ("if anything network slower" for CfC, Pythia, Mamba) and its stimulus dependence (shuffled M2 32.7). | Fixed: table cells annotated, and a paragraph on what M2 is relative to. |
| 9 | Claim 3 lacked the caveat that the registered grid could not reach the mice on M2, and the playback inheritance. | Fixed. |
| 10 | The spiking network is unmatched on both measures, not only M2. | Fixed: in Methods and the M1 cell. |
| 11 | The S6 exclusion of 9 mice was not described as post hoc, nor how they differ. | Fixed: in Methods and the limits. |
| 12 | "Corrected ... until they were within tolerance" overstates; at most 5 then 10 corrections, 35 unreached, 1 MemoryError. | Fixed. |
| 13 | S-R4 reproduced Study 2's numbers only; the code-stamp gap was omitted. | Fixed: scope stated, gap stated. |
| 14 | Study 3's criteria were called "registered"; Study 3 was never frozen. | Fixed: "draft rules, never frozen, with each version's criteria written before its calibration run". |
| 15 | Result 4's general conclusion went beyond the record; repeats were 8 to 10, not 10. | Fixed: limited to these two measures at this data size; 8 to 10. |
| 16 | Barcoding "passed calibration of these measures" ignores that the drive exponent failed; the stop was the owner's choice after review B-R1, which also found blocking rule problems. | Fixed. |
| 17 | "Matching the instrument per animal is necessary for these comparisons" (abstract) goes beyond what was shown (one network, one measure). | Fixed: "was necessary for the slow-memory comparison". |
| 18 | Results 2 and 3 look contradictory (random network below the mice, then its gains bracket every mouse) without explaining the different measure, stimulus and set-up. | Fixed: a sentence in the Discussion. |
| 19 | "On M2, only networks with intrinsic noise come near the mice" is undercut by tests.json: Pythia, Mamba and the task RNN are within about one ruler unit, and the task RNN's internal state is faster than the mice's (M2 0.47 against 0.69). This sentence came from SLOW_SUMMARY, so the record itself carries the inconsistency. | Fixed in the draft (softened, with the numbers). The record is corrected too: see below. |

### Minor

| Finding | Response |
|---|---|
| "Three results follow" but four Results; "a clock-free measure" when there are two. | Fixed. |
| Playback check was run on the random RNN only; the spiking network excluded by rule. | Fixed. |
| A2 clip limit should name the task RNN, the 23 of 49 capped recordings, and that no verdict changed. | Fixed. |
| "Seven families": only five were counted. | Fixed in abstract and discussion. |
| One instance per family per mouse (by rank); Pythia-1B instances differ in text, not seed. | Fixed. |
| Pupil data exist for 26 mice only. | Fixed. |
| Lags run only to a quarter clip (7.5 s). | Fixed. |
| Envelope shift up to 0.64 (0.60 was the partial run); "1 of 8 cells" ambiguous. | Fixed. |
| "Wrong in both directions" gives no specifics a reader can check. | Removed (the phrase is not in MAP_SUMMARY). |
| Two citations without authors (Soni et al.; Chun et al.); Rupasinghe et al. is a reviewed preprint. | Fixed. |
| Code list omitted `scripts/map_permouse.py` and `scripts/map_slowdrive.py`. | Fixed. Repository confirmed public through the GitHub API (17 Nov). |
| Figure 1 is dark, Figure 2 light. | Fixed (17 Nov, later): Figure 1 redrawn in Figure 2's light style from the same data by `scripts/plot_map_paper.py` (`docs/figures/slow_paper/fig1_permouse.png`); counts recomputed: 33 of 35 lower, 31 of 31 higher. |
| Gokce et al.: "asks whether" undersells that the paper answers. | Fixed: states its finding. |
| "We do not apply generic Poisson noise" sits awkwardly with the draft's own Poisson spike model. | Reworded: "Rather than adding generic Poisson noise, we record ...". |

## Correction carried back into the record

Finding 19 applies to `docs/SLOW_SUMMARY.md` itself ("only networks with internal noise come near the mice;
every noise-free network's internal state is relatively slower"). The task-trained RNN is noise-free and its
internal state is relatively faster than the mice's (M2 0.47 against 0.69, tests.json). The summary line is
now marked "[CORRECTED by review P-R1, 17 Nov]" with the fix; the original words are kept.

## Still open before any sharing

- Author list and affiliations.
- The project owner's go-ahead. Nothing has been sent or shared.
