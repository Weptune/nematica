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

**22:45. F2 probe: the GRU character network (A3), first attempt.** Training took 1,404 s (shared CPUs).
The network's timescale is 1.71 characters. Raw activity over a 3,000-character clip shown 20 times, each
after 200 to 600 characters of other text: the internal share, by position in the clip, is 0.10 in the first
10 characters, 0.011 at 10 to 50, 0.008 at 50 to 200, and 0.004 to 0.006 after that. **The preceding
text is forgotten within about 10 characters.** (Pooled over standardised units the lag-0 and lag-1
shares read 0.20 and 0.66; the per-position figure weights units by their variance, the pooled one weights
them equally, so a few low-variance units that carry context dominate the pooled number. To be resolved
through the instrument, which is what counts.) The run was then killed for memory (4.0 GB) during the
instrument step, while the mouse loader test below shared the machine. Rerun alone, with the trained network
saved to `data/derived/slow_nets/` (git-ignored) so it is not trained again.

**22:50. Mouse loader written and tested on one session (shapes only, no statistics).**
`nematica/slow/data.py`: spikes of the map study's units (Allen good units, at most 2,400, the same seeded
subset, so its QC mask still applies) during every repeat of natural_movie_one, stored as uint16
milliseconds from the repeat's start with a uint8 repeat number (third-party data, local only, in
`data/cache/allen_movie/`). A repeat is dropped if it overlaps one of Allen's invalid intervals. Test
on sub-699733573: cached in 42 s, **17 of 20 repeats valid (3 dropped)**, 2,110 units, counts array
(17, 1,501, 2,110), 12.9 MB on disk (about 0.75 GB for all 58). Nothing about the activity itself was
computed or printed. Consequence for the design: the number of valid repeats varies by mouse, so each
AI uses the same number of repeats as its mouse.

**23:00 to 23:40. F3: the two-photon replication is feasible** (summary `docs/figures/slow_f3.json`).
- Manifest (Allen's public bucket, `visual-coding-2p/ophys_experiments.json`, metadata only, kept in
  `data/external/allen2p/`): 1,518 imaging experiments from **271 mice**; every mouse has a session A
  (natural_movie_one shown 10 times, plus natural_movie_three). Session types: A 506, B 506, C 114, C2 392.
  Areas: VISp 510, VISl 345, VISpm 282, VISal 138, VISrl 123, VISam 120. NWB files are 200 to 350 MB each
  on the same bucket (to be read by range, keeping only the movie epochs).
- Calibration through the map study's **calcium** model, 10 repeats, clip 900 frames (30 Hz), stand-in
  instrument numbers (the map's R3 median, and the same with white share 0.8), 2 seeds per level:

| instrument | M1_lag1 over share 0.05 to 0.8 (rho) | M2_lag1 over ratio 1 to 16 (rho) |
|---|---|---|
| calcium, R3 numbers | 0.06, 0.12, 0.23, 0.46, 0.84 (0.98) | 1.07, 1.78, 3.77, 7.10, 14.75 (0.98) |
| calcium, white share 0.8 | 0.06, 0.11, 0.23, 0.45, 0.85 (0.98) | 1.05, 1.88, 3.85, 6.97, 13.59 (0.98) |

  C1 passes. Unlike the map study's clock-bound measures, the within-system ratios survive the calcium
  filter: the indicator smooths internal and locked activity alike.
- **Draft F3 decision: the replication is Allen Visual Coding two-photon, session A, natural_movie_one,
  one experiment per mouse** (rule to freeze: the mouse's VISp experiment if it has one, else its lowest
  experiment id), each AI recorded through the calcium model matched to that mouse's numbers measured on
  its movie epochs. The IBL brain-wide map is dropped as the replication (its repeated unit is a trial
  type, a weaker analogue). Real instrument numbers are measured only after freezing.

**23:50. GRU (A3) through the median instrument, and why it reads high.** Rerun alone (training 993 s;
network saved). Through the spike instrument the 3,000-character clip became 10,930 bins (each character
held about 3.6 bins), and read **M1_lag1 0.377, M2_lag1 67**: a large internal share, and an internal part
far slower than the input-driven part. The raw per-position share (0.004 after 1,000 characters) said the
opposite. Inspection of single units (saved network, same clip):
- about **85 of 512 units (17%) keep an internal share above 0.5 throughout the clip** (128 in the first
  10 characters, 99 at 10 to 100, 85 at 1,000 to 3,000);
- these units vary little: their SD over the run is 0.003 to 0.1, against a median unit SD of 0.63. Their
  value is set by the preceding text and then held (one sits at |h| = 1). They are **latching memory
  units**: slow internal state in a small, quiet subpopulation.
- The spike instrument standardises every unit, so quiet units count as much as loud ones, as for the
  mice, whose units are standardised the same way. The per-position share weights units by variance, so
  the latching units vanish from it.
- So the GRU has slow internal state, carried by a minority of quiet units. With the trained task RNN
  (20:25), that makes two trained recurrent families that **may go against the thesis**. Nothing is
  changed because of this. Two things go into the draft for transparency, both reported, neither
  tested: (a) the variance-weighted share for every AI; (b) the fraction of units with internal share
  above 0.5. A rule for silent units is needed anyway (Allen keeps only units that fire; a unit with SD
  near 0 has no analogue). Draft: AI units with SD below 1% of the median unit SD are excluded as silent
  (this would remove 1 of the 5 strongest latching units here, not the phenomenon).

**00:05. The autocovariance is now computed with FFTs, a chunk of 64 units at a time.** The GRU
recording (20 repeats of 10,930 bins, 512 units) peaked at 4.3 GB, mostly in `repeat_autocov`, which held
several float64 copies of the whole array and looped over 2,700 lags. The new version standardises and
transforms 64 units at a time. Checked against the original lag-by-lag version (kept as
`_repeat_autocov_direct`) on a test array with a constant unit: largest difference 3e-16 (same) and 4e-17
(cross). Same quantities, less memory, faster.
(Background-job outputs filtered through `grep` were block-buffered, so lines appeared late; filters now
use `--line-buffered`.)

**Clock correction (machine clock 15:08, 15 Nov).** The times on the entries from "18:00. F2 started" to
"00:05" above are sequence labels I assigned, not clock readings, and they ran ahead of the real clock: all
of that work happened on 15 Nov between about 12:00 and 15:05 by the machine clock (whose zone is
unlabelled). Their order is correct. From here on, entries carry the machine clock time.

**15:15. Draft registration v0.2** (`SLOW.md`; not frozen). Changes, all from the feasibility work above:
- replication dataset fixed (Allen two-photon, session A, one experiment per mouse, calcium model);
- units: the map study's Allen subset and QC mask, no pooling; repeats: all valid repeats, the AI gets the
  mouse's number;
- the family table now states each family's input and repeat structure; the vision network is dropped
  (no internal state by construction, and not one of the map study's families);
- one instance per family per mouse (instance = mouse rank mod 3), for the compute budget;
- playback speed from the undriven native timescale, in 4 quartile groups of mice; real time for the LIF;
- instruments: the LIF recorded like a mouse (20 ms bins, thinned); silent AI units (SD below 1% of the
  median) excluded; bins per clip reported;
- reported, not tested: variance-weighted internal share and the fraction of latching units.

**15:20. Two lost trainings, and the fix.** The task RNN and CfC networks trained fine but could not be
saved: both are local classes in the map study's code, which torch cannot pickle; the task RNN's failed
save left a corrupt file (deleted). `inputs.save_char_net` / `load_char_net` and `save_task_rnn` /
`load_task_rnn` now save state dicts and rebuild the modules (tested: a reloaded GRU gives the same output;
the CfC reloads). The GRU file was converted. Both probes rerun, one after the other.

**15:45. Probes: task RNN through the instrument, and three language models on a short clip.**
- Task RNN (A2, seed 0, retrained in 715 s, accuracy 0.728, now saved): through the median instrument the
  100-trial clip became **18,009 bins** (matched bin 2.33 steps, hold 7: the network's raw timescale is
  only 1.2 steps because of its fast within-trial structure). **M1_lag1 0.69, M2_lag1 0.10** (internal
  integral time 2.7 bins, locked 26.3). At this instrument the internal part is large but fast. The slow
  fading of the internal share over dozens of trials seen in the raw probe is a small, slow component that
  the one-bin measures weight little. To note for the registration: (a) the clip for A2 should be sized
  like the others, about 1,500 recorded bins (about 58 trials here); (b) the reported fraction of latching
  units will show whether a slow subpopulation exists.
- Language models, clip of **300 tokens** (about 1,500 recorded bins, the mouse's clip length), contexts of
  256 tokens, 20 repeats, median instrument:

| model | timescale (tokens) | raw lag-0 internal share | M1_lag1 | M2_lag1 |
|---|---|---|---|---|
| Pythia-14m | 0.89 | 0.00 | 0.018 | (absent) |
| Pythia-160m (seed 1) | 0.93 | 0.03 | 0.137 | 0.74 |

  The larger model carries more of its context into the clip. Clip length matters for language models
  (the context's effect fades along the clip: Pythia-14m read 0.010 on a 1,000-token clip), so the clip is
  fixed by the same rule as for movies: the token count that records as about 1,500 bins at the mouse's
  instrument.
- Mamba-130m did not finish 20 forward passes of 556 tokens within 10 minutes on this CPU (the
  transformers implementation without its compiled kernels is slow). It goes to background runs; F4's
  estimate for A7 is raised accordingly.
- Disk: 2.5 GB free after the Pythia-160m and Mamba-130m downloads.

**16:20. Mamba-130m probe** (background, 1,132 s: the reference PyTorch scan, since the compiled
`mamba_ssm` kernels are not installed). Clip 300 tokens, contexts 256, 20 repeats, median instrument:
timescale 1.13 tokens, raw lag-0 internal share **0.18**, recorded 1,455 bins, **M1_lag1 0.61, M2_lag1
1.03**. The state-space model carries much more of its preceding context into the clip than the
transformers of similar size (Pythia-160m: 0.137), consistent with its recurrent state; its internal part
moves about as fast as its input-driven part. F4: about 19 minutes per Mamba-130m recording set on this
machine, so A7 at about 58 mice x 2 sizes needs generation shared across mice (the clip and contexts do
not depend on the mouse; only the instrument does), which is the plan: generate once per instance,
record per mouse.

**16:45. CfC (A5) probe, and a rule for systems with no measurable timescale.** CfC trained in 1,501 s
(saved). Its activity has **no measurable timescale** at the character step (like the LIF network), and the
preceding text leaves no trace: raw internal share 0.001 at lag 0, 0.08 in the first 10 characters of the
clip, 0.000 after that. The spike instrument could not be matched (no timescale to match), so:
- `record.record_repeats` now **pre-holds** a system whose native timescale is undefined: each native step
  is repeated 4 times (`PREHOLD`) before matching, which gives it a timescale the matcher can use. The
  measures are clock-free (C4: a 9-fold change of native clock moved them by 0.01 of their range), so the
  choice of 4 should not matter; to be checked with 2 and 8 as a sensitivity. Systems with a timescale are
  unaffected (the check runs on the first 20,000 rows).
- Result: 15,787 bins per 3,000-character clip, **M1_lag1 0.003** (M2 absent under the 0.05 rule; the
  lag-0 M1 read 0.084, the old bias again).

**Probe summary so far** (seed 0 or one released seed, median mouse instrument, not measurements):

| family | M1_lag1 | M2_lag1 | note |
|---|---|---|---|
| A1 random RNN, movie gain 0.05 / 0.25 / 1 | 0.91 / 0.35 / 0.02 | 0.55 / 0.33 / 0.28 | gain sets M1; internal always faster |
| A2 task RNN | 0.69 | 0.10 | large, fast internal part; slow fading over trials |
| A3 GRU | 0.38 | 67 | quiet latching units (17%) hold context |
| A4 LIF, gain 0.5 / 2 | -0.59 / -0.05 | absent | internal part anticorrelated bin to bin |
| A5 CfC | 0.003 | absent | forgets context within 10 characters |
| A6 Pythia-14m / 160m | 0.018 / 0.137 | absent / 0.74 | 300-token clip |
| A7 Mamba-130m | 0.61 | 1.03 | carries context in its state |

The families differ a great deal from each other. Whether any of them resembles a mouse is unknown: no
mouse has been measured, and none will be until the registration is frozen and reviewed.

**17:05. Pre-hold sensitivity** (1,000-character clip, 20 repeats, median instrument):

| network | pre-hold | bins | M1_lag1 | M2_lag1 |
|---|---|---|---|---|
| CfC | 2 / 4 / 8 | 5,171 / 4,924 / 5,221 | 0.004 / 0.004 / 0.007 | 0.38 / 0.74 / 0.77 (absent by rule) |
| GRU | 1 / 4 | 3,688 / 3,619 | 0.304 / 0.288 | 221 / 227 |

- M1_lag1 does not depend on the pre-hold. Kept at 4.
- **New problem: M2 has a ceiling set by the clip.** The GRU read M2_lag1 221 on a 1,000-character clip
  and 67 on a 3,000-character clip. Its latching units hold a nearly constant value through a repeat, so
  their internal autocovariance never reaches zero and the integral time is cut only by the largest lag
  (a quarter of the clip). C4 did not catch this, because its synthetic internal part always had a
  timescale shorter than the clip. Draft decisions:
  - M2 is analysed on a **log scale** (it is a ratio; the ruler and differences are taken on log M2);
  - a recording whose internal integral time reaches the largest lag is flagged **at ceiling**, and its
    value is reported as a lower bound;
  - a C4 check with internal timescales longer than the clip is added before freezing.

**17:20. Ceiling flag and a long-timescale C4 check.** `internal_measures` now returns `M2_ceiling`: true
when the internal autocovariance stays above zero at every lag up to the largest (a quarter of the clip).
Synthetic systems at the median instrument, clip 3,500 native steps, share 0.5, locked timescale 6:

| internal timescale (native steps) | M1_lag1 | M2_lag1 | at ceiling |
|---|---|---|---|
| 24 | 0.63 | 2.9 | no |
| 600 | 0.67 | 52 | yes |
| 3,500 (the clip) | 0.68 | 97 | yes |
| 35,000 | 0.65 | 111 | yes |

- M1_lag1 is unaffected by how slow the internal part is.
- M2_lag1 keeps its order but compresses as it nears the ceiling (52, 97, 111 for 100-fold, 580-fold and
  5,800-fold slower internal parts). So beyond the ceiling M2 is an ordinal lower bound; the paired tests
  are rank-based (Wilcoxon), which tolerates this, and the ruler is taken on log M2.

**17:35. Draft decision rules tightened** (`SLOW.md` section 7, still a draft): M2 on a log scale with
ceiling values as lower bounds; a refutation rule (the opposite one-sided test with median d below -0.5
ruler units); the absent-M2 rule (if the AI's M2 is absent in more than half its pairs, the family's M2
verdict is "no internal part"); the thesis counts families confirmed on M1 or M2 and needs none refuted on
either; H2 specified (balanced-gain random RNN with the map study's slow drives, share chosen on half the
mice on M2, equivalence tested on the other half on both measures).

**17:45. H2 candidate probed** (driven random RNN, balanced gain 0.86, seed 0, median instrument):

| slow drive | recorded bins | M1_lag1 | M2_lag1 | ceiling |
|---|---|---|---|---|
| none | 468 | 0.025 | 0.28 | no |
| map version (50 x own timescale), share 0.1 / 0.3 | 404 / 234 | 0.32 / 0.60 | 12.1 / 15.1 | yes |
| 1 s of movie time, share 0.1 / 0.3 | 332 / 364 | 0.31 / 0.53 | 2.32 / 2.67 | no |
| 5 s of movie time, share 0.1 / 0.3 | 341 / 280 | 0.30 / 0.57 | 8.75 / 10.41 | yes |

- The map study's drive takes its time constant from the network's own timescale, which becomes long once
  the network is driven, so the drive outlasts the clip (ceiling) and coarsens the instrument (234 bins).
  New `inputs.add_slow_drive` takes the time constant in movie time instead.
- Slow drives raise both measures, and the time constant moves M2 from about 2.5 (1 s) to the ceiling
  (5 s). So H2 now tunes share and time constant together on the training half (grid of 5 x 4), then
  tests on the other half (`SLOW.md`, H2).
- Recorded bins fall to 280 to 360 with drives; C4 covered down to about 280 bins (ratio 0.06). At the
  edge; to be extended to 200 bins in the final C4.

**17:55. C4 down to about 200 bins** (3 seeds, median instrument, share 0.5, ratio 4): at 181 to 253
recorded bins, M1_lag1 0.646 and M2_lag1 3.11 (SD 0.32); at 1,584 to 2,051 bins, 0.645 and 2.87 (SD 0.12).
Shift 0.24 in M2_lag1 against a C1 range of about 10 (ratio 0.02); the spread grows at short clips, as
expected. The measures hold down to about 200 bins.

**18:30. The pipeline: `scripts/slow_run.py`** (stages `mice`, `ais`, `tests`; each appends results row by
row to `docs/figures/slow_runs/*.jsonl` and resumes after a crash).
- **Freeze guard:** the `mice` and `ais` stages exit unless `SLOW.md` contains "Frozen at commit <hash>"
  (checked: it refuses now). `--dry` runs them on synthetic stand-in mice instead, writing `*_dry.jsonl`
  (git-ignored); nothing real is read.
- `mice`: per session, the cached movie repeats in 20 ms bins, the map study's unit inclusion rule, the
  map study's instrument numbers (`instrument_numbers`, with repeat boundaries as segments), the measures
  and the reported extras.
- `ais`: mice get an instance (rank mod 3) and a playback-speed group (quartile of bins per timescale).
  Each AI run is generated once per (instance, group, gain), recorded at every mouse it serves with that
  mouse's repeats and instrument, then discarded (disk). Silent units are excluded. The LIF network is
  binned at 20 ms and thinned to the mouse's spikes per bin. A1 and A4 are wired in; A2, A3, A5, A6, A7
  follow the same pattern and are added next.
- Dry runs passed for `mice` (6 stand-ins, recovered numbers near the synthetic instrument: 3.3 bins per
  timescale for a nominal 2.6, white share 0.92 for 0.90) and for `ais` with A1 and A4.
- Two small fixes from the dry run: Python's `hash` is randomised per process, so seeds now come from
  `zlib.crc32`; and the LIF network, once thinned to mouse sparseness, has **no positive one-bin
  covariance at all**, which left M1_lag1 undefined. Rule: M1_lag1 is then set to 0 and flagged
  `no_lag1_cov` (nothing slow to share out). To go into `SLOW.md` section 3.
- `tests` is not written yet; it must be written and committed before freezing.

**19:10. All seven families wired into the pipeline; dry runs pass.** A2, A3, A5, A6 and A7 size their clip
with a pilot: 3 repeats of a guessed clip are recorded at the group's median instrument and the clip is
scaled to record as about 1,500 bins (the mouse's clip). Trained networks are trained once per instance
(the A2 accuracy guard of 0.7 applies) and saved. Pythia 14M, 160M and 410M use the released seeds 1 to 3
as in the map study; Pythia 1B and Mamba use one model with instance-specific text. A bug found by the dry
run: for families with text or trials between repeats, the clip length is not the spacing of repeat
starts; generators now return it explicitly. Dry runs (stand-in mice, real AIs, values not to be read as
results): A1, A2, A3, A4, A6 complete without errors.

**19:40. The `tests` stage and the H2 family are written** (`scripts/slow_run.py`).
- `tests`: rulers (SD over mice of M1, and of log M2 where it exists); per family and measure, the paired d
  with the AI value closest to each mouse among that family's gains or model sizes; one-sided Wilcoxon
  tests both ways; median d in ruler units with a 90% bootstrap interval; the absent-M2 rule; the thesis
  count. H2: the (share, time constant) pair chosen on the seeded half (seed 2026) and equivalence tested on
  the other half. H3: Pythia 1B against 14M by how much closer each is to each mouse.
- `A1-slow` (H2): the balanced-gain random RNN generated once per instance and speed group (kept in memory
  for its grid), with each of the 20 slow-drive settings added.
- A dry run of `tests` on the stand-in results completes (its numbers mean nothing: the stand-in mice are
  copies of one synthetic system, so the rulers are tiny).

**20:00. A loader bug caught before any data were read, and the shuffled-movie check.**
- Reading only stimulus tables (metadata): natural_movie_one is called
  `natural_movie_one_more_repeats_presentations` in the 26 functional_connectivity sessions (DANDI 000022),
  not `natural_movie_one_presentations`. The loader would have failed on all 26. It now takes the name that
  exists. Checked on one session per dandiset: 17 valid repeats of 20 (000021, 3 dropped for invalid
  intervals) and 60 of 60 (000022); every repeat spans 30.03 s.
- The shuffled movie's `frame` column runs 0 to 899 in presentation order, so the table alone does not say
  whether the shuffle is the same on every repeat. Allen staff state on their forum (community.brain-map.org,
  thread 1010) that the shuffled movie was created once by permuting the frames of movie one and is
  identical on every repeat and in every session. So it gives a clean **validity check of M2**: same
  images, faster input. Written into `SLOW.md` section 7 (locked time must fall and M2 rise, one-sided
  Wilcoxon p < 0.05 each) and into the pipeline (`mice` stage computes the shuffled measures for 000022
  sessions with the same units; `tests` reports the check). The loader caches the shuffled repeats
  separately (20 of 20 valid in the test session).

**20:15. Two-photon loader** (`data.twop_experiments`, `data.twop_movie`). The Allen two-photon NWB files
keep dF/F per imaging plane (cells x about 115,700 frames, gzip, one chunk row per cell) and the movie's
presentation table (9,000 rows: 10 repeats of 900 frames, with timestamps). For each movie frame the loader
takes the imaging frame at or after its onset, reads only the span covering the movie, and caches
(R, 900, cells) as float16 (third-party, local, `data/cache/allen2p_movie/`). The selection rule gives 271
mice, 49% from VISp. Test on the first mouse (shapes only, no statistics): (10, 900, 171), 2.9 MB; about
0.8 GB for all. A pipeline stage for the replication (calcium instrument numbers on the movie epochs with
GCaMP6f's registered half-decay; AIs through the calcium model with 10 repeats of 900 frames) is next.

**20:35. The replication arm is in the pipeline** (`--arm 2p`). Stages read and write `2p_*` files; the
mouse stage takes dF/F on the 10 movie repeats and the map study's calcium instrument numbers (GCaMP6f,
repeats as segments); AIs, including the LIF network, go through the calcium model at each mouse's
numbers; clips are sized to 900 frames; playback uses one group at the Neuropixels median timescale. The
freeze guard covers it. Regression check: the Neuropixels dry run gives the same numbers as before the
change (A1 at gain 0.25: M1_lag1 0.3509, 0.3648). A calcium recording of the driven random RNN (gain 0.25,
the map study's R3 calcium numbers as a stand-in, 10 repeats): M1_lag1 0.377, M2_lag1 0.33, against 0.35
and 0.29 through the spike instrument. The two instruments agree on this system.

---

### Timestamps from here on

The review below found that, even after the clock correction, my entry labels again ran ahead of the clock
and repeated (16:20, 17:05, 17:45, 18:30, 19:10, 19:40 and 20:00 each occur twice). From here on every entry
is stamped with `date -u` (UTC) and cited by its title, not its time. For the record, the entries from
"Clock correction" to "The replication arm is in the pipeline" were committed between 15:10 and 17:04 UTC
(commit times in `git log`).

### Review S-R1: independent pre-freeze review (17:12 UTC)

An independent reviewer (a separate agent with no part in the work, read-only) reviewed `SLOW.md`, this
notebook and all study-2 code at commit 2a12dd5 plus the working tree, running small synthetic checks only.
Its findings, in its own severity order, with what I do about each (fixes are logged in the entries that
follow, each citing the finding number):

**Critical**
1. **Spike-train structure counts as internal.** The lag-1 measures assume spike noise is white at 20 ms.
   It is not in real neurons. In a synthetic check with zero internal share, a 10 ms dead time gave
   M1_lag1 -0.41 and mild bursting gave +0.56; Poisson gave 0.005. AIs go through a Poisson model, mice do
   not, so this alone could make or erase a gap. C1 and C4 used Poisson spikes only. *Response:* compute the
   autocovariances over pairs of **distinct units** (population sum minus self terms). Single-unit spike-train
   structure is then excluded at every lag; recalibrate with refractory and bursting spike generators.
2. **The closest-gain rule creates spurious verdicts.** On a discrete grid the nearest value can sit on
   either side of the mouse; with the gain curve passing through every simulated mouse the reviewer obtained
   both "confirmed" and "refuted". The draft's claim that a gap so confirmed "holds for every input strength"
   is false. *Response:* bracket rule: d = 0 when the mouse lies within the family's range over the grid
   (or its model sizes), else mouse minus the nearer end. Same rule for model sizes, written into `SLOW.md`.
3. **Rate drift between blocks reads as slow internal state, and the claimed QC is absent.** Units are
   centred over all repeats, so a per-unit rate change between the two movie blocks adds a constant to
   C_int (rate change SD 0.2 gave M1_lag1 0.05 and M2 48 at ceiling with no internal state). Mice see two
   blocks with other stimuli between; AIs run continuously. The amendment-25 QC mask that `SLOW.md` cites is
   not applied, and there is no area filter (hippocampal, thalamic and midbrain units would count).
   *Response:* centre each unit **within each repeat** (primary; this also matches the formula in
   `SLOW.md`); apply the QC mask; keep only visual-cortex units; store block ids.

**Major**
4. **M2 at ceiling scales with clip length**, and a signed-rank test does not handle censoring. *Response:*
   the largest lag is a fixed fraction of the clip in every system (so the cap is the same in movie time);
   a pair where both are at ceiling counts as a tie (d = 0); a locked part at ceiling is flagged too.
5. **M2 is clock-free but not input-free**: the locked time reflects the input's own timescale and the
   playback speed, which rests on an unvalidated anchor. *Response:* register a playback sensitivity (x0.5,
   x2, and the driven-timescale rule) and report it beside every M2 verdict for movie-driven families.
6. **Pairs are not independent**: about 12 generator runs per family serve 58 mice. *Response:* cluster
   bootstrap over (instance, group) cells for every interval, and a cell-level sign test beside the
   Wilcoxon.
7. **H2 cannot show "the smallest ingredient"**: two parameters tuned to two medians on an exchangeable
   half nearly guarantee equivalence, and no competitor must fail. *Response:* add negative controls tuned the
   same way that must fail equivalence (a fast drive at or below the locked time; more network noise),
   and drop "smallest" from the claim unless the controls fail.
8. **Calibration did not use the instruments that will be used** (movie-block numbers are unknown before
   freezing), and the C4 gate is in synthetic-range units, not mouse-ruler units. *Response:* register
   post-freeze nuisance checks in mouse-ruler units (clip length, pre-hold, re-matching, playback); a test is
   "not testable" if a nuisance moves values by 0.5 ruler units or more; give C3 a threshold and a
   consequence.
9. **The shuffled check is inconsistent, weak and has a NaN bug** (NaN passes a truthiness filter; M2 rises
   mechanically when the locked time falls; the thesis count ignores the check). *Response:* finite
   filters; add that the internal time must not fall (invariance within 0.5 ruler units); if the check fails
   the thesis count uses M1 only, in code.
10. **Matching quality is not stored.** *Response:* store all knobs, achieved numbers and `reached`; an
    unreached match is reported and excluded.
11. **Missing data handling is undefined**, and the fastest-playback A1 cell with 60 repeats may run out of
    memory. *Response:* dry-run the extreme cell; a pair counts only if every grid point exists; report
    what is missing.
12. **Text and trial families have transient internal state**, so M1 depends on clip length, and the
    clips vary with the mice's instruments; `SLOW.md` still says 100 trials and 3,000 characters.
    *Response:* fix these clips independently of the mouse, and report M1 by position in the clip.
13. **A locked lag-1 covariance at or below 0 is mislabelled "no internal part".** *Response:* its own code
    and rule.

**Minor**
14. Repeat cutting gives each repeat a different sub-bin phase (M1_lag1 0.020 against 0.000 aligned).
    *Response:* record with repeat starts as segments.
15. Instance assignment depends on file order. *Response:* index from the fixed session order.
16. The A1 timescale is hard-coded for all instances. *Response:* measure per instance.
17. Pythia-1B and Mamba instances share one clip. *Response:* draw the clip position with the instance seed.
18. H3 code and text differ, and on M2 Pythia-14M is absent almost everywhere. *Response:* align the text to
    the code (median over mice of how much closer 1B is), H3 on M1 only, M2 reported.
19. Outliers move the SD ruler. *Response:* MAD-based ruler; M1 bounded to [-1, 1].
20. Promised but not computed: M3 carry-over, the adaptation trend, the balanced-gain A1 without a drive.
    *Response:* compute the last two; drop M3 from the registration (it has no lag-1 version yet).
21. Notebook timestamps (above). *Response:* done.
22. Decided in the log or code but missing from `SLOW.md`: pre-hold, the A2 guard, seeds, the language-model
    layer and units. *Response:* written in.
23. MIN_SPIKES over the whole movie means different rate thresholds in 20- and 60-repeat sessions.
    *Response:* a rate threshold only (the map study's 0.05 Hz) plus a minimum of 200 spikes computed
    over the first 17 repeats in every session.

On calibration the reviewer notes that C1 and C4 checked rank order, not bias, and only for stationary,
additive, Gaussian parts with Poisson spikes. Accepted: the recalibration after the fixes adds
non-Poisson spikes, block drift, unequal clip lengths, transient internal state and a quiet latching
minority, and reports bias as well as rank order.

Freezing waits until every critical and major finding is resolved and logged.

### Fix for S-R1 findings 1 and 3: measures from lag 2, units centred within each repeat (17:15 UTC)

First attempt, rejected: autocovariances over pairs of distinct units (`measures.pair_autocov`, checked
exact against a brute-force sum, difference 8e-18). It removes each unit's own spike-train structure, but
averaging signed covariances over pairs cancels whenever units load on the shared signals with mixed signs:
at true internal share 0 it read M1 -0.14. It is kept in the code, unused.

Adopted (draft): `measures.lag_measures`, which starts at lag k0 = 2 bins (40 ms), past refractoriness and
bursts, with every unit centred within each repeat (so a unit's rate change between the two movie blocks
no longer adds a constant to the internal part). Synthetic check (`/tmp/s7/spiketrain.py`; 200 units, 20
repeats of 1,500 bins, about 3 Hz, a locked signal identical on every repeat; spikes generated at 1 ms
resolution with Poisson statistics, a 10 ms dead time, or bursts; per-unit rate drift between the two halves
of the repeats; true internal share 0 or 0.3, internal timescale 25 times the locked one):

| spikes | drift SD | true share | M1, k0 = 1 | M1, k0 = 2 | M1, k0 = 3 | M1, k0 = 2 but centred over all repeats |
|---|---|---|---|---|---|---|
| Poisson | 0 | 0 | -0.05 | -0.04 | -0.05 | -0.00 |
| dead time | 0 | 0 | -1.00 | -0.03 | -0.04 | 0.01 |
| bursts | 0 | 0 | 0.77 | -0.01 | -0.03 | 0.03 |
| Poisson | 0.2 | 0 | -0.03 | -0.02 | -0.03 | 0.07 (M2 24, spurious) |
| Poisson | 0.3 | 0 | -0.02 | -0.01 | -0.02 | 0.13 (M2 37, spurious) |
| Poisson | 0 | 0.3 | 0.26 | 0.30 | 0.35 | 0.38 |
| dead time | 0 | 0.3 | -1.00 | 0.29 | 0.34 | 0.37 |
| bursts | 0 | 0.3 | 0.85 | 0.33 | 0.35 | 0.41 |

- At lag 1 the reviewer's finding reproduces (dead time drives M1 to -1, bursts to +0.77 with nothing
  internal). From lag 2 the spike type no longer matters: M1 is -0.04 to -0.01 at share 0 and 0.29 to 0.33
  at share 0.3, and M2 is 6.9 to 8.5 for every spike type.
- Centring over all repeats lets block drift through (M1 0.07 and 0.13, M2 24 and 37 with no internal
  state); centring within each repeat removes it. The cost: internal change slower than one repeat (30 s) is
  no longer counted, for mice and AIs alike. Stated in the claim.
- A small negative bias at share 0 (-0.01 to -0.05) from per-repeat centring. To be quantified in C1.
- C1 is being rerun at the four instruments with these measures (`/tmp/s7/c1.py`, results to
  `/tmp/s7/c1k2.jsonl`).

### Draft v0.3: the review's findings resolved in text and code (17:33 UTC)

`SLOW.md` is rewritten as v0.3 and `scripts/slow_run.py` changed to match. Finding by finding:
- **1, 3 (critical):** measures from lag 2 with units centred within each repeat (entry above); unit
  selection now Allen good units passing Allen's QC (amendment 25) in visual cortex only
  (`data.unit_meta`, `data.visual_cortex`: peak-channel area starting with VIS; metadata only). On the one
  cached test session: 2,110 units, 637 in visual cortex, 932 passing QC, **268 both**. A mouse with fewer
  than 30 included units is excluded. The claim now says that change slower than one repeat is not counted.
- **2 (critical):** the bracket rule replaces the closest-value rule, in text and in `tests` (`_pair`).
  The balanced gain 0.86 is added to the grid.
- **4:** ties for ceiling pairs; the largest lag is a quarter of the clip everywhere; `lock_ceiling` flag.
- **5:** `A1-play` sensitivity family (x0.5, x2, driven-timescale rule) and a registered consequence: if
  playback moves the balanced-gain A1 by 0.5 ruler units or more on M2, the M2 tests of the movie-driven
  families are not counted.
- **6:** cluster bootstrap over generator cells for every interval; a sign test over cell medians is
  required for a verdict.
- **7:** H2 has two negative controls tuned the same way (`A1-fast`, one-frame drive; `A1-noise`, noise
  0.2 to 1.6); H2 is confirmed only if the slow drive is equivalent and neither control is. "Smallest" is
  gone from the claim.
- **8:** post-freeze C3 (odd against even repeats, Spearman across mice at least 0.5, else the measure is not
  tested) and the playback nuisance check in ruler units; C1, C4 and spike-type checks are rerun for the
  new measures before freezing.
- **9:** finite filters; the internal time must move less than the locked time; if the check fails the
  thesis count uses M1 only (in code).
- **10:** knobs, achieved numbers and `reached` stored; unreached matches excluded and counted.
- **11:** a pair counts only if every gain or size exists at that mouse; missing pairs reported. The extreme
  cell (fastest playback, 60 repeats) still needs a dry run for memory.
- **12:** clips for A2, A3, A5, A6, A7 fixed per instance at the median instrument of all mice; M1 per half
  of the clip reported.
- **13:** "no locked part" has its own code.
- **14:** spike recording bins each repeat from its own start (segments); checked: share 0 gives M1 -0.001,
  share 0.5 gives 0.679.
- **15:** instance from the fixed session order (`rank`). **16:** A1 timescale per instance. **17:** clip
  position per instance for Pythia 1B and Mamba. **18:** H3 on M1 only, text matches code. **19:** robust
  (MAD) ruler; M1 bounded. **20:** adaptation trend computed; M3 dropped; balanced gain on the grid.
  **21:** UTC stamps. **22:** pre-hold, A2 guard (now: retrain with the next seed if accuracy is below 0.7),
  seeds, language-model units written in. **23:** the 200-spike minimum counted over the first 17 repeats.

Still to do before freezing: the C1, C4 and spike-type reruns for the final measures (C1 running); a dry
run of the whole pipeline including the extreme memory cell; a second independent review.
