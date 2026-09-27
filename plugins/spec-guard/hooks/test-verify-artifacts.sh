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

echo "verify-artifacts regression passed ($PASS cases)"
