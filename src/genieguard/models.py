from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


Coord = tuple[int, int]


def _to_coord(value: Any) -> Coord:
    if isinstance(value, tuple) and len(value) == 2:
        return int(value[0]), int(value[1])
    if isinstance(value, list) and len(value) == 2:
        return int(value[0]), int(value[1])
    raise ValueError(f"Invalid coordinate: {value!r}")


def _coord_to_list(value: Coord) -> list[int]:
    return [value[0], value[1]]


@dataclass
class Meta:
    name: str = "CTF10"
    seed: int = 1337
    version: str = "0.1"


@dataclass
class MapSpec:
    w: int
    h: int
    walls: list[Coord]
    flags: dict[str, Coord]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MapSpec":
        walls = [_to_coord(x) for x in data.get("walls", [])]
        flags_raw = data.get("flags", {})
        flags = {team: _to_coord(coord) for team, coord in flags_raw.items()}
        return cls(
            w=int(data["w"]),
            h=int(data["h"]),
            walls=walls,
            flags=flags,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "w": self.w,
            "h": self.h,
            "walls": [_coord_to_list(c) for c in self.walls],
            "flags": {k: _coord_to_list(v) for k, v in self.flags.items()},
        }


@dataclass
class Rules:
    max_turns: int = 60
    win: str = "capture_flag"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Rules":
        return cls(
            max_turns=int(data.get("max_turns", 60)),
            win=str(data.get("win", "capture_flag")),
        )


@dataclass
class Params:
    move_cost: int = 1
    capture_range: int = 0
    deadlock_repeat: int = 6

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Params":
        return cls(
            move_cost=int(data.get("move_cost", 1)),
            capture_range=int(data.get("capture_range", 0)),
            deadlock_repeat=int(data.get("deadlock_repeat", 6)),
        )


@dataclass
class GameSpec:
    meta: Meta
    map: MapSpec
    spawns: dict[str, Coord]
    rules: Rules
    params: Params

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameSpec":
        meta_raw = data.get("meta", {})
        meta = Meta(
            name=str(meta_raw.get("name", "CTF10")),
            seed=int(meta_raw.get("seed", 1337)),
            version=str(meta_raw.get("version", "0.1")),
        )
        spawns_raw = data.get("spawns", {})
        spawns = {team: _to_coord(coord) for team, coord in spawns_raw.items()}
        return cls(
            meta=meta,
            map=MapSpec.from_dict(data["map"]),
            spawns=spawns,
            rules=Rules.from_dict(data.get("rules", {})),
            params=Params.from_dict(data.get("params", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": asdict(self.meta),
            "map": self.map.to_dict(),
            "spawns": {k: _coord_to_list(v) for k, v in self.spawns.items()},
            "rules": asdict(self.rules),
            "params": asdict(self.params),
        }

    def clone(self) -> "GameSpec":
        return GameSpec.from_dict(self.to_dict())


@dataclass
class GameLog:
    seed: int
    policy_a: str
    policy_b: str
    winner: str | None
    terminal_reason: str
    turns: int
    trace: list[str]
    state_hashes: list[str]
    events: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "policy_a": self.policy_a,
            "policy_b": self.policy_b,
            "winner": self.winner,
            "terminal_reason": self.terminal_reason,
            "turns": self.turns,
            "trace": list(self.trace),
            "state_hashes": list(self.state_hashes),
            "events": list(self.events),
        }


@dataclass
class AuditReport:
    metrics: dict[str, float]
    policy_win_rates: dict[str, float]
    findings: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    recommendations: list[str]
    reproducible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": dict(self.metrics),
            "policy_win_rates": dict(self.policy_win_rates),
            "findings": list(self.findings),
            "evidence": list(self.evidence),
            "recommendations": list(self.recommendations),
            "reproducible": self.reproducible,
        }


@dataclass
class PatchProposal:
    patch_ops: list[dict[str, Any]]
    rationale: str
    expected_effect: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "patch_ops": list(self.patch_ops),
            "rationale": self.rationale,
            "expected_effect": dict(self.expected_effect),
        }

