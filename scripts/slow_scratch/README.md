# Study 2 working scripts (archived 17 Nov 2026)

These are the scripts behind Study 2's feasibility checks, calibration (C1, C4, the lag-1 floor checks,
re-matching, pre-hold), memory probes and the logic test. `docs/SLOW_LOG.md` cites them by their working
path, `/tmp/s7/<name>.py`. They ran from a scratch directory and were not committed when they ran. They are
copied here unchanged, so the logged numbers can be traced to code. Paths inside them are the working
paths of the time. The registered pipeline is `scripts/slow_run.py`. The final C1 (`docs/figures/slow_c1_v4.json`)
was produced by `c1.py` and summarised by `c1_sum.py` in their last versions. Because only the last version of
each file survived, earlier logged runs may have used earlier versions.
