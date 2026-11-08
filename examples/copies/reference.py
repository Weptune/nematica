"""Reference copies from the NEMATICA project, for comparison on the benchmark's charts.

    python -m nematica score examples/copies/reference.py:Emulator --seeds 3
    python -m nematica score examples/copies/reference.py:Var3Rest --seeds 3
    python -m nematica score examples/copies/reference.py:FirstHybrid --seeds 3

They implement the low-level interface (fit(train, val), simulate(rec, rng) -> PumpProbe) rather than
BrainCopy.run, because they reuse the project's research code. Note: Var3Rest and FirstHybrid read
out one row per neuron class; real neurons are read out one by one and then averaged, which inflates
those two copies' echo size and spread (README, "A worm emulator", step 5). The emulator reads out
neuron by neuron, as a BrainCopy does.
"""

from nematica.systems.causal_models import ClassVAR, HybridKernel


class Var3Rest(ClassVAR):
    """A linear model of how neuron classes drive each other, from stimulation-free activity."""
    def __init__(self):
        super().__init__(lags=3, frames="spontaneous")
        self.name = "VAR(3) from rest"


class FirstHybrid(HybridKernel):
    """Watching plus poking: rest dynamics, and causal kernels learned from training pokes."""
    def __init__(self):
        super().__init__()
        self.name = "first hybrid"


class Emulator(HybridKernel):
    """The NEMATICA emulator (corrected readout): slow interacting brain-wide states, a donor worm's
    slow structure, each class's own degree of slow participation, a fast VAR on what is left
    (no coupling between classes), causal kernels from pokes, neuron-by-neuron readout."""
    def __init__(self):
        super().__init__(slow=6)
        self.slow_dyn = True
        self.indiv_slow, self.slow_w_own = True, 1.0
        self.highpass = True
        self.members, self.member_fix = True, True
        self.coupling = "diagonal"
        self.h_sd = 1.0
        self.name = "emulator"
