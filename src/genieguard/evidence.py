from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_evidence_zip(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "zip_path": str(path),
        "manifest_version": None,
        "file_count": 0,
        "missing": [],
        "mismatched": [],
    }

    if not path.exists():
        payload["error"] = "zip_not_found"
        return payload

    with ZipFile(path, "r") as zf:
        names = set(zf.namelist())
        normalized_to_zip = {name.replace("\\", "/"): name for name in names}
        if "manifest.json" not in names:
            payload["error"] = "manifest_missing"
            return payload

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        payload["manifest_version"] = manifest.get("manifest_version")
        payload["genieguard_version"] = manifest.get("genieguard_version")
        payload["git_sha"] = manifest.get("git_sha")
        payload["created_at"] = manifest.get("created_at")

        files = manifest.get("files", [])
        if not isinstance(files, list):
            payload["error"] = "manifest_files_invalid"
            return payload

        payload["file_count"] = len(files)
        missing: list[str] = []
        mismatched: list[dict[str, str]] = []

        for item in files:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", ""))
            expected = str(item.get("sha256", ""))
            if not name or not expected:
                continue
            normalized_name = name.replace("\\", "/")
            zip_name = normalized_to_zip.get(normalized_name)
            if zip_name is None:
                missing.append(name)
                continue
            actual = _sha256_bytes(zf.read(zip_name))
            if actual != expected:
                mismatched.append({"name": name, "expected": expected, "actual": actual})

        payload["missing"] = missing
        payload["mismatched"] = mismatched
        payload["ok"] = (len(missing) == 0 and len(mismatched) == 0)
        return payload
