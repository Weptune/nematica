"""Pythia-1B (A6-1b) for scripts/map_ais.py with a memory-only change: the recording hook keeps only the
sampled units of each segment instead of all 8,192 MLP units (the full buffer ran out of memory on this
8 GB machine). The units kept are the same as nematica.map.ai.record would choose (the same seeded draw over
the same number of units), so the activity is identical; everything else is scripts/map_ais.py (its code
hash is stored). Usage: python scripts/map_ais_big.py [AI ids]"""
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_ais as AIS  # noqa: E402
from nematica.map import ai  # noqa: E402


def record_lowmem(model_name, tokens, layer=None, seg=2048, keep=1000, revision=None, seed=0, burn=128,
                  ou_tau=None, **kw):
    assert not ou_tau and "mamba" not in model_name
    from transformers import AutoModelForCausalLM
    torch.set_num_threads(2)
    m = AutoModelForCausalLM.from_pretrained(model_name, revision=revision, dtype=torch.float16,
                                             low_cpu_mem_usage=True).eval()
    m = m.float()                                         # converted parameter by parameter: lower peak memory
                                                          # than loading in float32; the same float32 weights
    blocks = m.gpt_neox.layers
    L = layer if layer is not None else len(blocks) // 2
    d = m.config.intermediate_size
    cols = np.sort(np.random.default_rng(seed).choice(d, min(keep, d), replace=False))   # as ai.record
    ct = torch.tensor(cols)
    buf = []
    h = blocks[L].mlp.act.register_forward_hook(lambda mod, inp, out: buf.append(out[0][:, ct].float().numpy()))
    tokens = np.asarray(tokens)
    starts = list(range(0, len(tokens) - seg + 1, seg))
    with torch.no_grad():
        for s in starts:
            m(torch.tensor(tokens[s:s + seg][None], dtype=torch.long))
    h.remove()
    del m
    A = np.concatenate([b[burn:] for b in buf], 0)
    return A.astype(np.float32), [i * (seg - burn) for i in range(1, len(buf))], {
        "model": model_name, "layer": int(L), "units_total": int(d), "lowmem": True}


if __name__ == "__main__":
    ai.record = record_lowmem
    for aid in sys.argv[1:] or ["A6-1b"]:
        AIS.run(aid)
