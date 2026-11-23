import random

import numpy as np
import pytest

from mtl.arrivals import ArrivalStream
from mtl.config import load_config
from mtl.controllers import MDPController
from mtl.env import Intersection
from mtl.model import build_model
from mtl.runner import Session, make_controller, run_episode, solve
from mtl.safety import SafetyLayer
from mtl.solvers import policy_iteration, value_iteration
from mtl.state import (KEEP, N_STATES, SWITCH, elapsed_bucket, encode, from_index,
                       level_of, to_index)

CFG, SCN = load_config()


# ----------------------------------------------------------------------- state
def test_state_roundtrip_all_96():
    seen = set()
    for s in range(N_STATES):
        t = from_index(s)
        assert to_index(*t) == s
        seen.add(t)
    assert N_STATES == 96 and len(seen) == 96


@pytest.mark.parametrize("q,lvl", [(0, 0), (1, 1), (3, 1), (4, 2), (7, 2), (8, 3), (12, 3), (40, 3)])
def test_level_boundaries(q, lvl):
    assert level_of(q) == lvl


def test_elapsed_bucket_boundaries():
    # dt=5, G_min=10, G_max=60
    assert [elapsed_bucket(k, CFG) for k in (0, 1, 2, 11, 12, 13)] == [0, 0, 1, 1, 2, 2]


# ----------------------------------------------------------------------- model
def test_model_rows_are_distributions():
    m = build_model(CFG, 0.25, 0.1)
    assert np.allclose(m.P.sum(axis=2), 1.0)
    assert (m.P >= 0).all()


def test_safety_envelope_in_model():
    m = build_model(CFG, 0.2, 0.2)
    for s in range(N_STATES):
        e = from_index(s)[3]
        if e == 0:       # SWITCH vetoed -> same row as KEEP
            assert np.allclose(m.P[SWITCH, s], m.P[KEEP, s])
        if e == 2:       # KEEP overridden -> same row as SWITCH
            assert np.allclose(m.P[KEEP, s], m.P[SWITCH, s])


# ---------------------------------------------------------------------- solvers
def test_vi_equals_pi_and_is_start_independent():
    for lam in (0.1, 0.25):
        m = build_model(CFG, lam, lam)
        vi, pi = value_iteration(m), policy_iteration(m)
        assert np.array_equal(vi.policy, pi.policy)
        assert np.allclose(vi.V, pi.V, atol=1e-2)


def test_report_table_4_1_rows():
    """Sanity rows from the report's Table 4.1 (free decisions, e = 1 'normal')."""
    pol = solve(CFG, 0.25, 0.25)[1].policy
    assert pol[to_index(3, 0, 0, 1)] == KEEP      # served direction loaded, cross empty
    assert pol[to_index(0, 3, 0, 1)] == SWITCH    # served empty, cross heavy
    assert pol[to_index(3, 3, 0, 1)] == KEEP      # both loaded -> keep clearing
    assert pol[to_index(0, 0, 0, 1)] == KEEP and pol[to_index(0, 0, 1, 1)] == KEEP
    assert pol[to_index(2, 1, 1, 0)] == KEEP      # below G_min (safety veto)
    assert pol[to_index(1, 2, 0, 2)] == SWITCH    # at G_max (forced)


# ---------------------------------------------------------------------- safety
def test_safety_layer_rules():
    sl = SafetyLayer(CFG)
    assert sl.apply(SWITCH, 0).reason == "vetoed" and sl.apply(SWITCH, 0).applied == KEEP
    assert sl.apply(SWITCH, 1).applied == KEEP
    assert sl.apply(SWITCH, 2).reason == "ok" and sl.apply(SWITCH, 2).applied == SWITCH
    assert sl.apply(KEEP, 11).applied == KEEP
    d = sl.apply(KEEP, 12)
    assert d.applied == SWITCH and d.reason == "forced"


class RandomController:
    name = "random"

    def __init__(self, seed):
        self.rng = random.Random(seed)

    def reset(self):
        pass

    def act(self, obs):
        return self.rng.randint(0, 1)


def test_signals_never_conflict_and_timing_rules_hold():
    """Property test with random action streams."""
    for seed in range(5):
        sess = Session(CFG, SCN["S2"], seed, RandomController(seed))
        prev_sig, green_run, last_green_axis, yellow_run, ar_run = None, 0, None, 0, 0
        elapsed_at_switch = []
        while not sess.done:
            k_before = sess.env.k
            out = sess.step()
            if out["decision"].applied == SWITCH:
                elapsed_at_switch.append(k_before * CFG.dt)
            for tk in out["result"]["ticks"]:
                ns, ew = tk["sig"]
                assert not (ns == "G" and ew == "G")
                assert not (ns in "GY" and ew in "GY")  # never two non-red axes
        assert all(g >= CFG.g_min for g in elapsed_at_switch)
        assert all(g <= CFG.g_max for g in elapsed_at_switch)


def test_switch_step_inserts_yellow_and_all_red():
    env = Intersection(CFG, ArrivalStream(1, 3600), SCN["S1"].rates)
    res = env.step(True)
    sigs = [tuple(t["sig"]) for t in res["ticks"]]
    assert sigs == [("Y", "R")] * 3 + [("R", "R")] + [("R", "G")]
    assert env.phase == 1 and env.k == 0
    # no discharge from the old axis during clearance
    assert all(sum(t["dep"]) == 0 for t in res["ticks"][:4])


# ------------------------------------------------------------------- simulator
def test_determinism_and_shared_arrivals():
    a = run_episode(CFG, SCN["S3"], 7, make_controller("mdp", CFG, SCN["S3"]))
    b = run_episode(CFG, SCN["S3"], 7, make_controller("mdp", CFG, SCN["S3"]))
    assert a == b
    # identical arrival streams for different controllers
    arrived = {run_episode(CFG, SCN["S3"], 7, make_controller(k, CFG, SCN["S3"]))["arrived"]
               for k in ("fixed", "mdp", "lqf")}
    assert len(arrived) == 1


def test_flow_conservation():
    sess = Session(CFG, SCN["S5"], 3, make_controller("fixed", CFG, SCN["S5"]))
    while not sess.done:
        sess.step()
    env = sess.env
    assert env.arrived == env.departed + sum(env.queue_lengths())


def test_surge_rates():
    s5 = SCN["S5"]
    assert s5.rates(0) == (0.10, 0.10)
    assert s5.rates(1600) == (0.35, 0.35)
    assert s5.rates(2200) == (0.10, 0.10)


def test_mdp_latency_below_50ms():
    ctrl = make_controller("mdp", CFG, SCN["S1"])
    sess = Session(CFG, SCN["S1"], 1, ctrl)
    worst = 0.0
    while not sess.done:
        sess.step()
        worst = max(worst, ctrl.last_latency_ms)
    assert worst < 50.0


def test_mdp_beats_fixed_on_asymmetric_demand():
    for sid in ("S3", "S4"):
        mdp = np.mean([run_episode(CFG, SCN[sid], s, make_controller("mdp", CFG, SCN[sid]))["avg_wait_s"]
                       for s in (1, 2, 3)])
        fix = np.mean([run_episode(CFG, SCN[sid], s, make_controller("fixed", CFG, SCN[sid]))["avg_wait_s"]
                       for s in (1, 2, 3)])
        assert mdp < fix
