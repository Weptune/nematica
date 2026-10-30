"""The fidelity benchmark: artificial systems scored against the spread between real worms."""

from .sample import BenchSample, from_recording
from .levels import LEVELS
from .reference import Reference, build_reference, combine_folds, score_system

__all__ = ["BenchSample", "from_recording", "LEVELS", "Reference", "build_reference", "combine_folds", "score_system"]
