from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .runtime import RESULT_SCHEMA_VERSION


@dataclass(frozen=True)
class RunPaths:
    out_dir: str
    report_html: str = ""
    result_json: str = ""
    evidence_zip: str = ""
    spec_before: str = ""
    spec_after: str = ""
    audit_before: str = ""
    audit_after: str = ""
    patch: str = ""
    diff: str = ""


@dataclass(frozen=True)
class GateInfo:
    gate_passed: bool
    before_gate_passed: bool
    after_gate_passed: bool
    gate_thresholds: dict[str, float]
    gate_reasons: dict[str, str]


@dataclass(frozen=True)
class PipelineResult:
    gate: GateInfo
    before_metrics: dict[str, float]
    after_metrics: dict[str, float]
    selected_patch: dict[str, Any]
    short_circuit: bool
    attempt: int
    paths: RunPaths
    meta: dict[str, Any]
    attempts: list[dict[str, Any]]
    schema_version: int = RESULT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        meta = payload["meta"]
        return {
            "schema_version": payload["schema_version"],
            "gate_passed": payload["gate"]["gate_passed"],
            "before_gate_passed": payload["gate"]["before_gate_passed"],
            "after_gate_passed": payload["gate"]["after_gate_passed"],
            "gate_thresholds": payload["gate"]["gate_thresholds"],
            "gate_reasons": payload["gate"]["gate_reasons"],
            "seeds": meta.get("seeds", []),
            "policy_names": meta.get("policy_names", []),
            "before_metrics": payload["before_metrics"],
            "after_metrics": payload["after_metrics"],
            "selected_patch": payload["selected_patch"],
            "short_circuit": payload["short_circuit"],
            "attempt": payload["attempt"],
            "paths": payload["paths"],
            "meta": payload["meta"],
            "attempts": payload["attempts"],
        }
