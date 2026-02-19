from __future__ import annotations

import collections
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python tools/inspect_logs.py <ndjson>")
        return 1
    path = Path(sys.argv[1])
    wins = collections.Counter()
    reasons = collections.Counter()
    by_pair = collections.Counter()
    total = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        wins[row.get("winner")] += 1
        reasons[row.get("terminal_reason")] += 1
        by_pair[(row.get("policy_a"), row.get("policy_b"), row.get("winner"))] += 1
        total += 1
    print("total", total)
    print("wins", dict(wins))
    print("terminal_reason", dict(reasons))
    print("sample_pairs", dict(list(by_pair.items())[:10]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
