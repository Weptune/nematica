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
