from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Direction = Literal["lower_is_better", "higher_is_better"]


@dataclass(frozen=True)
class MetricSpec:
    name: str
    direction: Direction
    threshold: float
    slack: float = 0.0
    min_improve: float = 0.0

    def is_passing(self, value: float) -> bool:
        if self.direction == "lower_is_better":
            return value <= (self.threshold + self.slack)
        return value >= (self.threshold - self.slack)

    def improved(self, before: float, after: float) -> bool:
        if self.direction == "lower_is_better":
            return (before - after) >= self.min_improve
        return (after - before) >= self.min_improve


@dataclass(frozen=True)
class GateSpec:
    metrics: tuple[MetricSpec, ...]

    def thresholds_dict(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for metric in self.metrics:
            if metric.direction == "lower_is_better":
                out[f"{metric.name}_max"] = metric.threshold
            else:
                out[f"{metric.name}_min"] = metric.threshold
        return out

    def evaluate(self, values: dict[str, float]) -> tuple[bool, dict[str, bool], dict[str, str]]:
        passing: dict[str, bool] = {}
        reasons: dict[str, str] = {}
        all_ok = True

        for metric in self.metrics:
            value = float(values.get(metric.name, 1e9))
            ok = metric.is_passing(value)
            passing[metric.name] = ok
            if not ok:
                all_ok = False
                reasons[metric.name] = (
                    f"{metric.name}={value} violates threshold={metric.threshold} "
                    f"(slack={metric.slack})"
                )
        return all_ok, passing, reasons

    def improvement_ok(
        self,
        before: dict[str, float],
        after: dict[str, float],
    ) -> tuple[bool, dict[str, str]]:
        ok = True
        reasons: dict[str, str] = {}
        before_pass, _, _ = self.evaluate(before)

        if before_pass:
            after_pass, _, after_reasons = self.evaluate(after)
            return after_pass, after_reasons

        for metric in self.metrics:
            b = float(before.get(metric.name, 1e9))
            a = float(after.get(metric.name, 1e9))
            failing_before = not metric.is_passing(b)

            if failing_before and not metric.improved(b, a):
                ok = False
                reasons[metric.name] = (
                    f"no improvement on failing metric: {metric.name} {b} -> {a} "
                    f"(min_improve={metric.min_improve})"
                )
                continue

            if not failing_before:
                if not metric.is_passing(a):
                    ok = False
                    reasons[metric.name] = (
                        f"introduced regression past threshold: {metric.name} {b} -> {a} "
                        f"(threshold={metric.threshold}, slack={metric.slack})"
                    )
        return ok, reasons


def default_gate_spec(exploit_threshold: float = 0.25) -> GateSpec:
    return GateSpec(
        metrics=(
            MetricSpec(
                name="deadlock_rate",
                direction="lower_is_better",
                threshold=0.01,
                slack=0.0,
                min_improve=0.01,
            ),
            MetricSpec(
                name="win_skew",
                direction="lower_is_better",
                threshold=0.10,
                slack=0.0,
                min_improve=0.01,
            ),
            MetricSpec(
                name="exploit_dominance",
                direction="lower_is_better",
                threshold=exploit_threshold,
                slack=0.0,
                min_improve=0.02,
            ),
        )
    )
