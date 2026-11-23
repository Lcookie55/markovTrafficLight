"""Seeded arrival streams shared by every controller (common random numbers).

A stream stores uniform random numbers u[t, approach]. The arrival count in a
tick is the inverse-CDF Poisson draw for the *current* rate, so the same stream
gives identical arrivals to every controller and still supports rates that
change over time (S5) or live from the UI.
"""
from __future__ import annotations

import math

import numpy as np


def poisson_inv(u: float, lam: float) -> int:
    if lam <= 0.0:
        return 0
    p = math.exp(-lam)
    c = p
    k = 0
    while u > c and k < 60:
        k += 1
        p *= lam / k
        c += p
    return k


class ArrivalStream:
    N_APPROACHES = 4  # N, S, E, W

    def __init__(self, seed: int, horizon: int):
        rng = np.random.default_rng(seed)
        self._u = rng.random((horizon + 1, self.N_APPROACHES)).tolist()
        self.seed = seed
        self.horizon = horizon

    def counts(self, t: int, lam_ns: float, lam_ew: float) -> list:
        row = self._u[min(t, self.horizon)]
        rates = (lam_ns, lam_ns, lam_ew, lam_ew)
        return [poisson_inv(row[i], rates[i]) for i in range(self.N_APPROACHES)]
