from __future__ import annotations

import argparse
import json
import webbrowser
from pathlib import Path

from .pipeline import PipelineConfig, run_pipeline


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="GenieGuard v0.1 pipeline")
    p.add_argument("--prompt", type=str, default="Generate a CTF game spec with possible balancing risks.")
    p.add_argument("--spec", type=Path, default=None, help="Existing GameSpec JSON path.")
    p.add_argument("--out", type=Path, default=None, help="Artifact output directory.")
    p.add_argument("--seed", type=int, default=1337)
    p.add_argument("--seed-count", type=int, default=50)
    p.add_argument("--max-attempts", type=int, default=2)
    p.add_argument("--policies", type=str, default="", help="Comma-separated policy names.")
    p.add_argument("--use-gemini", action="store_true")
    p.add_argument("--no-html", action="store_true")
    p.add_argument("--open", action="store_true", help="Open report.html after run.")
    p.add_argument(
        "--fail-on-soft-fail",
        action="store_true",
        help="Return non-zero exit code when gate is not passed.",
    )
    p.add_argument("--json", action="store_true", help="Print full result JSON.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    policies = [x.strip() for x in args.policies.split(",") if x.strip()] or None
    config = PipelineConfig(
        prompt=args.prompt,
        seed=args.seed,
        seed_count=args.seed_count,
        spec_path=args.spec,
        out_dir=args.out,
        policy_names=policies,
        use_gemini=args.use_gemini,
        max_attempts=args.max_attempts,
        write_html=not args.no_html,
    )

    result = run_pipeline(config)
    if args.open and not args.no_html:
        report_html = Path(result["paths"]["report_html"]).resolve()
        if report_html.exists():
            webbrowser.open(report_html.as_uri())

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if (args.fail_on_soft_fail and not result["gate_passed"]) else 0

    print(f"Gate: {'PASS' if result['gate_passed'] else 'SOFT-FAIL'}")
    print(f"Before metrics: {result['before_metrics']}")
    print(f"After metrics:  {result['after_metrics']}")
    print(f"Patch: {result['selected_patch']['patch_ops']}")
    print(f"Artifacts: {result['paths']['out_dir']}")
    return 1 if (args.fail_on_soft_fail and not result["gate_passed"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
