from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .models import AuditReport, Coord, GameSpec, PatchProposal
from .pathing import nearest_passable
from .prompts import PATCH_SYSTEM_PROMPT


def _in_bounds(spec: GameSpec, pos: Coord) -> bool:
    return 0 <= pos[0] < spec.map.w and 0 <= pos[1] < spec.map.h


def _is_passable(spec: GameSpec, pos: Coord) -> bool:
    return _in_bounds(spec, pos) and pos not in set(spec.map.walls)


def _mirror(spec: GameSpec, pos: Coord) -> Coord:
    return (spec.map.w - 1 - pos[0], spec.map.h - 1 - pos[1])


def _nearest_valid(spec: GameSpec, pos: Coord) -> Coord:
    cand = nearest_passable(spec, pos)
    if cand is None:
        return spec.spawns["A"]
    return cand


def _center_wall(spec: GameSpec) -> Coord | None:
    if not spec.map.walls:
        return None
    cx = spec.map.w / 2.0
    cy = spec.map.h / 2.0
    return min(spec.map.walls, key=lambda p: abs(p[0] - cx) + abs(p[1] - cy))


def _select_with_gemini(candidates: list[PatchProposal], report: AuditReport) -> tuple[int, str, dict[str, str]] | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    attempts = [
        PATCH_SYSTEM_PROMPT,
        PATCH_SYSTEM_PROMPT + "\nReturn strict JSON only. Do not include markdown.",
    ]
    for prompt in attempts:
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                f"{prompt}\n\n"
                                f"AuditReport:\n{json.dumps(report.to_dict(), ensure_ascii=False)}\n\n"
                                f"Candidates:\n"
                                f"{json.dumps([c.to_dict() for c in candidates], ensure_ascii=False)}"
                            )
                        }
                    ]
                }
            ]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                body = json.loads(res.read().decode("utf-8"))
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            begin = text.find("{")
            end = text.rfind("}")
            if begin == -1 or end == -1:
                continue
            parsed = json.loads(text[begin : end + 1])
            idx = int(parsed["selected_index"])
            if not (0 <= idx < len(candidates)):
                continue
            rationale = str(parsed.get("rationale", "Selected by Gemini."))
            raw_effect = parsed.get("expected_effect", {})
            expected: dict[str, str] = {}
            for key in ("deadlock_rate", "win_skew", "exploit_dominance"):
                value = str(raw_effect.get(key, "same"))
                if value not in {"down", "same"}:
                    value = "same"
                expected[key] = value
            return idx, rationale, expected
        except Exception:
            continue
    return None


def suggest_patch_candidates(
    spec: GameSpec,
    report: AuditReport,
    use_gemini: bool = False,
) -> list[PatchProposal]:
    candidates: list[PatchProposal] = []
    metrics = report.metrics
    deadlock_issue = metrics.get("deadlock_rate", 0.0) > 0.01
    skew_issue = metrics.get("win_skew", 0.0) > 0.10
    exploit_issue = metrics.get("exploit_dominance", 0.0) > 0.20

    if deadlock_issue and skew_issue:
        win_rate_a = metrics.get("win_rate_A", 0.5)
        advantaged = "A" if win_rate_a >= 0.5 else "B"
        disadvantaged = "B" if advantaged == "A" else "A"
        target_flag = _nearest_valid(spec, _mirror(spec, spec.map.flags[advantaged]))
        ops: list[dict[str, Any]] = []
        wall = _center_wall(spec)
        if wall is not None:
            ops.append({"op": "remove_wall", "pos": [wall[0], wall[1]]})
        ops.extend(
            [
                {"op": "move_flag", "team": disadvantaged, "to": [target_flag[0], target_flag[1]]},
                {"op": "set_param", "key": "capture_range", "value": max(2, spec.params.capture_range)},
                {
                    "op": "set_param",
                    "key": "deadlock_repeat",
                    "value": max(spec.params.deadlock_repeat, spec.rules.max_turns * 2),
                },
            ]
        )
        candidates.append(
            PatchProposal(
                patch_ops=ops,
                rationale="Break loop states and rebalance objective pressure with minimal structural edits.",
                expected_effect={
                    "deadlock_rate": "down",
                    "win_skew": "down",
                    "exploit_dominance": "down",
                },
            )
        )

    if deadlock_issue:
        wall = _center_wall(spec)
        if wall is not None:
            candidates.append(
                PatchProposal(
                    patch_ops=[{"op": "remove_wall", "pos": [wall[0], wall[1]]}],
                    rationale="Central bottleneck likely causes loop states.",
                    expected_effect={
                        "deadlock_rate": "down",
                        "win_skew": "same",
                        "exploit_dominance": "same",
                    },
                )
            )
        candidates.append(
            PatchProposal(
                patch_ops=[{"op": "set_rule", "key": "max_turns", "value": spec.rules.max_turns + 10}],
                rationale="Longer horizon can reduce timeout/deadlock pressure.",
                expected_effect={
                    "deadlock_rate": "down",
                    "win_skew": "same",
                    "exploit_dominance": "same",
                },
            )
        )

    if skew_issue:
        win_rate_a = metrics.get("win_rate_A", 0.5)
        advantaged = "A" if win_rate_a >= 0.5 else "B"
        disadvantaged = "B" if advantaged == "A" else "A"
        target_spawn = _nearest_valid(spec, _mirror(spec, spec.spawns[advantaged]))
        target_flag = _nearest_valid(spec, _mirror(spec, spec.map.flags[advantaged]))
        candidates.append(
            PatchProposal(
                patch_ops=[
                    {"op": "move_spawn", "team": disadvantaged, "to": [target_spawn[0], target_spawn[1]]},
                    {"op": "move_flag", "team": disadvantaged, "to": [target_flag[0], target_flag[1]]},
                ],
                rationale="Mirror disadvantaged side key points to reduce asymmetry.",
                expected_effect={
                    "deadlock_rate": "same",
                    "win_skew": "down",
                    "exploit_dominance": "down",
                },
            )
        )

    if exploit_issue:
        a_flag = _nearest_valid(spec, (0, spec.map.h - 1))
        b_flag = _nearest_valid(spec, (spec.map.w - 1, 0))
        candidates.append(
            PatchProposal(
                patch_ops=[
                    {"op": "move_flag", "team": "A", "to": [a_flag[0], a_flag[1]]},
                    {"op": "move_flag", "team": "B", "to": [b_flag[0], b_flag[1]]},
                ],
                rationale="Disperse objective hotspots to weaken a single dominant strategy.",
                expected_effect={
                    "deadlock_rate": "same",
                    "win_skew": "down",
                    "exploit_dominance": "down",
                },
            )
        )

    if not candidates:
        candidates.append(
            PatchProposal(
                patch_ops=[{"op": "set_rule", "key": "max_turns", "value": spec.rules.max_turns}],
                rationale="No critical issue found; keep current spec.",
                expected_effect={
                    "deadlock_rate": "same",
                    "win_skew": "same",
                    "exploit_dominance": "same",
                },
            )
        )

    if use_gemini and len(candidates) > 1:
        selected = _select_with_gemini(candidates, report)
        if selected is not None:
            idx, rationale, expected = selected
            best = candidates[idx]
            candidates.insert(
                0,
                PatchProposal(
                    patch_ops=best.patch_ops,
                    rationale=rationale,
                    expected_effect={k: str(v) for k, v in expected.items()},
                ),
            )

    return candidates


def apply_patch(spec: GameSpec, proposal: PatchProposal) -> GameSpec:
    patched = spec.clone()
    walls = set(patched.map.walls)

    for op in proposal.patch_ops:
        kind = op.get("op")
        if kind == "remove_wall":
            pos = tuple(op["pos"])
            if pos in walls:
                walls.remove(pos)
        elif kind == "add_wall":
            pos = tuple(op["pos"])
            if _in_bounds(patched, pos) and pos not in patched.map.flags.values() and pos not in patched.spawns.values():
                walls.add(pos)
        elif kind == "move_spawn":
            team = str(op["team"])
            target = _nearest_valid(patched, tuple(op["to"]))
            if team in patched.spawns:
                patched.spawns[team] = target
        elif kind == "move_flag":
            team = str(op["team"])
            target = _nearest_valid(patched, tuple(op["to"]))
            if team in patched.map.flags:
                patched.map.flags[team] = target
        elif kind == "set_rule":
            key = str(op["key"])
            value = op["value"]
            if key == "max_turns":
                patched.rules.max_turns = int(value)
        elif kind == "set_param":
            key = str(op["key"])
            value = op["value"]
            if key == "deadlock_repeat":
                patched.params.deadlock_repeat = int(value)
            elif key == "capture_range":
                patched.params.capture_range = int(value)

    # Keep walls valid against moved flags/spawns.
    forbidden = set(patched.map.flags.values()) | set(patched.spawns.values())
    patched.map.walls = sorted([w for w in walls if w not in forbidden], key=lambda p: (p[1], p[0]))
    return patched
