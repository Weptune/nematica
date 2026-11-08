import numpy as np
import pytest

from nematica.bench.causal import window
from nematica.data.pumpprobe import PumpProbe, neuron_class
from nematica.score import BrainCopy, CopyAdapter, echo_agreement, load_copy, template_of


def worm(T=400, seed=0):
    rng = np.random.default_rng(seed)
    names = ["AVAL", "AVAR", "", "RIML", "ASHL"]
    x = rng.standard_normal((len(names), T))
    x[3, :50] = np.nan
    return PumpProbe(uid="w0", x=x, names=names, classes=[neuron_class(n) for n in names],
                     stims=[(4, 100), (0, 250), (1, 395)], all_stim_frames=[100, 250, 395])


def test_template_drive_matches_internal_protocol():
    rec = worm()
    tpl = template_of(rec)
    npre, npost = window(rec.dt)
    assert [p.frame for p in tpl.pokes] == [100, 250]            # the pulse at 395 runs off the end
    k, f = rec.stims[0]
    want = (rec.x[k, f:f + npost] - np.nanmean(rec.x[k, f - npre:f])) / np.nanstd(rec.x[k])
    np.testing.assert_allclose(tpl.pokes[0].drive, want)
    assert tpl.pokes[0].neuron == "ASHL" and tpl.classes[0] == "AVA"


class Half(BrainCopy):
    name = "half"

    def run(self, w, rng):
        x = rng.standard_normal((len(w.names), w.n_frames))
        x[1] = np.nan                                             # does not model AVAR
        return x


def test_adapter_keeps_modelled_named_neurons_and_remaps_pokes():
    rec = worm()
    sim = CopyAdapter(Half()).fit([rec], []).simulate(rec, np.random.default_rng(0))
    assert sim.names == ["AVAL", "RIML", "ASHL"]
    assert sim.stims == [(2, 100), (0, 250)]
    assert sim.x.shape == (3, rec.n_frames)


class Wrong(BrainCopy):
    def run(self, w, rng):
        return np.zeros((2, 3))


def test_adapter_rejects_wrong_shape():
    with pytest.raises(ValueError, match="expected"):
        CopyAdapter(Wrong()).simulate(worm(), np.random.default_rng(0))


def test_load_copy(tmp_path):
    p = tmp_path / "c.py"
    p.write_text("from nematica.score import BrainCopy\nclass C(BrainCopy):\n    name = 'c'\n")
    assert load_copy(f"{p}:C")().name == "c"


def test_echo_agreement():
    rows = [{"split": "cv3", "fold": 0, "metric": m, "verdict": v, "system_median": 0.9, "bio_median": 0.9}
            for m, v in (("L1.distribution", "inside"), ("C1.pattern", "outside"))]
    assert echo_agreement(rows) == pytest.approx(0.1)
