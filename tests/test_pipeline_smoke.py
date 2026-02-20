from __future__ import annotations

import json
from pathlib import Path

from genieguard.demo_cases import resolve_demo_case
from genieguard.models import PatchProposal
from genieguard.patcher import apply_patch
from genieguard.pipeline import PipelineConfig, run_pipeline
from genieguard.spec_gen import default_gamespec


def test_pipeline_improves_default_spec(tmp_path: Path) -> None:
    out_dir = tmp_path / "run"
    result = run_pipeline(
        PipelineConfig(
            seed=1337,
            seed_count=10,
            out_dir=out_dir,
            max_attempts=2,
            write_html=True,
        )
    )

    before = result["before_metrics"]
    after = result["after_metrics"]
    assert result["gate_passed"] is True
    assert after["deadlock_rate"] <= before["deadlock_rate"]
    assert after["win_skew"] <= before["win_skew"]
    assert (out_dir / "report.html").exists()
    assert (out_dir / "result.json").exists()
    assert (out_dir / "evidence.zip").exists()


def test_pipeline_short_circuit_pass_for_good_spec(tmp_path: Path) -> None:
    spec = default_gamespec(seed=1337)
    good_spec = apply_patch(
        spec,
        PatchProposal(
            patch_ops=[
                {"op": "remove_wall", "pos": [6, 5]},
                {"op": "move_flag", "team": "B", "to": [9, 0]},
                {"op": "set_param", "key": "capture_range", "value": 2},
                {"op": "set_param", "key": "deadlock_repeat", "value": 120},
            ],
            rationale="fixture",
            expected_effect={},
        ),
    )
    spec_path = tmp_path / "good_spec.json"
    spec_path.write_text(json.dumps(good_spec.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    result = run_pipeline(
        PipelineConfig(
            spec_path=spec_path,
            seed=1337,
            seed_count=10,
            out_dir=tmp_path / "good_run",
            max_attempts=2,
        )
    )

    assert result["gate_passed"] is True
    assert result["selected_patch"]["patch_ops"] == []
    assert result["attempts"][0]["short_circuit"] is True


def _assert_demo_case_red_to_green(tmp_path: Path, case_name: str) -> None:
    case = resolve_demo_case(case_name)
    result = run_pipeline(
        PipelineConfig(
            spec_path=case.spec_path,
            seeds_path=case.seeds_path,
            out_dir=tmp_path / case_name,
            max_attempts=2,
            policy_names=case.policy_names,
        )
    )
    before = result["before_metrics"]
    after = result["after_metrics"]

    before_is_red = (
        before["deadlock_rate"] > 0.01
        or before["win_skew"] > 0.10
        or before["exploit_dominance"] > 0.25
    )
    assert before_is_red is True
    assert result["gate_passed"] is True
    assert result["selected_patch"]["patch_ops"] != []
    assert after["deadlock_rate"] <= 0.01
    assert after["win_skew"] <= 0.10
    assert after["exploit_dominance"] <= 0.25


def test_fixed_demo_case_is_red_to_green(tmp_path: Path) -> None:
    _assert_demo_case_red_to_green(tmp_path, "ctf10")


def test_bias_demo_case_is_red_to_green(tmp_path: Path) -> None:
    _assert_demo_case_red_to_green(tmp_path, "ctf_bias")


def test_exploit_demo_case_is_red_to_green(tmp_path: Path) -> None:
    _assert_demo_case_red_to_green(tmp_path, "ctf_exploit")
