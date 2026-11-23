import numpy as np

from mtl.config import load_config
from mtl.runner import solve
from mtl.solvers.q_learning import policy_agreement, q_learning

CFG, SCN = load_config()


def test_q_learning_recovers_most_of_dp_policy():
    lam = CFG.nominal_lambda
    vi = solve(CFG, lam, lam)[1]
    ql, visits = q_learning(CFG, lam, lam, episodes=600, episode_len=1800, seed=0)
    agr = policy_agreement(ql.policy, vi.policy, visits)
    # model-free learning on the real simulator is expected to match the DP policy
    # on most free states (it differs where the bucketed model is only approximate)
    assert agr["agree_unweighted"] >= 0.7
