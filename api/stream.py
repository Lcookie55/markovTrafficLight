"""WebSocket live simulation: several controllers on one shared arrival stream."""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mtl.arrivals import ArrivalStream
from mtl.controllers import MDPController
from mtl.runner import CONTROLLER_KINDS, Session, make_controller, solve
from mtl.state import ACTION_NAMES, from_index

from .routes import CFG, SCENARIOS, config_json, scenario_json

router = APIRouter()


class Rates:
    """Arrival rates shared by all sessions; can be overridden live from the UI."""

    def __init__(self, scenario):
        self.scenario = scenario
        self.override = None

    def __call__(self, t: int):
        return self.override if self.override else self.scenario.rates(t)


def frame_of(sessions: dict, outs: dict, rates: Rates, t: int) -> dict:
    ctrls = {}
    for name, out in outs.items():
        o, d, r = out["obs"], out["decision"], out["result"]
        l_ns, l_ew, p, e = from_index(o.state_idx)
        sess = sessions[name]
        ctrls[name] = {
            "state": [l_ns, l_ew, p, e], "state_idx": o.state_idx, "k": o.k,
            "requested": ACTION_NAMES[d.requested], "applied": ACTION_NAMES[d.applied],
            "reason": d.reason, "reward": r["reward"],
            "ticks": [{"sig": "".join(tk["sig"]), "q": tk["q"], "dep": tk["dep"],
                       "arr": tk["arr"]} for tk in r["ticks"]],
            "metrics": sess.summary(),
        }
    return {"type": "frame", "t": t, "lam": list(rates(t)), "controllers": ctrls}


@router.websocket("/ws/sim")
async def ws_sim(ws: WebSocket):
    await ws.accept()
    try:
        start = await ws.receive_json()
        if start.get("type") != "start":
            await ws.close(code=1003)
            return
        sid = start.get("scenario", "S3")
        seed = int(start.get("seed", 1))
        kinds = [k for k in start.get("controllers", ["mdp", "fixed"]) if k in CONTROLLER_KINDS]
        if not kinds:
            await ws.send_json({"type": "error", "message": "no valid controllers"})
            return
        scenario = SCENARIOS.get(sid)
        if start.get("lam_ns") is not None and start.get("lam_ew") is not None:
            base = SCENARIOS.get("S1")
            scenario = base.custom(float(start["lam_ns"]), float(start["lam_ew"]))
        if scenario is None:
            await ws.send_json({"type": "error", "message": f"unknown scenario {sid}"})
            return

        cfg = CFG
        rates = Rates(scenario)
        stream = ArrivalStream(seed, cfg.horizon)           # shared by all controllers
        sessions = {k: Session(cfg, scenario, seed, make_controller(k, cfg, scenario),
                               stream=stream, rate_fn=rates) for k in kinds}
        state = {"paused": False, "speed": float(start.get("speed", 5)), "steps": 0,
                 "closed": False}
        await ws.send_json({"type": "init", "config": config_json(cfg),
                            "scenario": scenario_json(scenario), "controllers": kinds,
                            "seed": seed})

        async def reader():
            try:
                while True:
                    m = await ws.receive_json()
                    typ = m.get("type")
                    if typ == "pause":
                        state["paused"] = True
                    elif typ == "resume":
                        state["paused"] = False
                    elif typ == "speed":
                        state["speed"] = max(0.25, min(500.0, float(m.get("value", 5))))
                    elif typ == "step":
                        state["steps"] += 1
                    elif typ == "set_lambda":
                        lam_ns = max(0.0, min(1.0, float(m["lam_ns"])))
                        lam_ew = max(0.0, min(1.0, float(m["lam_ew"])))
                        rates.override = (lam_ns, lam_ew)
                        sol = solve(cfg, lam_ns, lam_ew)[1]   # re-solve (96 states: instant)
                        for k, sess in sessions.items():
                            if k == "mdp" and isinstance(sess.controller, MDPController):
                                sess.controller.policy = sol.policy
                    elif typ == "stop":
                        state["closed"] = True
                        return
            except WebSocketDisconnect:
                state["closed"] = True
            except Exception:
                state["closed"] = True

        task = asyncio.create_task(reader())
        loop = asyncio.get_running_loop()
        try:
            first = next(iter(sessions.values()))
            while not state["closed"] and not first.done:
                if state["paused"] and state["steps"] <= 0:
                    await asyncio.sleep(0.05)
                    continue
                if state["paused"]:
                    state["steps"] -= 1
                t0 = loop.time()
                outs = {k: s.step() for k, s in sessions.items()}
                t_end = first.env.t
                await ws.send_json(frame_of(sessions, outs, rates, t_end))
                wait = cfg.dt / state["speed"] - (loop.time() - t0)
                if wait > 0 and not state["paused"]:
                    await asyncio.sleep(wait)
            if not state["closed"]:
                await ws.send_json({"type": "done",
                                    "summary": {k: s.summary() for k, s in sessions.items()}})
        finally:
            task.cancel()
    except WebSocketDisconnect:
        return
