"""Worm-level train / validation / test splits, frozen to a YAML file.

Rules:
  * splits are by animal, never by time within an animal;
  * the test set is stratified by condition (e.g. heat vs baseline) and by
    recording date, so test worms are not all from one session or rig day;
  * once written, a split is loaded, never regenerated, and its hash is checked.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import yaml


def _date_key(uid: str) -> str:
    # Flavell uids look like 2023-01-10-14: date then a session number.
    parts = uid.split("-")
    return "-".join(parts[:3]) if len(parts) >= 3 else uid


def make_worm_split(uids: Sequence[str], conditions: Sequence[str], n_test: int,
                    n_val: int, seed: int = 0) -> dict:
    """Pick test and validation worms, balanced across conditions and spread over dates."""
    uids = list(uids)
    if len(set(uids)) != len(uids):
        raise ValueError("duplicate uids")
    if n_test + n_val >= len(uids):
        raise ValueError("not enough worms for the requested split")
    rng = np.random.default_rng(seed)

    by_cond: dict[str, list[str]] = {}
    for u, c in zip(uids, conditions):
        by_cond.setdefault(c, []).append(u)

    def pick(pool: dict[str, list[str]], n: int) -> list[str]:
        chosen: list[str] = []
        total = sum(len(v) for v in pool.values())
        # proportional allocation per condition, at least one where possible
        quota = {c: max(1, round(n * len(v) / total)) if v else 0 for c, v in pool.items()}
        while sum(quota.values()) > n:
            biggest = max(quota, key=lambda c: quota[c])
            quota[biggest] -= 1
        while sum(quota.values()) < n:
            room = [c for c in pool if quota[c] < len(pool[c])]
            quota[max(room, key=lambda c: len(pool[c]) - quota[c])] += 1
        for c, members in pool.items():
            # prefer worms from dates not yet represented, then random
            order = [str(u) for u in rng.permutation(members)]
            seen_dates = {_date_key(u) for u in chosen}
            order.sort(key=lambda u: _date_key(u) in seen_dates)
            chosen.extend(order[: quota[c]])
        return chosen

    test = pick(by_cond, n_test)
    remaining = {c: [u for u in v if u not in test] for c, v in by_cond.items()}
    val = pick(remaining, n_val)
    train = [u for u in uids if u not in test and u not in val]
    return {"seed": seed, "train": sorted(train), "val": sorted(val), "test": sorted(test)}


def split_hash(split: dict) -> str:
    payload = json.dumps({k: split[k] for k in ("train", "val", "test")}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def save_split(split: dict, path: str | Path, dataset: str) -> None:
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} exists; splits are frozen and never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"dataset": dataset, "hash": split_hash(split), **split}
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(doc, fh, sort_keys=False)


def load_split(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if split_hash(doc) != doc["hash"]:
        raise ValueError(f"{path}: split hash mismatch; the frozen split was edited")
    overlap = (set(doc["train"]) & set(doc["test"])) | (set(doc["val"]) & set(doc["test"])) \
        | (set(doc["train"]) & set(doc["val"]))
    if overlap:
        raise ValueError(f"{path}: worms in more than one split: {sorted(overlap)}")
    return doc
