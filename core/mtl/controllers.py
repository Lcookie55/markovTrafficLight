"""Controllers. They only *request* an action; the SafetyLayer decides what happens."""
from __future__ import annotations

import time
from typing import Protocol

import numpy as np

from .config import Config
from .env import Obs
from .state import KEEP, SWITCH


class Controller(Protocol):
    name: str

    def reset(self) -> None: ...
    def act(self, obs: Obs) -> int: ...


class MDPController:
    """Looks up pi*(encode(obs)) in the solved policy table (report Section 5.4)."""

    def __init__(self, policy: np.ndarray, name: str = "mdp"):
        self.policy = np.asarray(policy, dtype=int)
        self.name = name
        self.last_latency_ms = 0.0

    def reset(self) -> None:
        pass

    def act(self, obs: Obs) -> int:
        t0 = time.perf_counter()
        a = int(self.policy[obs.state_idx])
        self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
        return a


class FixedTimeController:
    """30 s / 30 s pre-timed plan (report Section 5.2)."""

    def __init__(self, cfg: Config, name: str = "fixed"):
        self.cfg = cfg
        self.name = name

    def reset(self) -> None:
        pass

    def act(self, obs: Obs) -> int:
        return SWITCH if obs.k * self.cfg.dt >= self.cfg.fixed_green else KEEP


class LongestQueueFirstController:
    """Simple priority rule: go to the axis with the longer queue (with hysteresis)."""

    def __init__(self, cfg: Config, margin: int = 2, name: str = "lqf"):
        self.cfg = cfg
        self.margin = margin
        self.name = name

    def reset(self) -> None:
        pass

    def act(self, obs: Obs) -> int:
        served, other = (obs.q_ns, obs.q_ew) if obs.phase == 0 else (obs.q_ew, obs.q_ns)
        return SWITCH if other - served >= self.margin else KEEP
