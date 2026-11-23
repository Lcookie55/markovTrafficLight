"""Analytic MDP model P(s'|s,a), R(s,a) for the 96-state formulation (Chapter 4).

Two approximations are needed because the bucketed state hides the exact queue
count and the exact time spent in the current phase (documented in PLAN.md 4.2):

* the exact queue inside a level is uniform over the integers of that level;
* the elapsed-step counter inside bucket e is uniform over the bucket's values.

Dynamics per decision step (dt = 5 s):
    q' = min(q_max, max(0, q + Arrivals - Capacity))        (per axis, Section 4.4)
    Arrivals ~ Poisson(2 * lambda * dt)    (two approaches per axis)
    KEEP:   served axis capacity = cap_keep, other axis 0
    SWITCH: 4 s clearance (no service), then the new axis serves cap_switch
The safety envelope is applied first (SWITCH in e=0 -> KEEP, anything in e=2 -> SWITCH).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .config import Config
from .state import (KEEP, LEVEL_RANGES, N_LEVELS, N_STATES, SWITCH,
                    elapsed_bucket, elapsed_members, from_index, level_of, to_index)


def poisson_pmf(mean: float, q_max: int, cap: int) -> np.ndarray:
    n = int(mean + 12 * math.sqrt(max(mean, 1e-9)) + q_max + cap + 30)
    pmf = np.zeros(n + 1)
    if mean <= 0:
        pmf[0] = 1.0
        return pmf
    pmf[0] = math.exp(-mean)
    for a in range(1, n + 1):
        pmf[a] = pmf[a - 1] * mean / a
    pmf[-1] += max(0.0, 1.0 - pmf.sum())  # lump the (negligible) tail
    return pmf


def axis_transition(mean_arrivals: float, cap: int, q_max: int) -> np.ndarray:
    """T[q, q'] for exact queue q in 0..q_max."""
    pmf = poisson_pmf(mean_arrivals, q_max, cap)
    T = np.zeros((q_max + 1, q_max + 1))
    a = np.arange(len(pmf))
    for q in range(q_max + 1):
        qn = np.clip(q + a - cap, 0, q_max)
        np.add.at(T[q], qn, pmf)
    return T


def level_matrices(mean_arrivals: float, cap: int, q_max: int):
    """Level-to-level transition (4x4) and expected exact q' (4,) for one axis."""
    T = axis_transition(mean_arrivals, cap, q_max)
    W = np.zeros((N_LEVELS, q_max + 1))          # uniform within level
    for L, rng in enumerate(LEVEL_RANGES):
        members = [q for q in rng if q <= q_max]
        W[L, members] = 1.0 / len(members)
    Lq = W @ T                                    # level -> exact q'
    B = np.zeros((q_max + 1, N_LEVELS))
    for q in range(q_max + 1):
        B[q, level_of(q)] = 1.0
    return Lq @ B, Lq @ np.arange(q_max + 1)


@dataclass
class MDPModel:
    cfg: Config
    lam_ns: float
    lam_ew: float
    P: np.ndarray   # (2, S, S)  indexed by *requested* action
    R: np.ndarray   # (S, 2)
    effective: np.ndarray  # (S, 2) action actually applied after the safety envelope


def effective_action(e: int, a: int) -> int:
    if e == 0:
        return KEEP
    if e == 2:
        return SWITCH
    return a


def build_model(cfg: Config, lam_ns: float, lam_ew: float) -> MDPModel:
    P = np.zeros((2, N_STATES, N_STATES))
    R = np.zeros((N_STATES, 2))
    eff = np.zeros((N_STATES, 2), dtype=int)

    mats = {}  # cache (axis_rate_key, cap) -> level matrices

    def lm(axis: int, cap: int):
        lam = lam_ns if axis == 0 else lam_ew
        key = (axis, cap)
        if key not in mats:
            mats[key] = level_matrices(2 * lam * cfg.dt, cap, cfg.q_max)
        return mats[key]

    # elapsed-bucket transition under KEEP (uniform over members of the bucket)
    e_keep = np.zeros((3, 3))
    for e in range(3):
        members = elapsed_members(e, cfg)
        for k in members:
            e_keep[e, elapsed_bucket(k + 1, cfg)] += 1.0 / len(members)

    for s in range(N_STATES):
        l_ns, l_ew, p, e = from_index(s)
        for a in (KEEP, SWITCH):
            ae = effective_action(e, a)
            eff[s, a] = ae
            if ae == KEEP:
                caps = (cfg.cap_keep if p == 0 else 0, cfg.cap_keep if p == 1 else 0)
                p_next, e_dist = p, e_keep[e]
                switched = 0
            else:
                new = 1 - p
                caps = (cfg.cap_switch if new == 0 else 0, cfg.cap_switch if new == 1 else 0)
                p_next, e_dist = new, np.array([1.0, 0.0, 0.0])
                switched = 1
            T_ns, E_ns = lm(0, caps[0])
            T_ew, E_ew = lm(1, caps[1])
            for ln2 in range(N_LEVELS):
                pn = T_ns[l_ns, ln2]
                if pn <= 0:
                    continue
                for le2 in range(N_LEVELS):
                    pe = T_ew[l_ew, le2]
                    if pe <= 0:
                        continue
                    for e2 in range(3):
                        pr = e_dist[e2]
                        if pr <= 0:
                            continue
                        P[a, s, to_index(ln2, le2, p_next, e2)] += pn * pe * pr
            R[s, a] = -(E_ns[l_ns] + E_ew[l_ew]) - cfg.c_switch * switched
    return MDPModel(cfg, lam_ns, lam_ew, P, R, eff)
