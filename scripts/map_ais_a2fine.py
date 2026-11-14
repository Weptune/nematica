"""A2 re-recorded at a finer step (amendment 24). At 512 units the trained task RNN is much faster than the
128-unit one whose timescale (about 1,500 steps) set the 100-step block means of amendment 19; with those
blocks its native timescale is 0.6 to 2 samples, outside calibrated speed; with 10-step blocks it was still 0.7
(the units mostly follow the white evidence input). Here every step is kept (the original 128-unit
recording path) with 4,000 trials (240,000 steps; two 5,000-timescale crops need about 100,000). Same training (seeds, lr 3e-4,
accuracy guard); everything else is scripts/map_ais.py._record unchanged (its code hash is stored)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_ais as AIS  # noqa: E402
from nematica.map import zoo  # noqa: E402


def a2(s):
    A, seg, meta = zoo.task_rnn(seed=s, n=512, trials=4_000, every=1, lr=3e-4)
    print("A2 seed", s, "accuracy", meta["accuracy"], flush=True)
    if meta["accuracy"] < 0.7:
        raise RuntimeError(f"A2 seed {s} did not learn the task (accuracy {meta['accuracy']:.2f})")
    return A, seg


if __name__ == "__main__":
    d = json.loads((ROOT / "docs/figures/map_step1.json").read_text())["preparations"]
    AIS._record("A2", "", lambda: [a2(s) for s in range(3)], ["R2", "R4g"], d, "")
