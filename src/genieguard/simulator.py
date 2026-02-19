from __future__ import annotations

import hashlib
import json
from collections import defaultdict

from .models import Coord, GameLog, GameSpec
from .policies import ACTIONS, Observation, Policy


MOVE = {
    "U": (0, -1),
    "D": (0, 1),
    "L": (-1, 0),
    "R": (1, 0),
    "Stay": (0, 0),
}


def _normalize_action(action: str) -> str:
    if action not in ACTIONS:
        return "Stay"
    return action


class DeterministicRunner:
    def __init__(self, spec: GameSpec) -> None:
        self.spec = spec
        self.wall_set = set(spec.map.walls)

    def _attempt_move(self, pos: Coord, action: str) -> tuple[Coord, bool]:
        dx, dy = MOVE[action]
        nxt = (pos[0] + dx, pos[1] + dy)
        if 0 <= nxt[0] < self.spec.map.w and 0 <= nxt[1] < self.spec.map.h and nxt not in self.wall_set:
            return nxt, True
        return pos, False

    def _state_hash(self, turn: int, pos_a: Coord, pos_b: Coord) -> str:
        # Turn index is intentionally excluded so cycles collapse to the same hash.
        payload = {"A": [pos_a[0], pos_a[1]], "B": [pos_b[0], pos_b[1]]}
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    def _dist(self, p: Coord, q: Coord) -> int:
        return abs(p[0] - q[0]) + abs(p[1] - q[1])

    def _observation(
        self,
        team: str,
        turn: int,
        pos_a: Coord,
        pos_b: Coord,
    ) -> Observation:
        if team == "A":
            self_pos, opp_pos = pos_a, pos_b
            own_flag, opp_flag = self.spec.map.flags["A"], self.spec.map.flags["B"]
        else:
            self_pos, opp_pos = pos_b, pos_a
            own_flag, opp_flag = self.spec.map.flags["B"], self.spec.map.flags["A"]
        return Observation(
            team=team,
            turn=turn,
            max_turns=self.spec.rules.max_turns,
            self_pos=self_pos,
            opp_pos=opp_pos,
            own_flag=own_flag,
            opp_flag=opp_flag,
            map_w=self.spec.map.w,
            map_h=self.spec.map.h,
            walls=tuple(self.spec.map.walls),
        )

    def run(self, seed: int, policy_a: Policy, policy_b: Policy) -> GameLog:
        pos_a = self.spec.spawns["A"]
        pos_b = self.spec.spawns["B"]
        trace: list[str] = []
        state_hashes: list[str] = []
        events: list[str] = []
        hash_count: dict[str, int] = defaultdict(int)
        capture_range = self.spec.params.capture_range

        for turn in range(1, self.spec.rules.max_turns + 1):
            obs_a = self._observation("A", turn, pos_a, pos_b)
            obs_b = self._observation("B", turn, pos_a, pos_b)

            raw_a = policy_a.act(obs_a)
            raw_b = policy_b.act(obs_b)
            action_a = _normalize_action(raw_a)
            action_b = _normalize_action(raw_b)

            nxt_a, ok_a = self._attempt_move(pos_a, action_a)
            nxt_b, ok_b = self._attempt_move(pos_b, action_b)
            if not ok_a:
                events.append(f"turn={turn}:A_invalid_move:{raw_a}")
            if not ok_b:
                events.append(f"turn={turn}:B_invalid_move:{raw_b}")

            pos_a, pos_b = nxt_a, nxt_b
            trace.append(f"A:{action_a}|B:{action_b}")

            a_captured = self._dist(pos_a, self.spec.map.flags["B"]) <= capture_range
            b_captured = self._dist(pos_b, self.spec.map.flags["A"]) <= capture_range
            if a_captured and b_captured:
                state_hashes.append(self._state_hash(turn, pos_a, pos_b))
                return GameLog(
                    seed=seed,
                    policy_a=policy_a.name,
                    policy_b=policy_b.name,
                    winner=None,
                    terminal_reason="draw",
                    turns=turn,
                    trace=trace,
                    state_hashes=state_hashes,
                    events=events,
                )
            if a_captured:
                state_hashes.append(self._state_hash(turn, pos_a, pos_b))
                return GameLog(
                    seed=seed,
                    policy_a=policy_a.name,
                    policy_b=policy_b.name,
                    winner="A",
                    terminal_reason="capture",
                    turns=turn,
                    trace=trace,
                    state_hashes=state_hashes,
                    events=events,
                )
            if b_captured:
                state_hashes.append(self._state_hash(turn, pos_a, pos_b))
                return GameLog(
                    seed=seed,
                    policy_a=policy_a.name,
                    policy_b=policy_b.name,
                    winner="B",
                    terminal_reason="capture",
                    turns=turn,
                    trace=trace,
                    state_hashes=state_hashes,
                    events=events,
                )

            state_hash = self._state_hash(turn, pos_a, pos_b)
            state_hashes.append(state_hash)
            hash_count[state_hash] += 1
            if hash_count[state_hash] >= self.spec.params.deadlock_repeat:
                return GameLog(
                    seed=seed,
                    policy_a=policy_a.name,
                    policy_b=policy_b.name,
                    winner=None,
                    terminal_reason="deadlock",
                    turns=turn,
                    trace=trace,
                    state_hashes=state_hashes,
                    events=events,
                )

        return GameLog(
            seed=seed,
            policy_a=policy_a.name,
            policy_b=policy_b.name,
            winner=None,
            terminal_reason="timeout",
            turns=self.spec.rules.max_turns,
            trace=trace,
            state_hashes=state_hashes,
            events=events,
        )
