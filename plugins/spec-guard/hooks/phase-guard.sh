#!/usr/bin/env bash
# Read-only guidance for the local multi-spec convention.
set -u

# 只用 bash 内建取脚本目录：本 hook 只能依赖 bash、git 与 python3。
case "${BASH_SOURCE[0]}" in */*) HOOKDIR="${BASH_SOURCE[0]%/*}" ;; *) HOOKDIR=. ;; esac
HOOKDIR="$(cd "$HOOKDIR" && pwd)"
# Claude Code 提供 CLAUDE_PROJECT_DIR；Codex 不提供，并在会话目录里运行 hook。
# 从仓库子目录启动时按 git 仓库根目录判断激活，不在仓库里时才用当前目录。
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  ROOT="$CLAUDE_PROJECT_DIR"
else
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || ROOT=""
  [ -n "$ROOT" ] || ROOT="$(pwd)"
fi
# 桌面版 worktree 会话里，宿主给的项目目录可能是主检出目录，而会话在 linked worktree 里：hook 输入的 cwd
# 所在 git 仓库优先（session_context.py --resolve-root，最多等 1 秒）。标准输入只读这一次，原文留给后面的会话事实。
# 输入不可用或缺 python3 时根目录不变。
HOOK_INPUT=""
if [ ! -t 0 ] && command -v python3 >/dev/null 2>&1; then
  RESOLVED="$(python3 "$HOOKDIR/session_context.py" --resolve-root "$ROOT" 2>/dev/null)" || RESOLVED=""
  case "$RESOLVED" in *$'\n'*) ROOT="${RESOLVED%%$'\n'*}"; HOOK_INPUT="${RESOLVED#*$'\n'}" ;; esac
fi
cd "$ROOT" 2>/dev/null || exit 0

# 激活信号必须是本插件写下的：独占一行的声明块标记（与 managed-block.py 相同），或含
# activeModule 的 state.json。正文里提到标记不算。注意判据是纯文本匹配：别的工具若在自己的
# .agent/state.json 里也用 activeModule 这个键（包括嵌套位置），同样会激活——比此前那条按值匹配
# 的判据宽。代价有限：本 hook 只读文件并打印阶段，不写任何东西。
# activeModule 是本插件写这个文件的唯一理由，所以它是准确的激活证据；此前判据用的
# `tracker` 字段已随远端 tracker 模式退役（docs/retirements/state-tracker-field.md）。
# 逐行匹配只用 bash 内建（不依赖 grep；审查 F12）：$2 是扩展正则，读不到文件即不匹配。
file_has_line() {  # $1=文件 $2=正则
  local line pattern="$2"
  [ -r "$1" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    [[ $line =~ $pattern ]] && return 0
  done < "$1"
  return 1
}

has_block() {
  file_has_line CLAUDE.md '^[[:space:]]*<!-- BEGIN:agent-skills-convention -->[[:space:]]*$' ||
    file_has_line AGENTS.md '^[[:space:]]*<!-- BEGIN:spec-guard-codex-convention -->[[:space:]]*$'
}

has_state() {
  file_has_line .agent/state.json '"activeModule"[[:space:]]*:'
}

has_block || has_state || exit 0

# 已启用却缺 python3 时不能静默：静默会被当成“未启用”。这段 JSON 手写转义，不依赖 python3。
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"spec-guard: 本项目已启用约定，但 python3 不可用，本轮没有阶段注入。这不是「未启用」；安装 python3 后恢复。"}}'
  exit 0
fi

# python3 在 PATH 上却跑不起来时 emit 自己也会失败；同样不能静默，退回一段手写转义的 JSON。
emit() {
  local out
  out="$(printf '%s' "$1" | python3 -c '
import json, sys
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": sys.stdin.read(),
}}))
' 2>/dev/null)" || out=""
  case "$out" in
    '{'*) printf '%s\n' "$out" ;;
    *) printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"spec-guard: 本项目已启用约定，但 python3 无法运行，本轮没有阶段注入。这不是「未启用」；修复 python3 后恢复。"}}' ;;
  esac
}

# 会话事实（session_context.py，只读）：第一行是主会话上下文 token 数，第二行是位置行，读不到为空。
# hook 输入已在上面读过，这里转交那一行原文。
FACTS="$(printf '%s' "$HOOK_INPUT" | python3 "$HOOKDIR/session_context.py" . 2>/dev/null)" || FACTS=""
TOKENS="${FACTS%%$'\n'*}"
case "$TOKENS" in ''|*[!0-9]*) TOKENS="" ;; esac
LOCATION=""
case "$FACTS" in *$'\n'*) LOCATION="${FACTS#*$'\n'}" ;; esac
# 第三行是 Codex 记录里的上下文窗口（Claude 为空）。
WINDOW=""
case "$LOCATION" in *$'\n'*) WINDOW="${LOCATION#*$'\n'}" ;; esac
# 第四行是 unattended（claude -p、codex exec）或空：没人在场时不出「请告诉用户 /compact、/clear」那两行。
UNATTENDED=""
case "$WINDOW" in *$'\n'unattended*) UNATTENDED=1 ;; esac
WINDOW="${WINDOW%%$'\n'*}"
case "$WINDOW" in ''|*[!0-9]*) WINDOW="" ;; esac
LOCATION="${LOCATION%%$'\n'*}"
# 位置行放在标题与“当前阶段”之间，所有阶段都带；不在 git 仓库里时没有这一行。
HEADER="## spec-guard local workflow"
[ -z "$LOCATION" ] || HEADER="${HEADER}

${LOCATION}"

SPECS=0
for spec in spec/*.md; do
  [ -e "$spec" ] || continue
  [ "${spec##*/}" = CAPABILITY-MAP.md ] || SPECS=$((SPECS + 1))
done

# 能力图存在却读不了是读取故障，不是能力图的状态：不论有没有模块 spec 都报 UNKNOWN（与 module_stage 同一行）。
if [ -e spec/CAPABILITY-MAP.md ] && { [ ! -f spec/CAPABILITY-MAP.md ] || [ ! -r spec/CAPABILITY-MAP.md ]; }; then
  if [ ! -f spec/CAPABILITY-MAP.md ]; then REASON="not a regular file"; else REASON="no read permission"; fi
  emit "${HEADER}

当前阶段: **UNKNOWN**

- Capability map: present but unreadable (${REASON})
- Module specs: ${SPECS}

Suggested next step: make \`spec/CAPABILITY-MAP.md\` a readable file (check its permissions), then send the next prompt; this is a read failure, not a state of the map."
  exit 0
fi

if [ ! -f spec/CAPABILITY-MAP.md ]; then
  emit "${HEADER}

当前阶段: **IDLE**

- Capability map: absent
- Module specs: ${SPECS}

Suggested next step: create and review a capability map before planning."
  exit 0
fi

if [ "$SPECS" -eq 0 ]; then
  emit "${HEADER}

当前阶段: **MAP_ONLY**

- Capability map: present
- Module specs: absent

Suggested next step: write the first reviewed module spec under \`spec/\`."
  exit 0
fi

# 按模块判断当前在哪一步（module_stage.py，只读）；它失败时注入诊断，而不是静默。
if STAGE="$(python3 "$HOOKDIR/module_stage.py" . ${TOKENS:+--context-tokens "$TOKENS"} ${WINDOW:+--context-window "$WINDOW"} ${UNATTENDED:+--unattended} 2>/dev/null)"; then
  emit "${HEADER}

${STAGE}"
else
  emit "${HEADER}

当前阶段: **UNKNOWN**

- Module specs: ${SPECS}
- The module stage could not be computed; run \`/spec-guard:verify-artifacts\` for details."
fi
