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


def driven_rnn(feat, other, R=10, n=480, g=1.5, alpha=0.2, noise=0.1, gain=0.86, spf=3.0, seed=0, burn=2000,
               interlude=(30, 90), keep_every=1):
    """Controls K1 to K3 (docs/PERSIST.md section 5): Study 2's movie-driven random RNN
    (`nematica.slow.inputs.driven_random_rnn`, same update and weights for a given seed), generalised to a
    clip of any length (NM3: 3,600 frames) and with an interlude before every repeat: a random stretch of
    30 to 90 frames of a different movie (`other`, NM1 features), so the state entering each repeat differs,
    as the language models' contexts do. K1: g 1.5, noise 0 (chaotic, noise-free). K2: g 0.8, noise 0
    (stable, noise-free). K3: g 1.5, noise 0.1 (Study 2's A1). Returns (A, starts) in kept samples."""
    rng = np.random.default_rng(seed)
    d = feat.shape[1]
    W = rng.normal(0, 1 / np.sqrt(n), (n, n))
    B = rng.normal(0, 1 / np.sqrt(d), (n, d))
    drive = gain * (feat @ B.T)
    drive_o = gain * (other @ B.T)
    nf = len(feat)
    L = int(round(nf * spf))
    fi = np.minimum((np.arange(L) / spf).astype(int), nf - 1)
    ri = np.random.default_rng(90_000 + seed)
    x = rng.normal(0, 1, n)
    for _ in range(burn):
        x = (1 - alpha) * x + alpha * np.tanh(g * W @ x) + noise * rng.standard_normal(n)
    k = int(keep_every)
    out, starts, acc, cnt, kept = [], [], np.zeros(n), 0, 0

    def step(u):
        nonlocal x, acc, cnt, kept
        x = (1 - alpha) * x + alpha * np.tanh(g * W @ x + u) + noise * rng.standard_normal(n)
        acc += x
        cnt += 1
        if cnt == k:
            out.append((acc / k).astype(np.float32))
            acc[:] = 0
            cnt = 0
            kept += 1

    for r in range(R):
        m = int(ri.integers(interlude[0], interlude[1] + 1))
        a = int(ri.integers(0, len(other) - m))
        Li = int(round(m * spf))
        fo = a + np.minimum((np.arange(Li) / spf).astype(int), m - 1)
        for t in range(Li):
            step(drive_o[fo[t]])
        if cnt:                                     # align the repeat's start to a kept sample
            acc[:] = 0
            cnt = 0
        starts.append(kept)
        for t in range(L):
            step(drive[fi[t]])
    return np.stack(out), starts, {"g": g, "noise": noise, "gain": gain, "spf": spf, "keep_every": k,
                                   "clip_kept": L // k}
