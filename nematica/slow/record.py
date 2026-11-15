"""Recording repeated-input activity through a matched instrument (docs/SLOW.md, section 5).

A system's native activity is one continuous run in which the clip occupies known native steps. It is
recorded continuously through the registered spike model (nematica.map.recording, matched with
recording.match), optionally pooled in groups, and then cut into equal-length repeat windows, so that the
instrument and its noise are applied exactly as for the map study's recordings."""
from __future__ import annotations

import numpy as np

from ..map import recording


def cut_repeats(Y, starts, length, per_sample):
    """Cut recorded samples into repeats. `starts` are native steps of each repeat's start; `length` is the
    repeat's native length; per_sample is native steps per recorded sample. Returns (R, T_rec, units)."""
    n = int(np.floor(length / per_sample)) - 1        # one sample short, so rounding never drops a repeat
    out = []
    for s in starts:
        a = int(np.ceil(s / per_sample))
        if a + n <= len(Y):
            out.append(Y[a:a + n])
    return np.stack(out)


def record_repeats(A, starts, length, prof, rtype="spikes", seed=0, group=None, k=None):
    """Match (unless knobs k are given) and record native activity A (time x units), cut into repeats.
    Returns (repeats, knobs)."""
    A = np.asarray(A)
    if k is None:
        k = recording.match(A, rtype, prof, seed=seed)
    Y, _ = recording.record_matched(A, rtype, k, rng=np.random.default_rng(seed + 7))
    if group:
        Y = recording.pool(Y, int(group), seed=seed)
    per = recording.per_sample(k, rtype)
    return cut_repeats(Y, starts, length, per), k
