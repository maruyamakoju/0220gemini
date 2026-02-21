from __future__ import annotations

from genieguard.runtime import (
    EVIDENCE_MANIFEST_VERSION,
    RESULT_SCHEMA_VERSION,
    build_runtime_meta,
)


def test_runtime_meta_required_keys() -> None:
    meta = build_runtime_meta()
    assert RESULT_SCHEMA_VERSION == 2
    assert EVIDENCE_MANIFEST_VERSION == 2
    for key in ("genieguard_version", "git_sha", "created_at", "python_version", "platform"):
        assert key in meta
        assert isinstance(meta[key], str)
        assert meta[key] != ""
