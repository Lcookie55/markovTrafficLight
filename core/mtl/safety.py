"""Safety & signal actuation layer (report Sections 3.2 Layer 3 and 5.4).

The layer validates every action coming from a controller:
  * SWITCH requested before G_min        -> vetoed, treated as KEEP
  * KEEP requested once G_max is reached -> forced SWITCH
Yellow / all-red clearance is inserted by the environment whenever the applied
action is SWITCH, so this layer is the only path by which signals can change.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .state import KEEP, SWITCH


@dataclass(frozen=True)
class SafetyDecision:
    requested: int
    applied: int
    reason: str  # "ok" | "vetoed" | "forced"


class SafetyLayer:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def apply(self, requested: int, k: int) -> SafetyDecision:
        elapsed = k * self.cfg.dt
        if elapsed >= self.cfg.g_max and requested == KEEP:
            return SafetyDecision(requested, SWITCH, "forced")
        if elapsed < self.cfg.g_min and requested == SWITCH:
            return SafetyDecision(requested, KEEP, "vetoed")
        return SafetyDecision(requested, requested, "ok")
