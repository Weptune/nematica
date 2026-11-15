# Study 2 lab notebook (docs/SLOW.md)

Every run, failure, restart and decision, in order, written at the time. Times are local (IST) unless
marked UTC.

## 15 Nov 2026

**16:16. Decision to start study 2.** The user asked whether the main question can be at least partly
answered, and what it would take. Answer given: a partial answer is within reach if the slow-internal-
state thesis is tested on every AI family with a clock-free measure, mouse by mouse, in many mice, and
replicated. The user agreed. They framed it as a long-term project and asked that everything be
documented.

**16:20. Feasibility check F1 started** (`/tmp/s7/movies.py`; metadata only: the
`intervals/*natural_movie*` tables of every Allen session, streamed; no spike read).

**16:25. Draft registration written** (`docs/SLOW.md` v0, not frozen). Main choices and why:
- *Repeat-based measures (M1 internal share, M2 internal over stimulus-locked half-life).* Both are
  computed inside one system, so they need no conversion between a mouse's milliseconds and a network's
  steps or tokens. The map study's main blocker was exactly that conversion.
- *Per-mouse instruments and paired tests,* because of the map study's transfer result.
- *Freeze only after feasibility and calibration,* to avoid the map study's chain of amendments.

**16:40. Estimator implemented and checked on synthetic systems** (`nematica/slow/measures.py`,
`nematica/slow/synthetic.py`). The systems have a known internal share (0.2, 0.5, 0.8), stimulus-locked
timescale 10 and internal timescale 10 or 40 samples, 20 repeats of 900 samples, 100 units, and white
noise of 0.7 SD.
- Recovered M1: 0.197 to 0.803 against the true 0.2 to 0.8.
- Recovered M2: 1.05 to 1.07 against a true ratio of 1, and 3.94 to 4.02 against 4.
- Noise share: 0.33, which is exact.

Not yet tested: spiking instruments, pooling, short clips, few repeats. These belong to F5.

**17:00. F1 done.** All 58 sessions readable (0 errors):
- 32 brain_observatory sessions: movie one 20 times (2 blocks of 10) and movie three 10 times (2 blocks);
- 26 functional_connectivity sessions: movie one 60 times (2 blocks) and a shuffled movie one 20 times;
- movie one per mouse: 600 s (20 repeats) or 1,803 s (60 repeats).

Decision: **movie one is the common clip** (every mouse has it). The shuffled version gives a within-mouse
control in 26 mice. Metadata summary: `docs/figures/slow_f1_movie_meta.json`.

**Next:**
- F2: an input pipeline for each AI family (movie features for RNN, spiking and vision networks; repeated
  text after varied context for language models and character networks).
- F4: the compute budget.
- F5: calibration through each mouse's instrument (spiking, pooling, 20 against 60 repeats).
- F3: choosing the replication dataset.

**17:05. F5 started: the measures through the Allen spike instrument** (synthetic only).
`nematica/slow/record.py`: a system's native activity runs continuously; the clip occupies known steps
and is repeated back to back, as in the Allen blocks. It is matched and recorded with the map study's
registered spike model at the Allen median single-unit numbers (2.60 bins per timescale, 0.066 spikes
per bin, white share 0.90, rate spread 1.22), then cut into equal repeat windows. Synthetic systems
(`synthetic.continuous`) have 480 units, 20 repeats of 4,000 native steps, a stimulus-locked part
(timescale 6) identical on every repeat, and an internal part running continuously.

**17:10. First pass** (one seed; shares 0.2, 0.5, 0.8; ratio 4):
- M1 kept the order (0.35, 0.66, 0.89) but read high.
- M2 by half-life read 0.5 to 1.7 against a true ratio of 4. Two causes:
  - both timescales are only 2 to 4 recorded bins at this instrument, so a half-life is crude;
  - the spike model's exponential mixes the two parts multiplicatively, so internal fluctuations modulate
    the locked response.
- Decision: also compute an **integrated autocorrelation time** (the sum of the normalised autocovariance
  up to its first zero), which is more robust at a few samples. M2_int is the ratio of the two integrated
  times. Fix: repeat windows are now cut one sample short, so that rounding never drops a repeat (one run
  had 19 of 20).

**17:15 to 17:40. C1 sweeps** (2 seeds per level; `/tmp/s7/sweep.py`):

| measure | sweep | groups of 8: rho | single units: rho |
|---|---|---|---|
| M1 | internal share 0.1 to 0.8 | 0.98 | 0.98 |
| M2, half-life | ratio 1 to 16 | 0.94 | 0.94 |
| M2, integral (M2_int) | ratio 1 to 16 | **0.98** (0.8 to 7.8) | **0.98** (0.8 to 7.5) |

Cross-talk (reported, not a gate):
- M2_int moves with share (rho 0.76 to 0.81 over the M1 sweep);
- M1 moves slightly with the ratio (0.61 to 0.72).

Pooling is not needed: repeats already average out spike noise, because noise is independent across
repeats. **Decisions (draft):** M2 is defined as the integral ratio (the half-life ratio is reported); single
units, no pooling.

**17:45. C4 sweep started** (`/tmp/s7/c4.py`, background): the measures must not move with knobs the
instrument does not match. Knobs: native timescale (2/8, 6/24, 18/72 steps), population (200, 480,
1,200), repeats (20, 60), clip length (2,000, 4,000, 8,000 steps). Ratio = range of the means across a
knob's levels over the C1 range (M1 0.66, M2_int 6.4, M2 2.3). Results logged when it finishes.

(Clock note: after a machine restart the system clock reads about 12:00 in an unlabelled zone; the
times below continue the notebook's own sequence, not that clock.)

**18:00. F2 started: the movie for the AIs.**
- The Allen NWB files hold the movie's timing but not its frames. The frames are on Allen's public bucket:
  `visual-coding-neuropixels/ecephys-cache/natural_movie_templates/natural_movie_1.h5` (166,348,896
  bytes). Downloaded to `data/external/allen/` (git-ignored; third-party, local only).
- The file is named `.h5` but is not HDF5: it is a NumPy array saved under Python 2, shape (900, 304,
  608), uint8 (grey levels 54 to 255 on frame 0, mean about 126). Read with `allow_pickle=False`.
- `nematica/slow/inputs.py`:
  - `movie_features`: block-average each frame by 8 (to 38 x 76), centre per pixel, keep the top 64
    principal components, each scaled to unit variance. Cached to `data/derived/` (git-ignored, derived
    from third-party data). The features are smooth: frame-to-frame correlation 0.97 at 1 frame, 0.91 at
    2, 0.69 at 5, 0.37 at 10, about 0 at 30 frames (1 s).
  - `steps_per_frame`: the clip plays at the same speed relative to each system's own clock as for the
    mouse. A mouse with timescale `bins_per_tau` 20 ms bins sees bins_per_tau x 20 / 33.3 frames per
    timescale; a system with native timescale tau gets tau / that steps per frame (fractional allowed).
  - `driven_random_rnn`: family A1 with a fixed random input matrix B (variance 1/64), the clip shown R
    times back to back, as in an Allen block, after a 2,000-step burn-in on a blank input.
- The undriven A1 network (480 units, g 1.5) has a native timescale (`tau_med`) of 27.2 steps, so at the
  Allen median mouse (2.60 bins per timescale) each frame lasts 17.4 steps and one repeat 15,670 steps.
- Open decision, noted for the registration: the playback speed uses the **undriven** native timescale.
  The mouse's `bins_per_tau` was measured over the whole session, which mixes stimuli; driving the network
  changes its timescale. The alternative (match the driven timescale by iteration) is a sensitivity.

**18:10. F2 probe: how much of the driven A1 network is internal?** Raw native activity, no instrument, 10
repeats, thinned to about 3 samples per frame (`/tmp/s7/f2_rnn.py`, seed 0):

| input gain | M1 (internal share) | M2_int (internal / locked time) |
|---|---|---|
| 0.05 | 0.91 | 0.51 |
| 0.1 | 0.75 | 0.40 |
| 0.25 | 0.44 | 0.19 |
| 0.5 | 0.22 | 0.13 |
| 1 | 0.10 | 0.07 |
| 2 | 0.06 | 0.05 |
| 4 | 0.04 | 0.04 |

- The gain is a free parameter, and it sets M1 almost by itself, from nearly all internal to nearly all
  locked. So **M1 alone cannot separate this family from a mouse**: some gain will match any mouse.
- M2_int stays **below 1 at every gain**: what is not driven by the movie is faster than what is. The
  internal part is the network's own chaos and noise (time about one native timescale or less), while the
  locked part inherits the movie's slow features.
- A principled single gain exists: the movie input is as strong as the recurrent input. In the undriven
  network the recurrent input g W x has SD 0.85 per unit; the movie input B u has SD 1.00 at gain 1. So
  "balanced" is gain 0.86, where M1 is about 0.1.
- **Consequence for the draft (not yet written into SLOW.md):** the test for a family should be on the
  joint pair (M1, M2_int) across the whole gain curve, not at one gain: "no input strength brings the
  family's M2_int into the mouse's range". This removes the free parameter instead of fixing it by hand.
  It must be written into the registration before any mouse is measured.

**18:20. F2 probe: language models.** `inputs.text_clip_and_contexts` and `inputs.lm_repeats`: a language
model keeps no state between calls, so a repeat's internal state is its preceding context. Repeat r is one
forward pass over a different context (from the map study's book sample, away from the clip) followed by
the same clip; only the clip's tokens are kept. Units as in the map study (middle-layer MLP neurons for
Pythia, gated SSM outputs for Mamba), 480 at random.
- Pythia-14m, clip 1,000 tokens, 20 repeats, contexts of 256 or 1,024 tokens: native timescale 0.83
  tokens (below the map study's native-speed floor of 1.5); **raw internal share 0.00** (lag 0,
  `(C_same(0) - C_cross(0)) / C_same(0)`). The clip almost fully determines the middle layer; the preceding
  context leaves no measurable trace in the clip's activity.
- Through the spike instrument the same activity read **M1 = 0.10 to 0.11**, M2_int 0.23. The raw share is
  zero, so the instrument reading is a bias. This led to the check below.

**18:30. A bias in M1 found: the lag-0 extrapolation reads above zero when nothing is internal.**
Synthetic systems with internal share 0, through the Allen median spike instrument (2 seeds, 480 units):

| native locked timescale | M1 (lag-0 extrapolation) | M1_lag1 (new) |
|---|---|---|
| 0.7 | 0.07 | 0.00 |
| 1.5 | 0.09 | 0.00 |
| 6 | 0.12 | -0.00 |

- Cause: M1's internal variance is the extrapolated noise-free lag-0 variance minus the cross-repeat
  lag-0 covariance. The cross-repeat term is exact (spike noise is independent across repeats), so every
  error of the cubic extrapolation lands in the internal part. With white spike noise only lag 0 is
  contaminated, so **lag 1 needs no extrapolation at all**.
- New measures (draft), computed alongside the old ones:
  - `M1_lag1 = (C_same(1) - C_cross(1)) / C_same(1)`: the internal share of the one-bin covariance;
  - `M2_lag1`: integral times summed from lag 1 and normalised by lag 1, internal over locked.
- Price: lag-1 share mixes share with speed a little (a fast internal part has decayed more by one bin);
  the bin is matched to each mouse's timescale, so the mixing is the same for AI and mouse.
- At share 0, M2_int also reads 0.11 to 0.16, which is meaningless: there is no internal part to time.
  A rule is needed: M2 only where the internal part is clearly present (threshold to be set from the
  share-0 spread; draft: M1_lag1 at least 0.05).

**18:40. Lag-1 measures against known truth** (`/tmp/s7/floor2.py`; locked timescale 6 native steps,
share 0.5, 2 seeds):

| true ratio | 1 | 2 | 4 | 8 | 16 |
|---|---|---|---|---|---|
| M2_int | 0.69 | 1.27 | 2.50 | 4.52 | 8.66 |
| M2_lag1 | 0.88 | 1.58 | 2.93 | 5.38 | 10.71 |
| M1 | 0.65 | 0.64 | 0.64 | 0.66 | 0.67 |
| M1_lag1 | 0.58 | 0.60 | 0.62 | 0.65 | 0.66 |

- M2_lag1 is monotone and closer to the true ratio than M2_int (range 0.88 to 10.7 against 0.69 to 8.7).
- At locked timescale 1.5 (ratio 4): M2_lag1 2.78, M2_int 2.04.
- The run hit the 10-minute limit before the low-share cases (0.2, 0.05); they are rerun below.
- **Draft decision:** M1_lag1 and M2_lag1 become the primary measures; the extrapolated versions are
  reported. To be confirmed by C4, which now includes them.

**18:45. C4 restarted.** The first C4 run was stopped by the background time limit before printing
(it printed only at the end). Rerun as `/tmp/s7/c4b.py`, saving each job to `/tmp/s7/c4b.jsonl` as it
finishes and skipping finished jobs on restart, with the lag-1 measures added.

**18:55. Low-share cases** (true ratio 4; 2 seeds; run alongside C4, stopped by the limit before the last
two cases):

| locked timescale | true share | M1 | M1_lag1 | M2_int | M2_lag1 |
|---|---|---|---|---|---|
| 1.5 | 0.2 | 0.35 | 0.29 | 1.82 | 2.56 |
| 6 | 0.2 | 0.36 | 0.28 | 1.82 | 2.80 |
| 6 | 0.05 | 0.16 | 0.07 | 1.14 | 2.67 |
| 6 (above) | 0.5 | 0.64 | 0.62 | 2.50 | 2.93 |

- **M2_lag1 hardly moves with share** (2.67 to 2.93 from share 0.05 to 0.5), while M2_int falls from 2.50
  to 1.14 as the share shrinks, because the extrapolation bias is a growing part of a small internal
  variance. So the cross-talk logged at 17:40 (M2_int moving with share, rho 0.76 to 0.81) was mostly
  this bias.
- M1_lag1 reads close to the truth at small shares (0.07 at 0.05; M1 reads 0.16).

**19:05. Last low-share cases** (2 seeds; locked timescale 6):

| true ratio | true share | M1 | M1_lag1 | M2_int | M2_lag1 |
|---|---|---|---|---|---|
| 1 | 0.05 | 0.18 | 0.06 | 0.35 | 0.85 |
| 16 | 0.05 | 0.18 | 0.08 | 3.25 | 9.14 |
| 4 | 0 | 0.12 | -0.00 | 0.11 | 0.19 |

- At share 0.05, M2_lag1 still spans 0.85 to 9.14 for true ratios 1 to 16, close to its values at share
  0.5 (0.88 to 10.71). M2_int collapses to 0.35 to 3.25.
- At share 0 there is nothing to time and M2_lag1 reads 0.19 (noise). A small-share rule is still needed;
  M1_lag1 at share 0 reads 0.00 in every case so far, and 0.06 to 0.08 at share 0.05.

**19:10. C4 runs out of memory with two jobs at once.** The cgroup killed a C4 job at 4.9 GB while a
calibration run shared the machine; the pool then hung on the lost jobs. 15 of 22 jobs had finished
(light ones), plus one heavy one. The remaining heavy jobs (1,200 units; 60 repeats; 8,000-step clips;
one seed of the slowest timescale) now run one at a time with nothing else beside them.
