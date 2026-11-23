"""State encoding for the 96-state MDP (report Section 4.2).

S_t = (q_NS, q_EW, p, e)
  q_*  queue level 0..3  (0 | 1-3 | 4-7 | 8+)
  p    current green phase: 0 = North-South, 1 = East-West
  e    elapsed-time bucket: 0 (< G_min), 1 (G_min <= t < G_max), 2 (>= G_max)
"""
from __future__ import annotations

from .config import Config

N_LEVELS = 4
N_STATES = N_LEVELS * N_LEVELS * 2 * 3  # 96
KEEP, SWITCH = 0, 1
ACTION_NAMES = ("KEEP", "SWITCH")

# exact queue counts that belong to each level (counts are capped at q_max = 12)
LEVEL_RANGES = (range(0, 1), range(1, 4), range(4, 8), range(8, 13))


def level_of(q: int) -> int:
    if q <= 0:
        return 0
    if q <= 3:
        return 1
    if q <= 7:
        return 2
    return 3


def elapsed_bucket(k: int, cfg: Config) -> int:
    """k = elapsed decision steps in the current green."""
    t = k * cfg.dt
    if t < cfg.g_min:
        return 0
    if t < cfg.g_max:
        return 1
    return 2


def elapsed_members(e: int, cfg: Config) -> list:
    """Step counters k that fall in bucket e (for the uniform-within-bucket model)."""
    if e == 0:
        return list(range(0, cfg.kmin))
    if e == 1:
        return list(range(cfg.kmin, cfg.kmax))
    return [cfg.kmax]


def to_index(l_ns: int, l_ew: int, p: int, e: int) -> int:
    return ((l_ns * N_LEVELS + l_ew) * 2 + p) * 3 + e


def from_index(idx: int) -> tuple:
    e = idx % 3
    idx //= 3
    p = idx % 2
    idx //= 2
    l_ew = idx % N_LEVELS
    l_ns = idx // N_LEVELS
    return (l_ns, l_ew, p, e)


def encode(q_ns: int, q_ew: int, p: int, k: int, cfg: Config) -> int:
    """Raw observation -> state index (shared by solver and controller)."""
    return to_index(level_of(min(q_ns, cfg.q_max)), level_of(min(q_ew, cfg.q_max)),
                    p, elapsed_bucket(k, cfg))


def state_label(idx: int) -> str:
    l_ns, l_ew, p, e = from_index(idx)
    return f"(q_NS={l_ns}, q_EW={l_ew}, {'NS' if p == 0 else 'EW'} green, e={e})"
