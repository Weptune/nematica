# Review P1-R1: independent check of preprint draft 1's related-findings paragraph

Draft: "Looking right is not being right: a calibrated benchmark for whole-brain models of *C. elegans*"
(Claude Doc, https://claude.ai/artifact/SB2WgGBuQ3giXQJCu81ZZu, private). Checked at doc revision 58;
corrections applied at revision 60.

Reviewer: an independent agent that wrote none of the draft, read-only, 17 Nov 2026. It checked the
"Related findings in other systems" paragraph (added 17 Nov), the reference entries it uses, and how the
rest of the draft and the repository record relate to the cited works. Two links (PMC pages,
arxiv.org/abs/2502.16238) were not opened because a permission prompt went unanswered; the same works were
checked through other pages (eLife reviews for 106827v2, the CCN 2025 abstract, the arXiv HTML of
2502.16238v1, Randi arXiv 2208.04790v3, the RePEc record of the Nature version).

**Verdict (reviewer's, paraphrased):** all three cited works are real and correctly identified, and the
paragraph describes their direction fairly. It had one factual error and some overstatements. The larger
issue was outside the paragraph: the Introduction claimed two contributions without crediting Feather and
Sourmpis, and Result 4 restated Randi et al.'s headline finding without citing it.

## Findings and responses

| # | Finding | Response (rev 60) |
|---|---|---|
| 1 | Error: "The same gap has since been reported in mouse cortex." Sourmpis et al. came first (bioRxiv Sep 2024; eLife RP Jun 2025, VOR Jan 2026); this project began Oct 2026. | Fixed: "A related gap was reported earlier". |
| 2 | Sourmpis summary credited "excitatory and inhibitory structure and spiking dynamics"; the source says Dale's law and local-only inhibition matter most, and spiking helped least (not significant). | Fixed: "some biological constraints, chiefly Dale's law and local-only inhibition". |
| 3 | "Recurrent networks ... generalize poorly" reads as all fitted RNNs; the source means generic (sigmoid) RNNs. | Fixed: "generic recurrent networks". |
| 4 | "The same gap": Sourmpis uses task trials (whisker detection, six areas), and its in vivo test is probably against behaviour, not neural activity during the light. | Fixed: "a related gap ... on task trials across six cortical areas". The behavioural-readout point was not confirmed from the full text, so the draft does not state it. |
| 5 | The paragraph hid a real contrast: Sourmpis finds biological constraints help, while this draft finds connectome-restricted kernels far worse than unrestricted ones and the connectome-constrained model outside on pattern. | Fixed: one sentence states the contrast. |
| 6a | The Introduction lists the worm-variation ruler and "realism at rest does not predict realism under perturbation" as contributions without citing Feather et al. or Sourmpis et al. (the repo's own STRATEGY note already says Sourmpis covers mice). | Fixed: both items now cite the prior work and state what is new here (worm, whole-brain, two-sided, calibrated). |
| 6b | Result 4's "the wiring diagram is a poor map of where signals go" restates Randi et al.'s headline finding without citation (the README already credits it). | Fixed: citation added. |
| 7 | Heading "in other systems" does not fit a paragraph that includes the worm. | Fixed: "Related findings". |
| 8 | "Our ruler applies that demand" undersells it and is loose about Feather: their test is one-sided (a model may surpass brain-to-brain similarity), excludes perturbation, and treats time as optional. | Fixed: the paragraph says the ruler extends the demand (two-sided, dynamics, perturbation) and describes Feather's pass rule. |
| 9 | Sourmpis reference lacks eLife volume and article number (eLife <vol>:RP106827); a newer version, eLife.106827.3, exists. | Open: check the citation format before submission. |
| 10 | Paragraph links (PMC, arXiv PDF) differed from the reference links (DOI, abs page). | Fixed: the paragraph now uses the DOIs and the abs page. |
| (not checked by reviewer) | Whether earlier worm work, for example Creamer, Leifer and Pillow 2024, already shows rest-fitted models failing under perturbation. | Checked by me: the draft already discusses Creamer et al.'s three published models in detail (Result 2, "The published models need care"), scores them, and notes that for them the "right at rest, wrong under stimulation" pattern does not apply because they also fail at rest. Their paper fits perturbation data directly and reports how well that model captures perturbation responses; it does not claim rest realism fails to predict perturbation realism. No change needed. |

Verified correct by the reviewer: Randi et al. 2023 (Nature 623, 406 to 414) and its abstract claim;
Feather et al. 2025 authors, title and arXiv number; Sourmpis et al. authors, title and DOI; the project's
own claim about the ruler against "The ruler" section and the README.
