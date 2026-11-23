"""Performance metrics (report Section 1.3 / FR-8)."""
from __future__ import annotations


class Metrics:
    def __init__(self):
        self.ticks = 0
        self.queue_sum = 0
        self.max_queue_total = 0
        self.max_queue_approach = 0
        self.switches = 0
        self.forced = 0
        self.vetoed = 0
        self.total_reward = 0.0
        self.steps = 0

    def on_step(self, step: dict, decision) -> None:
        for tk in step["ticks"]:
            tot = sum(tk["q"])
            self.ticks += 1
            self.queue_sum += tot
            self.max_queue_total = max(self.max_queue_total, tot)
            self.max_queue_approach = max(self.max_queue_approach, max(tk["q"]))
        self.steps += 1
        self.total_reward += step["reward"]
        if decision.applied == 1:
            self.switches += 1
        if decision.reason == "forced":
            self.forced += 1
        elif decision.reason == "vetoed":
            self.vetoed += 1

    def summary(self, env) -> dict:
        arrived, departed = env.arrived, env.departed
        remaining = arrived - departed
        avg_wait_dep = env.wait_sum / departed if departed else 0.0
        avg_wait_all = ((env.wait_sum + env.remaining_wait()) / arrived) if arrived else 0.0
        hours = env.t / 3600.0
        return {
            "avg_wait_s": avg_wait_all,            # includes vehicles still queued
            "avg_wait_departed_s": avg_wait_dep,
            "mean_queue": self.queue_sum / self.ticks if self.ticks else 0.0,
            "max_queue": self.max_queue_total,
            "max_queue_approach": self.max_queue_approach,
            "throughput_vph": departed / hours if hours else 0.0,
            "arrived": arrived,
            "departed": departed,
            "remaining": remaining,
            "switches": self.switches,
            "forced_switches": self.forced,
            "vetoed_switches": self.vetoed,
            "total_reward": self.total_reward,
        }
