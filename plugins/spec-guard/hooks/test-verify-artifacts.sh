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

# 主解析器成功、仅 Plan/todo 二次汇总失败时不能把零结果冒充为零警告。
project summary-helper-fails
mkdir -p "$PROJECT/tasks/alpha"
touch "$PROJECT/tasks/alpha/plan.md"
mkdir -p "$WORK/summary-fails"
cat > "$WORK/summary-fails/python3" <<'SH'
#!/bin/sh
if [ "$1" = -c ]; then
  case "$2" in
    *'from module_stage import module_state'*)
      printf 'called\n' > "$SPEC_GUARD_TEST_SENTINEL"
      exit 29
      ;;
  esac
fi
exec "$SPEC_GUARD_TEST_REAL_PYTHON" "$@"
SH
chmod +x "$WORK/summary-fails/python3"
SPEC_GUARD_TEST_REAL_PYTHON="$(command -v python3)" \
SPEC_GUARD_TEST_SENTINEL="$WORK/summary-helper-called" \
RUN_PATH="$WORK/summary-fails:$PATH" \
  check "二次汇总失败时明确报未验证" 0 "未验证：有 Plan 无 todo.md 汇总脚本没有正常运行"
[ -f "$WORK/summary-helper-called" ] || fail "二次汇总失败用例没有运行目标 helper"

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

# plan.md 里独占一行的 no-todo 声明：汇总只列没有声明的模块，全有声明时不发警告。
many_modules no-todo-marked 3
plan_only m01; plan_only m02; plan_only m03
printf '%s\n' '# Plan' '<!-- spec-guard: no-todo -->' | tee "$PROJECT/tasks/m01/plan.md" "$PROJECT/tasks/m03/plan.md" >/dev/null
printf '%s\n' '# Plan' '> 登记说明：没有 todo 是有意的。' > "$PROJECT/tasks/m02/plan.md"
check "只列没有 no-todo 声明的模块" 0 "1 个模块有 Plan 但没有 todo.md，按已完成计：m02"
printf '%s\n' '# Plan' '<!-- spec-guard: no-todo -->' > "$PROJECT/tasks/m02/plan.md"
check "全部带声明时警告数为 0" 0 "0 警告"
check_absent "全部带声明时没有汇总警告" "没有 todo.md"

# tracker 字段已退役，不再抑制任何判断：缺 todo 汇总只看文件，与 state.json 的内容无关。
many_modules no-todo-github 3
plan_only m02; mkdir -p "$PROJECT/.agent"
SUMMARY="1 个模块有 Plan 但没有 todo.md，按已完成计：m02"
printf '{"tracker":"github","modules":{}}\n' > "$PROJECT/.agent/state.json"
check "退役 tracker github 不再抑制缺 todo 汇总" 0 "$SUMMARY"
printf '{"tracker":"gitlab","modules":{}}\n' > "$PROJECT/.agent/state.json"
check "退役 tracker gitlab 不再抑制缺 todo 汇总" 0 "$SUMMARY"
printf '{"activeModule":""}\n' > "$PROJECT/.agent/state.json"
check "当前格式的 state.json 同样发缺 todo 汇总" 0 "$SUMMARY"

# 历史状态文件告警只针对真正的退役字段，不对插件自己刚装的 state.json 报警。
LEGACY="检测到已退役的 tracker 字段"
project legacy-state; mkdir -p "$PROJECT/.agent"
printf '{"activeModule":""}\n' > "$PROJECT/.agent/state.json"
check_absent "当前格式的 state.json 不发历史状态告警" "$LEGACY"
check "当前格式的 state.json 没有警告" 0 "0 警告"
printf '{"tracker":"none","modules":{},"activeModule":""}\n' > "$PROJECT/.agent/state.json"
check "含 tracker 键时发退役字段告警" 0 "$LEGACY"
rm -f "$PROJECT/.agent/state.json"
check_absent "没有 state.json 时不发退役字段告警" "$LEGACY"

echo "verify-artifacts regression passed ($PASS cases)"
