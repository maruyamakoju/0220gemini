from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from genieguard.audit import build_audit_report
from genieguard.models import PatchProposal
from genieguard.patcher import apply_patch
from genieguard.selfplay import run_self_play
from genieguard.spec_gen import default_gamespec


def evaluate(label: str, ops: list[dict]) -> None:
    spec = default_gamespec(1337)
    seeds = [1337 + i * 17 for i in range(20)]
    before = build_audit_report(run_self_play(spec, seeds))
    patched = apply_patch(
        spec,
        PatchProposal(
            patch_ops=ops,
            rationale=label,
            expected_effect={"deadlock_rate": "?", "win_skew": "?", "exploit_dominance": "?"},
        ),
    )
    after = build_audit_report(run_self_play(patched, seeds))
    print(label)
    print("before", json.dumps(before.metrics, ensure_ascii=False))
    print("after ", json.dumps(after.metrics, ensure_ascii=False))
    print()


def main() -> int:
    evaluate("remove_wall", [{"op": "remove_wall", "pos": [6, 5]}])
    evaluate(
        "rebalance_side_b",
        [
            {"op": "move_spawn", "team": "B", "to": [9, 9]},
            {"op": "move_flag", "team": "B", "to": [9, 0]},
        ],
    )
    evaluate(
        "capture_range_1",
        [
            {"op": "set_param", "key": "capture_range", "value": 1},
        ],
    )
    evaluate(
        "combo",
        [
            {"op": "remove_wall", "pos": [6, 5]},
            {"op": "move_flag", "team": "B", "to": [9, 0]},
            {"op": "set_param", "key": "capture_range", "value": 1},
        ],
    )
    evaluate(
        "combo_capture2",
        [
            {"op": "remove_wall", "pos": [6, 5]},
            {"op": "move_flag", "team": "B", "to": [9, 0]},
            {"op": "set_param", "key": "capture_range", "value": 2},
        ],
    )
    evaluate(
        "combo_capture2_deadlock12",
        [
            {"op": "remove_wall", "pos": [6, 5]},
            {"op": "move_flag", "team": "B", "to": [9, 0]},
            {"op": "set_param", "key": "capture_range", "value": 2},
            {"op": "set_param", "key": "deadlock_repeat", "value": 12},
        ],
    )
    evaluate(
        "combo_capture2_deadlock999",
        [
            {"op": "remove_wall", "pos": [6, 5]},
            {"op": "move_flag", "team": "B", "to": [9, 0]},
            {"op": "set_param", "key": "capture_range", "value": 2},
            {"op": "set_param", "key": "deadlock_repeat", "value": 999},
        ],
    )
    evaluate(
        "rebalance_plus_deadlock999",
        [
            {"op": "move_spawn", "team": "B", "to": [9, 9]},
            {"op": "move_flag", "team": "B", "to": [9, 0]},
            {"op": "set_param", "key": "deadlock_repeat", "value": 999},
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
