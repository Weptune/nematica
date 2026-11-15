"""Study 2 inputs (feasibility check F2, docs/SLOW.md section 8).

The mice saw Allen's natural_movie_one (900 frames at 30 Hz, shown back to back in blocks). The AIs must see
the same clip, repeated the same way, with their own internal state free to differ from repeat to repeat.

Third-party data rule: the movie template comes from Allen's public bucket and stays in data/external
(git-ignored). Only derived summary numbers may be committed. The template file is named .h5 but is a NumPy
array (900, 304, 608) uint8 saved under Python 2; it is read with allow_pickle=False.
"""
import os
import numpy as np

MOVIE1 = os.path.join(os.path.dirname(__file__), "..", "..", "data", "external", "allen", "natural_movie_1.h5")
FRAME_MS = 1000.0 / 30.0      # natural_movie_one frame duration
BIN_MS = 20.0                 # the bin width behind every Allen `bins_per_tau` value


def movie_frames(path=MOVIE1):
    return np.load(path, mmap_mode="r", allow_pickle=False)


def movie_features(path=MOVIE1, d=64, ds=8, cache=True):
    """Movie -> (900, d) features: frames block-averaged by `ds` in each direction (304x608 -> 38x76), centred
    per pixel, then the top `d` principal components, each scaled to unit variance. A fixed, model-free
    summary of the clip; every movie-driven AI gets it through its own fixed random input weights."""
    out = os.path.join(os.path.dirname(path), "..", "..", "derived", f"movie1_pca{d}_ds{ds}.npy")
    if cache and os.path.exists(out):
        return np.load(out)
    F = movie_frames(path)
    n, h, w = F.shape
    h2, w2 = h // ds, w // ds
    X = np.empty((n, h2 * w2), np.float32)
    for i in range(n):
        X[i] = np.asarray(F[i, :h2 * ds, :w2 * ds], np.float32).reshape(h2, ds, w2, ds).mean((1, 3)).ravel()
    X -= X.mean(0)
    U, s, _ = np.linalg.svd(X, full_matrices=False)
    Z = (U[:, :d] * s[:d]).astype(np.float32)
    Z /= Z.std(0)
    if cache:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        np.save(out, Z)
    return Z


def steps_per_frame(tau_native, bins_per_tau):
    """Play the clip at the same speed relative to the system's own clock as for the mouse: a mouse whose
    timescale is `bins_per_tau` 20 ms bins sees bins_per_tau * 20 / 33.3 frames per timescale, so a system with
    native timescale `tau_native` steps gets tau_native / that many steps per frame (not rounded)."""
    frames_per_tau = bins_per_tau * BIN_MS / FRAME_MS
    return tau_native / frames_per_tau


def frame_index(T, spf):
    """Frame shown at each of T native steps when each frame lasts `spf` (possibly fractional) steps."""
    return np.minimum((np.arange(T) / spf).astype(int), 899)


def driven_random_rnn(feat, R=20, n=480, g=1.5, alpha=0.2, noise=0.1, gain=1.0, spf=3.0, seed=0, burn=2000,
                      lead_frames=None):
    """Family A1, movie-driven: x <- (1 - alpha) x + alpha tanh(g W x + gain B u(t)) + noise, with W as in
    nematica.map.zoo.random_rnn and B a fixed Gaussian input matrix (variance 1/d). The clip is shown R times
    back to back, as in an Allen block; the network runs continuously from a burn-in on a blank (zero) input,
    so each repeat starts from whatever state the previous one left. Returns (A, starts), A in native steps."""
    rng = np.random.default_rng(seed)
    d = feat.shape[1]
    W = rng.normal(0, 1 / np.sqrt(n), (n, n))
    B = rng.normal(0, 1 / np.sqrt(d), (n, d))
    drive = gain * (feat @ B.T)                       # (900, n), computed once
    L = int(round(900 * spf))
    fi = frame_index(L, spf)
    x = rng.normal(0, 1, n)
    for _ in range(burn):
        x = (1 - alpha) * x + alpha * np.tanh(g * W @ x) + noise * rng.standard_normal(n)
    A = np.empty((R * L, n), np.float32)
    for r in range(R):
        for t in range(L):
            x = (1 - alpha) * x + alpha * np.tanh(g * W @ x + drive[fi[t]]) + noise * rng.standard_normal(n)
            A[r * L + t] = x
    return A, [r * L for r in range(R)], {"family": "A1-movie", "n": n, "g": g, "gain": gain, "spf": spf}


def text_clip_and_contexts(tokens, clip_len, ctx_len, R, seed=0, clip_at=None):
    """A fixed text clip and R different preceding contexts, all from the book sample used in the map study
    (data/external/books/tokens.npy). The clip is taken from one place; each context is a different
    stretch elsewhere, chosen at random without overlap with the clip or each other."""
    rng = np.random.default_rng(seed)
    T = len(tokens)
    a = clip_at if clip_at is not None else T // 2
    clip = tokens[a:a + clip_len]
    n_slots = T // ctx_len
    banned = set(range(max(a - ctx_len, 0) // ctx_len, (a + clip_len) // ctx_len + 1))
    slots = [s for s in rng.permutation(n_slots) if s not in banned][:R]
    return clip, [tokens[s * ctx_len:(s + 1) * ctx_len] for s in slots]


def lm_repeats(model_name, clip, contexts, keep=480, layer=None, seed=0, dtype="float32"):
    """Language models (families A6, A7) are deterministic and carry no state between calls, so a repeat's
    internal state is its preceding context: repeat r is one forward pass over contexts[r] + clip, and only
    the clip's tokens are kept. Units as in the map study (nematica.map.ai): MLP neurons after the
    nonlinearity of the middle layer (Pythia), gated SSM outputs before out_proj (Mamba); `keep` of them at
    random (seed). Returns (A, starts): the R clip blocks end to end, so the shared recording code applies."""
    import torch
    from transformers import AutoModelForCausalLM
    torch.set_num_threads(2)
    m = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=getattr(torch, dtype)).eval()
    C = len(clip)
    if "mamba" in model_name:
        blocks = m.backbone.layers
        L = layer if layer is not None else len(blocks) // 2
        target = blocks[L].mixer.out_proj
        grab = lambda mod, inp, out: buf.append(inp[0][0, -C:].detach().float().numpy())
    else:
        blocks = m.gpt_neox.layers
        L = layer if layer is not None else len(blocks) // 2
        target = blocks[L].mlp.act
        grab = lambda mod, inp, out: buf.append(out[0, -C:].detach().float().numpy())
    buf = []
    h = target.register_forward_hook(grab)
    with torch.no_grad():
        for ctx in contexts:
            m(torch.tensor(np.concatenate([ctx, clip])[None], dtype=torch.long))
    h.remove()
    units = buf[0].shape[1]
    cols = np.sort(np.random.default_rng(seed).choice(units, min(keep, units), replace=False))
    A = np.concatenate([b[:, cols] for b in buf], 0).astype(np.float32)
    del m
    return A, [r * C for r in range(len(contexts))], {"model": model_name, "layer": int(L), "clip": C,
                                                     "context": len(contexts[0]), "units_total": int(units)}


# ---------------------------------------------------------------- A2: the trained decision-task RNN
def trained_task_rnn(seed=0, n=512, lr=3e-4):
    """The map study's A2 network, trained by the registered code (nematica.map.zoo.task_rnn, settings of
    amendments 19 and 22). task_rnn does not return the network, so its long-session helper is swapped for
    one that captures it; nothing else in the training path changes."""
    import torch
    from ..map import zoo
    got = {}

    def capture(net, n_, trials, every, seed_, chunk=1000):
        got["net"] = net
        return np.zeros((1, n_), np.float32), None

    orig = zoo._long_session
    zoo._long_session = capture
    try:
        zoo.task_rnn(seed=seed, n=n, trials=1000, every=60, lr=lr)
    finally:
        zoo._long_session = orig
    net = got["net"]
    X, y = zoo.decision_task(1000, rng=np.random.default_rng(seed + 777))
    with torch.no_grad():
        _, o = net(torch.tensor(X))
    acc = float((o[:, -1].argmax(-1).numpy() == y).mean())
    return net, acc


def task_rnn_repeats(net, R=20, clip_trials=100, between=(5, 15), seed=0, n=512):
    """The same sequence of `clip_trials` trials (one fixed draw of evidence noise) shown R times; between
    repeats a random number (uniform in `between`) of fresh random trials, so that each repeat starts from
    a different state. The network runs as one continuous session, as in the map study. Returns (A, starts)
    in native steps (60 per trial)."""
    import torch
    from ..map import zoo
    rng = np.random.default_rng(50_000 + seed)
    clip, _ = zoo.decision_task(clip_trials, rng=np.random.default_rng(60_000 + seed))
    clip = clip.reshape(1, -1, 3)
    parts, starts, t = [], [], 0
    with torch.no_grad():
        h0 = torch.zeros(1, 1, n)
        for r in range(R + 1):
            g, _ = zoo.decision_task(int(rng.integers(between[0], between[1] + 1)), rng=rng)
            h, h0 = net.rnn(torch.tensor(g.reshape(1, -1, 3)), h0)
            parts.append(h[0].numpy())
            t += h.shape[1]
            if r == R:
                break
            h, h0 = net.rnn(torch.tensor(clip), h0)
            parts.append(h[0].numpy())
            starts.append(t)
            t += h.shape[1]
    return np.concatenate(parts).astype(np.float32), starts


# ---------------------------------------------------------------- A3, A5: character networks
def trained_char_net(kind="gru", seed=0, n=512, train_steps=1500, seq=128, batch=32, record_chars=200_000):
    """The map study's character network (nematica.map.zoo.char_net), trained by a verbatim copy of its
    training code, which returns only activity; the same seeds and data give the same weights (checked
    against zoo.char_net's first recorded states, see SLOW_LOG)."""
    import torch
    from ..map import zoo
    torch.set_num_threads(2)
    data, V = zoo.chars()
    split = len(data) - record_chars
    torch.manual_seed(seed)
    emb = torch.nn.Embedding(V, 32)
    cell = torch.nn.GRUCell(32, n) if kind == "gru" else zoo._cfc_cell(torch, 32, n)
    head = torch.nn.Linear(n, V)
    params = list(emb.parameters()) + list(cell.parameters()) + list(head.parameters())
    opt = torch.optim.Adam(params, lr=2e-3)
    rng = np.random.default_rng(seed)
    for i in range(train_steps):
        s = rng.integers(0, split - seq - 1, batch)
        xb = torch.tensor(np.stack([data[a:a + seq] for a in s]))
        yb = torch.tensor(np.stack([data[a + 1:a + seq + 1] for a in s]))
        h = torch.zeros(batch, n)
        e = emb(xb)
        loss = 0
        for t in range(seq):
            h = cell(e[:, t], h)
            loss = loss + torch.nn.functional.cross_entropy(head(h), yb[:, t])
        loss = loss / seq
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
    return (emb, cell, n), data, split


def char_repeats(model, data, split, clip_len, R=20, between=(200, 600), seed=0):
    """A fixed clip of held-out characters shown R times; before each repeat, a stretch of other held-out
    text of random length (uniform in `between`), so the state entering each repeat differs. One continuous
    run from a zero state. Returns (A, starts) in characters."""
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
    with torch.no_grad():
        e = emb(x)
        h = torch.zeros(1, n)
        for i in range(len(x)):
            h = cell(e[i:i + 1], h)
            out[i] = h[0].numpy()
    return out, starts


# ---------------------------------------------------------------- A4: the spiking network, movie-driven
def driven_lif(feat, R=20, spf=2.0, gain=0.5, seed=0, n=1000, frac_e=0.8, p=0.1, dt=0.0005, step=0.005,
               lead_s=2.0):
    """The map study's LIF network (nematica.map.zoo.lif_network, same constants), with the external
    Poisson rate of each neuron modulated by the movie: rate_i(t) = nu_ext * max(0, 1 + gain * (B u(t))_i),
    B a fixed Gaussian matrix with unit-variance rows over the 64 features (so B u has SD about 1).
    `spf` native 5 ms steps per frame. Runs continuously: `lead_s` seconds of blank input, then R repeats
    back to back. Activity: spike counts per 5 ms step. Returns (A, starts)."""
    rng = np.random.default_rng(seed)
    ne = int(n * frac_e)
    tau_m, v_th, v_r, t_ref = 0.02, 1.0, 0.0, 0.002
    J, g = 0.02, 5.0
    W = (rng.random((n, n)) < p).astype(np.float32)
    np.fill_diagonal(W, 0)
    W[:, :ne] *= J
    W[:, ne:] *= -g * J
    nu_ext = 1.1 * v_th / (J * p * ne * tau_m)
    lam = nu_ext * p * ne * dt
    rin = np.random.default_rng(80_000 + seed)
    B = rin.normal(0, 1 / np.sqrt(feat.shape[1]), (n, feat.shape[1]))
    mod = np.clip(1 + gain * (feat @ B.T), 0, None)          # (900, n)
    per = int(round(step / dt))
    L = int(round(900 * spf))
    lead = int(round(lead_s / step))
    fi = frame_index(L, spf)
    steps = lead + R * L
    v = rng.random(n) * v_th
    ref = np.zeros(n)
    out = np.zeros((steps, n), np.float32)
    for t in range(steps * per):
        s_ = t // per
        m = 1.0 if s_ < lead else mod[fi[(s_ - lead) % L]]
        I = J * rng.poisson(lam * m, n)
        v += dt / tau_m * (-v) + I
        v[ref > 0] = v_r
        ref -= dt
        s = np.flatnonzero(v >= v_th)
        if len(s):
            v[s] = v_r
            ref[s] = t_ref
            v += W[:, s].sum(1)
            out[s_, s] += 1
    return out, [lead + r * L for r in range(R)]


# ---------------------------------------------------------------- saving trained networks (state dicts)
def save_char_net(model, path, kind):
    """The map study's cells are local classes, which torch cannot pickle; save state dicts instead."""
    import torch
    emb, cell, n = model
    torch.save({"kind": kind, "n": n, "emb": emb.state_dict(), "cell": cell.state_dict(),
                "vocab": emb.num_embeddings}, path)


def load_char_net(path):
    import torch
    from ..map import zoo
    d = torch.load(path, weights_only=False)
    emb = torch.nn.Embedding(d["vocab"], 32)
    cell = torch.nn.GRUCell(32, d["n"]) if d["kind"] == "gru" else zoo._cfc_cell(torch, 32, d["n"])
    emb.load_state_dict(d["emb"])
    cell.load_state_dict(d["cell"])
    return emb.eval(), cell.eval(), d["n"]


def save_task_rnn(net, path):
    import torch
    torch.save({"rnn": net.rnn.state_dict(), "n": net.rnn.hidden_size}, path)


def load_task_rnn(path):
    import torch
    from types import SimpleNamespace
    d = torch.load(path, weights_only=False)
    rnn = torch.nn.RNN(3, d["n"], batch_first=True, nonlinearity="tanh")
    rnn.load_state_dict(d["rnn"])
    return SimpleNamespace(rnn=rnn.eval())


def add_slow_drive(A, share, tau_steps, seed=0, k=10):
    """H2 candidate: k Ornstein-Uhlenbeck drives with 1/e time `tau_steps` (native steps) through a fixed random
    projection, added to unit activity so they carry `share` of each unit's variance (as
    nematica.map.zoo.with_slow_drives, but with the time constant given directly, in movie time: the map
    version's 50 x the network's own timescale outlasts the clip once the network is driven; SLOW_LOG 17:45)."""
    A = np.asarray(A, np.float32)
    rng = np.random.default_rng(10_000 + seed)
    a = np.exp(-1 / tau_steps)
    Zs = np.empty((len(A), k), np.float32)
    z = rng.standard_normal(k)
    e = rng.standard_normal((len(A), k)) * np.sqrt(1 - a * a)
    for t in range(len(A)):
        z = a * z + e[t]
        Zs[t] = z
    S = Zs @ rng.normal(0, 1, (k, A.shape[1])).astype(np.float32)
    S = (S - S.mean(0)) / S.std(0)
    return A + S * (A.std(0) * np.sqrt(share / (1 - share)))
