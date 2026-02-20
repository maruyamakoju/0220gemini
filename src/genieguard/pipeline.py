from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .audit import build_audit_report
from .io_utils import read_json, write_json
from .models import GameSpec, PatchProposal
from .patcher import suggest_patch_candidates
from .policies import default_policy_names
from .regression import (
    DEFAULT_EXPLOIT_THRESHOLD,
    RegressionResult,
    check_reproducible,
    gate_limits_ok,
    report_passes_gate,
    run_regression_gate,
)
from .reporting import write_evidence_zip, write_run_artifacts
from .selfplay import run_self_play
from .spec_gen import generate_gamespec


@dataclass
class PipelineConfig:
    prompt: str = "Generate a 2D CTF map that might have balancing risks."
    seed: int = 1337
    seed_count: int = 50
    seeds_path: Path | None = None
    spec_path: Path | None = None
    out_dir: Path | None = None
    policy_names: list[str] | None = None
    use_gemini: bool = False
    max_attempts: int = 2
    write_html: bool = True


def _seed_set(base_seed: int, n: int) -> list[int]:
    return [base_seed + i * 17 for i in range(n)]


def _load_seeds(path: Path) -> list[int]:
    payload = read_json(path)
    raw = payload
    if isinstance(payload, dict):
        raw = payload.get("seeds")
    if not isinstance(raw, list):
        raise ValueError(f"Invalid seeds payload in {path}")
    seeds = [int(x) for x in raw]
    if not seeds:
        raise ValueError(f"Seeds list is empty in {path}")
    return seeds


def _load_or_generate_spec(config: PipelineConfig) -> GameSpec:
    if config.spec_path is not None:
        data = read_json(config.spec_path)
        return GameSpec.from_dict(data)
    return generate_gamespec(prompt=config.prompt, seed=config.seed, use_gemini=config.use_gemini)


def run_pipeline(config: PipelineConfig) -> dict[str, Any]:
    policy_names = config.policy_names or default_policy_names()
    seeds = _load_seeds(config.seeds_path) if config.seeds_path is not None else _seed_set(config.seed, config.seed_count)
    spec = _load_or_generate_spec(config)

    logs_before = run_self_play(spec=spec, seeds=seeds, policy_names=policy_names)
    report_before = build_audit_report(logs_before)
    report_before.reproducible = check_reproducible(spec, seeds, policy_names)
    before_gate_ok = report_passes_gate(report_before)

    if before_gate_ok:
        no_patch = PatchProposal(
            patch_ops=[],
            rationale="Spec already satisfies CI gate thresholds; patch not required.",
            expected_effect={
                "deadlock_rate": "same",
                "win_skew": "same",
                "exploit_dominance": "same",
            },
        )
        regression = RegressionResult(
            passed=True,
            selected_patch=no_patch,
            patched_spec=spec.clone(),
            after_report=report_before,
            after_logs=logs_before,
            attempts=[
                {
                    "attempt": 0,
                    "short_circuit": True,
                    "patch": no_patch.to_dict(),
                    "metrics_after": report_before.metrics,
                    "reproducible": report_before.reproducible,
                    "gate_limits_ok": True,
                    "improved_vs_before": True,
                    "passed": True,
                }
            ],
        )
    else:
        candidates = suggest_patch_candidates(spec=spec, report=report_before, use_gemini=config.use_gemini)
        regression = run_regression_gate(
            spec=spec,
            before_report=report_before,
            seeds=seeds,
            policy_names=policy_names,
            candidates=candidates,
            max_attempts=config.max_attempts,
        )
    after_gate_ok = gate_limits_ok(
        metrics=regression.after_report.metrics,
        reproducible=regression.after_report.reproducible,
        exploit_threshold=DEFAULT_EXPLOIT_THRESHOLD,
    )

    out_dir = config.out_dir
    if out_dir is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("artifacts") / f"run_{stamp}"

    paths = write_run_artifacts(
        out_dir=out_dir,
        prompt=config.prompt,
        spec_before=spec,
        logs_before=logs_before,
        report_before=report_before,
        regression=regression,
        write_html=config.write_html,
    )

    result = {
        "gate_passed": regression.passed,
        "seeds": seeds,
        "policy_names": policy_names,
        "before_metrics": report_before.metrics,
        "after_metrics": regression.after_report.metrics,
        "before_gate_passed": before_gate_ok,
        "after_gate_passed": after_gate_ok,
        "gate_thresholds": {
            "deadlock_rate_max": 0.01,
            "win_skew_max": 0.10,
            "exploit_dominance_max": DEFAULT_EXPLOIT_THRESHOLD,
        },
        "selected_patch": regression.selected_patch.to_dict(),
        "attempts": regression.attempts,
        "paths": paths,
    }
    result_path = out_dir / "result.json"
    write_json(result_path, result)
    evidence_zip_path = write_evidence_zip(out_dir)
    result["paths"]["result"] = str(result_path)
    result["paths"]["evidence_zip"] = str(evidence_zip_path)
    write_json(result_path, result)
    return result
