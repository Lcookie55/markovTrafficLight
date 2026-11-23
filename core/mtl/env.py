"""Discrete-time intersection simulator (report Sections 3.3 and 5.2).

* 4 approaches (N, S, E, W) each with a FIFO of arrival times -> exact per-vehicle waits.
* 1 s internal tick, one decision every ``cfg.dt`` ticks.
* Discharge at ``mu * lanes`` veh/s per approach while its axis has green
  (fractional credit accumulator, carried across consecutive green ticks).
* A SWITCH step lasts ``dt`` ticks: yellow (3) + all-red (1) + remaining ticks of
  the new green. The elapsed counter then restarts at 0.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable

from .arrivals import ArrivalStream
from .config import Config
from .state import SWITCH, encode, from_index

APPROACHES = ("N", "S", "E", "W")
AXIS_OF = (0, 0, 1, 1)  # N,S -> axis 0 (NS) ; E,W -> axis 1 (EW)


@dataclass
class Obs:
    t: int
    queues: list          # per approach [N, S, E, W]
    q_ns: int
    q_ew: int
    phase: int
    k: int                # elapsed decision steps in the current green
    state_idx: int


class Intersection:
    def __init__(self, cfg: Config, stream: ArrivalStream,
                 rate_fn: Callable[[int], tuple]):
        self.cfg = cfg
        self.stream = stream
        self.rate_fn = rate_fn
        self.t = 0
        self.phase = 0
        self.k = 0
        self.queues = [deque() for _ in range(4)]
        self.credit = [0.0] * 4
        self.arrived = 0
        self.departed = 0
        self.wait_sum = 0

    # ------------------------------------------------------------------ views
    def queue_lengths(self) -> list:
        return [len(q) for q in self.queues]

    def observe(self) -> Obs:
        q = self.queue_lengths()
        q_ns, q_ew = q[0] + q[1], q[2] + q[3]
        return Obs(self.t, q, q_ns, q_ew, self.phase, self.k,
                   encode(q_ns, q_ew, self.phase, self.k, self.cfg))

    def remaining_wait(self) -> int:
        return sum(self.t - a for q in self.queues for a in q)

    # ------------------------------------------------------------------- step
    def _signal_plan(self, switch: bool) -> list:
        """List of (signal_letters, green_axis|None) for each tick of the step."""
        cfg = self.cfg
        plan = []
        old, new = self.phase, 1 - self.phase
        if not switch:
            sig = ("G", "R") if old == 0 else ("R", "G")
            return [(sig, old)] * cfg.dt
        for i in range(cfg.dt):
            if i < cfg.t_yellow:
                sig = ("Y", "R") if old == 0 else ("R", "Y")
                plan.append((sig, None))
            elif i < cfg.clearance:
                plan.append((("R", "R"), None))
            else:
                sig = ("G", "R") if new == 0 else ("R", "G")
                plan.append((sig, new))
        return plan

    def step(self, switch: bool) -> dict:
        """Advance one decision step. Returns telemetry for the step."""
        cfg = self.cfg
        plan = self._signal_plan(switch)
        ticks = []
        for sig, green_axis in plan:
            dep = [0, 0, 0, 0]
            wait_dep = 0
            for i in range(4):
                if AXIS_OF[i] == green_axis:
                    self.credit[i] += cfg.mu * cfg.lanes
                    q = self.queues[i]
                    while self.credit[i] >= 1.0 and q:
                        wait_dep += self.t - q.popleft()
                        self.credit[i] -= 1.0
                        dep[i] += 1
                    if not q:
                        self.credit[i] = 0.0
                else:
                    self.credit[i] = 0.0
            lam_ns, lam_ew = self.rate_fn(self.t)
            arr = self.stream.counts(self.t, lam_ns, lam_ew)
            for i in range(4):
                for _ in range(arr[i]):
                    self.queues[i].append(self.t)
            n_arr, n_dep = sum(arr), sum(dep)
            self.arrived += n_arr
            self.departed += n_dep
            self.wait_sum += wait_dep
            ticks.append({"t": self.t, "sig": sig, "q": self.queue_lengths(),
                          "dep": dep, "arr": arr, "wait_dep": wait_dep})
            self.t += 1
        if switch:
            self.phase = 1 - self.phase
            self.k = 0
        else:
            self.k += 1
        q = self.queue_lengths()
        reward = -(q[0] + q[1] + q[2] + q[3]) - cfg.c_switch * (1 if switch else 0)
        return {"ticks": ticks, "reward": reward, "queues": q}
