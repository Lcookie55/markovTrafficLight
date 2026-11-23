"""Run S1-S5 x 5 seeds x controllers, the model-vs-sim check and the Q-learning check."""
import csv
import json
import time

import numpy as np

from mtl import experiments, validate
from mtl.config import OUTPUT_DIR, load_config
from mtl.runner import solve
from mtl.solvers.q_learning import policy_agreement, q_learning

if __name__ == "__main__":
    cfg, scenarios = load_config()
    t0 = time.time()
    rows = experiments.run_grid(cfg, scenarios)
    summary = experiments.summarize(rows)
    experiments.save(rows, summary)
    print(f"grid: {len(rows)} runs in {time.time() - t0:.1f}s")

    hdr = f"{'scn':4}{'controller':13}{'avg wait (s)':>16}{'mean queue':>14}{'throughput/h':>16}{'switches':>10}"
    print(hdr)
    for r in summary:
        print(f"{r['scenario']:4}{r['controller']:13}"
              f"{r['avg_wait_s_mean']:9.1f} ±{r['avg_wait_s_std']:5.1f}"
              f"{r['mean_queue_mean']:9.1f}±{r['mean_queue_std']:4.1f}"
              f"{r['throughput_vph_mean']:11.0f}±{r['throughput_vph_std']:4.0f}"
              f"{r['switches_mean']:9.0f}")

    # model vs simulator
    comp = []
    for sid, sc in scenarios.items():
        c = validate.compare(cfg, sc)
        comp.append({k: v for k, v in c.items() if k != "rows"})
        print(f"model-vs-sim {sid}: weighted TV = {c['weighted_tv']:.3f} "
              f"(queue+phase part {c['tv_queue_and_phase_only']:.3f}, "
              f"elapsed part {c['tv_elapsed_only']:.3f}; "
              f"{c['pairs_compared']} (s,a) pairs, {c['transitions']} transitions)")
    (OUTPUT_DIR / "model_vs_sim.json").write_text(json.dumps(comp, indent=1))

    # Q-learning vs value iteration
    lam = cfg.nominal_lambda
    vi = solve(cfg, lam, lam)[1]
    t0 = time.time()
    ql, visits = q_learning(cfg, lam, lam, episodes=600, episode_len=1800, seed=0)
    agr = policy_agreement(ql.policy, vi.policy, visits)
    agr["episodes"] = 600
    agr["seconds"] = round(time.time() - t0, 1)
    # performance of the learned vs the DP policy on the real simulator
    from mtl.controllers import MDPController
    from mtl.runner import run_episode
    perf = {}
    for sid in ("S2", "S3", "S5"):
        for name, pol in (("value_iteration", vi.policy), ("q_learning", ql.policy)):
            perf[f"{sid}_{name}_avg_wait_s"] = float(np.mean([
                run_episode(cfg, scenarios[sid], sd, MDPController(pol))["avg_wait_s"]
                for sd in cfg.seeds]))
    agr["avg_wait_by_policy"] = perf
    (OUTPUT_DIR / "qlearning_check.json").write_text(json.dumps(agr, indent=1))
    print("q-learning vs VI:", agr)
