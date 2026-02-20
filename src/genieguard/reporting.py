from __future__ import annotations

import copy
import difflib
import json
from collections import Counter
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from .io_utils import ensure_dir, write_json, write_ndjson, write_text
from .models import AuditReport, GameLog, GameSpec
from .regression import RegressionResult


def _spec_diff(before: GameSpec, after: GameSpec) -> str:
    left = json.dumps(before.to_dict(), ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    right = json.dumps(after.to_dict(), ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    diff = difflib.unified_diff(left, right, fromfile="spec.before.json", tofile="spec.after.json", lineterm="")
    return "\n".join(diff)


def _trace_text(log: GameLog) -> str:
    lines = [
        f"seed={log.seed}",
        f"policy_a={log.policy_a}",
        f"policy_b={log.policy_b}",
        f"winner={log.winner}",
        f"terminal_reason={log.terminal_reason}",
        f"turns={log.turns}",
        "",
        "trace:",
    ]
    lines.extend(log.trace)
    if log.events:
        lines.append("")
        lines.append("events:")
        lines.extend(log.events)
    return "\n".join(lines)


def _attach_evidence(report: AuditReport, logs: list[GameLog], evidence_dir: Path, prefix: str) -> AuditReport:
    out = copy.deepcopy(report)
    for ev in out.evidence:
        seed = int(ev.get("seed", -1))
        policy_a = str(ev.get("policy_a", ""))
        policy_b = str(ev.get("policy_b", ""))
        matched = None
        for log in logs:
            if log.seed != seed:
                continue
            if policy_a and log.policy_a != policy_a:
                continue
            if policy_b and log.policy_b != policy_b:
                continue
            matched = log
            break
        if matched is None:
            continue
        file_name = f"{prefix}_{ev['id']}_seed{matched.seed}.trace.txt"
        file_path = evidence_dir / file_name
        write_text(file_path, _trace_text(matched))
        ev["trace_ref"] = str(Path("evidence") / file_name)
    return out


def _metric_compare(before: AuditReport, after: AuditReport) -> dict[str, Any]:
    keys = ["deadlock_rate", "win_skew", "exploit_dominance"]
    compare: dict[str, Any] = {}
    for k in keys:
        b = float(before.metrics.get(k, 0.0))
        a = float(after.metrics.get(k, 0.0))
        compare[k] = {
            "before": round(b, 4),
            "after": round(a, 4),
            "delta": round(a - b, 4),
            "improved": a < b,
        }
    return compare


def _reason_breakdown(logs: list[GameLog]) -> dict[str, dict[str, float]]:
    reasons = ("deadlock", "timeout", "capture", "draw")
    counts = Counter(log.terminal_reason for log in logs)
    total = len(logs) if logs else 1
    out: dict[str, dict[str, float]] = {}
    for reason in reasons:
        c = float(counts.get(reason, 0))
        out[reason] = {
            "count": c,
            "rate": round(c / total, 4),
        }
    return out


def _worst_case(logs: list[GameLog]) -> GameLog | None:
    if not logs:
        return None
    reason_rank = {"deadlock": 4, "timeout": 3, "draw": 2, "capture": 1}
    return max(logs, key=lambda x: (reason_rank.get(x.terminal_reason, 0), x.turns))


def _write_worst_trace(evidence_dir: Path, prefix: str, log: GameLog | None) -> dict[str, Any]:
    if log is None:
        return {}
    file_name = f"{prefix}_worst_seed{log.seed}_{log.policy_a}_vs_{log.policy_b}.trace.txt"
    file_path = evidence_dir / file_name
    write_text(file_path, _trace_text(log))
    return {
        "seed": log.seed,
        "policy_a": log.policy_a,
        "policy_b": log.policy_b,
        "winner": log.winner,
        "terminal_reason": log.terminal_reason,
        "turns": log.turns,
        "trace_ref": str(Path("evidence") / file_name),
    }


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _render_reason_rows(
    before_reasons: dict[str, dict[str, float]],
    after_reasons: dict[str, dict[str, float]],
) -> str:
    rows = []
    for reason in ("deadlock", "timeout", "capture", "draw"):
        b = before_reasons.get(reason, {"count": 0.0, "rate": 0.0})
        a = after_reasons.get(reason, {"count": 0.0, "rate": 0.0})
        b_rate = float(b["rate"]) * 100.0
        a_rate = float(a["rate"]) * 100.0
        rows.append(
            "<tr>"
            f"<td>{reason}</td>"
            f"<td>{int(b['count'])} ({b_rate:.1f}%)</td>"
            f"<td>{int(a['count'])} ({a_rate:.1f}%)</td>"
            f"<td><div class='bar before' style='width:{b_rate:.1f}%'></div></td>"
            f"<td><div class='bar after' style='width:{a_rate:.1f}%'></div></td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_policy_rows(before: AuditReport, after: AuditReport) -> str:
    names = sorted(set(before.policy_win_rates.keys()) | set(after.policy_win_rates.keys()))
    rows = []
    for name in names:
        b = float(before.policy_win_rates.get(name, 0.0))
        a = float(after.policy_win_rates.get(name, 0.0))
        delta = a - b
        color = "#166534" if delta < 0 else "#1f2933"
        rows.append(
            "<tr>"
            f"<td>{name}</td>"
            f"<td>{b:.4f}</td>"
            f"<td>{a:.4f}</td>"
            f"<td style='color:{color}'>{delta:+.4f}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_worst_case(title: str, item: dict[str, Any]) -> str:
    if not item:
        return f"<div class='muted'>{title}: N/A</div>"
    trace = item.get("trace_ref", "")
    link = f"<a href='{_html_escape(trace)}' target='_blank'>{_html_escape(trace)}</a>" if trace else "N/A"
    return (
        f"<div><strong>{_html_escape(title)}</strong></div>"
        f"<div>seed={item.get('seed')} | {item.get('policy_a')} vs {item.get('policy_b')}</div>"
        f"<div>terminal_reason={item.get('terminal_reason')} | turns={item.get('turns')} | winner={item.get('winner')}</div>"
        f"<div>trace: {link}</div>"
    )


def _render_html(
    prompt: str,
    before: AuditReport,
    after: AuditReport,
    compare: dict[str, Any],
    patch_ops: list[dict[str, Any]],
    patch_rationale: str,
    gate_passed: bool,
    diff_text: str,
    before_reasons: dict[str, dict[str, float]],
    after_reasons: dict[str, dict[str, float]],
    worst_before: dict[str, Any],
    worst_after: dict[str, Any],
) -> str:
    rows = []
    for key, value in compare.items():
        color = "#166534" if value["improved"] else "#9b1c1c"
        rows.append(
            f"<tr><td>{key}</td><td>{value['before']:.4f}</td>"
            f"<td>{value['after']:.4f}</td><td style='color:{color}'>{value['delta']:+.4f}</td></tr>"
        )
    table_rows = "\n".join(rows)
    patch_json = _html_escape(json.dumps(patch_ops, ensure_ascii=False, indent=2))
    diff_html = _html_escape(diff_text)
    reason_rows = _render_reason_rows(before_reasons, after_reasons)
    policy_rows = _render_policy_rows(before, after)
    status = "PASS" if gate_passed else "SOFT-FAIL"
    status_color = "#14532d" if gate_passed else "#9a3412"

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GenieGuard Report</title>
  <style>
    :root {{
      --bg: #f2f7f3;
      --ink: #111827;
      --muted: #4b5563;
      --accent: #0f766e;
      --card: #ffffff;
      --line: #d1ddd5;
      --before: #ef4444;
      --after: #16a34a;
    }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Noto Sans JP", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(1000px 600px at 10% -20%, #d0efe7 0, transparent 60%),
        radial-gradient(900px 520px at 90% 10%, #fdecc8 0, transparent 55%),
        var(--bg);
    }}
    .wrap {{ max-width: 1200px; margin: 24px auto; padding: 0 12px 24px; }}
    .head {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 16px; }}
    .grid {{ margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 12px; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    h2 {{ margin: 0 0 8px; font-size: 16px; color: var(--accent); }}
    .muted {{ color: var(--muted); }}
    pre {{ background: #0b1220; color: #d1fae5; padding: 10px; border-radius: 8px; overflow: auto; font-size: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid var(--line); text-align: left; padding: 7px; vertical-align: top; }}
    .status {{ font-weight: 700; color: {status_color}; }}
    .bar {{
      height: 10px;
      border-radius: 5px;
      min-width: 2px;
    }}
    .bar.before {{ background: var(--before); }}
    .bar.after {{ background: var(--after); }}
    a {{ color: #0f766e; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <h1>GenieGuard v0.1</h1>
      <div>Prompt: {_html_escape(prompt)}</div>
      <div>Regression Gate: <span class="status">{status}</span></div>
      <div class="muted">Metrics: deadlock_rate / win_skew / exploit_dominance</div>
      <div class="muted">Thresholds: deadlock_rate &lt;= 0.01, win_skew &lt;= 0.10, exploit_dominance &lt;= 0.25</div>
    </div>
    <div class="grid">
      <section class="card">
        <h2>Audit Before / After</h2>
        <table>
          <thead><tr><th>Metric</th><th>Before</th><th>After</th><th>Delta</th></tr></thead>
          <tbody>{table_rows}</tbody>
        </table>
      </section>
      <section class="card">
        <h2>Patch Proposal</h2>
        <div>{_html_escape(patch_rationale)}</div>
        <pre>{patch_json}</pre>
      </section>
      <section class="card">
        <h2>Terminal Reason Breakdown</h2>
        <table>
          <thead><tr><th>Reason</th><th>Before</th><th>After</th><th>B%</th><th>A%</th></tr></thead>
          <tbody>{reason_rows}</tbody>
        </table>
      </section>
      <section class="card">
        <h2>Policy Win-rate Table</h2>
        <table>
          <thead><tr><th>Policy</th><th>Before</th><th>After</th><th>Delta</th></tr></thead>
          <tbody>{policy_rows}</tbody>
        </table>
      </section>
      <section class="card">
        <h2>Worst Case Top1</h2>
        {_render_worst_case("Before", worst_before)}
        <hr>
        {_render_worst_case("After", worst_after)}
      </section>
      <section class="card">
        <h2>Findings</h2>
        <div class="muted">Before</div>
        <pre>{_html_escape(json.dumps(before.findings, ensure_ascii=False, indent=2))}</pre>
        <div class="muted">After</div>
        <pre>{_html_escape(json.dumps(after.findings, ensure_ascii=False, indent=2))}</pre>
      </section>
      <section class="card" style="grid-column: 1 / -1;">
        <h2>Spec Diff</h2>
        <pre>{diff_html}</pre>
      </section>
    </div>
  </div>
</body>
</html>
"""


def write_run_artifacts(
    out_dir: Path,
    prompt: str,
    spec_before: GameSpec,
    logs_before: list[GameLog],
    report_before: AuditReport,
    regression: RegressionResult,
    write_html: bool = True,
) -> dict[str, str]:
    ensure_dir(out_dir)
    evidence_dir = out_dir / "evidence"
    ensure_dir(evidence_dir)

    report_before_ev = _attach_evidence(report_before, logs_before, evidence_dir=evidence_dir, prefix="before")
    report_after_ev = _attach_evidence(
        regression.after_report,
        regression.after_logs,
        evidence_dir=evidence_dir,
        prefix="after",
    )

    diff_text = _spec_diff(spec_before, regression.patched_spec)
    compare = _metric_compare(report_before_ev, report_after_ev)
    before_reasons = _reason_breakdown(logs_before)
    after_reasons = _reason_breakdown(regression.after_logs)
    worst_before = _write_worst_trace(evidence_dir, "before", _worst_case(logs_before))
    worst_after = _write_worst_trace(evidence_dir, "after", _worst_case(regression.after_logs))

    write_json(out_dir / "spec.before.json", spec_before.to_dict())
    write_json(out_dir / "spec.after.json", regression.patched_spec.to_dict())
    write_json(out_dir / "audit.before.json", report_before_ev.to_dict())
    write_json(out_dir / "audit.after.json", report_after_ev.to_dict())
    write_json(out_dir / "patch.selected.json", regression.selected_patch.to_dict())
    write_json(out_dir / "regression.attempts.json", regression.attempts)
    write_json(out_dir / "metrics.compare.json", compare)
    write_json(
        out_dir / "summary.before_after.json",
        {
            "terminal_reason_before": before_reasons,
            "terminal_reason_after": after_reasons,
            "worst_case_before": worst_before,
            "worst_case_after": worst_after,
            "policy_win_rates_before": report_before_ev.policy_win_rates,
            "policy_win_rates_after": report_after_ev.policy_win_rates,
        },
    )
    write_text(out_dir / "patch.diff", diff_text)
    write_ndjson(out_dir / "logs.before.ndjson", [x.to_dict() for x in logs_before])
    write_ndjson(out_dir / "logs.after.ndjson", [x.to_dict() for x in regression.after_logs])

    html_path = out_dir / "report.html"
    if write_html:
        html = _render_html(
            prompt=prompt,
            before=report_before_ev,
            after=report_after_ev,
            compare=compare,
            patch_ops=regression.selected_patch.patch_ops,
            patch_rationale=regression.selected_patch.rationale,
            gate_passed=regression.passed,
            diff_text=diff_text,
            before_reasons=before_reasons,
            after_reasons=after_reasons,
            worst_before=worst_before,
            worst_after=worst_after,
        )
        write_text(html_path, html)

    return {
        "out_dir": str(out_dir),
        "report_html": str(html_path),
        "spec_before": str(out_dir / "spec.before.json"),
        "spec_after": str(out_dir / "spec.after.json"),
        "audit_before": str(out_dir / "audit.before.json"),
        "audit_after": str(out_dir / "audit.after.json"),
        "patch": str(out_dir / "patch.selected.json"),
        "diff": str(out_dir / "patch.diff"),
    }


def write_evidence_zip(out_dir: Path) -> Path:
    zip_path = out_dir / "evidence.zip"
    include_files = [
        "report.html",
        "result.json",
        "summary.before_after.json",
        "metrics.compare.json",
        "patch.diff",
        "patch.selected.json",
        "audit.before.json",
        "audit.after.json",
        "spec.before.json",
        "spec.after.json",
    ]

    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as zf:
        for name in include_files:
            path = out_dir / name
            if path.exists() and path.is_file():
                zf.write(path, arcname=name)

        evidence_dir = out_dir / "evidence"
        if evidence_dir.exists():
            for trace in sorted(evidence_dir.glob("*.trace.txt")):
                zf.write(trace, arcname=str(Path("evidence") / trace.name))
    return zip_path
