from __future__ import annotations

import zipfile
from pathlib import Path

from genieguard.evidence import verify_evidence_zip
from genieguard.pipeline import PipelineConfig, run_pipeline


def test_verify_evidence_zip_detects_tampering(tmp_path: Path) -> None:
    out_dir = tmp_path / "run"
    run_pipeline(
        PipelineConfig(
            seed=1337,
            seed_count=6,
            out_dir=out_dir,
            max_attempts=2,
            write_html=False,
        )
    )

    source_zip = out_dir / "evidence.zip"
    verified = verify_evidence_zip(source_zip)
    assert verified["ok"] is True

    tampered_zip = tmp_path / "evidence.tampered.zip"
    with zipfile.ZipFile(source_zip, "r") as zf:
        payload = {name: zf.read(name) for name in zf.namelist()}
    payload["result.json"] = payload["result.json"] + b"\n"

    with zipfile.ZipFile(tampered_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in payload.items():
            zf.writestr(name, data)

    tampered = verify_evidence_zip(tampered_zip)
    assert tampered["ok"] is False
    assert any(item["name"] == "result.json" for item in tampered["mismatched"])
