from __future__ import annotations

from typing import Any

from .models import Coord, GameSpec
from .pathing import shortest_path


def _in_bounds(spec: GameSpec, pos: Coord) -> bool:
    return 0 <= pos[0] < spec.map.w and 0 <= pos[1] < spec.map.h


def validate_gamespec(spec: GameSpec) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if spec.map.w <= 1 or spec.map.h <= 1:
        errors.append("map size must be larger than 1x1")

    walls = set(spec.map.walls)
    if len(walls) != len(spec.map.walls):
        errors.append("walls contain duplicates")

    for wall in walls:
        if not _in_bounds(spec, wall):
            errors.append(f"wall out of bounds: {wall}")

    for key in ("A", "B"):
        if key not in spec.spawns:
            errors.append(f"missing spawn for team {key}")
        if key not in spec.map.flags:
            errors.append(f"missing flag for team {key}")

    if errors:
        return False, errors

    for team, pos in spec.spawns.items():
        if not _in_bounds(spec, pos):
            errors.append(f"spawn out of bounds: {team}={pos}")
        if pos in walls:
            errors.append(f"spawn on wall: {team}={pos}")

    for team, pos in spec.map.flags.items():
        if not _in_bounds(spec, pos):
            errors.append(f"flag out of bounds: {team}={pos}")
        if pos in walls:
            errors.append(f"flag on wall: {team}={pos}")

    if spec.spawns["A"] == spec.spawns["B"]:
        errors.append("spawns must not overlap")
    if spec.map.flags["A"] == spec.map.flags["B"]:
        errors.append("flags must not overlap")

    # Reachability checks for gameplay viability.
    for team in ("A", "B"):
        enemy = "B" if team == "A" else "A"
        path = shortest_path(spec, spec.spawns[team], spec.map.flags[enemy])
        if not path:
            errors.append(f"no path from spawn {team} to enemy flag {enemy}")

    return len(errors) == 0, errors


def assert_valid_gamespec(spec: GameSpec) -> None:
    ok, errors = validate_gamespec(spec)
    if not ok:
        lines = "; ".join(errors)
        raise ValueError(f"Invalid GameSpec: {lines}")
