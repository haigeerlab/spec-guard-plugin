#!/usr/bin/env bash
# Install the local, file-backed multi-spec convention.  Remote tracker modes
# were retired and deliberately do not have a fallback.
set -euo pipefail

HOST="claude"
DRY=false
REPLACE=false
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
    *) echo "usage: setup-convention.sh [local] [--host=codex] [--dry-run] [--replace]" >&2; exit 2 ;;
  esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$PROJECT"
ROOT="$(cd "$HERE/.." && pwd)"
if [ "$HOST" = codex ]; then
  TARGET=AGENTS.md
  TEMPLATE="$ROOT/templates/codex-block-local.md"
  BEGIN='<!-- BEGIN:spec-guard-codex-convention -->'
  END='<!-- END:spec-guard-codex-convention -->'
else
  TARGET=CLAUDE.md
  TEMPLATE="$ROOT/templates/claude-block-local.md"
  BEGIN='<!-- BEGIN:agent-skills-convention -->'
  END='<!-- END:agent-skills-convention -->'
fi

BLOCK_TOOL="$HERE/managed-block.py"

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
      return
    fi
    if [ "$DRY" = true ]; then
      printf '  • replace the convention block in %s\n' "$TARGET"
      return
    fi
    python3 "$BLOCK_TOOL" replace "$TARGET" "$BEGIN" "$END" "$TEMPLATE" >/dev/null
    printf '  ✅ updated %s\n' "$TARGET"
    return
  fi
  if [ "$DRY" = true ]; then
    printf '  • append a convention block to %s\n' "$TARGET"
    return
  fi
  [ -f "$TARGET" ] && printf '\n' >> "$TARGET"
  { printf '%s\n' "$BEGIN"; cat "$TEMPLATE"; printf '%s\n' "$END"; } >> "$TARGET"
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
fi
