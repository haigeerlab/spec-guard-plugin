#!/usr/bin/env bash
# Read-only guidance for the local multi-spec convention and legacy migration.
set -u

# 只用 bash 内建取脚本目录：本 hook 只能依赖 bash、git 与 python3。
case "${BASH_SOURCE[0]}" in */*) HOOKDIR="${BASH_SOURCE[0]%/*}" ;; *) HOOKDIR=. ;; esac
HOOKDIR="$(cd "$HOOKDIR" && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" 2>/dev/null || exit 0

# 激活信号必须是本插件写下的：独占一行的声明块标记（与 managed-block.py 相同），或带已知
# tracker 值的 state.json。正文里提到标记、或别的工具的 .agent/state.json 都不算。
has_block() {
  if grep -Eq '^[[:space:]]*<!-- BEGIN:agent-skills-convention -->[[:space:]]*$' CLAUDE.md 2>/dev/null; then
    return 0
  fi
  grep -Eq '^[[:space:]]*<!-- BEGIN:spec-guard-codex-convention -->[[:space:]]*$' AGENTS.md 2>/dev/null
}

has_state() {
  grep -Eq '"tracker"[[:space:]]*:[[:space:]]*"(none|github|gitlab)"' .agent/state.json 2>/dev/null
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

legacy_tracker() {
  [ -f .agent/state.json ] || return 1
  python3 - .agent/state.json <<'PY'
import json
import sys
try:
    value = json.load(open(sys.argv[1], encoding="utf-8")).get("tracker")
except Exception:
    value = None
raise SystemExit(0 if value in {"github", "gitlab"} else 1)
PY
}

SPECS=0
for spec in spec/*.md; do
  [ -e "$spec" ] || continue
  [ "${spec##*/}" = CAPABILITY-MAP.md ] || SPECS=$((SPECS + 1))
done

if legacy_tracker; then
  emit "## spec-guard migration notice (read-only)

当前阶段: **LEGACY_TRACKER_RETIRED**

- A previous remote-tracker state file is present.
- This release does not read its mappings, contact a tracker, select tasks, or modify local state.

Preserve the file and remote records as history. Complete or close any remaining tracker work with v0.14.0 before upgrading; use the retirement migration guide for the manual path."
  exit 0
fi

if [ ! -f spec/CAPABILITY-MAP.md ]; then
  emit "## spec-guard local workflow

当前阶段: **IDLE**

- Capability map: absent
- Module specs: ${SPECS}

Suggested next step: create and review a capability map before planning."
  exit 0
fi

if [ "$SPECS" -eq 0 ]; then
  emit "## spec-guard local workflow

当前阶段: **MAP_ONLY**

- Capability map: present
- Module specs: absent

Suggested next step: write the first reviewed module spec under \`spec/\`."
  exit 0
fi

# 按模块判断当前在哪一步（module_stage.py，只读）；它失败时注入诊断，而不是静默。
if STAGE="$(python3 "$HOOKDIR/module_stage.py" . 2>/dev/null)"; then
  emit "## spec-guard local workflow

${STAGE}"
else
  emit "## spec-guard local workflow

当前阶段: **UNKNOWN**

- Module specs: ${SPECS}
- The module stage could not be computed; run \`/spec-guard:verify-artifacts\` for details."
fi
