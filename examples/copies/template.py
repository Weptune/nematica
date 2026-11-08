"""Start here: a copy that does the minimum the benchmark needs, with every part of the contract shown.
Copy this file, then replace the two marked parts with your model.

    python -m nematica check examples/copies/template.py:Template      # contract check, about a minute
    python -m nematica score examples/copies/template.py:Template --seeds 3

This template is a deliberately weak copy: every identified neuron is an independent AR(1) process whose
coefficient (how slowly it changes) is the median over the training worms' neurons, poked neurons follow
their drive, and nothing else responds. It passes the contract check and fails the benchmark, as it should.
"""

import numpy as np

from nematica.data.pumpprobe import neuron_class
from nematica.score import BrainCopy


class Template(BrainCopy):
    name = "template (independent slow noise)"

    def fit(self, worms):
        # worms: training recordings for this fold (training and validation worms of the held-out
        # split; never the held-out worms). Each has .x (neurons x frames, NaN where untracked),
        # .names, .classes (AVAL -> AVA), .stims [(row, frame)], .dt (0.5 s).
        # ---- replace with your model's fitting -------------------------------------------------
        phi = []
        for w in worms:
            for row in w.x:
                v = row[np.isfinite(row)]
                if v.size > 100:
                    v = v - v.mean()
                    phi.append(np.dot(v[1:], v[:-1]) / np.dot(v, v))
        self.phi = float(np.clip(np.median(phi), 0.0, 0.995)) if phi else 0.9
        # ----------------------------------------------------------------------------------------

    def run(self, worm, rng):
        # worm.names: the real worm's neurons, "" where unidentified (leave those NaN or not; they are
        # not scored); worm.n_frames; worm.dt; worm.pokes with .index (row), .frame and .drive.
        n, T = len(worm.names), worm.n_frames
        x = np.full((n, T), np.nan)
        # ---- replace with your model's simulation (use only rng for randomness) -----------------
        e = rng.standard_normal((n, T)) * np.sqrt(1 - self.phi ** 2)
        y = np.zeros((n, T))
        for t in range(1, T):
            y[:, t] = self.phi * y[:, t - 1] + e[:, t]
        for j, name in enumerate(worm.names):
            if neuron_class(name):                  # model every identified neuron, for the whole run
                x[j] = y[j]
        for p in worm.pokes:                        # the poked neuron does what it did in the real worm
            k = min(len(p.drive), T - p.frame)
            x[p.index, p.frame:p.frame + k] = x[p.index, p.frame - 1] + np.nan_to_num(p.drive[:k]) * np.nanstd(x[p.index])
        # ----------------------------------------------------------------------------------------
        return x
