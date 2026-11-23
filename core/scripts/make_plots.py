"""Result figures + a statistics digest for the Results chapter (outputs/figures, outputs/digest.json)."""
import csv
import json
import statistics as st
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from mtl.arrivals import ArrivalStream  # noqa: E402
from mtl.config import OUTPUT_DIR, load_config  # noqa: E402
from mtl.runner import Session, make_controller, solve  # noqa: E402
from mtl.state import from_index, to_index  # noqa: E402

FIG = OUTPUT_DIR / "figures"
FIG.mkdir(parents=True, exist_ok=True)
COLOR = {"mdp": "#2f6fed", "mdp_nominal": "#13a8a8", "fixed": "#e07b00", "lqf": "#9b51e0"}
LABEL = {"mdp": "MDP (scenario λ)", "mdp_nominal": "MDP (nominal λ)",
         "fixed": "Fixed-time 30/30", "lqf": "Longest-queue-first"}
ORDER = ["fixed", "lqf", "mdp_nominal", "mdp"]
plt.rcParams.update({"font.family": "serif", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25,
                     "figure.dpi": 100, "savefig.dpi": 200, "savefig.bbox": "tight"})

cfg, scenarios = load_config()
rows = list(csv.DictReader(open(OUTPUT_DIR / "results.csv", encoding="utf-8")))
for r in rows:
    for k, v in r.items():
        if k not in ("scenario", "controller"):
            r[k] = float(v)
sids = list(scenarios)


def vals(sid, c, m):
    return [r[m] for r in rows if r["scenario"] == sid and r["controller"] == c]


def mean(sid, c, m):
    return st.fmean(vals(sid, c, m))


def sd(sid, c, m):
    return st.pstdev(vals(sid, c, m))


# ------------------------------------------------------------------ bar charts
def grouped(ax, metric, ylabel, ctrls=ORDER):
    w = 0.8 / len(ctrls)
    x = np.arange(len(sids))
    for i, c in enumerate(ctrls):
        ax.bar(x + (i - (len(ctrls) - 1) / 2) * w, [mean(s, c, metric) for s in sids], w,
               yerr=[sd(s, c, metric) for s in sids], color=COLOR[c], label=LABEL[c],
               capsize=2, error_kw={"lw": .8})
    ax.set_xticks(x, sids)
    ax.set_ylabel(ylabel)
    ax.grid(axis="x", visible=False)


fig, ax = plt.subplots(figsize=(7, 3.4))
grouped(ax, "avg_wait_s", "Average waiting time (s)")
ax.legend(ncol=2, frameon=False, fontsize=9)
fig.savefig(FIG / "fig_wait_by_scenario.png")
plt.close(fig)

fig, axs = plt.subplots(1, 3, figsize=(10, 3.1))
for ax, (m, yl) in zip(axs, [("mean_queue", "Mean total queue (veh)"),
                             ("max_queue", "Max total queue (veh)"),
                             ("throughput_vph", "Throughput (veh/h)")]):
    grouped(ax, m, yl, ["fixed", "lqf", "mdp"])
axs[0].legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(FIG / "fig_queue_throughput.png")
plt.close(fig)

# --------------------------------------------------------- time series (seed 1)
def queue_series(sc, kind, seed=1):
    stream = ArrivalStream(seed, cfg.horizon)
    sess = Session(cfg, sc, seed, make_controller(kind, cfg, sc), stream=stream)
    t, q, phase = [], [], []
    while not sess.done:
        out = sess.step()
        tk = out["result"]["ticks"][-1]
        t.append(tk["t"])
        q.append(sum(tk["q"]))
        phase.append(out["obs"].phase)
    return np.array(t), np.array(q)


fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.0), sharey=False)
for ax, sid in zip(axs, ["S3", "S2", "S5"]):
    for kind in ["fixed", "mdp"]:
        t, q = queue_series(scenarios[sid], kind)
        ax.plot(t, q, color=COLOR[kind], lw=1.2, label=LABEL[kind])
    if sid == "S5":
        s, e, _ = scenarios[sid].surge
        ax.axvspan(s, e, color="grey", alpha=.15, label="demand surge")
    ax.set_title(f"{sid} – {scenarios[sid].name}", fontsize=10)
    ax.set_xlabel("simulated time (s)")
axs[0].set_ylabel("Total queue (veh)")
axs[0].legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(FIG / "fig_queue_timeseries.png")
plt.close(fig)

# ----------------------------------------------------------- policy heat-map
lam = cfg.nominal_lambda
sol = solve(cfg, lam, lam)[1]
LV = ["0", "1–3", "4–7", "8+"]
fig, axs = plt.subplots(1, 2, figsize=(8, 3.6))
for p, ax in enumerate(axs):
    grid = np.zeros((4, 4))
    for ns in range(4):
        for ew in range(4):
            grid[ns, ew] = sol.policy[to_index(ns, ew, p, 1)]
    ax.imshow(grid, cmap=plt.matplotlib.colors.ListedColormap(["#cfe0ff", "#ffd9ad"]), vmin=0, vmax=1)
    for ns in range(4):
        for ew in range(4):
            ax.text(ew, ns, "SWITCH" if grid[ns, ew] else "KEEP", ha="center", va="center",
                    fontsize=8.5, fontweight="bold",
                    color="#8a4300" if grid[ns, ew] else "#1b3a8a")
    ax.set_xticks(range(4), LV)
    ax.set_yticks(range(4), LV)
    ax.set_xlabel("East–West queue level $q_{EW}$")
    ax.set_ylabel("North–South queue level $q_{NS}$")
    ax.set_title(("North–South" if p == 0 else "East–West") + " green, $e=1$", fontsize=10)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
fig.tight_layout()
fig.savefig(FIG / "fig_policy_heatmap.png")
plt.close(fig)

# ------------------------------------------- convergence + VI vs Q-learning
q_check = json.load(open(OUTPUT_DIR / "qlearning_check.json"))
fig, axs = plt.subplots(1, 2, figsize=(9, 3.2))
axs[0].semilogy(range(1, len(sol.history) + 1), sol.history, color="#2f6fed")
axs[0].axhline(cfg.eps, ls="--", color="grey", lw=1)
axs[0].text(len(sol.history) * .55, cfg.eps * 1.6, "ε = 1e-4", color="grey", fontsize=9)
axs[0].set_xlabel("Value Iteration sweep")
axs[0].set_ylabel("max |$V_{k+1}-V_k$|")
axs[0].set_title("Convergence of Value Iteration", fontsize=10)
perf = q_check["avg_wait_by_policy"]
x = np.arange(3)
for i, (name, lab, col) in enumerate([("value_iteration", "Value Iteration (DP)", "#2f6fed"),
                                      ("q_learning", "Q-Learning (simulator)", "#12a594")]):
    axs[1].bar(x + (i - .5) * .38, [perf[f"{s}_{name}_avg_wait_s"] for s in ("S2", "S3", "S5")], .38,
               color=col, label=lab)
axs[1].set_xticks(x, ["S2", "S3", "S5"])
axs[1].set_ylabel("Average waiting time (s)")
axs[1].set_title("DP policy vs model-free policy", fontsize=10)
axs[1].legend(frameon=False, fontsize=8.5)
axs[1].grid(axis="x", visible=False)
fig.tight_layout()
fig.savefig(FIG / "fig_convergence_ql.png")
plt.close(fig)

# --------------------------------------------------------------------- digest
digest = {"scenarios": {}, "latency_ms": {}, "policy": {}}
for sid in sids:
    d = {}
    for c in ORDER:
        d[c] = {m: {"mean": mean(sid, c, m), "std": sd(sid, c, m)} for m in
                ("avg_wait_s", "avg_wait_departed_s", "mean_queue", "max_queue", "max_queue_approach",
                 "throughput_vph", "switches", "forced_switches", "vetoed_switches", "total_reward",
                 "arrived", "departed", "remaining")}
    imp = {}
    for c in ("mdp", "lqf", "mdp_nominal"):
        for m, lower in (("avg_wait_s", True), ("mean_queue", True), ("throughput_vph", False)):
            a, b = mean(sid, c, m), mean(sid, "fixed", m)
            imp[f"{c}_{m}_vs_fixed_pct"] = (b - a) / b * 100 if lower else (a - b) / b * 100
        wins = sum(1 for x, y in zip(vals(sid, c, "avg_wait_s"), vals(sid, "fixed", "avg_wait_s")) if x < y)
        imp[f"{c}_seeds_better_than_fixed"] = wins
    d["improvement"] = imp
    digest["scenarios"][sid] = d

# decision latency of the policy lookup
ctrl = make_controller("mdp", cfg, scenarios["S3"])
sess = Session(cfg, scenarios["S3"], 1, ctrl)
lat = []
while not sess.done:
    sess.step()
    lat.append(ctrl.last_latency_ms)
digest["latency_ms"] = {"mean": float(np.mean(lat)), "max": float(np.max(lat)), "decisions": len(lat)}

# policy facts
pol = {}
for tag, (a, b) in {"S3": scenarios["S3"].mean_rates(cfg.horizon), "nominal": (lam, lam),
                    "S2": scenarios["S2"].mean_rates(cfg.horizon)}.items():
    _, s = solve(cfg, a, b)
    free = [i for i in range(96) if from_index(i)[3] == 1]
    pol[tag] = {"free_switch": int(sum(s.policy[i] for i in free)), "vi_iterations": s.iterations}
sols = [solve(cfg, *scenarios[s].mean_rates(cfg.horizon))[1].policy for s in sids]
sols.append(sol.policy)
digest["policy"] = {"per_tag": pol,
                    "n_distinct_policies_over_S1_S5_nominal": len({tuple(p) for p in sols}),
                    "free_state_disagreements_nominal_vs_S3": int(sum(
                        1 for i in range(96) if from_index(i)[3] == 1 and sol.policy[i] != sols[2][i]))}
digest["model_vs_sim"] = json.load(open(OUTPUT_DIR / "model_vs_sim.json"))
digest["qlearning"] = q_check
(OUTPUT_DIR / "digest.json").write_text(json.dumps(digest, indent=1), encoding="utf-8")
print("figures:", sorted(p.name for p in FIG.glob("*.png")))
print(json.dumps(digest["policy"]), digest["latency_ms"])
for sid in sids:
    print(sid, {k: round(v, 1) for k, v in digest["scenarios"][sid]["improvement"].items()})
