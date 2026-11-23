"""Value Iteration and Policy Iteration over the analytic model."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..model import MDPModel
from ..state import KEEP, N_STATES, SWITCH, from_index


@dataclass
class Solution:
    V: np.ndarray
    Q: np.ndarray                 # (S, 2)
    policy: np.ndarray            # (S,) action the controller *requests*
    iterations: int
    history: list = field(default_factory=list)  # max|dV| per iteration
    method: str = "value_iteration"


def q_from_v(model: MDPModel, V: np.ndarray) -> np.ndarray:
    gamma = model.cfg.gamma
    Q = np.zeros((N_STATES, 2))
    for a in (KEEP, SWITCH):
        Q[:, a] = model.R[:, a] + gamma * model.P[a] @ V
    return Q


def extract_policy(model: MDPModel, Q: np.ndarray, tol: float = 1e-9) -> np.ndarray:
    """Greedy policy; ties go to KEEP. Safety-determined states get the effective action."""
    pol = np.where(Q[:, SWITCH] > Q[:, KEEP] + tol, SWITCH, KEEP).astype(int)
    for s in range(N_STATES):
        e = from_index(s)[3]
        if e == 0:
            pol[s] = KEEP
        elif e == 2:
            pol[s] = SWITCH
    return pol


def value_iteration(model: MDPModel, eps: float | None = None,
                    max_iter: int = 100_000) -> Solution:
    eps = model.cfg.eps if eps is None else eps
    V = np.zeros(N_STATES)
    history = []
    it = 0
    for it in range(1, max_iter + 1):
        Q = q_from_v(model, V)
        V_new = Q.max(axis=1)
        delta = float(np.max(np.abs(V_new - V)))
        history.append(delta)
        V = V_new
        if delta < eps:
            break
    Q = q_from_v(model, V)
    return Solution(V, Q, extract_policy(model, Q), it, history, "value_iteration")


def policy_iteration(model: MDPModel, max_iter: int = 1000) -> Solution:
    gamma = model.cfg.gamma
    pol = np.zeros(N_STATES, dtype=int)
    V = np.zeros(N_STATES)
    it = 0
    for it in range(1, max_iter + 1):
        P_pi = np.array([model.P[pol[s], s] for s in range(N_STATES)])
        R_pi = np.array([model.R[s, pol[s]] for s in range(N_STATES)])
        V = np.linalg.solve(np.eye(N_STATES) - gamma * P_pi, R_pi)
        Q = q_from_v(model, V)
        new_pol = extract_policy(model, Q)
        if np.array_equal(new_pol, pol):
            break
        pol = new_pol
    Q = q_from_v(model, V)
    return Solution(V, Q, extract_policy(model, Q), it, [], "policy_iteration")
