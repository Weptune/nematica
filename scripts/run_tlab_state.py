"""Phase 5b: the worms' sign-aligned first-component state test on the transformer's phase 1 recordings."""
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica import tlab as T  # noqa: E402
import run_week1 as W1  # noqa: E402

for cond in ("trained", "untrained"):
    recs = pickle.load((T.CACHE / f"phase1_{cond}.pkl").open("rb"))
    ws = [w for w in (W1.Worm(r, valid_fn=lambda c: True) for r in recs) if W1.pc1_state(w) is not None]
    W1.run_b2(worms=ws, state_fn=W1.aligned_state_fn(ws), fname=f"b2_pc1_aligned_transformer_{cond}.txt", exclude=None)
