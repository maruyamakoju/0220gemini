# GenieGuard v0.2

GenieGuard is a pre-shipping CI loop for AI-generated game specs.
It runs `Generate -> Self-Play Audit -> Auto Patch -> Regression Verify` with reproducible evidence artifacts.

## Quick Demo
- Demo (Web): https://maruyamakoju.github.io/0220gemini/
- Run locally (one command): `tools\demo.bat`

## What This Repo Implements
- Deterministic 2D grid CTF simulator (`GameSpec + seed + policy -> identical result`)
- Self-play matrix with 4 adversarial policies:
  - `greedy_shortest_path`
  - `blocker`
  - `camper`
  - `random_epsilon`
- Audit metrics:
  - `deadlock_rate`
  - `win_skew`
  - `exploit_dominance`
- Rule-first patch synthesizer with optional Gemini selection/rationale
- Regression gate with rollback-by-selection behavior
- v0.2 boundary modules:
  - `gate.py` (`GateSpec` as single source of gate logic)
  - `results.py` (`PipelineResult` contract for stable `result.json`)
  - `artifacts.py` (`ArtifactLayout` + `evidence.zip` manifest)
- Demo artifacts:
  - before/after specs
  - before/after audits
  - trace evidence
  - patch diff
  - one-page HTML report

## Quick Start
Prerequisite: Python 3.11+

Run full pipeline:

```bash
python run_demo.py --seed-count 50 --max-attempts 2
```

Run guaranteed fixed demo case (always red -> patch -> green):

```bash
python run_demo.py --demo-case ctf10 --out artifacts/demo_latest --open --fail-on-soft-fail
```

Other fixed demo cases:

```bash
python run_demo.py --demo-case ctf_bias --out artifacts/demo_latest --fail-on-soft-fail
python run_demo.py --demo-case ctf_exploit --out artifacts/demo_latest --fail-on-soft-fail
```

Run and open the generated report automatically:

```bash
python run_demo.py --seed-count 50 --max-attempts 2 --open
```

Run and print full JSON result:

```bash
python run_demo.py --seed-count 20 --json
```

Use your own spec:

```bash
python run_demo.py --spec path/to/spec.json --seed-count 50
```

Use your own spec with fixed seed set:

```bash
python run_demo.py --spec path/to/spec.json --seeds path/to/seeds.json
```

Fail command (non-zero exit) on `SOFT-FAIL`:

```bash
python run_demo.py --seed-count 50 --fail-on-soft-fail
```

Windows one-click demo:

```bash
tools\demo.bat
```

Fixed demo case files:
- `examples/demo_case_ctf10/spec.before.json`
- `examples/demo_case_ctf10/seeds.json`
- `examples/demo_case_ctf_bias/spec.before.json`
- `examples/demo_case_ctf_bias/seeds.json`
- `examples/demo_case_ctf_exploit/spec.before.json`
- `examples/demo_case_ctf_exploit/seeds.json`
- Demo outputs are written under `artifacts/demo_latest/run_*` and the latest path is stored in `artifacts/demo_latest/LATEST_RUN.txt`.

## Optional Gemini Integration
Set environment variables:

```bash
set GEMINI_API_KEY=YOUR_KEY
set GEMINI_MODEL=gemini-2.0-flash
```

Then run with:

```bash
python run_demo.py --use-gemini
```

If Gemini call fails or key is missing, pipeline falls back to deterministic local generation/selection.

## Artifact Output
Each run writes to `artifacts/run_YYYYMMDD_HHMMSS/`.

Main files:
- `spec.before.json`
- `spec.after.json`
- `audit.before.json`
- `audit.after.json`
- `patch.selected.json`
- `regression.attempts.json`
- `metrics.compare.json`
- `summary.before_after.json`
- `patch.diff`
- `logs.before.ndjson`
- `logs.after.ndjson`
- `evidence/*.trace.txt`
- `report.html`
- `result.json`
- `evidence.zip`

Verify `evidence.zip` integrity (manifest + sha256):

```bash
python -m genieguard.cli --verify-evidence artifacts/demo_latest/run_xxx/evidence.zip --json
```
  - includes `manifest.json` (`manifest_version=2`, sha256 list, runtime metadata)

`result.json` contract (v0.2):
- `schema_version` (currently `2`)
- gate fields (`gate_passed`, `before_gate_passed`, `after_gate_passed`, `gate_thresholds`, `gate_reasons`)
- metrics (`before_metrics`, `after_metrics`)
- patch/attempts (`selected_patch`, `attempts`)
- runtime meta in `meta` (`genieguard_version`, `git_sha`, `created_at`, `python_version`, `platform`)

For one-click demo script output:
- `artifacts/demo_latest/`

## Tests
Install dev dependencies and run:

```bash
python -m pip install -e .[dev]
python -m pytest -q
```

## CI
GitHub Actions workflow is included at `.github/workflows/ci.yml`.

On each push/PR it runs:
1. Unit tests (`pytest`)
2. GenieGuard gate matrix (`ctf10`, `ctf_bias`, `ctf_exploit`)
3. Job Summary output (`PASS/FAIL + before/after + worst case`)
4. Artifact upload for each case (`report.html`, traces, diffs, metrics, result.json)

GitHub Pages workflow (`.github/workflows/pages.yml`) publishes:
- `report.sample.html`
- `demo_case_ctf10.zip`
- `evidence.sample.zip`
- `release_manifest.json`

## Release Bundle
Build distributable assets:

```bash
python tools/build_release_bundle.py
```

Generated in `dist/`:
- `demo_case_ctf10.zip`
- `report.sample.html`
- `evidence.sample.zip`
- `release_manifest.json`

Create and publish a GitHub release (Windows):

```bash
tools\release.bat v0.2.0
```

## Project Layout
```
src/genieguard/
  artifacts.py
  audit.py
  cli.py
  evidence.py
  models.py
  gate.py
  patcher.py
  pipeline.py
  policies.py
  regression.py
  reporting.py
  results.py
  runtime.py
  selfplay.py
  simulator.py
  spec_gen.py
docs/
  GenieGuard_v0.1.md
  GenieGuard_v0.2.md
tests/
```
