"""Recording unit activity from pretrained language models for the map (docs/MAP.md, A6 and A7, and
augmented candidate (b)).

Units: the computing units of a middle layer: MLP neurons after the nonlinearity (Pythia), and the gated
SSM output channels before the output projection (Mamba). Input: the fixed book sample, fed as
consecutive non-overlapping segments of `seg` tokens; the first `burn` tokens of each segment are dropped
(amendment 2) and segment boundaries are returned, so windows and autocovariances never cross them.
Candidate (b): an Ornstein-Uhlenbeck latent (time constant `ou_tau` tokens) through a fixed random
projection is added to the residual stream at the recorded layer's input, scaled so that it carries
`ou_share` of that stream's variance.
"""
from __future__ import annotations

import numpy as np
import torch


def record(model_name, tokens, layer=None, seg=2048, keep=1000, revision=None, seed=0, burn=128,
           ou_tau=None, ou_share=0.3, ou_k=16):
    from transformers import AutoModelForCausalLM
    torch.set_num_threads(2)
    m = AutoModelForCausalLM.from_pretrained(model_name, revision=revision, torch_dtype=torch.float32).eval()
    if "mamba" in model_name:
        blocks = m.backbone.layers
        L = layer if layer is not None else len(blocks) // 2
        target = blocks[L].mixer.out_proj
        grab = lambda mod, inp, out: buf.append(inp[0][0].detach().float().numpy())
    else:
        blocks = m.gpt_neox.layers
        L = layer if layer is not None else len(blocks) // 2
        target = blocks[L].mlp.act
        grab = lambda mod, inp, out: buf.append(out[0].detach().float().numpy())
    buf = []
    hooks = [target.register_forward_hook(grab)]
    tokens = np.asarray(tokens)
    starts = list(range(0, len(tokens) - seg + 1, seg))
    if ou_tau:                                            # candidate (b)
        rng = np.random.default_rng(20_000 + seed)
        state = {"scale": None}
        probe = []
        hp = blocks[L].register_forward_pre_hook(lambda mod, args: probe.append(args[0][0].detach()))
        with torch.no_grad():
            m(torch.tensor(tokens[:seg][None], dtype=torch.long))
        hp.remove()
        buf.clear()                                       # the probe pass is not part of the recording
        sd = probe[0].std(0)
        d = sd.shape[0]
        P = torch.tensor(rng.normal(0, 1, (ou_k, d)) / np.sqrt(ou_k), dtype=torch.float32)
        a = float(np.exp(-1 / ou_tau))

        def ou(n):
            z = np.zeros((n, ou_k))
            x = rng.standard_normal(ou_k)
            e = rng.standard_normal((n, ou_k)) * np.sqrt(1 - a * a)
            for t in range(n):
                x = a * x + e[t]
                z[t] = x
            return torch.tensor(z, dtype=torch.float32)

        def pre(mod, args):
            h = args[0]
            S = ou(h.shape[1]) @ P
            S = (S - S.mean(0)) / (S.std(0) + 1e-6)
            return (h + (S * sd * np.sqrt(ou_share / (1 - ou_share)))[None],) + tuple(args[1:])
        hooks.append(blocks[L].register_forward_pre_hook(pre))
    with torch.no_grad():
        for s in starts:
            m(torch.tensor(tokens[s:s + seg][None], dtype=torch.long))
    for h in hooks:
        h.remove()
    A = np.concatenate([b[burn:] for b in buf], 0)
    seg_starts = [i * (seg - burn) for i in range(1, len(buf))]
    rng = np.random.default_rng(seed)
    cols = rng.choice(A.shape[1], min(keep, A.shape[1]), replace=False)
    return A[:, np.sort(cols)].astype(np.float32), seg_starts, {
        "model": model_name, "layer": int(L), "seg": seg, "burn": burn, "units_total": int(A.shape[1]),
        "revision": revision, "ou_tau": ou_tau}
