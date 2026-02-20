from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .artifacts import ArtifactLayout, write_evidence_zip
from .audit import build_audit_report
from .gate import GateSpec, default_gate_spec
from .io_utils import read_json, write_json
from .models import AuditReport, GameLog, GameSpec, PatchProposal
from .patcher import suggest_patch_candidates
from .policies import default_policy_names
from .regression import RegressionResult, check_reproducible, run_regression_gate
from .reporting import write_run_artifacts
from .results import GateInfo, PipelineResult, RunPaths
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
    gate_spec: GateSpec | None = None


@dataclass
class PipelineCoreOutcome:
    prompt: str
    spec: GameSpec
    seeds: list[int]
    policy_names: list[str]
    logs_before: list[GameLog]
    report_before: AuditReport
    regression: RegressionResult
    gate_spec: GateSpec
    before_gate_passed: bool
    after_gate_passed: bool
    gate_reasons: dict[str, str]


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


def run_pipeline_core(config: PipelineConfig) -> PipelineCoreOutcome:
    policy_names = config.policy_names or default_policy_names()
    seeds = _load_seeds(config.seeds_path) if config.seeds_path is not None else _seed_set(config.seed, config.seed_count)
    spec = _load_or_generate_spec(config)
    gate_spec = config.gate_spec or default_gate_spec()

    logs_before = run_self_play(spec=spec, seeds=seeds, policy_names=policy_names)
    report_before = build_audit_report(logs_before)
    report_before.reproducible = check_reproducible(spec, seeds, policy_names)
    before_gate_raw, _, before_gate_reasons = gate_spec.evaluate(report_before.metrics)
    before_gate_passed = before_gate_raw and report_before.reproducible
    if not report_before.reproducible:
        before_gate_reasons["reproducible"] = "reproducibility check failed"

    if before_gate_passed:
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
                    "gate_reasons": {},
                    "improved_vs_before": True,
                    "improvement_reasons": {},
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
            gate_spec=gate_spec,
        )

    after_gate_raw, _, after_gate_reasons = gate_spec.evaluate(regression.after_report.metrics)
    after_gate_passed = after_gate_raw and regression.after_report.reproducible
    if not regression.after_report.reproducible:
        after_gate_reasons["reproducible"] = "reproducibility check failed"

    gate_reasons = dict(after_gate_reasons)
    if regression.attempts:
        last = regression.attempts[-1]
        if not last.get("improved_vs_before", True):
            for key, value in (last.get("improvement_reasons", {}) or {}).items():
                gate_reasons[f"improvement:{key}"] = str(value)

    return PipelineCoreOutcome(
        prompt=config.prompt,
        spec=spec,
        seeds=seeds,
        policy_names=policy_names,
        logs_before=logs_before,
        report_before=report_before,
        regression=regression,
        gate_spec=gate_spec,
        before_gate_passed=before_gate_passed,
        after_gate_passed=after_gate_passed,
        gate_reasons=gate_reasons,
    )


def persist_pipeline_result(outcome: PipelineCoreOutcome, config: PipelineConfig) -> PipelineResult:
    out_dir = config.out_dir
    if out_dir is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("artifacts") / f"run_{stamp}"

    paths = write_run_artifacts(
        out_dir=out_dir,
        prompt=outcome.prompt,
        spec_before=outcome.spec,
        logs_before=outcome.logs_before,
        report_before=outcome.report_before,
        regression=outcome.regression,
        write_html=config.write_html,
    )

    layout = ArtifactLayout(out_dir=out_dir)
    run_paths = RunPaths(
        out_dir=str(out_dir),
        report_html=paths.get("report_html", ""),
        result_json=str(layout.result_json),
        evidence_zip=str(layout.evidence_zip),
        spec_before=paths.get("spec_before", ""),
        spec_after=paths.get("spec_after", ""),
        audit_before=paths.get("audit_before", ""),
        audit_after=paths.get("audit_after", ""),
        patch=paths.get("patch", ""),
        diff=paths.get("diff", ""),
    )

    attempt = 0
    short_circuit = False
    if outcome.regression.attempts:
        attempt = int(outcome.regression.attempts[-1].get("attempt", 0))
        short_circuit = bool(outcome.regression.attempts[0].get("short_circuit", False))

    gate = GateInfo(
        gate_passed=bool(outcome.regression.passed),
        before_gate_passed=bool(outcome.before_gate_passed),
        after_gate_passed=bool(outcome.after_gate_passed),
        gate_thresholds=outcome.gate_spec.thresholds_dict(),
        gate_reasons=outcome.gate_reasons,
    )
    result = PipelineResult(
        gate=gate,
        before_metrics=outcome.report_before.metrics,
        after_metrics=outcome.regression.after_report.metrics,
        selected_patch=outcome.regression.selected_patch.to_dict(),
        short_circuit=short_circuit,
        attempt=attempt,
        paths=run_paths,
        meta={
            "prompt": outcome.prompt,
            "policy_names": outcome.policy_names,
            "seeds": outcome.seeds,
            "reproducible_before": bool(outcome.report_before.reproducible),
            "reproducible_after": bool(outcome.regression.after_report.reproducible),
        },
        attempts=outcome.regression.attempts,
    )

    write_json(layout.result_json, result.to_dict())
    write_evidence_zip(layout)
    return result


def run_pipeline_result(config: PipelineConfig) -> PipelineResult:
    outcome = run_pipeline_core(config)
    return persist_pipeline_result(outcome=outcome, config=config)


def run_pipeline(config: PipelineConfig) -> dict[str, Any]:
    return run_pipeline_result(config).to_dict()
