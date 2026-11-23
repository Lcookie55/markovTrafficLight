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
    from mtl.controllers import MDPController
    from mtl.runner import run_episode
    lam = cfg.nominal_lambda
    vi = solve(cfg, lam, lam)[1]
    t0 = time.time()
    TRAIN_SEEDS = (0, 1, 2, 3, 4)          # independent Q-learning training runs
    unw, wtd, perf_runs = [], [], {}
    for ts in TRAIN_SEEDS:
        ql, visits = q_learning(cfg, lam, lam, episodes=600, episode_len=1800, seed=ts)
        a = policy_agreement(ql.policy, vi.policy, visits)
        unw.append(a["agree_unweighted"])
        wtd.append(a["agree_weighted"])
        for sid in ("S2", "S3", "S5"):
            perf_runs.setdefault(f"{sid}_q_learning", []).append(float(np.mean([
                run_episode(cfg, scenarios[sid], sd, MDPController(ql.policy))["avg_wait_s"]
                for sd in cfg.seeds])))
    agr = {"free_states": 32, "episodes": 600, "training_seeds": len(TRAIN_SEEDS),
           "agree_unweighted": float(np.mean(unw)), "agree_unweighted_std": float(np.std(unw)),
           "agree_weighted": float(np.mean(wtd)), "agree_weighted_std": float(np.std(wtd)),
           "seconds": round(time.time() - t0, 1)}
    # performance of the learned vs the DP policy on the real simulator (seeds 1-5)
    perf = {}
    for sid in ("S2", "S3", "S5"):
        perf[f"{sid}_value_iteration_avg_wait_s"] = float(np.mean([
            run_episode(cfg, scenarios[sid], sd, MDPController(vi.policy))["avg_wait_s"]
            for sd in cfg.seeds]))
        runs = perf_runs[f"{sid}_q_learning"]
        perf[f"{sid}_q_learning_avg_wait_s"] = float(np.mean(runs))
        perf[f"{sid}_q_learning_avg_wait_s_std"] = float(np.std(runs))
        perf[f"{sid}_q_learning_avg_wait_s_min"] = float(np.min(runs))
        perf[f"{sid}_q_learning_avg_wait_s_max"] = float(np.max(runs))
    agr["avg_wait_by_policy"] = perf
    (OUTPUT_DIR / "qlearning_check.json").write_text(json.dumps(agr, indent=1))
    print("q-learning vs VI:", agr)
