"""Scenario x seed x controller experiment grid -> CSV / JSON (report Section 5.5)."""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

from .arrivals import ArrivalStream
from .config import Config, OUTPUT_DIR, Scenario
from .runner import CONTROLLER_KINDS, make_controller, run_episode

METRICS = ("avg_wait_s", "avg_wait_departed_s", "mean_queue", "max_queue",
           "max_queue_approach", "throughput_vph", "switches", "total_reward")


def run_grid(cfg: Config, scenarios: dict, controllers=CONTROLLER_KINDS, seeds=None) -> list:
    seeds = seeds or cfg.seeds
    rows = []
    for sid, sc in scenarios.items():
        for seed in seeds:
            stream = ArrivalStream(seed, cfg.horizon)   # identical for all controllers
            for kind in controllers:
                m = run_episode(cfg, sc, seed, make_controller(kind, cfg, sc), stream=stream)
                rows.append({"scenario": sid, "seed": seed, "controller": kind, **m})
    return rows


def summarize(rows: list) -> list:
    groups = {}
    for r in rows:
        groups.setdefault((r["scenario"], r["controller"]), []).append(r)
    out = []
    for (sid, kind), rs in groups.items():
        row = {"scenario": sid, "controller": kind, "runs": len(rs)}
        for m in METRICS:
            vals = [r[m] for r in rs]
            row[f"{m}_mean"] = statistics.fmean(vals)
            row[f"{m}_std"] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        out.append(row)
    return out


def save(rows: list, summary: list, out_dir: Path = OUTPUT_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in (("results.csv", rows), ("summary.csv", summary)):
        with open(out_dir / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
