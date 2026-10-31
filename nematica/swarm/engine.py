"""Many closed-loop worms in one arena (arc 6).

Each worm is a `BrainAgent` (nematica.systems.closed_loop): its own brain, body and copper
sense. The engine steps them together, one frame at a time:

    1. touch     each head is checked against every other worm's body from the previous
                 frame (contact distance `contact_mm`)
    2. think     every worm runs its brain and picks its posture and speed (touch may start
                 a reversal [A])
    3. exclude   a proposed head move that ends within `contact_mm` of another worm's body,
                 and closer than before, is refused: the head holds still [A]
    4. move      every worm commits its move

With `interact=False` worms pass through each other: touch and exclusion are off, but
contact, density and clusters are still measured (the chance-encounter baseline).
All interaction rules are stated assumptions [A] until calibrated against real multi-worm
tracking.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..systems.closed_loop import BrainAgent, SensoryVAR

CONTACT_MM = 0.1        # about two body widths [A]
P_TOUCH = 0.3           # chance per touched forward frame of starting a reversal [A]
DENSITY_MM = 1.0        # local density: other heads within one body length


@dataclass
class SwarmRun:
    heads: np.ndarray        # (N, T, 2) head positions, arena centre at the origin
    states: np.ndarray       # (N, T) 1 while reversing
    touched: np.ndarray      # (N, T) head within contact distance of another body
    blocked: np.ndarray      # (N, T) move refused by exclusion
    density: np.ndarray      # (N, T) other heads within DENSITY_MM
    links: list              # per frame, (j, k) pairs whose bodies are in contact
    dist: np.ndarray         # (N, T) head distance to copper (negative beyond it)
    origins: list            # which model each worm runs
    dt: float
    radius_mm: float


def average_worm(m: SensoryVAR, name: str = "__average__") -> str:
    """Adds the pooled model as one more 'worm' of `m`: pooled dynamics (W_pool), the mean
    residual covariance, the median reversal offsets and the pooled speeds. Returns its name."""
    if name not in m.W:
        covs = [L @ L.T for L in m.L.values()]
        m.W[name] = m.W_pool
        m.L[name] = np.linalg.cholesky(np.mean(covs, axis=0))
        if m.offsets:
            offs = np.array(list(m.offsets.values()))
            m.offsets[name] = (float(np.median(offs[:, 0])), float(np.median(offs[:, 1])))
    return name


def start_positions(n: int, radius_mm: float, rng: np.random.Generator, margin_mm: float = 1.0,
                    min_gap_mm: float = 0.5) -> np.ndarray:
    """Uniform head positions in the disc of radius R - margin, at least min_gap apart."""
    pts = []
    r_max = radius_mm - margin_mm
    tries = 0
    while len(pts) < n:
        tries += 1
        p = r_max * np.sqrt(rng.random()) * np.array([np.cos(a := rng.uniform(0, 2 * np.pi)), np.sin(a)])
        if tries > 10000 or all(np.hypot(*(p - q)) >= min_gap_mm for q in pts):
            pts.append(p)
    return np.array(pts)


def _min_dist_to_others(points: np.ndarray, bodies: np.ndarray, owner: np.ndarray, n: int) -> np.ndarray:
    """points (N, 2), bodies (N * P, 2) with owner (N * P,): for each worm j, the smallest
    distance from points[j] to any body point of another worm."""
    d = np.hypot(points[:, None, 0] - bodies[None, :, 0], points[:, None, 1] - bodies[None, :, 1])
    d[owner[None, :] == np.arange(n)[:, None]] = np.inf
    return d.min(axis=1)


def _body_links(bodies: np.ndarray, n: int, contact_mm: float) -> list:
    """(j, k) pairs whose bodies come within contact distance anywhere."""
    P = bodies.shape[0] // n
    B = bodies.reshape(n, P, 2)
    lo, hi = B.min(axis=1) - contact_mm, B.max(axis=1) + contact_mm
    out = []
    for j in range(n):
        for k in range(j + 1, n):
            if np.any(hi[j] < lo[k]) or np.any(hi[k] < lo[j]):
                continue                                   # bounding boxes apart
            d = np.hypot(B[j][:, None, 0] - B[k][None, :, 0], B[j][:, None, 1] - B[k][None, :, 1])
            if d.min() < contact_mm:
                out.append((j, k))
    return out


def run_swarm(m: SensoryVAR, origins: list, template, library, radius_mm: float, t: np.ndarray,
              rng: np.random.Generator, interact: bool = True, contact_mm: float = CONTACT_MM,
              p_touch: float = P_TOUCH, burn: int = 300, n_frames: int | None = None) -> SwarmRun:
    n = len(origins)
    T = template.x.shape[1] if n_frames is None else n_frames
    starts = start_positions(n, radius_mm, rng)
    agents: list[BrainAgent] = []
    for j, origin in enumerate(origins):
        a = m.agent(template, radius_mm, float(np.hypot(*starts[j])), library,
                    np.random.default_rng(int(rng.integers(1 << 31))), 0, burn=burn, origin=origin)
        a.head = starts[j].copy()                     # place it where the swarm put it
        a.d_prev = a.d_now = radius_mm - float(np.hypot(*a.head))
        a.p_touch = p_touch if interact else 0.0
        agents.append(a)
    touched = np.zeros((n, T), bool)
    blocked = np.zeros((n, T), bool)
    density = np.zeros((n, T), int)
    links = []
    prev_bodies = None
    owner = None
    for i in range(T):
        heads = np.array([a.head for a in agents])
        if prev_bodies is not None:
            touch = _min_dist_to_others(heads, prev_bodies, owner, n) < contact_mm
        else:
            touch = np.zeros(n, bool)
        dh = np.hypot(heads[:, None, 0] - heads[None, :, 0], heads[:, None, 1] - heads[None, :, 1])
        density[:, i] = (dh < DENSITY_MM).sum(axis=1) - 1
        for j, a in enumerate(agents):
            a.think(bool(touch[j]) and interact)
        touched[:, i] = touch
        bodies = np.vstack([a.body() for a in agents])
        if owner is None:
            owner = np.repeat(np.arange(n), bodies.shape[0] // n)
        links.append(_body_links(bodies, n, contact_mm))
        dt = float(t[i + 1] - t[i]) if i + 1 < len(t) and i + 1 < T else None
        if dt is not None and interact:
            prop = np.array([a.proposed_head(dt) for a in agents])
            now = _min_dist_to_others(heads, bodies, owner, n)
            nxt = _min_dist_to_others(prop, bodies, owner, n)
            blocked[:, i] = (nxt < contact_mm) & (nxt < now)
        for j, a in enumerate(agents):
            a.move(dt, blocked=bool(blocked[j, i]))
        prev_bodies = bodies
    return SwarmRun(
        heads=np.stack([a.path[:T] for a in agents]),
        states=np.stack([a.states[:T] for a in agents]),
        touched=touched, blocked=blocked, density=density, links=links,
        dist=np.stack([a.dist[:T] for a in agents]),
        origins=list(origins), dt=float(np.median(np.diff(t))), radius_mm=radius_mm)
