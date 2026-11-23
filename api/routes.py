"""REST endpoints (thin layer over the `mtl` package)."""
from __future__ import annotations

import json
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mtl import experiments
from mtl.config import OUTPUT_DIR, load_config
from mtl.model import build_model
from mtl.solvers import policy_iteration, value_iteration
from mtl.state import ACTION_NAMES, N_STATES, from_index

CFG, SCENARIOS = load_config()
router = APIRouter(prefix="/api")


def scenario_json(sc) -> dict:
    return {"id": sc.id, "name": sc.name, "description": sc.description,
            "lam_ns": sc.lam_ns, "lam_ew": sc.lam_ew,
            "surge": list(sc.surge) if sc.surge else None}


def config_json(cfg=CFG) -> dict:
    return {"dt": cfg.dt, "g_min": cfg.g_min, "g_max": cfg.g_max,
            "t_yellow": cfg.t_yellow, "t_allred": cfg.t_allred, "mu": cfg.mu,
            "lanes": cfg.lanes, "gamma": cfg.gamma, "c_switch": cfg.c_switch,
            "q_max": cfg.q_max, "eps": cfg.eps, "horizon": cfg.horizon,
            "fixed_green": cfg.fixed_green, "nominal_lambda": cfg.nominal_lambda,
            "seeds": list(cfg.seeds)}


@router.get("/config")
def get_config():
    return {"config": config_json(),
            "scenarios": [scenario_json(s) for s in SCENARIOS.values()]}


class SolveRequest(BaseModel):
    scenario: Optional[str] = None
    lam_ns: Optional[float] = None
    lam_ew: Optional[float] = None
    gamma: Optional[float] = None
    c_switch: Optional[float] = None
    lanes: Optional[float] = None


def solve_payload(req: SolveRequest) -> dict:
    cfg = CFG
    kw = {k: v for k, v in (("gamma", req.gamma), ("c_switch", req.c_switch),
                            ("lanes", req.lanes)) if v is not None}
    if "gamma" in kw and not (0.0 <= kw["gamma"] < 1.0):
        raise HTTPException(422, "gamma must be in [0, 1)")
    if "lanes" in kw and kw["lanes"] <= 0:
        raise HTTPException(422, "lanes must be positive")
    cfg = cfg.with_(**kw)
    if req.lam_ns is not None and req.lam_ew is not None:
        lam_ns, lam_ew, label = req.lam_ns, req.lam_ew, "custom"
    elif req.scenario in SCENARIOS:
        lam_ns, lam_ew = SCENARIOS[req.scenario].mean_rates(cfg.horizon)
        label = req.scenario
    elif req.scenario in (None, "nominal"):
        lam_ns = lam_ew = cfg.nominal_lambda
        label = "nominal"
    else:
        raise HTTPException(404, f"unknown scenario {req.scenario}")
    if min(lam_ns, lam_ew) < 0 or max(lam_ns, lam_ew) > 1.0:
        raise HTTPException(422, "arrival rates must be within [0, 1] veh/s")

    model = build_model(cfg, lam_ns, lam_ew)
    vi = value_iteration(model)
    pi = policy_iteration(model)
    states = []
    for s in range(N_STATES):
        l_ns, l_ew, p, e = from_index(s)
        states.append({
            "idx": s, "q_ns": l_ns, "q_ew": l_ew, "phase": p, "e": e,
            "action": ACTION_NAMES[int(vi.policy[s])],
            "kind": {0: "vetoed", 1: "free", 2: "forced"}[e],
            "q_keep": float(vi.Q[s, 0]), "q_switch": float(vi.Q[s, 1]),
            "v": float(vi.V[s]),
        })
    return {"label": label, "lam_ns": lam_ns, "lam_ew": lam_ew,
            "params": config_json(cfg), "states": states,
            "iterations": vi.iterations, "history": [float(h) for h in vi.history],
            "pi_iterations": pi.iterations,
            "vi_equals_pi": bool(np.array_equal(vi.policy, pi.policy))}


@router.post("/solve")
def post_solve(req: SolveRequest):
    return solve_payload(req)


@router.get("/policy")
def get_policy(scenario: str = "nominal"):
    return solve_payload(SolveRequest(scenario=scenario))


def _read_json(name: str):
    p = OUTPUT_DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@router.get("/benchmark")
def get_benchmark():
    return {"summary": _read_json("summary.json") or [],
            "model_vs_sim": _read_json("model_vs_sim.json"),
            "qlearning": _read_json("qlearning_check.json")}


@router.post("/benchmark/run")
def run_benchmark():
    rows = experiments.run_grid(CFG, SCENARIOS)
    summary = experiments.summarize(rows)
    experiments.save(rows, summary)
    return {"summary": summary}
