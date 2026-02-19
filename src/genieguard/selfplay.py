from __future__ import annotations

import hashlib

from .models import GameLog, GameSpec
from .policies import build_policy, default_policy_names
from .simulator import DeterministicRunner


def _stable_policy_seed(base_seed: int, policy_name: str, side: str) -> int:
    token = f"{base_seed}:{policy_name}:{side}".encode("utf-8")
    return int(hashlib.sha1(token).hexdigest()[:8], 16)


def run_self_play(
    spec: GameSpec,
    seeds: list[int],
    policy_names: list[str] | None = None,
) -> list[GameLog]:
    names = policy_names or default_policy_names()
    runner = DeterministicRunner(spec)
    logs: list[GameLog] = []
    for policy_a_name in names:
        for policy_b_name in names:
            for seed in seeds:
                p_a_seed = _stable_policy_seed(seed, policy_a_name, "A")
                p_b_seed = _stable_policy_seed(seed, policy_b_name, "B")
                policy_a = build_policy(policy_a_name, team="A", spec=spec, seed=p_a_seed)
                policy_b = build_policy(policy_b_name, team="B", spec=spec, seed=p_b_seed)
                log = runner.run(seed=seed, policy_a=policy_a, policy_b=policy_b)
                logs.append(log)
    return logs

