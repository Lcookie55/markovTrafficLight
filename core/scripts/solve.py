"""Solve the MDP for each scenario (and the nominal demand) and export the policy tables."""
import csv
import json

import numpy as np

from mtl.config import OUTPUT_DIR, load_config
from mtl.model import effective_action
from mtl.runner import solve
from mtl.solvers import policy_iteration
from mtl.state import ACTION_NAMES, N_STATES, from_index, state_label


def export(cfg, lam_ns, lam_ew, tag):
    model, sol = solve(cfg, lam_ns, lam_ew)
    pi = policy_iteration(model)
    same = bool(np.array_equal(pi.policy, sol.policy))
    path = OUTPUT_DIR / f"policy_{tag}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["state", "q_NS", "q_EW", "phase", "e", "action", "kind",
                    "Q_keep", "Q_switch", "V"])
        for s in range(N_STATES):
            l_ns, l_ew, p, e = from_index(s)
            kind = {0: "vetoed", 1: "free", 2: "forced"}[e]
            w.writerow([s, l_ns, l_ew, p, e, ACTION_NAMES[sol.policy[s]], kind,
                        round(sol.Q[s, 0], 4), round(sol.Q[s, 1], 4), round(sol.V[s], 4)])
    print(f"{tag}: lam=({lam_ns:.3f},{lam_ew:.3f}) VI iters={sol.iterations} "
          f"PI iters={pi.iterations} VI==PI: {same} -> {path.name}")
    return sol


if __name__ == "__main__":
    cfg, scenarios = load_config()
    OUTPUT_DIR.mkdir(exist_ok=True)
    for sid, sc in scenarios.items():
        export(cfg, *sc.mean_rates(cfg.horizon), sid)
    export(cfg, cfg.nominal_lambda, cfg.nominal_lambda, "nominal")
    sol = solve(cfg, cfg.nominal_lambda, cfg.nominal_lambda)[1]
    (OUTPUT_DIR / "convergence.json").write_text(json.dumps(sol.history))
