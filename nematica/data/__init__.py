"""Data layer: every real or artificial source becomes a Recording."""

from .recording import Recording, RoiLabel
from .wormwideweb import load_wormwideweb_json, load_wormwideweb_dir
from .copper import load_copper_h5, load_copper_dir
from .atanas_h5 import load_atanas_h5, load_atanas_dir
from .jld2_labels import load_neuropal_labels, rebuild_label
from .splits import make_worm_split, load_split, save_split


def load_any_dir(folder):
    """Copper set (HDF5 *-cudata.h5) or WormWideWeb JSON recordings (e.g. Atanas 2023)."""
    from pathlib import Path
    folder = Path(folder)
    if any(folder.glob("*-cudata.h5")):
        return load_copper_dir(folder)
    return load_wormwideweb_dir(folder)

__all__ = [
    "Recording",
    "RoiLabel",
    "load_wormwideweb_json",
    "load_wormwideweb_dir",
    "load_copper_h5",
    "load_copper_dir",
    "load_atanas_h5",
    "load_atanas_dir",
    "load_neuropal_labels",
    "rebuild_label",
    "make_worm_split",
    "load_split",
    "save_split",
    "load_any_dir",
]
