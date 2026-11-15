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
