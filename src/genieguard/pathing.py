from __future__ import annotations

from collections import deque

from .models import Coord, GameSpec


MOVE_DIRS: dict[str, Coord] = {
    "U": (0, -1),
    "D": (0, 1),
    "L": (-1, 0),
    "R": (1, 0),
}


def in_bounds(spec: GameSpec, pos: Coord) -> bool:
    return 0 <= pos[0] < spec.map.w and 0 <= pos[1] < spec.map.h


def passable(spec: GameSpec, pos: Coord) -> bool:
    return in_bounds(spec, pos) and pos not in set(spec.map.walls)


def neighbors(spec: GameSpec, pos: Coord) -> list[Coord]:
    wall_set = set(spec.map.walls)
    out: list[Coord] = []
    for dx, dy in MOVE_DIRS.values():
        nxt = (pos[0] + dx, pos[1] + dy)
        if 0 <= nxt[0] < spec.map.w and 0 <= nxt[1] < spec.map.h and nxt not in wall_set:
            out.append(nxt)
    return out


def shortest_path(spec: GameSpec, start: Coord, goal: Coord) -> list[Coord]:
    if start == goal:
        return [start]
    wall_set = set(spec.map.walls)
    q: deque[Coord] = deque([start])
    parent: dict[Coord, Coord | None] = {start: None}
    while q:
        cur = q.popleft()
        for dx, dy in MOVE_DIRS.values():
            nxt = (cur[0] + dx, cur[1] + dy)
            if not (0 <= nxt[0] < spec.map.w and 0 <= nxt[1] < spec.map.h):
                continue
            if nxt in wall_set or nxt in parent:
                continue
            parent[nxt] = cur
            if nxt == goal:
                path: list[Coord] = [goal]
                back = cur
                while back is not None:
                    path.append(back)
                    back = parent[back]
                path.reverse()
                return path
            q.append(nxt)
    return []


def shortest_distance(spec: GameSpec, start: Coord, goal: Coord) -> int:
    path = shortest_path(spec, start, goal)
    if not path:
        return 10**9
    return len(path) - 1


def nearest_passable(spec: GameSpec, target: Coord) -> Coord | None:
    if passable(spec, target):
        return target
    q: deque[Coord] = deque([target])
    seen = {target}
    wall_set = set(spec.map.walls)
    while q:
        cur = q.popleft()
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nxt = (cur[0] + dx, cur[1] + dy)
            if nxt in seen:
                continue
            seen.add(nxt)
            if not (0 <= nxt[0] < spec.map.w and 0 <= nxt[1] < spec.map.h):
                continue
            if nxt not in wall_set:
                return nxt
            q.append(nxt)
    return None
