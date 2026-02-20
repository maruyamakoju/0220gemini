from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from genieguard.models import GameSpec
from genieguard.pipeline import PipelineConfig, run_pipeline
from genieguard.spec_gen import default_gamespec


SEEDS = [1337 + i * 17 for i in range(50)]


def _write_spec(path: Path, spec: GameSpec) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_seeds(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"seeds": SEEDS}, ensure_ascii=False, indent=2), encoding="utf-8")


def evaluate_case(tag: str, spec: GameSpec, policies: list[str] | None = None) -> dict:
    tmp = ROOT / "artifacts" / "search_cases" / tag
    spec_path = tmp / "spec.json"
    seeds_path = tmp / "seeds.json"
    _write_spec(spec_path, spec)
    _write_seeds(seeds_path)
    return run_pipeline(
        PipelineConfig(
            spec_path=spec_path,
            seeds_path=seeds_path,
            out_dir=tmp / "run",
            max_attempts=2,
            policy_names=policies,
            write_html=False,
        )
    )


def search_bias(n: int = 120) -> None:
    rng = random.Random(7)
    base = default_gamespec(1337)
    base.map.walls = []
    base.params.deadlock_repeat = 120

    found = []
    for i in range(n):
        spec = base.clone()
        ax = rng.randint(5, 9)
        ay = rng.randint(0, 4)
        bx = rng.randint(0, 4)
        by = rng.randint(0, 4)
        if (bx, by) == spec.spawns["A"]:
            by = (by + 1) % spec.map.h
        spec.map.flags["A"] = (ax, ay)
        spec.map.flags["B"] = (bx, by)

        result = evaluate_case(f"bias_{i}", spec)
        before = result["before_metrics"]
        after = result["after_metrics"]
        if (
            result["gate_passed"]
            and result["selected_patch"]["patch_ops"]
            and before["win_skew"] > 0.1
            and after["win_skew"] <= 0.1
        ):
            found.append((before["win_skew"], after["win_skew"], spec.to_dict()))
            print("FOUND bias", before["win_skew"], "->", after["win_skew"])
            if len(found) >= 3:
                break
    print("bias found:", len(found))
    if found:
        out = ROOT / "artifacts" / "search_cases" / "bias_found.json"
        out.write_text(json.dumps(found[0][2], ensure_ascii=False, indent=2), encoding="utf-8")
        print("saved", out)


def search_exploit(n: int = 180) -> None:
    rng = random.Random(11)
    base = default_gamespec(1337)
    base.params.deadlock_repeat = 120
    base.map.walls = []
    policies = ["greedy_shortest_path", "blocker", "random_epsilon"]

    found = []
    for i in range(n):
        spec = base.clone()

        # random sparse walls + centered objectives to induce policy-specific performance.
        walls = set()
        for _ in range(rng.randint(5, 14)):
            x = rng.randint(1, 8)
            y = rng.randint(1, 8)
            walls.add((x, y))
        walls.discard(spec.spawns["A"])
        walls.discard(spec.spawns["B"])
        spec.map.walls = sorted(walls)
        spec.map.flags["A"] = (rng.randint(0, 3), rng.randint(6, 9))
        spec.map.flags["B"] = (rng.randint(6, 9), rng.randint(0, 3))
        if spec.map.flags["A"] in walls or spec.map.flags["B"] in walls:
            continue

        result = evaluate_case(f"exploit_{i}", spec, policies=policies)
        before = result["before_metrics"]
        after = result["after_metrics"]
        if (
            result["gate_passed"]
            and result["selected_patch"]["patch_ops"]
            and before["exploit_dominance"] > 0.2
            and after["exploit_dominance"] <= 0.25
        ):
            found.append((before["exploit_dominance"], after["exploit_dominance"], spec.to_dict()))
            print("FOUND exploit", before["exploit_dominance"], "->", after["exploit_dominance"])
            if len(found) >= 3:
                break
    print("exploit found:", len(found))
    if found:
        out = ROOT / "artifacts" / "search_cases" / "exploit_found.json"
        out.write_text(
            json.dumps({"spec": found[0][2], "policies": policies}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("saved", out)


if __name__ == "__main__":
    search_bias()
    search_exploit()
