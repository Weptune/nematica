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

**19:20. Memory fixes, and a note on matching.** The heavy C4 jobs were killed again (exit 137) even
alone. Two changes:
- `synthetic.continuous` now builds its output in float32, in place. Same random draws; the arrays differ
  from the float64 version by at most 4e-7 (checked).
- `record.record_repeats` passes only the first 200 columns to `recording.match`, which reads only those
  (`MATCH_MIN_UNITS`); checked to give the same knobs, in float32 and float64. This avoids a float64 copy
  of the whole activity. `nematica/map/recording.py` itself is unchanged (it is frozen by the map study).
- **Matching is sensitive to rounding.** The same synthetic system, rounded to float32, matched to gain
  0.845 instead of 0.913 in float64. The matched instrument is a solution within a tolerance, not a unique
  point, and tiny input changes can pick a different one. On a small test (6 repeats, 300 units) this
  moved M2_lag1 from 2.53 to 3.11, part of which is the different spike draws. Consequence: C4 and C3
  should include instrument re-matching as a source of spread (planned: match each system twice with
  different seeds and report the spread).
- All C4 jobs are being rerun with the lean code, one at a time, so that every row comes from the same
  code. The 16 earlier rows are kept in `/tmp/s7/c4b_mixed_old.jsonl` for comparison only.

**19:40. Recording memory.** Profiling one C4 job (20 repeats of 4,000 steps, 480 units): peak 0.84 GB
after the synthetic system, 2.42 GB after recording. `recording.record_matched` records units in blocks of
400 in float64, with a hold of 2 here, so its peak grows with rows x 400. Fix in `record.record_repeats`:
units go to `record_matched` 100 at a time (`UNIT_BLOCK`), with one shared random generator. Peak now
0.93 GB. Same spike model; different random draws than the single call, so the F5 numbers logged above
(17:15 to 19:05) came from the earlier path. They are statistically equivalent; the formal calibration
after freezing uses only the new path. C4 restarted from scratch.

**19:45. F2 code for the other families** (in `nematica/slow/inputs.py`, not yet tested at scale):
- A2 `trained_task_rnn` + `task_rnn_repeats`: the map study's trained decision-task RNN (512 units, lr
  3e-4), trained by the registered code itself (its long-session helper is swapped for one that returns
  the network). Repeats: one fixed draw of 100 trials, shown 20 times in one continuous session, with 5 to
  15 fresh random trials before each repeat, so every repeat starts from a different state.
- A3, A5 `trained_char_net` + `char_repeats`: a verbatim copy of the map study's character-network training
  (to be checked against `zoo.char_net`'s recorded states). Repeats: a fixed held-out clip, each repeat
  after 200 to 600 characters of other held-out text, one continuous run.
- A4 `driven_lif`: the map study's LIF network with each neuron's external Poisson rate multiplied by
  max(0, 1 + gain x (B u(t))_i), B fixed random over the 64 movie features.

**19:55. Draft registration v0.1** (`SLOW.md`, still not frozen):
- section 3: M1 and M2 are now the lag-1 versions (no extrapolation); the lag-0 versions and the half-life
  ratio are reported, not tested; M2 is computed only where M1 is at least 0.05 (draft threshold);
- section 7: movie-driven families are measured on a fixed input-gain grid (0.05 to 4), and each mouse is
  compared with the gain closest to it, so a confirmed gap holds for every input strength in the grid.

**20:00. F3 first look: a replication dataset.** Candidate: the **Allen Brain Observatory Visual Coding
two-photon** dataset. It shows the same natural_movie_one clip, repeated within session, in each of its
three session types, to many mice (calcium imaging, GCaMP6f; NWB files per session). Strengths: the same
clip, a different instrument, many more mice. Risk, from the map study: its two-photon arm (Stringer et al.
2019, deconvolved, 7 mice) failed step 2 because no measurement survived that instrument. The repeat
measures are ratios within one system, so a shared calcium filter acts on both parts alike, but this must
be calibrated through the calcium instrument before choosing. The IBL brain-wide map stays the fallback
(trial-averaged, so "locked" means per-condition average, a weaker analogue).
Next for F3: list sessions and repeats from the Allen two-photon manifest, and run C1 through the map
study's calcium recording model.

**20:15. C4 passed, by a wide margin.** All 22 jobs (one at a time, lean code; summary in
`docs/figures/slow_c4.json`). Ratio = spread of the level means over the measure's C1 range (gate 0.5):

| knob (levels) | M1_lag1 | M2_lag1 | M1 (lag 0) | M2_int |
|---|---|---|---|---|
| native timescale (2/8, 6/24, 18/72 steps) | 0.00 | 0.01 | 0.00 | 0.01 |
| population (200, 480, 1,200 units) | 0.04 | 0.01 | 0.03 | 0.02 |
| repeats (20, 60) | 0.02 | 0.00 | 0.02 | 0.01 |
| clip length (2,000, 4,000, 8,000 steps) | 0.03 | 0.02 | 0.03 | 0.03 |

- The measures do not move when a system's native clock changes 9-fold, which is the point of a
  clock-free design (the map study's timescales moved with the instrument by 1.8 mouse SDs).
- C1 ranges used: M1_lag1 0.59 (0.07 at share 0.05 to 0.66), M2_lag1 9.83 (0.88 to 10.71), from the
  18:40 to 19:05 runs.
- Still open in F5: (a) C1 for the lag-1 measures in a single formal sweep with 5 levels and 2 seeds each
  (the evidence so far is spread over several runs); (b) the spread from instrument re-matching (19:20);
  (c) calibration at the extreme per-mouse instruments, not only the median; (d) C1 through the calcium
  instrument if the two-photon replication is chosen.

**20:25. F2 probe: the trained task RNN (A2).** `trained_task_rnn(seed=0)`: the registered training ran
in 460 s (sharing the CPUs with C4); accuracy 0.728 on 1,000 independent trials (the map study's guard is
0.7). Repeats: 100 fixed trials (6,000 steps) shown 20 times, 5 to 15 random trials before each. Raw
activity, no instrument (`/tmp/s7/f2_a2.py`):
- **raw lag-0 internal share 0.72**: most of this network's activity differs between repeats of identical
  input;
- the internal share **fades slowly through the clip**: 0.94 in the first trial, 0.90 in the second, 0.85
  in the fifth, 0.81 in the 20th, 0.53 in the 100th. The state left by the preceding random trials
  persists for dozens of trials (thousands of steps), consistent with the map study's estimate of a
  timescale of about 930 to 1,500 steps for this network.
- Shares computed at lags of 10 to 600 steps exceeded 1 (1.14 to 2.51): with a 60-step trial structure the
  stimulus-locked autocovariance goes negative at some lags, so a ratio to C_same is not a share there.
  For M1 at lag 1 bin this needs care: the bin must be shorter than the trial structure. To be handled
  through the instrument (which bins at the mouse's timescale).
- **This family may contradict the thesis**: a task-trained RNN carries a large, slow internal state.
  That is exactly the kind of result the study must be able to report; nothing is changed because of it.
  (It is a probe of the input pipeline, not a measurement: the registration is not frozen and the mice
  have not been measured.)

**20:35 to 21:30. Formal C1 for the lag-1 measures, at four real instruments** (`/tmp/s7/c1.py`, 80 runs,
two at a time; summary `docs/figures/slow_c1.json`). The instruments are the map study's single-unit
numbers (whole sessions) of: the median mouse; the fastest (1.43 bins per timescale); the slowest (23.9);
the noisiest (white share 0.965). Each run: 20 repeats, 480 units, and the clip sized to **1,500 bins**,
the real length of natural_movie_one in 20 ms bins. The clip is sized from a pilot match of the same
system, because the matched bin depends on the system's measured timescale (a first attempt sized it from
the nominal timescale and got 744 to 3,428 bins instead of 1,500).

| instrument | M1_lag1 over share 0.05, 0.1, 0.2, 0.4, 0.8 (rho) | M2_lag1 over ratio 1, 2, 4, 8, 16 (rho) |
|---|---|---|
| median | 0.07, 0.15, 0.29, 0.54, 0.89 (0.98) | 0.94, 1.61, 2.88, 5.19, 10.64 (0.98) |
| fastest | 0.09, 0.17, 0.33, 0.61, 0.92 (0.98) | 0.86, 1.43, 2.41, 4.34, 8.01 (0.98) |
| slowest | 0.06, 0.10, 0.23, 0.43, 0.83 (0.98) | 1.28, 2.17, 4.11, 7.55, 13.60 (0.98) |
| noisiest | 0.07, 0.12, 0.23, 0.43, 0.83 (0.98) | 1.15, 2.06, 4.47, 7.44, 13.62 (0.98) |

- **C1 passes for both primary measures at every instrument** (gate rho 0.9). 0.98 is the ceiling here:
  two seeds per level, and the two seeds' order within a level does not count.
- The lag-0 M1 reads 0.12 to 0.28 at true share 0.05 and drops to rho 0.91 at the slowest instrument (it
  is non-monotone there: 0.12 then 0.07). The lag-1 choice is confirmed.
- **The instrument shifts the values** (M2_lag1 at true ratio 16: 8.0 at the fastest mouse, 13.6 at the
  slowest). This is why every AI is recorded at each mouse's own instrument and compared with that mouse
  only: the shift is the same for both members of a pair.
- Cross-talk (reported): at the slowest and noisiest instruments M2_lag1 moves with share at the smallest
  share (2.56 to 2.59 at share 0.05, against 3.9 to 4.5 above it; rho 0.54 and 0.84), and M1_lag1 rises a
  little with the ratio at the fastest instrument (0.62 to 0.75). At the median it is flat (rho -0.07).

**21:40. Spread from re-matching the instrument** (`/tmp/s7/rematch.py`; 5 synthetic systems at share
0.5, ratio 4, median instrument; each matched with 3 matching seeds and recorded with the same spike seed):
- the matched knobs vary a lot between matching seeds: bin width 2.9 to 5.3 native steps, gain 0.80 to
  1.03 (the timescale estimate behind matching is noisy on sparse spikes);
- the measures barely move: within a system, M1_lag1 varies by 0.01 to 0.03 and M2_lag1 by 0.1 to 0.25,
  against C1 ranges of about 0.8 and 10. Between the 5 systems (different seeds) M2_lag1 spans 2.6 to 3.2.
- So matching tolerance is a small source of spread for these measures (it was large for the map study's
  clock-bound measures). Planned anyway: each AI recording reports its matched knobs.

**21:45. Character-network training copy checked.** `inputs.trained_char_net` and the training part of
`zoo.char_net` are identical line by line (25 of 25 lines, compared programmatically with `inspect`,
allowing only the module prefix of `chars` and `_cfc_cell`). Same seeds and data, so the same networks.

**21:50. F2 probe: the driven random RNN through the median instrument** (`/tmp/s7/f2_rnn_inst.py`, seed
0, 20 repeats, playback at 17.4 steps per frame):

| gain | recorded bins per clip | matched bin (steps) | M1_lag1 | M2_lag1 | M1 (lag 0) |
|---|---|---|---|---|---|
| 0.05 | 1,794 | 8.7 | 0.910 | 0.55 | 0.94 |
| 0.25 | 1,039 | 15.0 | 0.345 | 0.33 | 0.51 |
| 1 | 471 | 33.2 | 0.018 | 0.28 | 0.09 |

- Through the instrument the picture of the raw probe (18:10) holds: the gain sets M1_lag1 (0.91 to
  0.02), and M2_lag1 stays well below 1 (0.28 to 0.55).
- **The recorded clip length depends on the gain** (1,794 to 471 bins, against 1,500 for every mouse).
  The instrument is matched to the system's timescale *while driven*, and driving slows this network
  (its activity takes on the movie's slower timescale). Playback speed was set from the undriven
  timescale (decision at 18:00). Options, to be decided before freezing:
  - keep it, and rely on C4 (clip length and native clock do not move the measures; C4 covered a 4-fold
    clip range and a 9-fold clock range);
  - or iterate the playback speed until the recorded clip is 1,500 bins. This cannot converge for a fully
    locked system, whose timescale scales with playback speed, so it would need a cap.
  Draft decision: keep the undriven rule, report recorded bins per clip for every AI, and add a C4 level
  at 500 bins.

**22:00. C4 extended to short clips** (median instrument, share 0.5, ratio 4, 2 seeds): at about 460
recorded bins per clip, M1_lag1 0.65 and M2_lag1 2.92 (base, about 1,700 bins: 0.65 and 2.81; ratio 0.01);
at about 280 bins, 0.64 and 3.37 (ratio 0.06). The gain-dependent clip length of driven AIs (470 to 1,800
bins) is inside the range where the measures do not move. The undriven playback rule stays.

**22:10. F2 probe: the movie-driven spiking network (A4).**
- The undriven LIF network (30 s, 17.7 Hz) has **no measurable timescale** at its 5 ms native step
  (`tau_med` is undefined: lag-1 autocovariance at or below zero). Its activity is asynchronous and
  irregular. So the spike instrument cannot be matched to it (matching failed with an empty range), and
  the playback speed cannot come from a native timescale.
- Decision (draft): the LIF network has real time units, so the movie plays in **real time** (33.3 ms per
  frame, 6.67 steps of 5 ms) and the network is recorded **like a mouse**: its own spikes summed into 20 ms
  bins, no spike model. To match each mouse's sparseness, spikes will be thinned at random to the mouse's
  spikes per bin (independent thinning adds only white noise, which the lag-1 measures ignore).
- Probe (seed 0, 20 repeats, 1,500 bins of 20 ms, 480 of 1,000 neurons, no thinning):

| gain | spikes per bin | M1_lag1 | M2_lag1 |
|---|---|---|---|
| 0.5 | 0.42 | -0.59 | absent |
| 2 | 0.76 | -0.05 | absent |

  The internal one-bin covariance is negative: what differs between repeats is anticorrelated from one
  20 ms bin to the next (inhibition and refractoriness), and there is no positive internal component to
  time. Under the draft rule, M2 is absent for this family.
- Code fix: `internal_measures` now computes the lag-1 measures before the lag-0 extrapolation check, so
  they exist even when that extrapolation fails (it did here at gain 0.5).

**22:20. Pythia-14m again, with the lag-1 measures** (clip 1,000 tokens, contexts 256, median
instrument): M1_lag1 **0.010** (the lag-0 M1 read 0.08 on the same recording, the bias of 18:30). Below the
draft threshold of 0.05, so M2 is absent for this model. The clip recorded as 5,066 bins (each token is
held for about 5 bins, since the model's timescale is under one token); 1,500 bins would be about 300
tokens.

**22:30. F4, the compute budget (estimate from the timings so far, two CPUs shared).**

| step | measured time |
|---|---|
| movie-driven random RNN, 480 units, 20 repeats, plus recording | 90 to 120 s |
| movie-driven LIF network, 20 repeats in real time | 100 to 130 s |
| Pythia-14m, 20 forward passes of 1,256 tokens, plus recording of 5,000-bin clips | 160 to 185 s |
| task RNN training (512 units) | 460 s |
| character network training (512 units) | over 25 min (running) |
| a synthetic recording at one mouse's instrument | about 60 s |

Count for the per-mouse design (58 mice):
- all instances at every mouse: about 69 recordings per mouse, 4,000 in all, about 46 hours. Too long.
- **draft plan: one instance per mouse** (instance = the mouse's rank mod 3, so each instance meets about
  a third of the mice; the instance spread enters the paired differences, as it should). Per mouse: the
  random RNN and LIF at 7 gains each, 1 task RNN, 2 character networks, 4 Pythia sizes, 2 Mamba sizes: 23
  recordings, about 1,330 in all. The LIF needs no spike model (thinning only, seconds). Estimate about
  15 hours of recording plus about 6 hours of generation and training.
- Playback speed depends on each mouse's timescale on the movie. To share generation across mice, mice
  are grouped into 4 playback-speed groups (quartiles of bins per timescale); each AI run is generated
  once per group.
- Constraints: disk (3.3 GB free; only Pythia-14m and 70m are cached, so the larger models are downloaded,
  used and removed one at a time); memory (one heavy job at a time, 6.2 GB limit); background jobs stop
  when the session goes idle, so every run writes results job by job and resumes.
