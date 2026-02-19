from __future__ import annotations

import json
from pathlib import Path

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
