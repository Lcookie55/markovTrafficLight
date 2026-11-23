"""Glue: environment + controller + safety layer + metrics, and the policy builder."""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .arrivals import ArrivalStream
from .config import Config, Scenario
from .controllers import (FixedTimeController, LongestQueueFirstController,
                          MDPController)
from .env import Intersection
from .metrics import Metrics
from .model import build_model
from .safety import SafetyLayer
from .solvers import value_iteration
from .state import ACTION_NAMES, from_index


@lru_cache(maxsize=256)
def _solve_cached(cfg: Config, lam_ns: float, lam_ew: float):
    model = build_model(cfg, lam_ns, lam_ew)
    return model, value_iteration(model)


def solve(cfg: Config, lam_ns: float, lam_ew: float):
    """Build the model for these per-approach arrival rates and solve it (cached)."""
    return _solve_cached(cfg, round(lam_ns, 6), round(lam_ew, 6))


def make_controller(kind: str, cfg: Config, scenario: Scenario):
    if kind == "fixed":
        return FixedTimeController(cfg)
    if kind == "lqf":
        return LongestQueueFirstController(cfg)
    if kind == "mdp":              # policy solved for the scenario's own mean arrival rates
        lam_ns, lam_ew = scenario.mean_rates(cfg.horizon)
        return MDPController(solve(cfg, lam_ns, lam_ew)[1].policy, "mdp")
    if kind == "mdp_nominal":      # one policy for a generic nominal demand
        lam = cfg.nominal_lambda
        return MDPController(solve(cfg, lam, lam)[1].policy, "mdp_nominal")
    raise ValueError(f"unknown controller '{kind}'")


CONTROLLER_KINDS = ("mdp", "mdp_nominal", "fixed", "lqf")


class Session:
    """One controller driving one intersection, step by step."""

    def __init__(self, cfg: Config, scenario: Scenario, seed: int, controller,
                 stream: ArrivalStream | None = None, rate_fn=None):
        self.cfg = cfg
        self.scenario = scenario
        self.controller = controller
        self.rate_fn = rate_fn or scenario.rates
        self.stream = stream or ArrivalStream(seed, cfg.horizon)
        self.env = Intersection(cfg, self.stream, self.rate_fn)
        self.safety = SafetyLayer(cfg)
        self.metrics = Metrics()
        self.controller.reset()

    @property
    def done(self) -> bool:
        return self.env.t + self.cfg.dt > self.cfg.horizon

    def step(self) -> dict:
        obs = self.env.observe()
        requested = self.controller.act(obs)
        decision = self.safety.apply(requested, obs.k)
        result = self.env.step(bool(decision.applied))
        self.metrics.on_step(result, decision)
        return {"obs": obs, "decision": decision, "result": result}

    def summary(self) -> dict:
        return self.metrics.summary(self.env)


def run_episode(cfg: Config, scenario: Scenario, seed: int, controller,
                stream: ArrivalStream | None = None, record: bool = False):
    sess = Session(cfg, scenario, seed, controller, stream)
    log = []
    while not sess.done:
        out = sess.step()
        if record:
            o, d, r = out["obs"], out["decision"], out["result"]
            l_ns, l_ew, p, e = from_index(o.state_idx)
            log.append({
                "t": o.t, "q_N": o.queues[0], "q_S": o.queues[1], "q_E": o.queues[2],
                "q_W": o.queues[3], "level_ns": l_ns, "level_ew": l_ew, "phase": p,
                "e": e, "k": o.k, "requested": ACTION_NAMES[d.requested],
                "applied": ACTION_NAMES[d.applied], "reason": d.reason,
                "reward": r["reward"],
            })
    return (sess.summary(), log) if record else sess.summary()
