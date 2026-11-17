"""Study 4 systems (docs/BARCODE.md): language models read at several depths in one forward pass, and a
stacked noisy random RNN driven by the flicker (reference)."""
from __future__ import annotations

import numpy as np

FRACS = (1 / 8, 3 / 8, 5 / 8, 7 / 8)


def depth_layers(n_layers, fracs=FRACS):
    return [int(min(n_layers - 1, max(0, round(f * n_layers - 0.5)))) for f in fracs]


def lm_depth_repeats(model_name, clip, contexts, keep=480, seed=0, dtype="float32"):
    """Like `nematica.slow.inputs.lm_repeats` (amendment S8 path: checkpoint precision, layers after the
    deepest one read are dropped, cast to float32, only the body runs), but units are read at 4 depths in
    one pass. Returns ([A_k for each depth], starts, meta); each A_k holds `keep` seeded units."""
    import gc

    import torch
    from transformers import AutoModelForCausalLM
    torch.set_num_threads(2)
    m = AutoModelForCausalLM.from_pretrained(model_name, dtype="auto").eval()
    C = len(clip)
    mamba = "mamba" in model_name
    body = m.backbone if mamba else m.gpt_neox
    if not mamba:
        m.embed_out = torch.nn.Identity()
    Ls = depth_layers(len(body.layers))
    body.layers = body.layers[:max(Ls) + 1]
    m = m.to(getattr(torch, dtype))
    gc.collect()
    bufs = {L: [] for L in Ls}
    hooks = []
    for L in Ls:
        if mamba:
            hooks.append(body.layers[L].mixer.out_proj.register_forward_hook(
                lambda mod, inp, out, L=L: bufs[L].append(inp[0][0, -C:].detach().float().numpy())))
        else:
            hooks.append(body.layers[L].mlp.act.register_forward_hook(
                lambda mod, inp, out, L=L: bufs[L].append(out[0, -C:].detach().float().numpy())))
    with torch.no_grad():
        for ctx in contexts:
            body(torch.tensor(np.concatenate([ctx, clip])[None], dtype=torch.long), use_cache=False)
    for h in hooks:
        h.remove()
    out = []
    for i, L in enumerate(Ls):
        units = bufs[L][0].shape[1]
        cols = np.sort(np.random.default_rng([seed, i]).choice(units, min(keep, units), replace=False))
        out.append(np.concatenate([b[:, cols] for b in bufs[L]], 0).astype(np.float32))
    del m
    return out, [r * C for r in range(len(contexts))], {"model": model_name, "layers": Ls, "clip": C}


def stacked_rnn(flicker, R=90, layers=4, n=480, g=1.5, alpha=0.2, noise=0.1, gain=0.5, spf=3.0, seed=0, burn=2000):
    """Reference (not counted): `layers` random RNNs in a chain. Layer 1 gets the full-field flicker
    (one value per frame, -1 or 1) through a fixed random input vector; each later layer gets the previous
    layer's activity through a fixed random matrix (variance 1/n), scaled by `gain`. Each layer has its own
    noise. The clip repeats R times back to back, as the flicker does. Returns ([A_k], starts) per layer."""
    rng = np.random.default_rng(seed)
    W = [rng.normal(0, 1 / np.sqrt(n), (n, n)) for _ in range(layers)]
    B0 = rng.normal(0, 1, n)
    F = [rng.normal(0, 1 / np.sqrt(n), (n, n)) for _ in range(layers - 1)]
    nf = len(flicker)
    L = int(round(nf * spf))
    fi = np.minimum((np.arange(L) / spf).astype(int), nf - 1)
    x = [rng.normal(0, 1, n) for _ in range(layers)]
    for _ in range(burn):
        for k in range(layers):
            x[k] = (1 - alpha) * x[k] + alpha * np.tanh(g * W[k] @ x[k]) + noise * rng.standard_normal(n)
    A = [np.empty((R * L, n), np.float32) for _ in range(layers)]
    for t in range(R * L):
        u = gain * B0 * flicker[fi[t % L]]
        for k in range(layers):
            drive = u if k == 0 else gain * (F[k - 1] @ x[k - 1])
            x[k] = (1 - alpha) * x[k] + alpha * np.tanh(g * W[k] @ x[k] + drive) + noise * rng.standard_normal(n)
            A[k][t] = x[k]
    return A, [r * L for r in range(R)]
