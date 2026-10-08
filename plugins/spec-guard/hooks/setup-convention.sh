#!/usr/bin/env bash
# Install the local, file-backed multi-spec convention.  Remote tracker modes
# were retired and deliberately do not have a fallback.
set -euo pipefail

HOST="claude"
DRY=false
REPLACE=false
DISPATCH_ARG=""
for arg in "$@"; do
  case "$arg" in
    local) : ;;
    github|gitlab)
      echo "${arg} tracker mode was retired; no files were changed." >&2
      exit 2
      ;;
    --host=codex) HOST=codex ;;
    --dry-run) DRY=true ;;
    --replace) REPLACE=true ;;
    --dispatch|--no-dispatch)
      want=on; [ "$arg" = --no-dispatch ] && want=off
      if [ -n "$DISPATCH_ARG" ] && [ "$DISPATCH_ARG" != "$want" ]; then
        echo "--dispatch and --no-dispatch are mutually exclusive; no files were changed." >&2
        exit 2
      fi
      DISPATCH_ARG="$want"
      ;;
    *) echo "usage: setup-convention.sh [local] [--host=codex] [--dry-run] [--replace] [--dispatch|--no-dispatch]" >&2; exit 2 ;;
  esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$PROJECT"
ROOT="$(cd "$HERE/.." && pwd)"
if [ "$HOST" = codex ]; then
  TARGET=AGENTS.md
  TEMPLATE="$ROOT/templates/codex-block-local.md"
  RULE="$ROOT/templates/codex-dispatch-rule.md"
  BEGIN='<!-- BEGIN:spec-guard-codex-convention -->'
  END='<!-- END:spec-guard-codex-convention -->'
else
  TARGET=CLAUDE.md
  TEMPLATE="$ROOT/templates/claude-block-local.md"
  RULE="$ROOT/templates/claude-dispatch-rule.md"
  BEGIN='<!-- BEGIN:agent-skills-convention -->'
  END='<!-- END:agent-skills-convention -->'
fi

BLOCK_TOOL="$HERE/managed-block.py"
# 可选的 build-task-dispatch 规则段：开关状态就是块内这一行标记（独占一行，去首尾空白后相等）。
DISPATCH_MARKER='<!-- spec-guard: build-task-dispatch -->'

# 标记必须独占一行（与 managed-block.py、phase-guard 相同）；正文里提到标记不算已有声明块。
marker_lines() {
  [ -f "$TARGET" ] || { echo 0; return; }
  grep -Ec "^[[:space:]]*($BEGIN|$END)[[:space:]]*$" "$TARGET" || true
}

# 任何写入之前先校验已有声明块：重复、缺失或顺序错误都拒绝，不留下半完成的目录或文件。
HAS_BLOCK=false
if [ "$(marker_lines)" -gt 0 ]; then
  python3 "$BLOCK_TOOL" validate "$TARGET" "$BEGIN" "$END" >/dev/null || {
    echo "  ❌ ${TARGET} 的声明块标记无效，未改动任何文件；请先人工修正标记" >&2
    exit 1
  }
  HAS_BLOCK=true
fi

# 期望的规则段状态：显式参数 > 已有块内的标记行 > 关。
dispatch_in_block() {
  awk -v b="$BEGIN" -v e="$END" -v m="$DISPATCH_MARKER" '
    {s=$0; gsub(/^[ \t\r]+|[ \t\r]+$/, "", s)}
    s==e {inb=0}
    inb && s==m {found=1}
    s==b {inb=1}
    END {exit found ? 0 : 1}' "$TARGET"
}
if [ -n "$DISPATCH_ARG" ]; then
  DISPATCH="$DISPATCH_ARG"; DISPATCH_SOURCE=--dispatch
  [ "$DISPATCH_ARG" = on ] || DISPATCH_SOURCE=--no-dispatch
elif [ "$HAS_BLOCK" = true ] && dispatch_in_block; then
  DISPATCH=on; DISPATCH_SOURCE="kept from existing block"
else
  DISPATCH=off; DISPATCH_SOURCE=""
fi
dispatch_status() {
  if [ -n "$DISPATCH_SOURCE" ]; then
    printf '  • build-task-dispatch rule: %s (%s)\n' "$DISPATCH" "$DISPATCH_SOURCE"
  else
    printf '  • build-task-dispatch rule: %s\n' "$DISPATCH"
  fi
}
# 写入内容＝基础模板，开启时其后接规则段；新建与 --replace 共用。
block_content() {
  cat "$TEMPLATE"
  [ "$DISPATCH" = on ] && cat "$RULE"
  return 0
}

# teardown 保留的状态不能被新的空 state 静默遮住；由用户先决定是否恢复。
if [ -e .agent/state.json.disabled ] || [ -L .agent/state.json.disabled ]; then
  if [ -e .agent/state.json ] || [ -L .agent/state.json ]; then
    echo '  ❌ .agent/state.json 与 .agent/state.json.disabled 并存；请先人工核对，未改动任何文件' >&2
  else
    echo '  ❌ 发现 .agent/state.json.disabled；确认要恢复后先改回 .agent/state.json，未改动任何文件' >&2
  fi
  exit 1
fi

install_block() {
  if [ "$HAS_BLOCK" = true ]; then
    if [ "$REPLACE" != true ]; then
      printf '  ⏭ %s already has a convention block (use --replace to update it)\n' "$TARGET"
      [ -z "$DISPATCH_ARG" ] || printf '  ⏭ --dispatch/--no-dispatch only take effect together with --replace\n'
      return
    fi
    if [ "$DRY" = true ]; then
      printf '  • replace the convention block in %s\n' "$TARGET"
      dispatch_status
      return
    fi
    BODY="$(mktemp)"
    trap 'rm -f "$BODY"' EXIT
    block_content > "$BODY"
    python3 "$BLOCK_TOOL" replace "$TARGET" "$BEGIN" "$END" "$BODY" >/dev/null
    printf '  ✅ updated %s\n' "$TARGET"
    return
  fi
  if [ "$DRY" = true ]; then
    printf '  • append a convention block to %s\n' "$TARGET"
    dispatch_status
    return
  fi
  [ -f "$TARGET" ] && printf '\n' >> "$TARGET"
  { printf '%s\n' "$BEGIN"; block_content; printf '%s\n' "$END"; } >> "$TARGET"
  printf '  ✅ updated %s\n' "$TARGET"
}

echo '═══ Spec Guard local convention ═══'
if [ "$DRY" = true ]; then
  echo '  • create spec/, tasks/, and .agent/ when absent'
  echo '  • create a local state file only when absent'
else
  mkdir -p spec tasks .agent
  if [ ! -f .agent/state.json ]; then
    printf '%s\n' '{"activeModule":""}' > .agent/state.json
    echo '  ✅ created .agent/state.json (local only)'
  else
    echo '  ⏭ .agent/state.json already exists; it was not changed'
  fi
  if [ ! -f spec/CAPABILITY-MAP.md ]; then
    cp "$ROOT/templates/CAPABILITY-MAP.md" spec/CAPABILITY-MAP.md
    echo '  ✅ created spec/CAPABILITY-MAP.md'
  else
    echo '  ⏭ spec/CAPABILITY-MAP.md already exists'
  fi
fi
install_block

if [ "$DRY" = true ]; then
  echo '（dry-run; no files were changed）'
else
  echo 'Next: review the capability map, then write module specs and local task lists.'
  echo 'Optional: set the artifact language and review cadence with /spec-guard:config (Codex: spec-guard-ops config).'
fi
