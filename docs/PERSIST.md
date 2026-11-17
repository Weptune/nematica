# Study 3: generated or carried? (registration draft v0.2, 17 Nov 2026, NOT frozen)

Status: draft. Nothing here is frozen. Feasibility, calibration and an independent review come before
freezing (sections 8 and 9). Notebook: `docs/PERSIST_LOG.md`.

## 1. Where this comes from, and what has already been seen

Study 2 (`docs/SLOW_SUMMARY.md`) found that mouse visual cortex does not carry more internal state than
standard artificial networks, nor slower state relative to its input. Its review (S-R4) and summary
pointed to two patterns, both seen **after** the data and so not findings:
- **L1, persistence.** Splitting natural movie one (30 s) into halves, the mice's internal share holds up
  (median M1 0.58 in the first half, 0.66 in the second), while the noise-free networks whose internal
  state is the preceding context lose it along the clip (GRU 0.21 to 0.01, CfC 0.31 to -0.02, Pythia-14M
  0.40 to 0.06, Pythia-1B 0.66 to 0.25, Mamba about 0.89 to 0.65). The task RNN held (0.82 to 0.80).
- **L2, noise.** On the relative-slowness measure M2, only networks with intrinsic noise came near the mice.

**The hypothesis these suggest:** cortex *generates* trial-to-trial variability continuously while it
processes an input, whereas standard artificial networks without intrinsic noise only *carry* variability
in from before the input, and it decays. Networks that generate variability, by noise or by chaos, should
look like cortex on this axis.

This is not a new idea in neuroscience. Trial-to-trial variability is ubiquitous in cortex; stimulus onset
reduces it (Churchland et al. 2010, Nat Neurosci 13:369), and chaotic recurrent networks generate
variability that inputs can suppress (Rajan, Abbott and Sompolinsky 2010). What this study adds is a
like-for-like test: the same clock-free measurement, the same instrument per animal, held-out brain data,
and the standard artificial families including large language models.

**Data already seen, and therefore not used for any confirmatory test:** natural movie one (NM1) in the
visual-cortex units of all 58 sessions (Study 2's whole mouse dataset, including its half-clip M1). Every
artificial result of Study 2 (all recorded on clips of about 1,500 bins).

## 2. The claims under test

1. **Cortex generates.** In mouse visual cortex watching a 120 s natural movie, the internal part of
   activity does not fade along the movie.
2. **Standard noise-free networks carry.** Their internal part fades along an input of the same recorded
   length, measured at each mouse's instrument, more than the mouse's does.
3. **A generator closes the gap.** Adding intrinsic noise to a noise-free network removes the difference
   on this axis; the same network without noise does not.
4. **Known controls behave as known** (a check of the measure on real conditions, not a finding): a
   noise-free *chaotic* random network generates; a noise-free *stable* random network carries.
5. **What kind of generator** (added in v0.2): in cortex, internal variability grows with the drive, as
   gain fluctuations do (Goris, Movshon and Simoncelli 2014), more than in networks whose variability is
   additive noise or chaos (which input suppresses: Rajan, Abbott and Sompolinsky 2010).

## 3. Data

**Primary (held out): natural movie three (NM3)** in DANDI 000021 (brain_observatory sessions): 120 s,
3,600 frames at 30 Hz, shown 10 times in 2 blocks of 5, back to back within a block. No NM3 spike has been
read in this project. Visual-cortex units, Allen QC and the inclusion rule of Study 2 (`SLOW.md` section 4),
with the spike minimum scaled to the clip length. Mice: every 000021 session with at least 8 valid NM3
repeats and at least 30 included units (count from feasibility F1, metadata only). The 9 mice without a
measurable timescale on NM1 are not excluded in advance; the NM3 instrument is measured on NM3.

**Secondary (held out): NM1 outside visual cortex.** The same 58 sessions' NM1 spikes in units whose peak
channel is not in visual cortex (thalamus, hippocampus and others). These spikes are in the local cache but
have never been measured in this project. Reported per region group, not counted for the claims.

**Discovery set (not confirmatory):** NM1 visual cortex, where L1 was seen. The same measures are reported
on it for continuity, labelled as the discovery set.

Overlap: the primary set uses the same animals as Study 2, a different stimulus and a different part of
each session. So it is held out in data, not in animals. Two-photon data (independent animals) remains for
a later, separate registration (`SLOW.md` section 4 explains the calcium problem).

## 4. Measures

Each repeat of the clip is cut into **8 equal windows** (NM3: 15 s, 750 bins of 20 ms). In window w, the
lag-2 same-repeat and cross-repeat covariances are computed over bin pairs inside the window, with units
centred within each repeat as in Study 2 (`measures.lag_measures`; with 2 windows the code reproduces
Study 2's half-clip M1 exactly). Two amplitudes per window, each unit normalised by its whole-clip
within-repeat variance and averaged over units: the internal amplitude I_w (same minus cross) and the locked
amplitude L_w (cross).

**Primary (v0.2): the drive-time fit.** Across windows, I_w = a x L_w^b x exp(c x t_w), with t_w the
window's centre as a fraction of the clip, fitted by least squares on I_w (windows with L_w <= 0 left out;
at least 4 windows):
- **c, the fade at fixed drive**, per clip length, clipped to [-6, 6]: below 0 the internal part fades along
  the clip whatever the drive does (carried); near 0 it is renewed (generated).
- **b, the drive exponent**: about 0 to 0.6 for an additive internal part seen through the spike instrument,
  above 1 for gain-type variability, lower if drive suppresses internal variability.

**Why v0.1's indices were replaced.** In the first calibration runs (section 8), the simple late-minus-early
indices (P_share, P_amp) separated generated from carried systems only for one fixed envelope of the locked
drive. When the same system's envelope was flattened or reversed, a generated system's index moved by up to
0.6, as far as the generated-carried gap. Mouse and network locked responses to the same movie differ in
envelope, so those indices would confound drive with fading. The fit controls for the drive in each window.
This was decided on synthetic systems only, after seeing partial calibration results (`PERSIST_LOG.md`).
P_share and P_amp are still computed and reported.

Also reported (not tested): the 8-window profiles of M1 and of both amplitudes, the log-linear version of
the fit, and whole-clip M1 and M2 on NM3 (for L2).

## 5. Systems

All recorded through Study 2's streaming recorder at each mouse's own NM3 instrument (`SLOW.md` sections 5,
amendments S3 to S5, S7), with the clip length rule of `SLOW.md` section 4 set to **6,000 bins** at the
median NM3 instrument (Study 2 used 1,500). Three instances each; instance = mouse rank mod 3 as before.

| family | systems | what makes its internal state | role |
|---|---|---|---|
| A2 task RNN | Study 2's trained networks | preceding trials | carrier (as standard) |
| A3 GRU, A5 CfC | Study 2's character networks | preceding text | carrier |
| A6 Pythia | 14M, 160M, 410M (seeds 1 to 3), 1B | preceding context | carrier |
| A7 Mamba | 130M, 370M | preceding context | carrier |
| N3 GRU + noise | A3 with Gaussian noise added to the hidden state at every step (level set in section 8, then fixed) | noise | claims 3 and 5 |
| N6 Pythia-160M + noise | A6 160M with Gaussian noise added to the residual stream after every layer up to the recorded one, and to the recorded layer's MLP input, at every token | noise | claims 3 and 5 |
| K1 chaotic random RNN | Study 2's movie-driven random RNN with g 3.0 and **no noise** | chaos | control (claim 4), claim 5 |
| K2 stable random RNN | the same with g 0.8 and no noise | preceding input | control (claim 4) |
| K3 noisy random RNN | Study 2's A1 (g 1.5, noise 0.1) | noise and chaos | reference generator, claim 5 |

The K controls see NM3 features (computed exactly as Study 2's NM1 features) at movie gain 0.25, and before
every repeat an interlude of 30 to 90 frames of a different movie (NM1), so the state entering each repeat
differs, as the language models' contexts do (`nematica/persist/inputs.driven_rnn`). Why g 3.0 and gain
0.25 for K1: a probe on random features (`PERSIST_LOG.md`, 09:40) showed that input suppresses chaos in the
noise-free network, as Rajan et al. predict. At g 1.5 and Study 2's balanced gain 0.86, the internal part
was gone by the last quarter of the clip. At g 3.0 and gain 0.25 it persisted (early 0.91, late 0.78 of the
total). The controls play the movie at Study 2's playback rule; a network with no undriven timescale (K2)
uses K3's.

Text and task networks get a different preceding context before each repeat, as in Study 2. The playback
sensitivity is repeated on K3 at x0.5 and x2 (section 7).

## 6. Instruments

As Study 2: every network is recorded through the spike model at each mouse's numbers
measured on that mouse's NM3 repeats, checked on the recorded repeats (up to 5 corrections), unreached
recordings excluded and counted. Changes from Study 2, both found while preparing this study:
- The clip pilot records with the same streaming recorder as the real recordings (Study 2's used the
  pre-S3 recorder and made A2's clips about 9 times too long: `SLOW.md` S9).
- A correction never makes a recording longer than 4 x 6,000 bins (`max_bins`). Study 2's rule for a
  recording with no measurable timescale halves the bin width each round. That produced the 44.6 GiB
  MemoryError in Study 2's retry, and three memory kills in this study's calibration.
No retry stage: an unreached recording is excluded and counted.
Mouse inclusion: Study 2's rule, with the spike minimum counted over the first 8 repeats and scaled to
the same rate (200 spikes per 510 s of movie, so 376 over 960 s).

## 7. Hypotheses and decision rules (to be frozen)

Paired, mouse by mouse, d = mouse minus network, on c (claims 1 to 4) and on b (claim 5). Rulers: robust SDs of the mice's c and b.
Margin: the larger of 0.5 ruler units and the bias bound from calibration C3. Per-instance one-sided
Wilcoxon tests (all 3 instances) and a cluster bootstrap over generator cells, as in Study 2, with the S-R4
caveat that 3 clusters show agreement across instances, not a population interval. A family with more than
25% missing pairs is "not testable".

- **H1 (cortex generates):** the mice's median c is above minus the margin, tested one-sided
  (non-inferiority) with the lower end of the 90% bootstrap interval over mice above minus the margin.
- **H2 (carriers fade more than cortex), per noise-free family A2, A3, A5, A6, A7:** confirmed if d exceeds
  the margin with p < 0.05 overall and within each instance and the cluster interval above 0; refuted the
  other way; otherwise not decided. For A6 and A7, every size is tested separately (no bracket rule: S-R4
  showed it decides families with a wide range by construction). A family counts as confirmed if every size is confirmed (A7: both), except A6, which needs 3 of its 4.
  **Claim 2 holds** if at least 4 of the 5 families are confirmed and none has a refuted size.
- **H3 (a generator closes the gap):** N3 and N6 are each equivalent to the mice (90% cluster interval of
  the median d inside plus or minus 0.5 ruler units), and their noise-free versions (A3, A6 160M) are
  confirmed under H2. **Claim 3 holds** if both pairs behave so.
- **H4 (controls):** K1 and K3 not confirmed under H2; K2 confirmed. Reported as a check on the measure;
  if K2 is not confirmed or K1 is, every claim is reported with "the measure did not separate the known
  controls".
- **H5 (what kind of generator):** d_b = mouse b minus network b, per generator system (K1, K3, N3, N6),
  confirmed if d_b exceeds the margin with p < 0.05 overall and within each instance and the cluster
  interval above 0. **Claim 5 holds** if at least 3 of the 4 are confirmed and none refuted. Reported beside
  it: where the mice's b lies relative to the calibration's additive and gain-type ranges.
- **Behaviour:** running and pupil regressed out as in Study 2; claims 1, 2 and 5 reported with and without.
  (Running and arousal are a known source of gain-type variability, so claim 5 with behaviour removed is the
  stricter reading.)
- **Playback:** K3 at x0.5 and x2 playback; if either moves the mice-to-K3 median d by 0.5 ruler units or
  more, the movie-driven controls are reported but not used for claim 4.
- **Secondary:** NM1 outside visual cortex, the mice's P per region group (thalamus, hippocampus, other),
  reported with intervals; the discovery set reported as such.

## 8. Calibration (before freezing; no held-out activity read)

Code: `scripts/persist_calibrate.py`, synthetic systems in `nematica/persist/synthetic.py`. Synthetic
systems (300 units, 10 back-to-back repeats, clip length set so it records as about 6,000 bins) are
recorded through four real instruments: the median, fastest, slowest and noisiest of the 49 Study 2 mice
on NM1 (the only instruments known before NM3 is read), 2 seeds each. A locked part (10 Ornstein-Uhlenbeck
latents) has an amplitude envelope that varies slowly along the clip, as a natural movie's drive does (log
amplitude a slow random process, SD 0.5); internal share 0.4. Internal parts:
- **generated**: stationary Ornstein-Uhlenbeck latents running through the repeats, timescales 0.25, 0.5, 1
  and 2.5 times the locked timescale;
- **carried**: a random state at each repeat's onset decaying with time constant 0.1, 0.25, 0.5 or 2 clip
  lengths, no new variability (as in a deterministic network given a different preceding context);
- **gain-type**: no additive internal part; a slow random gain multiplies the locked part (log-SD 0.3).

Criteria, per index (c from the least-squares fit, c from the log-linear fit, P_share, P_amp), evaluated on
recordings that reached the instrument, as in the data:
- **C1, separation:** at every instrument and seed, every generated run has a higher P than every carried run
  with decay 0.1 to 0.5 clip lengths. (Decay over 2 clip lengths is reported; it must lie below the generated
  median.)
- **C2, locked-content invariance:** for the generated system (timescale 1) and the carried one (0.5 clip
  lengths), P moves by at most a quarter of the gap between their medians when the envelope is flattened,
  reversed or squared.
- **C3, bias bound:** the largest range across the four instruments of the median P of one synthetic
  system; becomes the bias bound in section 7.
- **C4, gain-type variability** counts as generated: its P lies within the range of the generated runs at
  that instrument, widened by the C2 tolerance.
- **C5, drive exponent:** at every instrument and seed, b of every additive generated run is below b of the
  gain-type run.

Selection rule (v0.2, set after the partial results described in section 4): the first index in the order
fitted c, log-linear c, P_share, P_amp that passes C1, C2 and C4 on the full calibration. If none passes,
the persistence claims (1 to 4) are dropped before any held-out data is read. Claim 5 needs C5; if C5 fails,
claim 5 is dropped.

Noise levels for N3 and N6 are set after calibration and before any mouse comparison: the noise variance
that brings the network's whole-clip M1 at the median instrument within 0.05 of its noise-free value is not
achievable in general (noise adds internal share by definition), so the level is instead the one giving the
noisy network's whole-clip M1 equal to the median mouse's NM1 M1 (0.59), fixed and logged before NM3 is read.

## 9. Feasibility (before freezing)

- **F1** (metadata only): NM3 present in the 000021 sessions, valid repeats after invalid intervals, block
  structure, and spike-time download size (each session's spike-time array is about 0.6 to 1.1 GB, because
  spike times are stored for the whole session).
- **F2:** the NM3 spike cache needs millisecond offsets up to 120,000 ms (Study 2 stored uint16, limit
  65,535): a new cache with 32-bit offsets, written before any NM3 spike is measured.
- **F3:** compute and disk for 6,000-bin clips (4 times Study 2's) for the language models and the streaming
  recorder.

## 10. Documentation

As Study 2: every run, crash, review and decision in `PERSIST_LOG.md` with UTC times; amendments dated and
labelled before or after data; independent reviews before freezing (P-R1) and of the results; third-party
data stays local, summary numbers only.
