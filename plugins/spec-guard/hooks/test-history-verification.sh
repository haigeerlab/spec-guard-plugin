#!/usr/bin/env bash
set -euo pipefail
trap 'echo "  ❌ ${BASH_SOURCE[0]}:${LINENO} 断言失败" >&2' ERR

HOOKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HISTORY="$HOOKDIR/capability-history.py"
VERIFY="$HOOKDIR/verify-history.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PROJECT="$TMP/project"
CP="20260902T090000Z-0001"
mkdir -p "$PROJECT/spec/history/a/$CP" "$PROJECT/.agent/history/a/$CP"
printf 'map\n' > "$PROJECT/spec/history/a/$CP/CAPABILITY-MAP.md"
printf '{}\n' > "$PROJECT/.agent/history/a/$CP/state.json"
MAP="$(shasum -a 256 "$PROJECT/spec/history/a/$CP/CAPABILITY-MAP.md" | awk '{print $1}')"
STATE="$(shasum -a 256 "$PROJECT/.agent/history/a/$CP/state.json" | awk '{print $1}')"
LEDGER="$PROJECT/spec/CAPABILITY-HISTORY.json"
printf '%s\n' "{\"schemaVersion\":1,\"initiatives\":[{\"id\":\"a\",\"title\":\"A\",\"events\":[{\"type\":\"created\",\"at\":\"now\",\"checkpoint\":{\"id\":\"$CP\",\"map\":{\"path\":\"spec/history/a/$CP/CAPABILITY-MAP.md\",\"sha256\":\"$MAP\"},\"state\":{\"path\":\".agent/history/a/$CP/state.json\",\"sha256\":\"$STATE\"},\"modules\":[]}}]}]}" > "$LEDGER"
"$HISTORY" verify "$LEDGER" "$PROJECT" >/dev/null || exit 1
printf 'tampered\n' > "$PROJECT/.agent/history/a/$CP/state.json"
if "$HISTORY" verify "$LEDGER" "$PROJECT" >/dev/null 2>&1; then
  echo "  ❌ 篡改后的 checkpoint 仍校验通过" >&2; exit 1
fi
rm -f "$LEDGER"
grep -q '未验证' <<<"$("$VERIFY" "$PROJECT")"
printf '%s\n' '{"schemaVersion":1,"initiatives":[]}' > "$LEDGER"
mkdir -p "$PROJECT/spec/history/orphan/20260902T090000Z-0001"
printf 'orphan\n' > "$PROJECT/spec/history/orphan/20260902T090000Z-0001/CAPABILITY-MAP.md"
if "$VERIFY" "$PROJECT" >/dev/null 2>&1; then
  echo "  ❌ 未登记的历史目录仍校验通过" >&2; exit 1
fi

# 未登记目录在 tasks/history、.agent/history 下也必须被发现（不止 spec/history）。
PROJECT2="$TMP/project2"
CP2="20260902T090000Z-0002"
mkdir -p "$PROJECT2/spec/history/b/$CP2" "$PROJECT2/.agent/history/b/$CP2"
printf 'map\n' > "$PROJECT2/spec/history/b/$CP2/CAPABILITY-MAP.md"
printf '{}\n' > "$PROJECT2/.agent/history/b/$CP2/state.json"
MAP2="$(shasum -a 256 "$PROJECT2/spec/history/b/$CP2/CAPABILITY-MAP.md" | awk '{print $1}')"
STATE2="$(shasum -a 256 "$PROJECT2/.agent/history/b/$CP2/state.json" | awk '{print $1}')"
LEDGER2="$PROJECT2/spec/CAPABILITY-HISTORY.json"
printf '%s\n' "{\"schemaVersion\":1,\"initiatives\":[{\"id\":\"b\",\"title\":\"B\",\"events\":[{\"type\":\"created\",\"at\":\"now\",\"checkpoint\":{\"id\":\"$CP2\",\"map\":{\"path\":\"spec/history/b/$CP2/CAPABILITY-MAP.md\",\"sha256\":\"$MAP2\"},\"state\":{\"path\":\".agent/history/b/$CP2/state.json\",\"sha256\":\"$STATE2\"},\"modules\":[]}}]}]}" > "$LEDGER2"
"$VERIFY" "$PROJECT2" >/dev/null || { echo "  ❌ 干净的账本未通过校验" >&2; exit 1; }

mkdir -p "$PROJECT2/tasks/history/ghost/x"
printf 'ghost plan\n' > "$PROJECT2/tasks/history/ghost/x/plan.md"
if "$VERIFY" "$PROJECT2" >/dev/null 2>&1; then
  echo "  ❌ tasks/history 下未登记的目录仍校验通过" >&2; exit 1
fi
rm -rf "$PROJECT2/tasks/history/ghost"

mkdir -p "$PROJECT2/.agent/history/ghost/y"
printf '{}\n' > "$PROJECT2/.agent/history/ghost/y/state.json"
if "$VERIFY" "$PROJECT2" >/dev/null 2>&1; then
  echo "  ❌ .agent/history 下未登记的目录仍校验通过" >&2; exit 1
fi
rm -rf "$PROJECT2/.agent/history/ghost"

# 正例：账本登记了模块 spec 与 plan 后，三棵树的对应目录都应通过校验。
mkdir -p "$PROJECT2/spec/history/b/$CP2" "$PROJECT2/tasks/history/b/$CP2/m1"
printf 'module spec\n' > "$PROJECT2/spec/history/b/$CP2/m1.md"
printf 'module plan\n' > "$PROJECT2/tasks/history/b/$CP2/m1/plan.md"
SPEC2="$(shasum -a 256 "$PROJECT2/spec/history/b/$CP2/m1.md" | awk '{print $1}')"
PLAN2="$(shasum -a 256 "$PROJECT2/tasks/history/b/$CP2/m1/plan.md" | awk '{print $1}')"
printf '%s\n' "{\"schemaVersion\":1,\"initiatives\":[{\"id\":\"b\",\"title\":\"B\",\"events\":[{\"type\":\"created\",\"at\":\"now\",\"checkpoint\":{\"id\":\"$CP2\",\"map\":{\"path\":\"spec/history/b/$CP2/CAPABILITY-MAP.md\",\"sha256\":\"$MAP2\"},\"state\":{\"path\":\".agent/history/b/$CP2/state.json\",\"sha256\":\"$STATE2\"},\"modules\":[{\"id\":\"m1\",\"responsibility\":\"r\",\"dependsOn\":[],\"status\":\"unknown\",\"issue\":null,\"spec\":{\"path\":\"spec/history/b/$CP2/m1.md\",\"sha256\":\"$SPEC2\"},\"plan\":{\"path\":\"tasks/history/b/$CP2/m1/plan.md\",\"sha256\":\"$PLAN2\"}}]}}]}]}" > "$LEDGER2"
"$VERIFY" "$PROJECT2" >/dev/null || { echo "  ❌ 登记了模块 spec/plan 的账本未通过三棵树校验" >&2; exit 1; }

echo "  ✅ history verification regression passed"
