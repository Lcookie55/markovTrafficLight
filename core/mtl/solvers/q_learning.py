"""Model-free Q-Learning on the simulator (report Sections 2.2.4 and 5.3).

It learns Q(s, a) over the *same* 96 encoded states directly from sampled
interaction (no transition model). It is used to check that the dynamic-
programming policy can be recovered from experience alone.
"""
from __future__ import annotations

import numpy as np

from ..arrivals import ArrivalStream
from ..config import Config, Scenario
from ..env import Intersection
from ..safety import SafetyLayer
from ..state import KEEP, N_STATES, SWITCH, from_index
from .value_iteration import Solution


def q_learning(cfg: Config, lam_ns: float, lam_ew: float, episodes: int = 400,
               episode_len: int = 1800, seed: int = 0, eps_start: float = 0.4,
               eps_end: float = 0.02) -> tuple:
    """Return (Solution, visit_counts[S, 2])."""
    rng = np.random.default_rng(seed)
    Q = np.zeros((N_STATES, 2))
    n = np.zeros((N_STATES, 2))
    visits = np.zeros(N_STATES)
    safety = SafetyLayer(cfg)
    rate_fn = lambda t: (lam_ns, lam_ew)  # noqa: E731
    history = []
    for ep in range(episodes):
        eps = max(eps_end, eps_start * (1 - ep / max(1, episodes * 0.8)))
        env = Intersection(cfg, ArrivalStream(seed * 100003 + ep, episode_len), rate_fn)
        obs = env.observe()
        ret = 0.0
        while env.t + cfg.dt <= episode_len:
            s = obs.state_idx
            a = int(rng.integers(2)) if rng.random() < eps else int(Q[s].argmax())
            dec = safety.apply(a, obs.k)
            res = env.step(bool(dec.applied))
            obs = env.observe()
            r = res["reward"]
            ret += r
            alpha = max(0.01, 1.0 / (1.0 + n[s, a]) ** 0.6)
            Q[s, a] += alpha * (r + cfg.gamma * Q[obs.state_idx].max() - Q[s, a])
            n[s, a] += 1
            visits[s] += 1
        history.append(ret)
    pol = np.where(Q[:, SWITCH] > Q[:, KEEP], SWITCH, KEEP).astype(int)
    for s in range(N_STATES):
        e = from_index(s)[3]
        if e == 0:
            pol[s] = KEEP
        elif e == 2:
            pol[s] = SWITCH
    return Solution(Q.max(axis=1), Q, pol, episodes, history, "q_learning"), visits


def policy_agreement(a: np.ndarray, b: np.ndarray, weights: np.ndarray | None = None) -> dict:
    """Agreement on the *free* decisions (e = 1), optionally visit-weighted."""
    free = [s for s in range(N_STATES) if from_index(s)[3] == 1]
    same = np.array([a[s] == b[s] for s in free], dtype=float)
    out = {"free_states": len(free), "agree_unweighted": float(same.mean())}
    if weights is not None:
        w = np.array([weights[s] for s in free], dtype=float)
        out["agree_weighted"] = float((same * w).sum() / w.sum()) if w.sum() else float("nan")
    return out
