from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from genieguard.pipeline import PipelineConfig, run_pipeline
from genieguard.runtime import EVIDENCE_MANIFEST_VERSION, RESULT_SCHEMA_VERSION


def _zip_demo_case(case_dir: Path, out_zip: Path) -> None:
    with zipfile.ZipFile(out_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in ("README.md", "spec.before.json", "seeds.json"):
            file_path = case_dir / rel
            zf.write(file_path, arcname=f"demo_case_ctf10/{rel}")


def main() -> int:
    dist = ROOT / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True, exist_ok=True)

    case_dir = ROOT / "examples" / "demo_case_ctf10"
    zip_path = dist / "demo_case_ctf10.zip"
    _zip_demo_case(case_dir, zip_path)

    sample_out = dist / "sample_run"
    result = run_pipeline(
        PipelineConfig(
            spec_path=case_dir / "spec.before.json",
            seeds_path=case_dir / "seeds.json",
            out_dir=sample_out,
            max_attempts=2,
            write_html=True,
            prompt="Fixed demo case: ctf10",
        )
    )

    report_src = sample_out / "report.html"
    report_dst = dist / "report.sample.html"
    shutil.copy2(report_src, report_dst)
    evidence_src = sample_out / "evidence.zip"
    evidence_dst = dist / "evidence.sample.zip"
    if evidence_src.exists():
        shutil.copy2(evidence_src, evidence_dst)

    result_meta = result.get("meta", {})
    gg_version = str(result_meta.get("genieguard_version", "unknown"))
    manifest = {
        "bundle_version": f"v{gg_version}",
        "result_schema_version": int(result.get("schema_version", RESULT_SCHEMA_VERSION)),
        "evidence_manifest_version": EVIDENCE_MANIFEST_VERSION,
        "genieguard_version": gg_version,
        "git_sha": str(result_meta.get("git_sha", "unknown")),
        "created_at": str(result_meta.get("created_at", "")),
        "python_version": str(result_meta.get("python_version", "")),
        "platform": str(result_meta.get("platform", "")),
        "result": {
            "gate_passed": result["gate_passed"],
            "schema_version": result.get("schema_version", RESULT_SCHEMA_VERSION),
            "before_metrics": result["before_metrics"],
            "after_metrics": result["after_metrics"],
            "selected_patch": result["selected_patch"],
            "paths": {
                "report_sample_html": str(report_dst.relative_to(ROOT)),
                "demo_case_zip": str(zip_path.relative_to(ROOT)),
                "evidence_sample_zip": str(evidence_dst.relative_to(ROOT)) if evidence_dst.exists() else "",
                "sample_run_dir": str(sample_out.relative_to(ROOT)),
            },
        },
    }
    (dist / "release_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Built release bundle at: {dist}")
    print(f"- {zip_path.relative_to(ROOT)}")
    print(f"- {report_dst.relative_to(ROOT)}")
    if evidence_dst.exists():
        print(f"- {evidence_dst.relative_to(ROOT)}")
    print(f"- {(dist / 'release_manifest.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
