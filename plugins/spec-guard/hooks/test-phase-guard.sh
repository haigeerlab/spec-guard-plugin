#!/usr/bin/env bash
set -euo pipefail

HOOKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PASS=0

fail() { echo "  ❌ $1" >&2; exit 1; }

run() {  # $1=项目目录；可用 RUN_PATH 替换 PATH
  PATH="${RUN_PATH:-$PATH}" CLAUDE_PROJECT_DIR="$1" /bin/bash "$HOOKDIR/phase-guard.sh" </dev/null
}

silent() {  # $1=用例名 $2=项目目录
  [ -z "$(run "$2")" ] || fail "$1: 应当静默，实际有输出"
  echo "  ✅ $1"; PASS=$((PASS + 1))
}

# 每条非空输出都必须是宿主接受的 UserPromptSubmit JSON，且正文包含期望文本。
injects() {  # $1=用例名 $2=项目目录 $3=正文必须包含的文本
  local out
  out="$(run "$2")"
  python3 -c '
import json, sys
output = json.loads(sys.stdin.read())["hookSpecificOutput"]
assert output["hookEventName"] == "UserPromptSubmit"
assert sys.argv[1] in output["additionalContext"], output["additionalContext"]
' "$3" <<<"$out" || fail "$1: 输出不是期望的 hook JSON
$out"
  echo "  ✅ $1"; PASS=$((PASS + 1))
}

map() {  # $1=项目目录
  mkdir -p "$1/spec"
  printf '%s\n' '# Capability Map' '| Module id | Responsibility | Depends on |' '|---|---|---|' \
    '| alpha | x | — |' '' 'Build order: alpha' > "$1/spec/CAPABILITY-MAP.md"
}

mkdir -p "$WORK/empty"
silent "无激活信号的目录静默" "$WORK/empty"

mkdir -p "$WORK/other-state/.agent"
printf '%s\n' '{"session":"x"}' > "$WORK/other-state/.agent/state.json"
silent "别的工具的 .agent/state.json 不激活" "$WORK/other-state"

mkdir -p "$WORK/prose"
printf '%s\n' '本项目不用 `<!-- BEGIN:agent-skills-convention -->` 这个块。' > "$WORK/prose/CLAUDE.md"
silent "正文里提到标记不激活" "$WORK/prose"

mkdir -p "$WORK/idle/.agent"
printf '%s\n' '{"tracker":"none","modules":{},"activeModule":""}' > "$WORK/idle/.agent/state.json"
injects "setup 写下的 state.json 激活并报告 IDLE" "$WORK/idle" "IDLE"

mkdir -p "$WORK/crlf"
printf '%s\r\n' '<!-- BEGIN:agent-skills-convention -->' '<!-- END:agent-skills-convention -->' > "$WORK/crlf/CLAUDE.md"
map "$WORK/crlf"
injects "CRLF 声明块激活并报告 MAP_ONLY" "$WORK/crlf" "MAP_ONLY"

local_project="$WORK/local"
mkdir -p "$local_project"
printf '%s\n' '<!-- BEGIN:spec-guard-codex-convention -->' > "$local_project/AGENTS.md"
map "$local_project"
injects "Codex 声明块激活并提示首个 spec" "$local_project" 'spec/'
touch "$local_project/spec/alpha.md"
injects "有 spec 没 plan 时报告 NEEDS_PLAN" "$local_project" "当前阶段: **NEEDS_PLAN**"
injects "指出当前模块" "$local_project" 'Current module: `alpha` (next in Build order)'
if grep -Eqi 'sync-map|spec-github-bridge|spec-gitlab-bridge' <<<"$(run "$local_project")"; then
  fail "legacy tracker advice leaked into local phase output"
fi

# 按模块判断：plan 与 todo 决定 BUILDING／DONE，activeModule 决定当前模块。
stages="$WORK/stages"
mkdir -p "$stages/spec" "$stages/tasks/alpha" "$stages/tasks/beta" "$stages/.agent"
printf '%s\n' '<!-- BEGIN:agent-skills-convention -->' > "$stages/CLAUDE.md"
printf '%s\n' '# Capability Map' '| Module id | Responsibility | Depends on |' '|---|---|---|' \
  '| alpha | x | — |' '| beta | y | alpha |' '' 'Build order: alpha → beta' > "$stages/spec/CAPABILITY-MAP.md"
touch "$stages/spec/alpha.md" "$stages/spec/beta.md"
printf '# Plan\n' > "$stages/tasks/alpha/plan.md"
printf '%s\n' '- [x] done' '- [ ] one' '* [ ] two' > "$stages/tasks/alpha/todo.md"
injects "todo 有未勾选项时报告 BUILDING" "$stages" "当前阶段: **BUILDING**"
injects "BUILDING 给出剩余项数" "$stages" "2 unchecked item(s) in \`tasks/alpha/todo.md\`"
injects "进行中时的全局计数" "$stages" "Modules 2 · Specs 2 · Plans 1 · In progress 1 · Done 0"
printf '%s\n' '- [x] done' '- [X] one' > "$stages/tasks/alpha/todo.md"
injects "当前模块完成后推进到下一个模块" "$stages" 'Current module: `beta` (next in Build order)'
printf '{"tracker":"none","modules":{},"activeModule":"alpha"}\n' > "$stages/.agent/state.json"
injects "activeModule 优先于 Build order" "$stages" 'Current module: `alpha` (activeModule)'
printf '{"tracker":"none","modules":{},"activeModule":"ghost"}\n' > "$stages/.agent/state.json"
injects "activeModule 不在图中时提示并回退" "$stages" 'activeModule `ghost` is not in the capability map'
printf '# Plan\n' > "$stages/tasks/beta/plan.md"
injects "全部完成时报告 DONE 并指向 Proposal" "$stages" "当前阶段: **DONE**"
injects "DONE 附全局计数" "$stages" "Modules 2 · Specs 2 · Plans 2 · In progress 0 · Done 2"
rm "$stages/spec/beta.md"
injects "缺 Spec 的模块报告 NEEDS_SPEC" "$stages" "当前阶段: **NEEDS_SPEC**"
printf '%s\n' '| alpha | x | — |' > "$stages/spec/CAPABILITY-MAP.md"
injects "能力图无效时报告 MAP_INVALID" "$stages" "当前阶段: **MAP_INVALID**"
printf '%s\n' '# Capability Map' '| Module id | Responsibility | Depends on |' '|---|---|---|' \
  '| alpha | x | — |' '' 'Build order: alpha' > "$stages/spec/CAPABILITY-MAP.md"
printf '\377\376 not utf-8\n' > "$stages/tasks/alpha/todo.md"
injects "阶段无法计算时注入诊断而不是静默" "$stages" "当前阶段: **UNKNOWN**"

legacy_project="$WORK/legacy"
mkdir -p "$legacy_project/.agent"
printf '%s\n' '{"tracker":"github","modules":{"alpha":{"issue":1}}}' > "$legacy_project/.agent/state.json"
injects "旧 tracker state 按本地约定报告阶段" "$legacy_project" "当前阶段: **IDLE**"
if grep -Eqi 'LEGACY|migration notice|sync-map|spec-github-bridge|spec-gitlab-bridge' <<<"$(run "$legacy_project")"; then
  fail "旧 tracker state 不应再注入迁移提示或已退役的调用路径"
fi

# 已启用却缺 python3：必须注入可诊断的合法 JSON，不能静默成“未启用”。
mkdir -p "$WORK/nopy"
ln -sf "$(command -v grep)" "$WORK/nopy/grep"
RUN_PATH="$WORK/nopy" injects "已启用但缺 python3 时注入诊断" "$local_project" "python3 不可用"
[ -z "$(RUN_PATH="$WORK/nopy" run "$WORK/other-state")" ] || fail "缺 python3 时无关项目也必须静默"

echo "phase-guard regression passed (${PASS} cases)"
