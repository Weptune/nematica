"""A copy built by watching: a linear model of how neuron classes drive each other, learned
only from the stretches of each training worm with no light pulse nearby. On held-out worms
it runs freely, the poked class is held to its drive, and the others follow the learned
couplings. The implementation lives in nematica/gallery.py (LinearRest); read it as a
template for your own copy.

    python -m nematica score examples/copies/linear_rest.py:LinearRest --quick
"""

from nematica.gallery import LinearRest  # noqa: F401
