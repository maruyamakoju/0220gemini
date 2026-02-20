from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


@dataclass(frozen=True)
class ArtifactLayout:
    out_dir: Path

    @property
    def report_html(self) -> Path:
        return self.out_dir / "report.html"

    @property
    def result_json(self) -> Path:
        return self.out_dir / "result.json"

    @property
    def evidence_zip(self) -> Path:
        return self.out_dir / "evidence.zip"

    @property
    def evidence_dir(self) -> Path:
        return self.out_dir / "evidence"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_evidence_zip(layout: ArtifactLayout, extra_files: list[Path] | None = None) -> Path:
    include_names = [
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
    manifest: dict[str, list[dict[str, str]]] = {"files": []}
    zip_path = layout.evidence_zip

    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as zf:
        for name in include_names:
            path = layout.out_dir / name
            if path.exists() and path.is_file():
                zf.write(path, arcname=name)
                manifest["files"].append({"name": name, "sha256": _sha256(path)})

        if layout.evidence_dir.exists():
            for trace in sorted(layout.evidence_dir.glob("*.trace.txt")):
                arc = str(Path("evidence") / trace.name)
                zf.write(trace, arcname=arc)
                manifest["files"].append({"name": arc, "sha256": _sha256(trace)})

        for path in extra_files or []:
            if path.exists() and path.is_file():
                zf.write(path, arcname=path.name)
                manifest["files"].append({"name": path.name, "sha256": _sha256(path)})

        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    return zip_path
