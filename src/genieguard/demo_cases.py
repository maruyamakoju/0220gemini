from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DemoCaseConfig:
    name: str
    spec_path: Path
    seeds_path: Path
    policy_names: list[str] | None = None


def _repo_root() -> Path:
    # src/genieguard/demo_cases.py -> repo root
    return Path(__file__).resolve().parents[2]


def _case_map() -> dict[str, DemoCaseConfig]:
    root = _repo_root() / "examples"
    return {
        "ctf10": DemoCaseConfig(
            name="ctf10",
            spec_path=root / "demo_case_ctf10" / "spec.before.json",
            seeds_path=root / "demo_case_ctf10" / "seeds.json",
        ),
        "ctf_deadlock": DemoCaseConfig(
            name="ctf_deadlock",
            spec_path=root / "demo_case_ctf10" / "spec.before.json",
            seeds_path=root / "demo_case_ctf10" / "seeds.json",
        ),
        "ctf_bias": DemoCaseConfig(
            name="ctf_bias",
            spec_path=root / "demo_case_ctf_bias" / "spec.before.json",
            seeds_path=root / "demo_case_ctf_bias" / "seeds.json",
        ),
        "ctf_exploit": DemoCaseConfig(
            name="ctf_exploit",
            spec_path=root / "demo_case_ctf_exploit" / "spec.before.json",
            seeds_path=root / "demo_case_ctf_exploit" / "seeds.json",
            policy_names=["greedy_shortest_path", "blocker", "random_epsilon"],
        ),
    }


def available_demo_cases() -> list[str]:
    return sorted(_case_map().keys())


def resolve_demo_case(case_name: str) -> DemoCaseConfig:
    key = case_name.strip().lower()
    cases = _case_map()
    if key in cases:
        return cases[key]
    raise ValueError(f"Unknown demo case: {case_name}. Available: {', '.join(sorted(cases.keys()))}")
