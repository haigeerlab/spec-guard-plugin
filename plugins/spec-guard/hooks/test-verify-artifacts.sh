#!/usr/bin/env bash
set -euo pipefail

HOOKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PASS=0

fail() { echo "  ❌ $1" >&2; exit 1; }

# $1=用例名 $2=期望退出码(0|1) $3=输出必须包含的文本；项目目录取 ${PROJECT}，可用 ${RUN_PATH} 替换 PATH
check() {
  local out rc
  set +e
  out="$(PATH="${RUN_PATH:-$PATH}" CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$HOOKDIR/verify-artifacts.sh" 2>&1)"
  rc=$?
  set -e
  [ "$rc" -eq "$2" ] || fail "$1: 退出码 ${rc}，期望 $2
$out"
  grep -F -- "$3" >/dev/null <<<"$out" || fail "$1: 输出缺少「$3」
$out"
  echo "  ✅ $1"; PASS=$((PASS + 1))
}

# $1=目录 $2...=额外追加到能力图末尾的行
project() {
  PROJECT="$WORK/$1"; shift
  mkdir -p "$PROJECT/spec"
  printf '%s\n' '# Capability Map: fixture' '' '## 目标' '' 'Verify artifacts.' '' '## 模块' '' \
    '| Module id | Responsibility | Depends on |' '| --- | --- | --- |' '| alpha | x | — |' '' \
    'Build order: alpha' "$@" > "$PROJECT/spec/CAPABILITY-MAP.md"
  touch "$PROJECT/spec/alpha.md"
}

project valid
check "有效能力图与对应 spec 通过" 0 "能力图通过严格解析"

project root-spec
touch "$PROJECT/SPEC-alpha.md"
check "根目录 spec 失败" 1 "根目录有不受支持的 spec 文件"

project orphan
touch "$PROJECT/spec/beta.md"
check "能力图上没有的 spec 失败" 1 "能力图上没有的模块 spec: beta"

# 自带正则曾把围栏示例和第二张表的首列当成模块 id。
project fenced '' '```markdown' '| ghost | 示例 | — |' '```'
touch "$PROJECT/spec/ghost.md"
check "围栏示例中的 id 不算模块" 1 "能力图上没有的模块 spec: ghost"

project second-table '' '## Risks' '' '| Risk | Mitigation |' '| --- | --- |' '| risk-one | watch |'
touch "$PROJECT/spec/risk-one.md"
check "其他表格首列不算模块" 1 "能力图上没有的模块 spec: risk-one"

project no-build-order
printf '%s\n' '# Capability Map: fixture' '' '## 模块' '' '| Module id | Responsibility | Depends on |' \
  '| --- | --- | --- |' '| alpha | x | missing |' > "$PROJECT/spec/CAPABILITY-MAP.md"
check "无效能力图失败并给出解析原因" 1 "能力图无效: "

# 环境故障只能报“未验证”，不能把合法 spec 判成违规。
project orphan-without-python
touch "$PROJECT/spec/beta.md"
mkdir -p "$WORK/nopy"
for tool in dirname grep; do ln -sf "$(command -v "$tool")" "$WORK/nopy/$tool"; done
RUN_PATH="$WORK/nopy" check "缺 python3 时报未验证而非失败" 0 "未验证：python3 不可用"

mkdir -p "$WORK/brokenpy"
printf '%s\n' '#!/bin/sh' 'echo broken; exit 1' > "$WORK/brokenpy/python3"
chmod +x "$WORK/brokenpy/python3"
RUN_PATH="$WORK/brokenpy:$PATH" check "解析器异常时报未验证而非失败" 0 "未验证：能力图解析器没有正常运行"

# 有 Plan 无 todo.md 的模块按已完成计：汇总成一条警告，不改退出码。
# $1=目录 $2=模块数；每个模块都有 spec，m01..mNN 全部在 Build order 内。
many_modules() {
  local i id ids="" rows=()
  PROJECT="$WORK/$1"; mkdir -p "$PROJECT/spec"
  for i in $(seq 1 "$2"); do
    id="$(printf m%02d "$i")"; ids="${ids}${ids:+, }${id}"
    rows+=("| ${id} | x | — |"); touch "$PROJECT/spec/${id}.md"
  done
  printf '%s\n' '# Capability Map: fixture' '' '## 模块' '' '| Module id | Responsibility | Depends on |' \
    '| --- | --- | --- |' "${rows[@]}" '' "Build order: ${ids}" > "$PROJECT/spec/CAPABILITY-MAP.md"
}
# $1=模块 id：只放 plan.md
plan_only() { mkdir -p "$PROJECT/tasks/$1"; touch "$PROJECT/tasks/$1/plan.md"; }
# $1=用例名 $2=不得出现的文本
check_absent() {
  local out
  out="$(CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$HOOKDIR/verify-artifacts.sh" 2>&1)" || true
  ! grep -F -- "$2" >/dev/null <<<"$out" || fail "$1: 输出不应包含「$2」
$out"
  echo "  ✅ $1"; PASS=$((PASS + 1))
}

many_modules no-todo-none 3
plan_only m01; touch "$PROJECT/tasks/m01/todo.md"
check "0 个缺 todo 的模块时警告数为 0" 0 "0 警告"
check_absent "0 个缺 todo 的模块时没有汇总警告" "没有 todo.md"

many_modules no-todo-one 3
plan_only m02
check "1 个缺 todo 的模块发一条警告并点名" 0 "1 个模块有 Plan 但没有 todo.md，按已完成计：m02"
check "1 个缺 todo 的模块警告数为 1、退出码不变" 0 "1 警告"

many_modules no-todo-twelve 12
for i in 01 02 03 04 05 06 07 08 09 10 11 12; do plan_only "m$i"; done
check "12 个缺 todo 的模块只列前 10 个并以等 12 个结尾" 0 \
  "12 个模块有 Plan 但没有 todo.md，按已完成计：m01, m02, m03, m04, m05, m06, m07, m08, m09, m10 等 12 个"
check "12 个缺 todo 的模块仍只多一条警告" 0 "1 警告"
check_absent "12 个缺 todo 的模块不列出第 11 个 id" "m11,"

# 已退役的远端 tracker 模式：state.json 仍是 github／gitlab 时不发缺 todo 汇总（历史状态文件警告仍在）。
many_modules no-todo-github 3
plan_only m02; mkdir -p "$PROJECT/.agent"
printf '{"tracker":"github","modules":{}}\n' > "$PROJECT/.agent/state.json"
check_absent "退役 tracker github 不发缺 todo 汇总" "没有 todo.md"
printf '{"tracker":"gitlab","modules":{}}\n' > "$PROJECT/.agent/state.json"
check_absent "退役 tracker gitlab 不发缺 todo 汇总" "没有 todo.md"
printf '{"tracker":"none","modules":{}}\n' > "$PROJECT/.agent/state.json"
check "tracker none 仍发缺 todo 汇总" 0 "1 个模块有 Plan 但没有 todo.md，按已完成计：m02"

echo "verify-artifacts regression passed ($PASS cases)"
