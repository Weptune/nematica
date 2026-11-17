"""Study 3 systems with intrinsic noise (docs/PERSIST.md section 5): N3, the GRU with Gaussian noise added
to its hidden state at every character; N6, Pythia with Gaussian noise added to the residual stream after
every layer at every token. With noise_sd = 0 both reproduce Study 2's functions exactly
(`nematica.slow.inputs.char_repeats` and `lm_repeats`; checked in scripts/persist_noise_check.py)."""
from __future__ import annotations

import numpy as np


def char_repeats_noisy(model, data, split, clip_len, R=20, between=(200, 600), seed=0, noise_sd=0.0,
                       noise_seed=0):
    """As `nematica.slow.inputs.char_repeats`, plus h <- h + noise_sd * N(0, 1) after every step (the noise
    enters the recurrence, so it propagates). The context draws are the same as Study 2's for a given seed."""
    import torch
    emb, cell, n = model
    rng = np.random.default_rng(70_000 + seed)
    held = data[split:]
    clip = held[:clip_len]
    seq, starts = [], []
    t = 0
    for r in range(R):
        L = int(rng.integers(between[0], between[1] + 1))
        a = int(rng.integers(clip_len, len(held) - L))
        seq.append(held[a:a + L])
        t += L
        starts.append(t)
        seq.append(clip)
        t += clip_len
    x = torch.tensor(np.concatenate(seq))
    out = np.empty((len(x), n), np.float32)
    gen = torch.Generator().manual_seed(int(noise_seed))
    with torch.no_grad():
        e = emb(x)
        h = torch.zeros(1, n)
        for i in range(len(x)):
            h = cell(e[i:i + 1], h)
            if noise_sd > 0:
                h = h + noise_sd * torch.randn(h.shape, generator=gen)
            out[i] = h[0].numpy()
    return out, starts


def lm_repeats_noisy(model_name, clip, contexts, keep=480, layer=None, seed=0, dtype="float32", noise_sd=0.0,
                     noise_seed=0):
    """As `nematica.slow.inputs.lm_repeats` (amendment S8 path), plus, after every kept layer, Gaussian noise
    of SD noise_sd x that layer output's SD (over the sequence and features) added to the residual stream,
    fresh for every token and every repeat. Pythia only."""
    import gc

    import torch
    from transformers import AutoModelForCausalLM
    torch.set_num_threads(2)
    m = AutoModelForCausalLM.from_pretrained(model_name, dtype="auto").eval()
    C = len(clip)
    body = m.gpt_neox
    L = layer if layer is not None else len(body.layers) // 2
    m.embed_out = torch.nn.Identity()
    body.layers = body.layers[:L + 1]
    m = m.to(getattr(torch, dtype))
    gc.collect()
    gen = torch.Generator().manual_seed(int(noise_seed))
    buf = []
    hooks = [body.layers[L].mlp.act.register_forward_hook(
        lambda mod, inp, out: buf.append(out[0, -C:].detach().float().numpy()))]
    if noise_sd > 0:
        def add_noise(mod, inp, out):
            hs = out[0] if isinstance(out, tuple) else out
            hs = hs + noise_sd * hs.std() * torch.randn(hs.shape, generator=gen, dtype=hs.dtype)
            return (hs, *out[1:]) if isinstance(out, tuple) else hs
        # noise after each layer before the recorded one, and inside the recorded layer on the input of its
        # MLP (the output of post_attention_layernorm; Pythia uses parallel attention and MLP), so the
        # recorded MLP units see noise of their own layer too
        for j in range(L):
            hooks.append(body.layers[j].register_forward_hook(add_noise))
        hooks.append(body.layers[L].post_attention_layernorm.register_forward_hook(add_noise))
    with torch.no_grad():
        for ctx in contexts:
            body(torch.tensor(np.concatenate([ctx, clip])[None], dtype=torch.long), use_cache=False)
    for h in hooks:
        h.remove()
    units = buf[0].shape[1]
    cols = np.sort(np.random.default_rng(seed).choice(units, min(keep, units), replace=False))
    A = np.concatenate([b[:, cols] for b in buf], 0).astype(np.float32)
    del m
    return A, [r * C for r in range(len(contexts))], {"model": model_name, "layer": int(L), "clip": C,
                                                     "context": len(contexts[0]), "units_total": int(units),
                                                     "noise_sd": float(noise_sd)}
