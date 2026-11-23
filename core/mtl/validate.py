"""Model-vs-simulator validation (report Section 4.4 cross-check).

Runs the MDP controller in the simulator, records observed (s, a, s') bucket
transitions and compares them with the analytic P(s'|s,a).
"""
from __future__ import annotations

import numpy as np

from .arrivals import ArrivalStream
from .config import Config, Scenario
from .runner import Session, make_controller, solve
from .state import N_STATES, from_index


def transition_counts(cfg: Config, scenario: Scenario, controller_kind: str = "mdp",
                      seeds=(1, 2, 3, 4, 5)) -> np.ndarray:
    counts = np.zeros((2, N_STATES, N_STATES))
    for seed in seeds:
        ctrl = make_controller(controller_kind, cfg, scenario)
        sess = Session(cfg, scenario, seed, ctrl)
        while not sess.done:
            out = sess.step()
            s = out["obs"].state_idx
            a = out["decision"].applied
            s2 = sess.env.observe().state_idx
            counts[a, s, s2] += 1
    return counts


def compare(cfg: Config, scenario: Scenario, min_visits: int = 20, **kw) -> dict:
    lam_ns, lam_ew = scenario.mean_rates(cfg.horizon)
    model, _ = solve(cfg, lam_ns, lam_ew)
    counts = transition_counts(cfg, scenario, **kw)
    rows, tv_w, w_sum = [], 0.0, 0.0
    tv_q_w = tv_e_w = 0.0

    def marg(vec, keep):
        """Marginalise a successor distribution onto a subset of state components."""
        out = {}
        for s2, pr in enumerate(vec):
            if pr > 0:
                comp = from_index(s2)
                key = tuple(comp[i] for i in keep)
                out[key] = out.get(key, 0.0) + pr
        return out

    def tv_of(d1, d2):
        keys = set(d1) | set(d2)
        return 0.5 * sum(abs(d1.get(k, 0.0) - d2.get(k, 0.0)) for k in keys)

    for a in (0, 1):
        for s in range(N_STATES):
            n = counts[a, s].sum()
            if n < min_visits:
                continue
            emp = counts[a, s] / n
            tv = 0.5 * float(np.abs(emp - model.P[a, s]).sum())
            tv_w += tv * n
            w_sum += n
            # diagnostics: which state components carry the mismatch?
            tv_q_w += n * tv_of(marg(emp, (0, 1, 2)), marg(model.P[a, s], (0, 1, 2)))
            tv_e_w += n * tv_of(marg(emp, (3,)), marg(model.P[a, s], (3,)))
            rows.append({"scenario": scenario.id, "state": s, "action": a,
                         "visits": int(n), "tv_distance": tv,
                         "state_tuple": from_index(s)})
    return {"scenario": scenario.id,
            "weighted_tv": tv_w / w_sum if w_sum else float("nan"),
            "tv_queue_and_phase_only": tv_q_w / w_sum if w_sum else float("nan"),
            "tv_elapsed_only": tv_e_w / w_sum if w_sum else float("nan"),
            "pairs_compared": len(rows), "transitions": int(w_sum), "rows": rows}
