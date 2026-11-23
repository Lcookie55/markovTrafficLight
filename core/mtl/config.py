"""Configuration: global parameters and the S1-S5 scenarios (report Table 5.2)."""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs" / "scenarios.json"
OUTPUT_DIR = REPO_ROOT / "outputs"


@dataclass(frozen=True)
class Config:
    dt: int = 5                  # decision step (s); simulator tick is 1 s
    g_min: int = 10              # minimum green (s)
    g_max: int = 60              # maximum green (s)
    t_yellow: int = 3
    t_allred: int = 1
    mu: float = 0.5              # saturation flow, veh/s/lane
    lanes: float = 1.4           # effective lanes per approach (calibrated)
    gamma: float = 0.95
    c_switch: float = 2.0
    q_max: int = 12              # cap of the queue per axis in the MDP model
    eps: float = 1e-4
    horizon: int = 3600
    fixed_green: int = 30
    nominal_lambda: float = 0.2
    seeds: tuple = (1, 2, 3, 4, 5)

    # ---- derived quantities -------------------------------------------------
    @property
    def clearance(self) -> int:
        return self.t_yellow + self.t_allred

    @property
    def kmin(self) -> int:       # elapsed steps at which a switch becomes legal
        return self.g_min // self.dt

    @property
    def kmax(self) -> int:       # elapsed steps at which a switch is forced
        return self.g_max // self.dt

    @property
    def cap_keep(self) -> int:
        """Vehicles an axis (2 approaches) can discharge during a full green step."""
        return int(round(2 * self.mu * self.lanes * self.dt))

    @property
    def cap_switch(self) -> int:
        """Vehicles the *new* axis can discharge in the green part of a SWITCH step."""
        return int(round(2 * self.mu * self.lanes * (self.dt - self.clearance)))

    def with_(self, **kw) -> "Config":
        return replace(self, **kw)


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    lam_ns: float                # per-approach arrival rate, veh/s
    lam_ew: float
    surge: Optional[tuple] = None  # (start_s, end_s, lam) applied to both axes

    def rates(self, t: float) -> tuple:
        if self.surge and self.surge[0] <= t < self.surge[1]:
            return (self.surge[2], self.surge[2])
        return (self.lam_ns, self.lam_ew)

    def mean_rates(self, horizon: int) -> tuple:
        """Time-averaged per-approach rates (used to build the MDP model)."""
        if not self.surge:
            return (self.lam_ns, self.lam_ew)
        s, e, lam = self.surge
        e = min(e, horizon)
        frac = max(0.0, e - s) / horizon
        return (self.lam_ns * (1 - frac) + lam * frac,
                self.lam_ew * (1 - frac) + lam * frac)

    def custom(self, lam_ns: float, lam_ew: float) -> "Scenario":
        return Scenario("custom", "Custom", "User-defined arrival rates",
                        lam_ns, lam_ew, None)


def load_config(path: Optional[Path] = None):
    """Return (Config, {id: Scenario})."""
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    raw = json.loads(path.read_text(encoding="utf-8"))
    d = dict(raw.get("defaults", {}))
    if "seeds" in d:
        d["seeds"] = tuple(d["seeds"])
    cfg = Config(**d)
    scenarios = {}
    for s in raw["scenarios"]:
        surge = s.get("surge")
        surge_t = (surge["start"], surge["end"], surge["lam"]) if surge else None
        scenarios[s["id"]] = Scenario(s["id"], s["name"], s["description"],
                                      s["lam_ns"], s["lam_ew"], surge_t)
    return cfg, scenarios
