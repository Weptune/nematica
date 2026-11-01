"""The floor: a copy with no brain. Every neuron is independent noise, and the poked neuron
simply follows its drive. Nothing else answers a poke, so the poking levels should fail.

    python -m nematica score examples/copies/silent.py:Silent --quick
"""

import numpy as np

from nematica.score import BrainCopy


class Silent(BrainCopy):
    name = "silent"

    def run(self, worm, rng):
        x = rng.standard_normal((len(worm.names), worm.n_frames))
        for p in worm.pokes:
            seg = slice(p.frame, p.frame + len(p.drive))
            x[p.index, seg] = x[p.index, p.frame - 1] + np.nan_to_num(p.drive)
        x[[i for i, n in enumerate(worm.names) if not n]] = np.nan
        return x
