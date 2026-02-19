from __future__ import annotations

from genieguard.policies import build_policy
from genieguard.simulator import DeterministicRunner
from genieguard.spec_gen import default_gamespec


def test_deterministic_runner_same_inputs_same_output() -> None:
    spec = default_gamespec(seed=1337)
    runner = DeterministicRunner(spec)
    policy_a_1 = build_policy("random_epsilon", "A", spec, seed=123)
    policy_b_1 = build_policy("random_epsilon", "B", spec, seed=456)
    policy_a_2 = build_policy("random_epsilon", "A", spec, seed=123)
    policy_b_2 = build_policy("random_epsilon", "B", spec, seed=456)

    log1 = runner.run(seed=999, policy_a=policy_a_1, policy_b=policy_b_1)
    log2 = runner.run(seed=999, policy_a=policy_a_2, policy_b=policy_b_2)

    assert log1.winner == log2.winner
    assert log1.terminal_reason == log2.terminal_reason
    assert log1.turns == log2.turns
    assert log1.trace == log2.trace
