#!/usr/bin/env bash
set -uo pipefail

PROJECT="${1:-}"
[ -n "$PROJECT" ] || { echo "usage: verify-history.sh <project>" >&2; exit 2; }
LEDGER="$PROJECT/spec/CAPABILITY-HISTORY.json"
[ -f "$LEDGER" ] || { echo "未验证：没有 capability history ledger"; exit 0; }
ROOT="$(cd "$(dirname "$0")" && pwd)"
python3 "$ROOT/capability-history.py" verify "$LEDGER" "$PROJECT" || exit 1
EXPECTED="$(python3 "$ROOT/capability-history.py" artifact-dirs "$LEDGER")" || exit 1
python3 - "$PROJECT" "$EXPECTED" <<'PY'
import os, sys
project, expected_raw = sys.argv[1:3]
expected = set(line for line in expected_raw.splitlines() if line)
for base in ("spec/history", "tasks/history", ".agent/history"):
    root = os.path.join(project, base)
    if not os.path.isdir(root):
        continue
    for directory, _, files in os.walk(root):
        if not files:
            continue
        relative = os.path.relpath(directory, project)
        if relative not in expected:
            raise SystemExit("orphan history evidence: " + relative)
PY
[ "$?" -eq 0 ] || exit 1
echo "历史证据校验通过"
