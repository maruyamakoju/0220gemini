from __future__ import annotations

from genieguard.gate import default_gate_spec


def test_gate_evaluate_thresholds() -> None:
    gate = default_gate_spec()
    ok, passing, reasons = gate.evaluate(
        {
            "deadlock_rate": 0.02,
            "win_skew": 0.04,
            "exploit_dominance": 0.10,
        }
    )
    assert ok is False
    assert passing["deadlock_rate"] is False
    assert "deadlock_rate" in reasons


def test_gate_improvement_requires_failing_metrics_to_improve() -> None:
    gate = default_gate_spec()
    before = {
        "deadlock_rate": 0.20,
        "win_skew": 0.15,
        "exploit_dominance": 0.20,
    }
    after = {
        "deadlock_rate": 0.10,
        "win_skew": 0.11,
        "exploit_dominance": 0.20,
    }
    ok, reasons = gate.improvement_ok(before, after)
    assert ok is True
    assert reasons == {}
