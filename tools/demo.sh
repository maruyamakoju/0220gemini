#!/usr/bin/env bash
set -euo pipefail

OUT="artifacts/demo_latest"
rm -rf "$OUT"

python run_demo.py --demo-case ctf10 --max-attempts 2 --out "$OUT" --open --fail-on-soft-fail
echo "[GenieGuard] Demo completed: $OUT/report.html"
