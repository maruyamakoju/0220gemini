# Fixed Demo Case: ctf10

This demo case is pinned for deterministic red-to-green playback.

## Goal
- Before: at least one gate metric fails (`deadlock_rate`, `win_skew`, `exploit_dominance`)
- Patch: non-empty `patch_ops`
- After: gate thresholds pass with reproducible evidence

## Run
```bash
python run_demo.py --demo-case ctf10 --out artifacts/demo_latest --open --fail-on-soft-fail
```

Equivalent explicit command:
```bash
python run_demo.py --spec examples/demo_case_ctf10/spec.before.json --seeds examples/demo_case_ctf10/seeds.json --out artifacts/demo_latest --open --fail-on-soft-fail
```
