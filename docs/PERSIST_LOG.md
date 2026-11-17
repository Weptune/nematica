# Study 3 notebook: generated or carried?

Every run, failure, review and decision, with UTC times. Registration: `docs/PERSIST.md`.

## 17 Nov 2026

### Start (notebook opened 08:18 UTC)

The user approved drafting a registration for a test of Study 2's leads ("yes. keep working"). The
question: does cortex generate trial-to-trial variability continuously, while noise-free artificial
networks only carry it in from before an input? Draft v0.1 of `PERSIST.md` written. What has been seen is
listed in its section 1: Study 2's NM1 visual-cortex data (where the lead was found) and every Study 2
network result. The confirmatory data is natural movie three (120 s), which this project has never read,
plus NM1 outside visual cortex as a secondary held-out set (cached, never measured).

Background checked: stimulus onset quenches variability across cortex (Churchland et al. 2010); chaotic
recurrent networks generate variability that inputs can suppress (Rajan, Abbott and Sompolinsky 2010). The
study is framed as a like-for-like measurement, not as a new idea.

### Feasibility F1 started (shortly before 08:18 UTC)

`scripts/persist_feasibility.py` reads only stimulus tables and array shapes, over HTTP range requests, for
each of the 58 sessions; it writes `docs/figures/persist/feasibility.json`. First sessions: NM3 present in
000021 sessions, 10 complete repeats in 2 blocks, 120.1 s each; one session keeps 8 of 10 after invalid
intervals. Spike-time arrays are 0.6 to 1.1 GB per session (whole-session spike times), so reading NM3
spikes means downloading about that much per session again (Study 2's cache kept only NM1).

### Windowed measures, and calibration started (08:25 UTC)

- `nematica/persist/measures.py`: windowed lag-2 measures, streamed over the recorder's unit blocks. Check
  (`scripts/persist_window_check.py`): with 2 windows they equal Study 2's half-clip M1
  exactly (0.5549 and 0.5399 both ways), and the streamed and materialised versions of 8 windows agree to
  2e-16.
- `nematica/slow/stream.record_stream` gained an optional `extra(rec, inc)` hook that measures further
  quantities on the same recording and analysed units. With the hook absent, nothing changes. (Study 2 is
  closed; its pipeline does not pass the hook.)
- Three trial runs (median instrument, generated and carried; fastest, generated) took 28 to 59 s each.
  They showed two things, and the draft was changed before any calibration run was kept:
  1. The log-ratio P_amp was undefined for a carried system, because its faded internal part was estimated
     below 0. It is now bounded: (late - early) / (|late| + |early|).
  2. The window M1 of a generated system swings with the locked envelope (0.29 to 0.62 across windows),
     which is exactly the confound C2 tests.
- Fixed in the calibration script before the run: the random draws no longer depend on the envelope
  variant. Before the fix, the flattened, reversed and squared envelopes had been different random
  envelopes, not transforms of the same one.
- The draft now states the calibration criteria precisely (section 8). The noise level for N3 and N6 is set
  to give whole-clip M1 equal to the median mouse's NM1 M1 (0.59), because noise always adds internal share.
- 120 calibration runs started in 2 shards (`scripts/persist_calibrate.py`), writing
  `docs/figures/persist/calibration_runs.jsonl`.
- Study 2's working scripts were found uncommitted and are archived (`SLOW_LOG.md`, same time).

### Feasibility F1 done; prefetch started; a calibration shard killed for memory (08:43 UTC)

- **F1 (metadata only):** all 58 sessions read without error. NM3 is in all 32 DANDI 000021 sessions and
  in none of the 26 000022 sessions. Valid repeats after Allen's invalid intervals: 10 in 27 sessions, 9 in
  2, 8 in 3. All have 2 blocks of 5. The spike-time arrays to download total 28.7 GB (0.6 to 1.1 GB per
  session). Summary: `docs/figures/persist/feasibility.json`.
- **F2:** `nematica/persist/data.py` caches NM3 spikes like Study 2's cache, with uint32 millisecond offsets
  (`scripts/persist_prefetch.py`). It started at 08:43 UTC. Caching only: no statistic of NM3
  activity is computed before freezing.
- **Noise systems** (`nematica/persist/inputs.py`): with noise 0, the GRU and Pythia functions equal Study
  2's exactly; with noise, repeats with identical contexts differ (`scripts/persist_noise_check.py`).
- **Calibration shard 0 was killed for memory** (4.9 GB anonymous) on a fastest-instrument run, whose
  synthetic clip is 12,840 native steps; the prefetch was not yet running. Shard 1 continues. Shard 0 will
  be rerun alone afterwards (the run is resumable).

### Partial calibration: the simple indices fail; draft v0.2 (08:43 to 08:54 UTC)

Both calibration shards were killed for memory on the fastest instrument (4.7 and 4.9 GB anonymous; the
synthetic clip there is 12,840 native steps of 300 units). 41 runs survived (30 median, 11 fastest). The
calibration was restarted as a single process, which resumes from the saved rows.

What the 41 runs show (`scripts/persist_calibrate.py --summary` on partial data; synthetic systems only, no
mouse activity):
- **P_share and P_amp separate generated from carried systems only for a fixed envelope (C1 passes, C2
  fails).** Flattening or reversing the locked envelope of the same generated system moved P_share by up
  to 0.60, against a generated-carried gap of 0.48. P_amp failed the same way. Mouse and network locked
  responses to one movie differ in envelope, so these indices would confound drive with fading.
- **A fit that controls for the drive works on the same runs.** Across windows, internal amplitude
  I_w = a x L_w^b x exp(c x t_w), with L_w the locked amplitude. Log-linear version: c for generated systems
  -0.44 to +0.31; for carried systems with decay of 0.1 to 0.5 clip lengths, -7.4 to -0.4; under envelope
  changes, generated c stays within about 0.3. The least-squares version separates more strongly, but for
  fast-fading carried systems it gives very large values (to -199), so it is clipped to [-6, 6].
- **The drive exponent b separates additive from gain-type variability** (generated runs 0.26 to 0.60,
  gain-type 2.0, carried about 1), which opens a better question than fading alone (below).
- One run (median instrument, seed 1, generated system, squared envelope) did not reach the instrument
  (white share 0.996, almost no signal). Its indices were nonsense (P_share -1.38, b 14.8). The criteria
  are now evaluated on reached runs only, as in the data.

**Draft v0.2** (`PERSIST.md`):
- primary measure: the drive-time fit (c for fading at fixed drive, b for drive dependence);
- a fifth claim: what kind of generator cortex is. Mice: gain-type, growing with drive (Goris et al. 2014).
  Networks: additive noise or chaos, which input suppresses (Rajan et al. 2010);
- a selection rule for the index, plus C5 for b.

Labelled honestly: these choices were made after seeing partial calibration results on synthetic systems.
No held-out (NM3) activity has been measured; the NM3 prefetch only caches spikes.

A wider concern, to raise with the user: as first drafted, claims 1 to 3 come close to a known fact.
Brains are noisy. Standard networks at inference are deterministic, so their trial-to-trial variability
can only be carried in from the context. Claim 5, which asks what kind of variability cortex generates
and compares it with networks that generate variability in different ways, is the part with more
potential to say something new on the networks' side. The brain side alone overlaps recent work on
partitioning variability (Goris et al. 2014; Rupasinghe, Charles and Pillow, eLife 2026).
