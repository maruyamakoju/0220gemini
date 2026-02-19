from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .audit import build_audit_report
from .models import AuditReport, GameLog, GameSpec, PatchProposal
from .patcher import apply_patch
from .selfplay import run_self_play

DEFAULT_EXPLOIT_THRESHOLD = 0.25


@dataclass
class RegressionResult:
    passed: bool
    selected_patch: PatchProposal
    patched_spec: GameSpec
    after_report: AuditReport
    after_logs: list[GameLog]
    attempts: list[dict[str, Any]]


def check_reproducible(spec: GameSpec, seeds: list[int], policy_names: list[str]) -> bool:
    probe_seeds = seeds[: min(4, len(seeds))]
    a = run_self_play(spec=spec, seeds=probe_seeds, policy_names=policy_names)
    b = run_self_play(spec=spec, seeds=probe_seeds, policy_names=policy_names)
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        left = (x.seed, x.policy_a, x.policy_b, x.winner, x.terminal_reason, x.turns, x.trace)
        right = (y.seed, y.policy_a, y.policy_b, y.winner, y.terminal_reason, y.turns, y.trace)
        if left != right:
            return False
    return True


def gate_limits_ok(
    metrics: dict[str, float],
    reproducible: bool,
    exploit_threshold: float = DEFAULT_EXPLOIT_THRESHOLD,
) -> bool:
    return (
        metrics.get("deadlock_rate", 1.0) <= 0.01
        and metrics.get("win_skew", 1.0) <= 0.10
        and metrics.get("exploit_dominance", 1.0) <= exploit_threshold
        and reproducible
    )


def report_passes_gate(
    report: AuditReport,
    exploit_threshold: float = DEFAULT_EXPLOIT_THRESHOLD,
) -> bool:
    return gate_limits_ok(
        metrics=report.metrics,
        reproducible=report.reproducible,
        exploit_threshold=exploit_threshold,
    )


def _gate_score(metrics: dict[str, float]) -> float:
    return (
        metrics.get("deadlock_rate", 1.0)
        + metrics.get("win_skew", 1.0)
        + metrics.get("exploit_dominance", 1.0)
    )


def _is_improved(before: AuditReport, after: AuditReport) -> bool:
    b = before.metrics
    a = after.metrics
    not_worse = (
        a.get("deadlock_rate", 1.0) <= b.get("deadlock_rate", 1.0)
        and a.get("win_skew", 1.0) <= b.get("win_skew", 1.0)
        and a.get("exploit_dominance", 1.0) <= b.get("exploit_dominance", 1.0)
    )
    strictly_better = (
        a.get("deadlock_rate", 1.0) < b.get("deadlock_rate", 1.0)
        or a.get("win_skew", 1.0) < b.get("win_skew", 1.0)
        or a.get("exploit_dominance", 1.0) < b.get("exploit_dominance", 1.0)
    )
    return not_worse and strictly_better


def run_regression_gate(
    spec: GameSpec,
    before_report: AuditReport,
    seeds: list[int],
    policy_names: list[str],
    candidates: list[PatchProposal],
    max_attempts: int = 2,
    exploit_threshold: float = DEFAULT_EXPLOIT_THRESHOLD,
) -> RegressionResult:
    attempts: list[dict[str, Any]] = []
    best_candidate: PatchProposal | None = None
    best_spec: GameSpec | None = None
    best_report: AuditReport | None = None
    best_logs: list[GameLog] | None = None
    best_score = float("inf")

    for idx, candidate in enumerate(candidates[:max_attempts], start=1):
        patched_spec = apply_patch(spec, candidate)
        after_logs = run_self_play(spec=patched_spec, seeds=seeds, policy_names=policy_names)
        after_report = build_audit_report(after_logs)
        after_report.reproducible = check_reproducible(patched_spec, seeds, policy_names)

        metrics = after_report.metrics
        gate_ok = gate_limits_ok(
            metrics=metrics,
            reproducible=after_report.reproducible,
            exploit_threshold=exploit_threshold,
        )
        improved = _is_improved(before_report, after_report)
        passed = gate_ok and improved

        attempts.append(
            {
                "attempt": idx,
                "patch": candidate.to_dict(),
                "metrics_after": metrics,
                "reproducible": after_report.reproducible,
                "gate_limits_ok": gate_ok,
                "improved_vs_before": improved,
                "passed": passed,
            }
        )

        score = _gate_score(metrics)
        if score < best_score:
            best_candidate = candidate
            best_spec = patched_spec
            best_report = after_report
            best_logs = after_logs
            best_score = score

        if passed:
            return RegressionResult(
                passed=True,
                selected_patch=candidate,
                patched_spec=patched_spec,
                after_report=after_report,
                after_logs=after_logs,
                attempts=attempts,
            )

    assert best_candidate is not None
    assert best_spec is not None
    assert best_report is not None
    assert best_logs is not None
    return RegressionResult(
        passed=False,
        selected_patch=best_candidate,
        patched_spec=best_spec,
        after_report=best_report,
        after_logs=best_logs,
        attempts=attempts,
    )
