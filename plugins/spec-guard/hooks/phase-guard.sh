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
has_block() {
  if grep -Eq '^[[:space:]]*<!-- BEGIN:agent-skills-convention -->[[:space:]]*$' CLAUDE.md 2>/dev/null; then
    return 0
  fi
  grep -Eq '^[[:space:]]*<!-- BEGIN:spec-guard-codex-convention -->[[:space:]]*$' AGENTS.md 2>/dev/null
}

has_state() {
  grep -Eq '"activeModule"[[:space:]]*:' .agent/state.json 2>/dev/null
}

has_block || has_state || exit 0

# 已启用却缺 python3 时不能静默：静默会被当成“未启用”。这段 JSON 手写转义，不依赖 python3。
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"spec-guard: 本项目已启用约定，但 python3 不可用，本轮没有阶段注入。这不是「未启用」；安装 python3 后恢复。"}}'
  exit 0
fi

emit() {
  printf '%s' "$1" | python3 -c '
import json, sys
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": sys.stdin.read(),
}}))
'
}

# 会话事实（session_context.py，只读）：第一行是主会话上下文 token 数，第二行是位置行，读不到为空。
# hook 输入已在上面读过，这里转交那一行原文。
FACTS="$(printf '%s' "$HOOK_INPUT" | python3 "$HOOKDIR/session_context.py" . 2>/dev/null)" || FACTS=""
TOKENS="${FACTS%%$'\n'*}"
case "$TOKENS" in ''|*[!0-9]*) TOKENS="" ;; esac
LOCATION=""
case "$FACTS" in *$'\n'*) LOCATION="${FACTS#*$'\n'}" ;; esac
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
if STAGE="$(python3 "$HOOKDIR/module_stage.py" . ${TOKENS:+--context-tokens "$TOKENS"} 2>/dev/null)"; then
  emit "${HEADER}

${STAGE}"
else
  emit "${HEADER}

当前阶段: **UNKNOWN**

- Module specs: ${SPECS}
- The module stage could not be computed; run \`/spec-guard:verify-artifacts\` for details."
fi
