# Test R: the emulator's rest half on other labs' immobilised worms

Status: **stopped at feasibility** (no dataset passes the pre-set rule; see the log). Written 17 Nov 2026 (UTC) before any file of these datasets was
opened. Context: `docs/STRATEGY_2026-11-17.md`, last section; README "A worm emulator" and "Testing the
emulator recipe on data it was not built on".

## Why

The emulator recipe (slow interacting brain-wide states, individuality, causal kernels from pokes,
neuron-level observation) passes rest and pokes on the 113 atlas worms it was built on, fails narrowly on
unc-31 worms (3 of 5 seeds against a registered 4) and fails at rest on freely moving Atanas worms. The
exploratory reading was that immobilised worms under light every 30 s may be dominated by slow shared
states, while moving worms are not. The rest half can be tested on unseen immobilised worms from other
labs without new experiments. That separates two explanations of test T's failure: the recipe is specific
to the atlas lab's conditions, or it is specific to immobilised worms in general.

## Candidate datasets (WormID corpus, Sprague et al. 2024; all CC BY 4.0)

| DANDI | Lab code | Worms (paper) | Preparation (paper) | Rate (paper) | Note |
|---|---|---|---|---|---|
| 000565 | SK1 | 21 | immobilised, microfluidic chip | 1.04 Hz | "a subset" have unstimulated calcium imaging |
| 000541 | EY | 21 | probably immobilised (chip) | about 4 Hz | NeuroPAL paper; may include chemosensory stimuli |
| 000692 | KK | 9 (7 subjects) | semi-restricted | 1.67 Hz | "spontaneous" |
| 000776 | SF | 38 | freely moving | 1.7 Hz | the Atanas set: already seen (test T), **excluded** |

## Feasibility stop rule (fixed before opening any file)

Metadata only: group structure, array shapes, time stamps or rates, neuron labels, stimulus tables. No
activity values are read or summarised at this stage.

A dataset is **usable** if all of these hold:
1. At least 12 worms with calcium traces (the unc-31 test U used 13 worms in pools of 4 to 5).
2. Each counted worm has at least 500 s of recording with no stimulus delivered, as one stretch or as
   stretches of at least 120 s (stimulus periods, if any, are cut out with 30 s after each).
3. Frame interval between 0.25 s and 0.75 s, or faster than 0.25 s and evenly divisible down to about
   0.5 s by keeping every k-th frame after averaging k frames. Slower than 0.75 s is **not usable**: the
   recipe's frozen constants are in frames, and test T already stretched them to 0.6 s.
4. At least 40 traces per worm carry a neuron name that maps to an atlas class used by the emulator.

If no dataset is usable, test R stops here and the reason is recorded. If one or more are usable, the
registration (adapter, frozen recipe, controls, informativeness rule, pass rule, predictions) is written
below and reviewed before any activity is read.

## Feasibility log

Metadata only (file headers, DANDI asset listings). No activity values were read. Scripts:
`scripts/emur_feasibility.py` (full header walk; too slow on these files, about a minute or more per file
because of per-frame segmentation groups) and a targeted probe of named groups (same rules).

- **000776 (SF, Atanas)**: excluded before checking (already seen in test T).
- **000692 (KK)**: DANDI lists 9 files from 7 subjects, all "NeuroPAL+ Calcium Imaging without
  Stimulation", 8.6 to 9.4 GB each. **Fails rule 1** (fewer than 12 worms). Not opened.
- **000541 (EY)**: 21 files of about 1.5 GB. The first file holds `CalciumImageSeries` of 962 volumes at
  4.0 Hz, that is 240 s, with per-frame segmentation and 181 ROIs. The other 20 files are the same size.
  **Fails rule 2** (at least 500 s per worm).
- **000565 (SK1, FOCO lab, UCSF)**: 21 files, every session described as "NeuroPAL and calcium imaging
  of immobilized worm with optogenetic stimulus". A 4.3 GB file holds `SignalCalciumImResponseSeries`
  (dF/F) of 1500 frames by 118 ROIs at 1.04 Hz (about 1440 s), with sparse neuron names (`NeuronIDs`).
  A 0.8 GB file holds NeuroPAL images only. The `stimulus/presentation` and `stimulus/templates` groups
  are empty in both, so no stimulation times are recorded. **Fails rule 3** (0.96 s per frame, slower
  than 0.75 s), whatever the count of files with calcium.

**Outcome: no dataset is usable under the rule written before opening the files. Test R stops at
feasibility.** Two notes for the record, neither acted on:
1. 000692 passes the frame-rate rule (1.67 Hz in the corpus paper) and is "without stimulation", but has 9
   worms. Admitting it would need an amendment, written after this metadata check (not after any
   activity), with smaller pools and the informativeness rule to protect against a ruler too weak to fail
   anything. That is the project owner's decision.
2. 000565's sessions are described as optogenetic stimulation, but no stimulation times are stored. If the
   FOCO lab could share them, these worms would be the only public candidate for testing the poke half
   in a second lab. Contacting a lab needs the project owner's go-ahead.
