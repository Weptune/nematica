# Study 3, start to finish: generated or carried, and what kind of generator? (17 Nov 2026; stopped)

The full record is `docs/PERSIST.md` (the draft registration, v0.1 to v0.3, never frozen) and
`docs/PERSIST_LOG.md` (the notebook, UTC times). Where this file and those disagree, they are the record.

## Why

Study 2 (`docs/SLOW_SUMMARY.md`) found no support for "cortex carries more, slower internal state than
artificial networks". Two descriptive patterns, seen after its data, were the leads:
- mouse cortex keeps its trial-to-trial variability along a clip, while noise-free networks lose the
  variability they carry in from the preceding context;
- on relative slowness, only networks with intrinsic noise came near the mice.

Study 3 was drafted to test these on data never analysed in this project: natural movie three (120 s) in
32 mice. The user asked for a registration ("yes. keep working"). Later, after the first calibration
failed, the user chose to narrow the study to its fifth claim.

## What happened, in order (UTC)

| when | step | outcome |
|---|---|---|
| 08:18 | Draft v0.1 | four claims: cortex generates; noise-free networks carry; adding noise closes the gap; known controls behave |
| 08:13 to 08:43 | Feasibility (metadata only) | NM3 in all 32 DANDI 000021 sessions, 8 to 10 valid repeats, 2 blocks of 5 |
| 08:25 | Windowed measures | with 2 windows they equal Study 2's half-clip measure exactly |
| 08:43 to 09:10 | NM3 spikes cached | 32 sessions, 897 MB, local; no statistic computed |
| 08:43 to 08:54 | Partial calibration | simple fading indices confounded by the drive's time course; draft v0.2 replaces them with a fit (c: fading at fixed drive; b: dependence on drive) and adds claim 5 (what kind of generator) |
| 09:13 | Memory failures traced | Study 2's correction rule doubled recordings without limit; a bin cap added |
| 09:13 to 09:23 | Chaos probe | input suppresses chaos in noise-free random networks (Rajan et al. 2010); controls re-chosen |
| 09:58 | Full calibration v0.2 | no index passes its criteria; claims 1 to 4 dropped by the rule written before the run |
| 12:57 | v0.3 | the user chose claim 5 only; new criteria written before any v0.3 run |
| 13:44 | Calibration v0.3 | claim 5 fails all three criteria; the study stops |

## What the calibrations showed

Every result here comes from synthetic systems with known answers, recorded through four real mouse
instruments. No held-out mouse activity was measured.
- **Fading along a clip** can be told apart from steady generation only if the drive's time course is held
  fixed. Late-minus-early indices moved by as much under a flattened or reversed drive as between the two
  kinds of system. A fit that controls for the drive separated them at every instrument (fitted c). It
  still failed one registered criterion (carried systems moved further under some envelopes) and the
  gain-type check, so by the rule it was not used.
- **The drive exponent b** separates additive from gain-type variability in bulk (additive -0.14 to 0.84;
  gain-type mostly above 1), but not run by run (it failed in 1 of 8 cells), not in order of gain size, and
  not independently of the drive's time course (gain-type b moved by up to 12.8). With 10 repeats and 8
  windows, a slow gain is sampled too sparsely, and the exponential spike model mixes additive and
  multiplicative effects.
- Synthetic gain-type systems rarely reach the mice's instrument (5 of 48): their white share stays far
  below the mice's.

## What it means

Neither question can be answered with this measurement at this data size. That is a result about the
tool, not about brains or networks. Both registered stopping rules worked as intended: each study stopped
before held-out data could be spent on a measure that failed its own checks.

On framing: claims 1 to 3 were close to a known fact. Brains are noisy, and networks run at inference are
deterministic. Claim 5 had more potential, but on the brain side it overlaps existing work on partitioning
variability (Goris, Movshon and Simoncelli 2014; Rupasinghe, Charles and Pillow, eLife 2026).

## What remains useful

- The held-out NM3 data (cached locally) and its loaders.
- Windowed measures; the bin cap (`record_stream(max_bins=...)`), which removes a memory failure inherited
  from Study 2; noise versions of the GRU and Pythia that match Study 2's functions exactly at noise 0;
  movie-driven controls for any clip length, with interludes.
- Study 2's working scripts, archived in `scripts/slow_scratch/`.

## Where things are

`docs/PERSIST.md`, `docs/PERSIST_LOG.md`; `nematica/persist/`; `scripts/persist_*.py`;
`docs/figures/persist/` (feasibility, calibration runs and summaries, dry-run rows).
