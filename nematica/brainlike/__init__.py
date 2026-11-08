"""The NEMATICA brain-likeness test: how similar is an artificial network to a real brain?

Any recurrent network that runs step by step is put through the experiment the C. elegans signal
propagation atlas ran on real worms (Randi et al. 2023): units are recorded at rest and single units are
kicked, one at a time, every 30 seconds, in 30 independent runs ("animals"). The same brain signatures
are then measured on the network and on real worms, and each is placed against the range of real worm
groups of the same size.

    from nematica.brainlike import load_network, run_test
    report = run_test(load_network("my_rnn.npz"))
"""
from .networks import Network, RateRNN, OnnxNetwork, load_network  # noqa: F401
from .protocol import Protocol, make_schedule, record_population  # noqa: F401
from .signatures import SIGNATURES, measure  # noqa: F401
from .test import BrainLike, evaluate, run_python, run_test, score  # noqa: F401,E402
