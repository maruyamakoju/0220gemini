from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

from .models import Coord, GameSpec
from .pathing import shortest_path


ACTIONS = ("U", "D", "L", "R", "Stay")


@dataclass(frozen=True)
class Observation:
    team: str
    turn: int
    max_turns: int
    self_pos: Coord
    opp_pos: Coord
    own_flag: Coord
    opp_flag: Coord
    map_w: int
    map_h: int
    walls: tuple[Coord, ...]


class Policy(Protocol):
    name: str

    def act(self, obs: Observation) -> str:
        ...


def _to_action(start: Coord, nxt: Coord) -> str:
    dx = nxt[0] - start[0]
    dy = nxt[1] - start[1]
    if (dx, dy) == (0, -1):
        return "U"
    if (dx, dy) == (0, 1):
        return "D"
    if (dx, dy) == (-1, 0):
        return "L"
    if (dx, dy) == (1, 0):
        return "R"
    return "Stay"


def _greedy_toward(spec: GameSpec, start: Coord, goal: Coord) -> str:
    path = shortest_path(spec, start, goal)
    if len(path) < 2:
        return "Stay"
    return _to_action(start, path[1])


class GreedyShortestPathPolicy:
    name = "greedy_shortest_path"

    def __init__(self, team: str, spec: GameSpec, seed: int) -> None:
        self.team = team
        self.spec = spec
        self.seed = seed

    def act(self, obs: Observation) -> str:
        return _greedy_toward(self.spec, obs.self_pos, obs.opp_flag)


class BlockerPolicy:
    name = "blocker"

    def __init__(self, team: str, spec: GameSpec, seed: int) -> None:
        self.team = team
        self.spec = spec
        self.seed = seed

    def act(self, obs: Observation) -> str:
        opponent_path = shortest_path(self.spec, obs.opp_pos, obs.own_flag)
        if len(opponent_path) >= 2:
            target = opponent_path[1]
            my_path = shortest_path(self.spec, obs.self_pos, target)
            if len(my_path) >= 2:
                return _to_action(obs.self_pos, my_path[1])
        return _greedy_toward(self.spec, obs.self_pos, obs.opp_flag)


class CamperPolicy:
    name = "camper"

    def __init__(self, team: str, spec: GameSpec, seed: int) -> None:
        self.team = team
        self.spec = spec
        self.seed = seed
        self.target = self._pick_target()

    def _pick_target(self) -> Coord:
        opp_flag = self.spec.map.flags["B" if self.team == "A" else "A"]
        candidates = [
            opp_flag,
            (opp_flag[0], opp_flag[1] - 1),
            (opp_flag[0], opp_flag[1] + 1),
            (opp_flag[0] - 1, opp_flag[1]),
            (opp_flag[0] + 1, opp_flag[1]),
        ]
        wall_set = set(self.spec.map.walls)
        valid = [
            c
            for c in candidates
            if 0 <= c[0] < self.spec.map.w
            and 0 <= c[1] < self.spec.map.h
            and c not in wall_set
        ]
        if not valid:
            return self.spec.spawns[self.team]
        valid.sort(key=lambda p: (p[1], p[0]))
        return valid[0]

    def act(self, obs: Observation) -> str:
        if obs.self_pos == self.target:
            return "Stay"
        return _greedy_toward(self.spec, obs.self_pos, self.target)


class RandomEpsilonPolicy:
    name = "random_epsilon"

    def __init__(self, team: str, spec: GameSpec, seed: int, epsilon: float = 0.25) -> None:
        self.team = team
        self.spec = spec
        self.rng = random.Random(seed)
        self.epsilon = epsilon

    def act(self, obs: Observation) -> str:
        if self.rng.random() < self.epsilon:
            return self.rng.choice(list(ACTIONS))
        return _greedy_toward(self.spec, obs.self_pos, obs.opp_flag)


def build_policy(name: str, team: str, spec: GameSpec, seed: int) -> Policy:
    key = name.lower()
    if key == "greedy_shortest_path":
        return GreedyShortestPathPolicy(team=team, spec=spec, seed=seed)
    if key == "blocker":
        return BlockerPolicy(team=team, spec=spec, seed=seed)
    if key == "camper":
        return CamperPolicy(team=team, spec=spec, seed=seed)
    if key == "random_epsilon":
        return RandomEpsilonPolicy(team=team, spec=spec, seed=seed)
    raise ValueError(f"Unknown policy: {name}")


def default_policy_names() -> list[str]:
    return ["greedy_shortest_path", "blocker", "camper", "random_epsilon"]

