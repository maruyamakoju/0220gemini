from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    # src/genieguard/demo_cases.py -> repo root
    return Path(__file__).resolve().parents[2]


def available_demo_cases() -> list[str]:
    return ["ctf10"]


def resolve_demo_case(case_name: str) -> tuple[Path, Path]:
    key = case_name.strip().lower()
    if key == "ctf10":
        case_dir = _repo_root() / "examples" / "demo_case_ctf10"
        return case_dir / "spec.before.json", case_dir / "seeds.json"
    raise ValueError(f"Unknown demo case: {case_name}")
