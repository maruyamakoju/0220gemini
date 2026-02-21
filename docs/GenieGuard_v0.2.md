# GenieGuard 技術書 v0.2

## 位置づけ
- v0.1: MVP（Generate -> Audit -> Patch -> Verify）
- v0.2: 境界と契約の固定（GateSpec / PipelineResult / ArtifactLayout）

## v0.2 変更点（要約）
1. Gate判定の単一ソース化
- `src/genieguard/gate.py`
- `GateSpec` がしきい値判定と改善判定の契約を持つ

2. 結果契約の固定
- `src/genieguard/results.py`
- `PipelineResult` で `result.json` のキーを固定
- `schema_version=2` を導入

3. Artifact契約の固定
- `src/genieguard/artifacts.py`
- `evidence.zip` に `manifest.json` を同梱
- `manifest_version=2` と sha256 リストを出力

4. Pipeline責務分離
- `run_pipeline_core()`（計算）
- `persist_pipeline_result()`（I/O）

5. Runtimeメタデータの付与
- `src/genieguard/runtime.py`
- `genieguard_version`, `git_sha`, `created_at`, `python_version`, `platform`

## 成果物コントラクト（v0.2）
### result.json
- `schema_version`: `2`
- `gate_passed`, `before_gate_passed`, `after_gate_passed`
- `gate_thresholds`, `gate_reasons`
- `before_metrics`, `after_metrics`
- `selected_patch`, `attempts`
- `paths`
- `meta`:
  - `prompt`
  - `policy_names`
  - `seeds`
  - `reproducible_before`, `reproducible_after`
  - `genieguard_version`, `git_sha`, `created_at`, `python_version`, `platform`

### evidence.zip/manifest.json
- `manifest_version`: `2`
- `genieguard_version`, `git_sha`, `created_at`, `python_version`, `platform`
- `hash_algorithm`: `sha256`
- `files`: `{name, sha256}` の配列

### 証拠完全性検証コマンド
- `python -m genieguard.cli --verify-evidence <path-to-evidence.zip> --json`
- `manifest.json` と zip 内実体の sha256 を照合して `ok=true/false` を返す

## リリース方針
- Git tag: `v0.2.0`
- `pyproject.toml` version: `0.2.0`
- README見出し: `GenieGuard v0.2`
- Pages上の sample report も v0.2 契約情報を表示

## 互換性メモ
- 既存利用者向けに主要トップレベルキー（`gate_passed` など）は維持
- v0.2 追加情報は後方互換的に拡張
