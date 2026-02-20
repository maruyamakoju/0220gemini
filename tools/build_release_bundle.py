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

    manifest = {
        "version": "v0.1.0",
        "result": {
            "gate_passed": result["gate_passed"],
            "before_metrics": result["before_metrics"],
            "after_metrics": result["after_metrics"],
            "selected_patch": result["selected_patch"],
            "paths": {
                "report_sample_html": str(report_dst.relative_to(ROOT)),
                "demo_case_zip": str(zip_path.relative_to(ROOT)),
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
    print(f"- {(dist / 'release_manifest.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
