"""GRU rung: trains, simulates finite samples with the template's mask, one identity per worm."""

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from test_forecasters import worm  # noqa: E402


def test_gru_trains_and_generates():
    from nematica.systems.gru import GRUWorms
    train = [worm(s) for s in range(1, 6)]
    for emb in (0, 4):
        m = GRUWorms(hidden=16, emb=emb, steps=30, chunk=50, batch=4).fit(train, [worm(6)])
        assert np.isfinite(m.info["val_nll"])
        s = m.generate(worm(7), np.random.default_rng(0), which=2, burn=20)
        assert s.x.shape == worm(7).x.shape
        tpl = worm(7)
        modelled = np.zeros(len(tpl.classes), bool)
        modelled[m.space.core] = True
        assert np.isnan(s.x[~tpl.observed]).all()                       # template mask applied
        assert np.isfinite(s.x[tpl.observed & modelled]).all()           # modelled rows are real numbers
        assert s.name.endswith(":w3")
