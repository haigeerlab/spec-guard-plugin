#!/bin/bash
# 派活成本对照：在 ledgerlite 种子项目上跑一次完整的 /build auto，留下可由 module_cost_report.py 计价的会话记录。
# 用法：run.sh <claude|codex> <组> <编号>        例：run.sh claude N 1
# 组与 spec-guard 版本的对应见 README.md；组 custom 用 SG_REF（git 引用）与 SG_FLAG（--dispatch 或空）。
# DRY_RUN=1：只建好项目与约定块，不调用宿主。
set -u
HERE="$(cd "$(dirname "$0")" && pwd -P)"
REPO="$(git -C "$HERE" rev-parse --show-toplevel)" || exit 2
host=${1:-}; group=${2:-}; rep=${3:-}
[ -n "$host" ] && [ -n "$group" ] && [ -n "$rep" ] || { sed -n 2,4p "$0" >&2; exit 2; }
overlay=""
case "$host:$group" in
  claude:N) ref=639107e; flag="" ;;
  claude:R) ref=639107e; flag=--dispatch ;;
  claude:F) ref=v0.44.0; flag=--dispatch ;;
  claude:G) ref=v0.44.0; flag=--dispatch; overlay=G ;;
  claude:S) ref=v0.45.0; flag=--dispatch ;;
  codex:N)  ref=d2d1b70; flag="" ;;
  codex:R)  ref=d2d1b70; flag=--dispatch ;;
  codex:F)  ref=v0.44.0; flag=--dispatch; overlay=G ;;
  codex:W)  ref=v0.44.0; flag=--dispatch; overlay=W ;;
  *:custom) ref=${SG_REF:?SG_REF is required for group custom}; flag=${SG_FLAG:-} ;;
  *) echo "unknown host/group: $host $group (see README.md)" >&2; exit 2 ;;
esac
case "$host" in claude) name="C-$group$rep" ;; codex) name="X-$group$rep" ;; esac

# 运行目录必须在本仓库之外：Claude 会读取上级目录的 CLAUDE.md，放在仓库里会污染对照。
RUNS="${RUNS:-${TMPDIR:-/tmp}/dispatch-cost-runs}"
mkdir -p "$RUNS" && RUNS="$(cd "$RUNS" && pwd -P)" || exit 2
case "$RUNS/" in "$REPO"/*) echo "RUNS must be outside $REPO" >&2; exit 2 ;; esac

# spec-guard：从本仓库导出对应版本，联调时的临时规则变体（G / W）覆盖在 v0.44.0 上。
SG="$RUNS/plugins/$host-$group"
if [ ! -d "$SG" ]; then
  mkdir -p "$SG" && git -C "$REPO" archive "$ref" plugins/spec-guard | tar -x -C "$SG" --strip-components 2 || exit 2
  [ -z "$overlay" ] || command cp -f "$HERE/variants/$overlay/"*.md "$SG/templates/" || exit 2
fi

P="$RUNS/$name"
[ -e "$P" ] && { echo "$P exists; refusing to overwrite" >&2; exit 2; }
mkdir -p "$P" && command cp -R "$HERE/seed/." "$P/" && cd "$P" || exit 2
git init -q && git config user.email run@example.invalid && git config user.name run
git add -A && GIT_AUTHOR_DATE=2026-10-05T21:43:56+08:00 GIT_COMMITTER_DATE=2026-10-05T21:43:56+08:00 \
  git commit -qm "seed ledgerlite" || exit 2
host_arg=""; [ "$host" = codex ] && host_arg=--host=codex
CLAUDE_PROJECT_DIR="$P" /bin/bash "$SG/hooks/setup-convention.sh" local $host_arg $flag >/dev/null 2>&1 || exit 2
git add -A && git commit -qm "chore: install convention ($name)"
[ -z "${DRY_RUN:-}" ] || { echo "prepared $P ($ref${overlay:+ + $overlay} ${flag:-no flag})"; exit 0; }
export TZ=Asia/Shanghai TIER_GUARD_LOG_DIR="$RUNS/log-$name"
CONTINUE="按 spec（含「补充约定」）自行决定，继续完成全部剩余任务，不需要再确认。"
open_items() { grep -c '^- \[ \]' "$P/tasks/ledgerlite/todo.md"; }
START=$(date -u +%FT%TZ); stops=0; thread=""

if [ "$host" = claude ]; then
  A="${AGENT_SKILLS_DIR:?set AGENT_SKILLS_DIR to the agent-skills plugin directory}"
  TG="${TIER_GUARD_DIR:?set TIER_GUARD_DIR to the tier-guard plugin directory}"
  # `project,local` is a single --setting-sources value, not two array elements.
  # shellcheck disable=SC2054
  COMMON=(--model "${CLAUDE_MODEL:-opus}" --setting-sources project,local --plugin-dir "$A" --plugin-dir "$SG"
          --plugin-dir "$TG" --permission-mode acceptEdits --allowedTools "Bash(python3:*)" "Bash(git:*)"
          "Bash(sed:*)" "Bash(cat:*)" "Bash(ls:*)" "Bash(head:*)" "Bash(tail:*)" "Bash(wc:*)")
  claude -p "/build auto" "${COMMON[@]}" < /dev/null > "$RUNS/$name-1.txt" 2>&1
  claude -p "approve" --continue "${COMMON[@]}" < /dev/null > "$RUNS/$name-2.txt" 2>&1
  while [ "$(open_items)" -gt 0 ] && [ $stops -lt 2 ]; do
    stops=$((stops + 1))
    claude -p "$CONTINUE" --continue "${COMMON[@]}" < /dev/null > "$RUNS/$name-stop$stops.txt" 2>&1
  done
else
  # Codex 的 agent-skills / tier-guard 用本机 Codex 已安装的插件；codex exec 会把本项目记为 trusted，结束后撤回。
  CODEX="${CODEX:-codex}"
  CFG="${CODEX_HOME:-$HOME/.codex}/config.toml"; grep -Fqx "[projects.\"$P\"]" "$CFG" 2>/dev/null && HAD=1 || HAD=0
  COMMON=(-c "model=\"${CODEX_MODEL:-gpt-6.1-sol}\"" -c "model_reasoning_effort=\"${CODEX_EFFORT:-medium}\"")
  PROMPT='按 AGENTS.md 的约定和 agent-skills 的 build 流程（auto 模式），实现 tasks/ledgerlite/todo.md 中的全部任务（含 Checkpoint）。计划已获批准，不需要再确认。'
  "$CODEX" exec --json "${COMMON[@]}" "$PROMPT" < /dev/null > "$RUNS/$name-1.jsonl" 2> "$RUNS/$name-1.err"
  thread=$(python3 -c "import json,sys;[print(json.loads(l).get('thread_id')) for l in open(sys.argv[1]) if 'thread.started' in l]" \
    "$RUNS/$name-1.jsonl" | head -1)
  while [ -n "$thread" ] && [ "$(open_items)" -gt 0 ] && [ $stops -lt 2 ]; do
    stops=$((stops + 1))
    "$CODEX" exec resume --json "${COMMON[@]}" "$thread" "$CONTINUE" \
      < /dev/null > "$RUNS/$name-stop$stops.jsonl" 2> "$RUNS/$name-stop$stops.err"
  done
  if [ "$HAD" = 0 ] && [ -f "$CFG" ]; then python3 - "$CFG" "$P" <<'PY'
import os, sys, tempfile
path, project = sys.argv[1:]
lines = open(path, encoding="utf-8").read().split("\n"); header = '[projects."%s"]' % project
kept, i, removed = [], 0, False
while i < len(lines):
    if lines[i].strip() == header:
        j = i + 1
        while j < len(lines) and not lines[j].lstrip().startswith("["): j += 1
        if [l.strip() for l in lines[i+1:j] if l.strip()] == ['trust_level = "trusted"']:
            removed, i = True, j; continue
    kept.append(lines[i]); i += 1
if removed:
    fd, tmp = tempfile.mkstemp(prefix=".config.toml.", dir=os.path.dirname(path))
    with os.fdopen(fd, "w", encoding="utf-8") as h: h.write("\n".join(kept))
    os.chmod(tmp, os.stat(path).st_mode & 0o777); os.replace(tmp, path)
PY
  fi
fi

END=$(date -u +%FT%TZ)
printf '{"run":"%s","group":"%s","thread":"%s","start":"%s","end":"%s","stops":%d,"open_items":%d,"commits":%d,"spec_guard_ref":"%s","overlay":"%s"}\n' \
  "$name" "$group" "$thread" "$START" "$END" "$stops" "$(open_items)" "$(git -C "$P" rev-list --count HEAD)" "$ref" "$overlay" \
  > "$RUNS/$name.meta.json"
cat "$RUNS/$name.meta.json"
