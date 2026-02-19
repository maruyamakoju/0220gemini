from __future__ import annotations

from collections import defaultdict

from .models import AuditReport, GameLog


def _find_log(logs: list[GameLog], *, terminal_reason: str | None = None, winner: str | None = None) -> GameLog | None:
    for log in logs:
        if terminal_reason is not None and log.terminal_reason != terminal_reason:
            continue
        if winner is not None and log.winner != winner:
            continue
        return log
    return None


def compute_policy_win_rates(logs: list[GameLog]) -> dict[str, float]:
    wins: dict[str, int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)
    for log in logs:
        totals[log.policy_a] += 1
        totals[log.policy_b] += 1
        if log.winner == "A":
            wins[log.policy_a] += 1
        elif log.winner == "B":
            wins[log.policy_b] += 1
    rates: dict[str, float] = {}
    for name in totals:
        rates[name] = wins[name] / totals[name] if totals[name] else 0.0
    return dict(sorted(rates.items(), key=lambda kv: kv[0]))


def build_audit_report(logs: list[GameLog]) -> AuditReport:
    total = len(logs)
    if total == 0:
        return AuditReport(
            metrics={
                "deadlock_rate": 0.0,
                "win_rate_A": 0.0,
                "win_skew": 0.5,
                "exploit_dominance": 0.0,
            },
            policy_win_rates={},
            findings=[],
            evidence=[],
            recommendations=["No games executed."],
            reproducible=False,
        )

    deadlocks = sum(1 for x in logs if x.terminal_reason == "deadlock")
    wins_a = sum(1 for x in logs if x.winner == "A")
    wins_b = sum(1 for x in logs if x.winner == "B")
    decisive = wins_a + wins_b
    policy_rates = compute_policy_win_rates(logs)
    sorted_rates = sorted(policy_rates.values(), reverse=True)
    top1 = sorted_rates[0] if sorted_rates else 0.0
    top2 = sorted_rates[1] if len(sorted_rates) > 1 else 0.0
    exploit = max(0.0, top1 - top2)

    deadlock_rate = deadlocks / total
    win_rate_a = wins_a / decisive if decisive else 0.5
    win_skew = abs(win_rate_a - 0.5)

    metrics = {
        "deadlock_rate": round(deadlock_rate, 4),
        "win_rate_A": round(win_rate_a, 4),
        "win_skew": round(win_skew, 4),
        "exploit_dominance": round(exploit, 4),
    }

    findings: list[dict[str, str]] = []
    evidence: list[dict[str, str | int]] = []
    recommendations: list[str] = []
    next_evidence_id = 1

    if deadlock_rate > 0.01:
        eid = f"E{next_evidence_id}"
        next_evidence_id += 1
        deadlock_log = _find_log(logs, terminal_reason="deadlock")
        evidence.append(
            {
                "id": eid,
                "seed": deadlock_log.seed if deadlock_log else -1,
                "policy_a": deadlock_log.policy_a if deadlock_log else "",
                "policy_b": deadlock_log.policy_b if deadlock_log else "",
                "terminal_reason": "deadlock",
            }
        )
        findings.append(
            {
                "id": "F1",
                "type": "deadlock",
                "severity": "high",
                "evidence_ref": eid,
            }
        )
        recommendations.append("Open one choke wall or relax map bottlenecks.")

    if win_skew > 0.10:
        eid = f"E{next_evidence_id}"
        next_evidence_id += 1
        dominant_winner = "A" if win_rate_a > 0.5 else "B"
        skew_log = _find_log(logs, winner=dominant_winner)
        evidence.append(
            {
                "id": eid,
                "seed": skew_log.seed if skew_log else -1,
                "policy_a": skew_log.policy_a if skew_log else "",
                "policy_b": skew_log.policy_b if skew_log else "",
                "terminal_reason": skew_log.terminal_reason if skew_log else "",
            }
        )
        findings.append(
            {
                "id": "F2",
                "type": "spawn_or_objective_bias",
                "severity": "high",
                "evidence_ref": eid,
            }
        )
        recommendations.append("Rebalance spawn and flag distances to remove side advantage.")

    if exploit > 0.20:
        eid = f"E{next_evidence_id}"
        next_evidence_id += 1
        evidence.append({"id": eid, "seed": logs[0].seed, "policy_a": logs[0].policy_a, "policy_b": logs[0].policy_b})
        findings.append(
            {
                "id": "F3",
                "type": "exploit_dominance",
                "severity": "medium",
                "evidence_ref": eid,
            }
        )
        recommendations.append("Disrupt single-policy dominance via objective relocation.")

    if not findings:
        recommendations.append("No high-risk issues detected under current policy matrix.")

    return AuditReport(
        metrics=metrics,
        policy_win_rates=policy_rates,
        findings=findings,
        evidence=evidence,
        recommendations=recommendations,
        reproducible=True,
    )
