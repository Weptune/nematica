"""Study O (docs/OPTO.md): response profiles, the watching copy (W), the poke-learned copy (P), and synthetic
systems with known coupling for calibration. Bins are 20 ms throughout."""
from __future__ import annotations

import numpy as np

BIN = 0.02
TEST_BINS = 50          # the 1 s half-cosine
PRE_BINS = 50           # 1 s before onset


# ------------------------------------------------------------------ profiles and agreement
def unit_responses(counts, onsets, sd):
    """counts: (T, N) spike counts; onsets: bin indices; sd: (N,) SD of 1 s spontaneous counts.
    Response per unit and trial: rate 0-1 s after onset minus the 1 s before, in SD units. Returns (trials, N)."""
    out = []
    for o in onsets:
        post = counts[o:o + TEST_BINS].sum(0)
        pre = counts[o - PRE_BINS:o].sum(0)
        out.append((post - pre) / np.maximum(sd, 1e-9))
    return np.asarray(out)


def profile(resp, cls, classes):
    """Per class, the median over its units of the mean response across trials."""
    m = resp.mean(0)
    return np.array([np.median(m[cls == k]) for k in classes])


def agree(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 4 or np.std(a[ok]) == 0 or np.std(b[ok]) == 0:
        return np.nan
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


# ------------------------------------------------------------------ copies
def class_rates(counts, cls, classes):
    return np.stack([counts[:, cls == k].mean(1) for k in classes], 1)


def fit_watch(X):
    """W: VAR(1) on z-scored class rates of spontaneous activity, X (T, K). Returns (M, mu, sd)."""
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    M, *_ = np.linalg.lstsq(Z[:-1], Z[1:], rcond=None)
    return M.T, mu, sd


def predict_watch(model, tag_course, tag_index):
    """Clamp the tagged class to its measured response time course (z units), propagate with M, and return
    each class's mean change over the response window (z units)."""
    M, mu, sd = model
    K = M.shape[0]
    x = np.zeros(K)
    acc = np.zeros(K)
    for t in range(len(tag_course)):
        x = M @ x
        x[tag_index] = tag_course[t]
        acc += x
    return acc / len(tag_course)


def fit_poke(train_courses, tag_train, L=TEST_BINS):
    """P: FIR kernels from the tagged course to each class's course, by least squares on trial-averaged
    train-condition courses. train_courses (T, K), tag_train (T,)."""
    T = len(tag_train)
    D = np.zeros((T, L))
    for j in range(L):
        D[j:, j] = tag_train[:T - j]
    H, *_ = np.linalg.lstsq(D, train_courses, rcond=None)
    return H                                      # (L, K)


def predict_poke(H, tag_test):
    T, L = len(tag_test), H.shape[0]
    D = np.zeros((T, L))
    for j in range(L):
        D[j:, j] = tag_test[:T - j]
    return (D @ H).mean(0)


# ------------------------------------------------------------------ synthetic systems
def synthetic(rng, K=12, n_per=20, n_tag=8, silent=False, coupling=None, A=None, minutes=20, n_train=90, n_test=75,
              base_hz=5.0, gain=0.5):
    """A network of K classes plus a tagged class. Class latents follow stable linear dynamics with shared
    noise; the tagged latent drives the others through coupling c, linearly (links active at rest) or only
    above a threshold of 4 resting SDs (links silent at rest). Units fire Poisson spikes at
    base * exp(gain * latent). Returns counts (T, N), class labels (tagged = -1), onsets, and the coupling."""
    A = rng.normal(0, 1, (K, K)) / np.sqrt(K) if A is None else A
    A = A * (0.85 / max(abs(np.linalg.eigvals(A))))
    c = rng.normal(0, 1, K) if coupling is None else coupling
    rho, sig = 0.9, 0.3
    tag_sd = sig / np.sqrt(1 - rho ** 2)
    thr = 4 * tag_sd
    T_sp = int(minutes * 60 / BIN)
    gap = 100                                      # 2 s between trials
    T = T_sp + (n_train + n_test) * gap + PRE_BINS
    stim = np.zeros(T)
    on_train = T_sp + PRE_BINS + gap * np.arange(n_train)
    on_test = T_sp + PRE_BINS + gap * (n_train + np.arange(n_test))
    for o in on_train:
        stim[o] = 8 * tag_sd                       # a brief square pulse
    hc = np.sin(np.pi * np.arange(TEST_BINS) / TEST_BINS)
    for o in on_test:
        stim[o:o + TEST_BINS] += 1.2 * tag_sd * hc  # a 1 s half-cosine
    z = np.zeros((T, K)); tau = np.zeros(T)
    e = rng.normal(0, sig, (T, K)); et = rng.normal(0, sig, T)
    for t in range(1, T):
        tau[t] = rho * tau[t - 1] + et[t] + stim[t]
        drive = tau[t - 1] if not silent else max(0.0, tau[t - 1] - thr) * 3
        z[t] = A @ z[t - 1] + e[t] + 0.25 * c * drive
    zs = z / z[:T_sp].std(0)
    taus = tau / tau[:T_sp].std()
    cls = np.concatenate([np.full(n_tag, -1)] + [np.full(n_per, k) for k in range(K)])
    lat = np.concatenate([np.repeat(taus[:, None], n_tag, 1)] + [np.repeat(zs[:, [k]], n_per, 1) for k in range(K)], 1)
    base = base_hz * BIN * rng.lognormal(0, 0.6, lat.shape[1])
    counts = rng.poisson(base * np.exp(gain * lat)).astype(np.float32)
    return counts, cls, T_sp, on_train, on_test, c


# ------------------------------------------------------------------ amendment A4: class x time profiles
NB = 10  # 100 ms bins over the 1 s response window


def _chunks(Y, nb=NB):
    """(T, ...) -> (nb, ...) means over equal chunks of the first axis."""
    return Y[: (len(Y) // nb) * nb].reshape(nb, -1, *Y.shape[1:]).mean(1)


def unit_courses(counts, onsets, sd, nb=NB):
    """Per trial, unit and 100 ms bin: count minus the mean pre-onset count per bin, in units of the 1 s
    spontaneous SD scaled to the bin. Returns (trials, nb, N)."""
    out = []
    for o in onsets:
        post = counts[o:o + TEST_BINS].reshape(nb, -1, counts.shape[1]).sum(1)
        pre = counts[o - PRE_BINS:o].sum(0) / nb
        out.append((post - pre) / np.maximum(sd / np.sqrt(nb), 1e-9))
    return np.asarray(out)


def profile_t(resp, cls, classes):
    """Per class and bin, the median over its units of the trial mean. Returns flattened (K * nb,)."""
    m = resp.mean(0)
    return np.stack([np.median(m[:, cls == k], 1) for k in classes], 0).ravel()


def predict_watch_t(model, tag_course, tag_index):
    M = model[0]
    x = np.zeros(M.shape[0]); traj = []
    for t in range(len(tag_course)):
        x = M @ x
        x[tag_index] = tag_course[t]
        traj.append(x.copy())
    return np.delete(_chunks(np.asarray(traj)), tag_index, 1).T.ravel()


def predict_poke_t(H, tag_test):
    T, L = len(tag_test), H.shape[0]
    D = np.zeros((T, L))
    for j in range(L):
        D[j:, j] = tag_test[:T - j]
    return _chunks(D @ H).T.ravel()
