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
