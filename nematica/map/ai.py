"""Recording unit activity from pretrained language models for the map (docs/MAP.md, A6 and A7).

Units: the computing units of a middle layer: MLP neurons after the nonlinearity (Pythia), and the gated
SSM output channels before the output projection (Mamba). Input: the fixed book sample, fed as
consecutive non-overlapping segments of `seg` tokens (the same input regime for both families).
"""
from __future__ import annotations

import numpy as np
import torch


def record(model_name, tokens, layer=None, seg=2048, keep=1000, revision=None, seed=0):
    from transformers import AutoModelForCausalLM
    torch.set_num_threads(2)
    m = AutoModelForCausalLM.from_pretrained(model_name, revision=revision, torch_dtype=torch.float32).eval()
    if "mamba" in model_name:
        blocks = m.backbone.layers
        L = layer if layer is not None else len(blocks) // 2
        target = blocks[L].mixer.out_proj
        grab = lambda mod, inp, out: buf.append(inp[0][0].detach().float().numpy())
        h = target.register_forward_hook(grab)
    else:
        blocks = m.gpt_neox.layers
        L = layer if layer is not None else len(blocks) // 2
        target = blocks[L].mlp.act
        grab = lambda mod, inp, out: buf.append(out[0].detach().float().numpy())
        h = target.register_forward_hook(grab)
    buf = []
    tokens = np.asarray(tokens)
    with torch.no_grad():
        for s in range(0, len(tokens) - seg + 1, seg):
            m(torch.tensor(tokens[s:s + seg][None], dtype=torch.long))
    h.remove()
    A = np.concatenate(buf, 0)
    rng = np.random.default_rng(seed)
    cols = rng.choice(A.shape[1], min(keep, A.shape[1]), replace=False)
    return A[:, np.sort(cols)].astype(np.float32), {"model": model_name, "layer": int(L), "seg": seg,
                                                   "units_total": int(A.shape[1]), "revision": revision}
