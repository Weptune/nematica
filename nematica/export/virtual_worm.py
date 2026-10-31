"""A body for a simulated brain: motion matching on real training-worm posture.

The models generate neural activity plus behaviour (velocity, reversal state), but no body.
To show a simulated worm as a worm, its body is assembled from real postures:

    library      every well-tracked frame of the TRAINING worms: body shape relative to the
                 head direction (K points), the head's turn to the next frame, and behaviour
                 features (velocity now and over the next two frames, reversal state now and
                 in ~2 s) [M]
    matching     at each generated frame, the library frame whose behaviour features best
                 match the model's and whose body shape is closest to the current one is
                 chosen; continuing the current real clip is preferred (a jump costs
                 `jump_cost`), so movement stays smooth [A]
    orientation  the whole-body orientation (circular mean of segment angles) advances by
                 the matched clip's own turn per frame [M, borrowed]; using the head
                 direction instead makes the body spin with every head sweep
    path         the head moves at the MODEL's velocity along the head direction:
                 forward = head segment angle + pi (checked on real worms: cosine 0.90)

So the brain decides how fast and which way the worm goes; body shapes and steering are
borrowed from real worms. Provenance tag for the body: [L/borrowed].
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from .replay import K_POINTS, _display_level, _resample_posture

LOOKAHEAD = 3            # frames of reversal-state lookahead (~1.8 s)


def _wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def _features(vel, rev, v_scale, i):
    n = len(vel)
    j1, j2, j3 = min(i + 1, n - 1), min(i + 2, n - 1), min(i + LOOKAHEAD, n - 1)
    return np.array([vel[i] / v_scale, vel[j1] / v_scale, vel[j2] / v_scale,
                     1.5 * rev[i], 1.0 * rev[j3]])


def _causal_features(v, v_prev, rev, rev_prev, v_scale):
    return np.array([v / v_scale, v_prev / v_scale, 1.5 * rev, 1.0 * rev_prev])


@dataclass
class MotionLibrary:
    shapes: np.ndarray        # (N, K) segment angles relative to the whole-body orientation
    turn: np.ndarray          # (N,) whole-body orientation change to the next frame
    feats: np.ndarray         # (N, F)
    worm: np.ndarray          # (N,) worm index
    frame: np.ndarray         # (N,) frame index within the worm
    v_scale: float
    length_mm: float
    cfeats: np.ndarray | None = None   # causal features (now and previous frame), for closed loops

    @classmethod
    def from_recordings(cls, recs) -> "MotionLibrary":
        vel_all = np.concatenate([r.behaviour["velocity"] for r in recs])
        v_scale = float(np.std(vel_all))
        shapes, turn, feats, worm, frame, lengths, cfeats = [], [], [], [], [], [], []
        for wi, r in enumerate(recs):
            ang, length, good = _resample_posture(r.posture["segment_angle"])
            vel = r.behaviour["velocity"]
            rev = (r.behaviour["reversing"] > 0.5).astype(float)
            lengths.append(length)
            orient = np.angle(np.mean(np.exp(1j * ang), axis=1))      # whole-body orientation
            for i in range(len(vel) - LOOKAHEAD):
                if not (good[i] and good[i + 1]):
                    continue
                shapes.append(_wrap(ang[i] - orient[i]))
                turn.append(_wrap(orient[i + 1] - orient[i]))
                feats.append(_features(vel, rev, v_scale, i))
                cfeats.append(_causal_features(vel[i], vel[max(i - 1, 0)], rev[i], rev[max(i - 1, 0)], v_scale))
                worm.append(wi)
                frame.append(i)
        return cls(np.array(shapes), np.array(turn), np.array(feats), np.array(worm), np.array(frame),
                   v_scale, float(np.median(lengths)), np.array(cfeats))

    def synthesize(self, velocity: np.ndarray, reversing: np.ndarray, t: np.ndarray,
                   jump_cost: float = 1.5, pose_weight: float = 2.0, heading0: float = 0.0,
                   seed: int = 0):
        """Returns absolute segment angles (T, K), head path (T, 2) in mm, and the share of
        frames that continued the previous clip."""
        rng = np.random.default_rng(seed)
        tree = cKDTree(self.feats)
        pos_of = {(w, f): i for i, (w, f) in enumerate(zip(self.worm, self.frame))}
        T = len(velocity)
        rev = (reversing > 0.5).astype(float)
        angles = np.empty((T, self.shapes.shape[1]))
        path = np.zeros((T, 2))
        H = heading0
        cur = None
        continued = 0
        for i in range(T):
            f = _features(velocity, rev, self.v_scale, i)
            d, cand = tree.query(f, k=32)
            nxt = None if cur is None else pos_of.get((int(self.worm[cur]), int(self.frame[cur]) + 1))
            if cur is None:
                pose = np.zeros(len(cand))
            else:                                            # pose continuity: shape close to the current one
                pose = np.mean(_wrap(self.shapes[cand] - self.shapes[cur]) ** 2, axis=1)
            cost = d ** 2 + pose_weight * pose + 0.02 * rng.random(len(cand))
            j = int(np.argmin(cost))
            if nxt is not None:
                c_next = float(np.sum((self.feats[nxt] - f) ** 2)) \
                    + pose_weight * float(np.mean(_wrap(self.shapes[nxt] - self.shapes[cur]) ** 2))
                if c_next <= cost[j] + jump_cost:
                    j = None
            if j is None:
                best = nxt                                   # keep playing the current real clip
                continued += 1
            else:
                best = int(cand[j])
            jumped = cur is not None and best != nxt
            prev_shape = None if cur is None else self.shapes[cur]
            cur = best
            shape = self.shapes[cur]
            if jumped:                                        # crossfade into the new clip
                shape = prev_shape + 0.5 * _wrap(shape - prev_shape)
            angles[i] = shape + H
            if i + 1 < T:
                dt = float(t[i + 1] - t[i])
                fwd = angles[i, 0] + np.pi                   # crawl along the head direction
                path[i + 1] = path[i] + velocity[i] * dt * np.array([np.cos(fwd), np.sin(fwd)])
                H = H + self.turn[cur]
        return angles, path, continued / max(T - 1, 1)


class MotionStepper:
    """Motion matching one frame at a time, for closed loops where the future is unknown:
    matches on current and previous velocity and reversal state, with the same pose
    continuity and clip-continuation rules as MotionLibrary.synthesize."""

    def __init__(self, lib: MotionLibrary, jump_cost: float = 1.5, pose_weight: float = 2.0, seed: int = 0):
        self.lib, self.jump_cost, self.pose_weight = lib, jump_cost, pose_weight
        self.tree = cKDTree(lib.cfeats)
        self.pos_of = {(w, f): i for i, (w, f) in enumerate(zip(lib.worm, lib.frame))}
        self.rng = np.random.default_rng(seed)
        self.cur = None
        self.continued = 0
        self.steps = 0

    def step(self, v, v_prev, rev, rev_prev):
        lib = self.lib
        f = _causal_features(v, v_prev, float(rev), float(rev_prev), lib.v_scale)
        d, cand = self.tree.query(f, k=32)
        cur = self.cur
        nxt = None if cur is None else self.pos_of.get((int(lib.worm[cur]), int(lib.frame[cur]) + 1))
        pose = np.zeros(len(cand)) if cur is None else np.mean(_wrap(lib.shapes[cand] - lib.shapes[cur]) ** 2, axis=1)
        cost = d ** 2 + self.pose_weight * pose + 0.02 * self.rng.random(len(cand))
        j = int(np.argmin(cost))
        best = int(cand[j])
        if nxt is not None:
            c_next = float(np.sum((lib.cfeats[nxt] - f) ** 2)) \
                + self.pose_weight * float(np.mean(_wrap(lib.shapes[nxt] - lib.shapes[cur]) ** 2))
            if c_next <= cost[j] + self.jump_cost:
                best = nxt
                self.continued += 1
        shape = lib.shapes[best]
        if cur is not None and best != nxt:
            shape = lib.shapes[cur] + 0.5 * _wrap(shape - lib.shapes[cur])
        self.cur = best
        self.steps += 1
        return shape, float(lib.turn[best])


def class_levels(sample_x: np.ndarray, classes, neurons, a: int, n: int) -> list:
    """Display levels for each neuron from its class trace (both brains are shown this way)."""
    idx = {c: i for i, c in enumerate(classes)}
    cache = {}
    out = []
    for nr in neurons:
        ci = idx[nr["cls"]]
        if ci not in cache:
            cache[ci] = _display_level(sample_x[ci, a:a + n])
        out.append(cache[ci])
    return out


def write_bundle(path: Path, uid: str, source: str, t: np.ndarray, angles: np.ndarray, length_mm: float,
                 head_path: np.ndarray, velocity: np.ndarray, reversing: np.ndarray, neurons: list,
                 levels: list, notes: dict) -> int:
    bundle = {
        "format": "nematica-replay/1",
        "uid": uid,
        "dataset": "copper2026",
        "split": "test",
        "source": source,
        "n_frames": int(len(t)),
        "t": np.round(t - t[0], 3).tolist(),
        "body": {"k": int(angles.shape[1]), "length_mm": round(float(length_mm), 4),
                 "angles": np.round(angles, 4).ravel().tolist(), "tracked": [1] * len(t)},
        "path_mm": np.round(head_path, 4).ravel().tolist(),
        "arena": None,
        "behaviour": {"velocity": np.round(velocity, 4).tolist(),
                      "reversing": (reversing > 0.5).astype(int).tolist()},
        "neurons": [{**nr, "level": np.round(lv, 3).tolist()} for nr, lv in zip(neurons, levels)],
        "notes": notes,
    }
    path.write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    return path.stat().st_size


__all__ = ["MotionLibrary", "class_levels", "write_bundle", "K_POINTS"]
