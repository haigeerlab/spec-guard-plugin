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

# 与 injects 相同的 JSON 校验，但要求正文不包含指定文本。
lacks() {  # $1=用例名 $2=项目目录 $3=正文不得包含的文本
  local out
  out="$(run "$2")"
  python3 -c '
import json, sys
output = json.loads(sys.stdin.read())["hookSpecificOutput"]
assert output["hookEventName"] == "UserPromptSubmit"
assert sys.argv[1] not in output["additionalContext"], output["additionalContext"]
' "$3" <<<"$out" || fail "$1: 输出不是期望的 hook JSON，或含有不该出现的文本
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
# 模块完成而项目未完成：activeModule 指向已完成模块，beta 还没有 plan。
printf '{"tracker":"none","modules":{},"activeModule":"alpha"}\n' > "$stages/.agent/state.json"
injects "activeModule 已完成但项目未完成时报告 MODULE_DONE" "$stages" "当前阶段: **MODULE_DONE**"
injects "MODULE_DONE 仍指出当前模块" "$stages" 'Current module: `alpha` (activeModule)'
injects "MODULE_DONE 指向 Build order 中第一个未完成模块" "$stages" '`beta`'
injects "MODULE_DONE 报告该模块自己的阶段" "$stages" 'NEEDS_PLAN'
lacks "MODULE_DONE 不再冒充项目 DONE" "$stages" "当前阶段: **DONE**"
printf '# Plan\n' > "$stages/tasks/beta/plan.md"
# 全部完成且 activeModule 不在图中：回退后仍是项目 DONE（与拆分前同一场景）。
printf '{"tracker":"none","modules":{},"activeModule":"ghost"}\n' > "$stages/.agent/state.json"
injects "全部完成时报告 DONE" "$stages" "当前阶段: **DONE**"
injects "DONE 指向 /spec-guard:add-module" "$stages" "/spec-guard:add-module"
injects "DONE 把 Proposal 作为可选的留痕方式" "$stages" "use a Proposal when the addition needs a recorded, reviewed decision"
injects "DONE 附全局计数" "$stages" "Modules 2 · Specs 2 · Plans 2 · In progress 0 · Done 2"
# 全部完成但 activeModule 仍指向已完成模块：仍是项目 DONE，并提示可清除。
printf '{"tracker":"none","modules":{},"activeModule":"alpha"}\n' > "$stages/.agent/state.json"
injects "全部完成且 activeModule 未清除时仍报告 DONE" "$stages" "当前阶段: **DONE**"
injects "全部完成且 activeModule 未清除时指向 add-module" "$stages" "/spec-guard:add-module"
injects "全部完成且 activeModule 未清除时提示可清除" "$stages" 'activeModule `alpha` is already done and can be cleared'
lacks "全部完成时不出现模块级提示" "$stages" "before building it"
# 全部完成且没有 activeModule：输出不带清除提示。
printf '{"tracker":"none","modules":{},"activeModule":""}\n' > "$stages/.agent/state.json"
injects "全部完成且无 activeModule 时报告 DONE" "$stages" "当前阶段: **DONE**"
lacks "全部完成且无 activeModule 时无清除提示" "$stages" "can be cleared"
rm "$stages/spec/beta.md"
injects "缺 Spec 的模块报告 NEEDS_SPEC" "$stages" "当前阶段: **NEEDS_SPEC**"
printf '%s\n' '| alpha | x | — |' > "$stages/spec/CAPABILITY-MAP.md"
injects "能力图无效时报告 MAP_INVALID" "$stages" "当前阶段: **MAP_INVALID**"
printf '%s\n' '# Capability Map' '| Module id | Responsibility | Depends on |' '|---|---|---|' \
  '| alpha | x | — |' '' 'Build order: alpha' > "$stages/spec/CAPABILITY-MAP.md"
printf '\377\376 not utf-8\n' > "$stages/tasks/alpha/todo.md"
injects "阶段无法计算时注入诊断而不是静默" "$stages" "当前阶段: **UNKNOWN**"

# 插队：base 完成、infra 做到一半，当前模块是 urgent。
paused="$WORK/paused"
mkdir -p "$paused/spec" "$paused/tasks/base" "$paused/tasks/urgent" "$paused/tasks/infra" "$paused/.agent"
printf '%s\n' '<!-- BEGIN:agent-skills-convention -->' > "$paused/CLAUDE.md"
printf '%s\n' '# Capability Map' '| Module id | Responsibility | Depends on |' '|---|---|---|' \
  '| base | x | — |' '| urgent | y | base |' '| infra | z | base |' '' 'Build order: base → urgent → infra' > "$paused/spec/CAPABILITY-MAP.md"
touch "$paused/spec/base.md" "$paused/spec/infra.md"
printf '# Plan\n' > "$paused/tasks/base/plan.md"
printf '# Plan\n' > "$paused/tasks/infra/plan.md"
printf '%s\n' '- [x] done' > "$paused/tasks/base/todo.md"
printf '%s\n' '- [x] a' '- [ ] b' > "$paused/tasks/infra/todo.md"
printf '{"tracker":"none","modules":{},"activeModule":"urgent"}\n' > "$paused/.agent/state.json"
injects "插队缺 Spec 时报告 NEEDS_SPEC" "$paused" "当前阶段: **NEEDS_SPEC**"
injects "NEEDS_SPEC 显示被暂停的模块" "$paused" '- Paused: `infra` (1 unchecked item(s)); resume it after `urgent`.'
touch "$paused/spec/urgent.md"
injects "插队缺 Plan 时显示被暂停的模块" "$paused" '- Paused: `infra` (1 unchecked item(s)); resume it after `urgent`.'
printf '# Plan\n' > "$paused/tasks/urgent/plan.md"
printf '%s\n' '- [ ] u1' > "$paused/tasks/urgent/todo.md"
injects "插队 BUILDING 时报告阶段" "$paused" "当前阶段: **BUILDING**"
injects "BUILDING 显示被暂停的模块" "$paused" '- Paused: `infra` (1 unchecked item(s)); resume it after `urgent`.'
printf '%s\n' '- [x] u1' > "$paused/tasks/urgent/todo.md"
injects "插队完成后报告 MODULE_DONE" "$paused" "当前阶段: **MODULE_DONE**"
injects "MODULE_DONE 显示被暂停的模块" "$paused" '- Paused: `infra` (1 unchecked item(s)); resume it after `urgent`.'
injects "MODULE_DONE 点名被暂停的模块" "$paused" 'resume paused module `infra` (BUILDING). Set activeModule to it.'
printf '%s\n' '- [x] a' '- [x] b' > "$paused/tasks/infra/todo.md"
lacks "没有被暂停模块时不出现 Paused" "$paused" "Paused"
printf '%s\n' '- [ ] a' '- [ ] b' > "$paused/tasks/infra/todo.md"
lacks "只有未勾选项的模块不算被暂停" "$paused" "Paused"
printf '%s\n' '- [x] a' '- [ ] b' > "$paused/tasks/infra/todo.md"
printf '{"tracker":"none","modules":{},"activeModule":"infra"}\n' > "$paused/.agent/state.json"
lacks "当前模块自己做到一半时不算被暂停" "$paused" "Paused"

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

# 有 Plan 无 todo.md 的模块按已完成计；activeModule 指向它时给出提醒。
notodo="$WORK/notodo"
mkdir -p "$notodo/spec" "$notodo/tasks/base" "$notodo/tasks/alpha" "$notodo/tasks/beta" "$notodo/.agent"
printf '%s\n' '<!-- BEGIN:agent-skills-convention -->' > "$notodo/CLAUDE.md"
printf '%s\n' '# Capability Map' '| Module id | Responsibility | Depends on |' '|---|---|---|' \
  '| base | x | — |' '| alpha | y | base |' '| beta | z | alpha |' '' 'Build order: base → alpha → beta' > "$notodo/spec/CAPABILITY-MAP.md"
touch "$notodo/spec/base.md" "$notodo/spec/alpha.md" "$notodo/spec/beta.md"
printf '# Plan\n' | tee "$notodo/tasks/base/plan.md" "$notodo/tasks/alpha/plan.md" "$notodo/tasks/beta/plan.md" > /dev/null
printf '%s\n' '- [x] done' > "$notodo/tasks/base/todo.md"
printf '%s\n' '- [x] a' '- [ ] b' > "$notodo/tasks/beta/todo.md"
printf '{"tracker":"none","modules":{},"activeModule":"alpha"}\n' > "$notodo/.agent/state.json"
NOTODO_NOTE='activeModule `alpha` has a plan but no `tasks/alpha/todo.md`, so it counts as done; add the todo if work remains.'
injects "无 todo 的 activeModule 且项目未完成时报告 MODULE_DONE" "$notodo" "当前阶段: **MODULE_DONE**"
injects "MODULE_DONE 给出缺 todo 提醒" "$notodo" "$NOTODO_NOTE"
python3 -c '
import json, sys
text = json.loads(sys.stdin.read())["hookSpecificOutput"]["additionalContext"]
note, counts, paused = sys.argv[1], "- Modules 3", "- Paused:"
assert counts in text and paused in text and note in text, text
assert text.index(counts) < text.index(note) < text.index(paused), text
' "$NOTODO_NOTE" <<<"$(run "$notodo")" || fail "缺 todo 提醒应在计数行之后、Paused 行之前"
echo "  ✅ 缺 todo 提醒位于计数行与 Paused 行之间"; PASS=$((PASS + 1))
printf '%s\n' '- [x] a' '- [x] b' > "$notodo/tasks/beta/todo.md"
injects "无 todo 的 activeModule 且全部完成时报告 DONE" "$notodo" "当前阶段: **DONE**"
injects "DONE 给出缺 todo 提醒" "$notodo" "$NOTODO_NOTE"
injects "DONE 仍保留可清除提示" "$notodo" 'activeModule `alpha` is already done and can be cleared'
python3 -c '
import json, sys
text = json.loads(sys.stdin.read())["hookSpecificOutput"]["additionalContext"]
assert text.index(sys.argv[1]) < text.index("already done and can be cleared"), text
' "$NOTODO_NOTE" <<<"$(run "$notodo")" || fail "DONE 中缺 todo 提醒应在可清除提示之前"
echo "  ✅ DONE 中缺 todo 提醒先于可清除提示"; PASS=$((PASS + 1))
printf '{"tracker":"none","modules":{},"activeModule":"base"}\n' > "$notodo/.agent/state.json"
lacks "activeModule 有全勾 todo 时无缺 todo 提醒" "$notodo" "has a plan but no"
rm "$notodo/.agent/state.json"
lacks "无 activeModule 时不因其他缺 todo 模块提醒" "$notodo" "has a plan but no"
printf '{"tracker":"none","modules":{},"activeModule":"ghost"}\n' > "$notodo/.agent/state.json"
lacks "activeModule 不在图中时无缺 todo 提醒" "$notodo" "has a plan but no"

# Codex 不提供 CLAUDE_PROJECT_DIR，hook 在会话目录里运行（2026-09-28 真实 Codex 核实）。
# 从仓库子目录启动时，必须按 git 仓库根目录判断激活，而不是只看当前目录。
run_from() {  # $1=工作目录；不设 CLAUDE_PROJECT_DIR，模拟 Codex
  (cd "$1" && env -u CLAUDE_PROJECT_DIR /bin/bash "$HOOKDIR/phase-guard.sh" </dev/null)
}
git_project="$WORK/git-project"
mkdir -p "$git_project/src/deep"
git -C "$git_project" init -q
printf '%s\n' '<!-- BEGIN:spec-guard-codex-convention -->' > "$git_project/AGENTS.md"
out="$(run_from "$git_project/src/deep")"
python3 -c '
import json, sys
text = json.loads(sys.stdin.read())["hookSpecificOutput"]["additionalContext"]
assert "当前阶段: **IDLE**" in text, text
' <<<"$out" || fail "Codex 从仓库子目录启动时应按仓库根目录注入阶段
$out"
echo "  ✅ Codex 从仓库子目录启动时按仓库根目录注入"; PASS=$((PASS + 1))
unrelated="$WORK/unrelated-git"
mkdir -p "$unrelated/sub"
git -C "$unrelated" init -q
[ -z "$(run_from "$unrelated/sub")" ] || fail "无激活信号的仓库子目录必须静默"
echo "  ✅ 无激活信号的仓库子目录静默"; PASS=$((PASS + 1))
plain="$WORK/not-git"
mkdir -p "$plain"
printf '%s\n' '<!-- BEGIN:spec-guard-codex-convention -->' > "$plain/AGENTS.md"
python3 -c '
import json, sys
assert "当前阶段: **IDLE**" in json.loads(sys.stdin.read())["hookSpecificOutput"]["additionalContext"]
' <<<"$(run_from "$plain")" || fail "非 git 目录应退回当前目录判断"
echo "  ✅ 非 git 目录退回当前目录"; PASS=$((PASS + 1))

echo "phase-guard regression passed (${PASS} cases)"
