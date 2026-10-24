#!/usr/bin/env bash
set -euo pipefail
trap 'echo "  ❌ ${BASH_SOURCE[0]}:${LINENO} 断言失败" >&2' ERR
HOOKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATION="$HOOKDIR/history-migration.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/legacy/.agent"
printf '# map\n' > "$TMP/legacy/CAPABILITY-MAP.md"
printf '{}' > "$TMP/legacy/.agent/state.json"
printf '# old\n' > "$TMP/legacy/SPEC-payment.md"
OUT="$(python3 "$MIGRATION" preview "$TMP/legacy")"
printf '%s' "$OUT" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["candidates"][0]["status"] == "unknown"; assert d["candidates"][0]["legacySpecs"] == ["SPEC-payment.md"]'
mkdir -p "$TMP/legacy/spec"
: > "$TMP/legacy/spec/CAPABILITY-HISTORY.json"
python3 "$MIGRATION" preview "$TMP/legacy" | python3 -c 'import json,sys; assert json.load(sys.stdin)["conflicts"]'
rm -f "$TMP/legacy/spec/CAPABILITY-HISTORY.json"
python3 "$MIGRATION" import --confirm "$TMP/legacy" >/dev/null
python3 "$HOOKDIR/capability-history.py" verify "$TMP/legacy/spec/CAPABILITY-HISTORY.json" "$TMP/legacy" >/dev/null
test -f "$TMP/legacy/spec/CAPABILITY-MAP.md" || exit 1

mkdir -p "$TMP/current/.agent" "$TMP/current/spec"
printf '# map\n' > "$TMP/current/spec/CAPABILITY-MAP.md"
printf '{"initiative":{"title":"capability-history"}}' > "$TMP/current/.agent/state.json"
python3 "$MIGRATION" import --confirm "$TMP/current" >/dev/null
python3 "$HOOKDIR/capability-history.py" verify "$TMP/current/spec/CAPABILITY-HISTORY.json" "$TMP/current" >/dev/null
[ "$(python3 "$HOOKDIR/capability-history.py" status "$TMP/current/spec/CAPABILITY-HISTORY.json" capability-history)" = active ]

# review-residual-fixes（C7）：capability-history.py create 失败时，迁移不在项目根留下临时事件文件。
mkdir -p "$TMP/broken-hooks" "$TMP/broken/.agent"
cp "$HOOKDIR"/*.py "$TMP/broken-hooks/"
printf 'import sys\nsys.exit(1)\n' > "$TMP/broken-hooks/capability-history.py"
printf '# map\n' > "$TMP/broken/CAPABILITY-MAP.md"
printf '{}' > "$TMP/broken/.agent/state.json"
set +e
python3 "$TMP/broken-hooks/history-migration.py" import --confirm "$TMP/broken" >/dev/null 2>&1
rc=$?
set -e
[ "$rc" -eq 1 ]
leftover="$(find "$TMP/broken" -maxdepth 1 -name '.history-migration-*' -print)"
[ -z "$leftover" ] || { echo "  ❌ 迁移失败后留下临时事件文件：$leftover" >&2; exit 1; }
echo "  ✅ history migration regression passed"
