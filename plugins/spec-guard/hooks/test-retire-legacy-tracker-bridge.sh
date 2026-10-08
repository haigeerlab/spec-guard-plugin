#!/usr/bin/env bash
# The legacy tracker bridge must be removed from the shipped plugin, not merely
# hidden from a phase suggestion.  Released evidence and retirement documents
# are intentionally outside this assertion.
#
# Optional $1: an alternate repo root to scan (a fixture tree in tests).
# Defaults to this checkout's root, computed from the script's own location.
set -u

if [ "${1:-}" != "" ]; then
  ROOT="$(cd "$1" && pwd)" || { echo "cannot resolve root: $1" >&2; exit 2; }
else
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
fi
PLUGIN="$ROOT/plugins/spec-guard"
FAIL=0

missing() {
  if [ -e "$PLUGIN/$1" ]; then
    printf '  ❌ retired surface still shipped: %s\n' "$1"
    FAIL=$((FAIL + 1))
  else
    printf '  ✅ retired surface absent: %s\n' "$1"
  fi
}

absent_from() {
  local needle="$1"
  shift
  local hits rc
  # grep 退出码：0 命中、1 无命中、>1 出错（例如路径不存在）。出错不能当作“无命中”。
  hits="$(grep -rnE --exclude=test-retire-legacy-tracker-bridge.sh "$needle" "$@" 2>&1)"
  rc=$?
  if [ "$rc" -eq 1 ]; then
    printf '  ✅ active shipped surface has no %s reference\n' "$needle"
  elif [ "$rc" -eq 0 ]; then
    printf '  ❌ active shipped surface still references %s\n%s\n' "$needle" "$hits"
    FAIL=$((FAIL + 1))
  else
    printf '  ❌ cannot scan for %s (grep exit %s)\n%s\n' "$needle" "$rc" "$hits"
    FAIL=$((FAIL + 1))
  fi
}

echo '═══ legacy tracker bridge retirement ═══'
for path in \
  skills/spec-github-bridge \
  skills/spec-gitlab-bridge \
  commands/sync-map.md \
  commands/next.md \
  commands/deliver.md \
  commands/bind-workspace.md \
  hooks/gitlab-bridge.sh \
  hooks/gitlab_tracker.py \
  hooks/sync-map-gitlab.sh \
  hooks/workspace_binding.py; do
  missing "$path"
done

absent_from 'spec-github-bridge|spec-gitlab-bridge|sync-map-gitlab|gitlab-bridge\.sh|workspace_binding' \
  "$PLUGIN/commands" "$PLUGIN/skills" "$PLUGIN/templates" "$PLUGIN/hooks/hooks.json"

absent_from 'Epic issue|远端 tracker|feat/<id>' "$PLUGIN/templates"

absent_from 'spec-github-bridge`|spec-gitlab-bridge`|/sync-map' \
  "$ROOT/README.md" "$ROOT/AGENTS.md" "$ROOT/docs/design.md" "$ROOT/docs/maintainer-workflow.md"

absent_from 'spec-github-bridge|spec-gitlab-bridge|sync-map|gitlab_tracker|workspace_binding|\.agent/state\.json' \
  "$PLUGIN/hooks/proposal_contract.py" \
  "$PLUGIN/hooks/proposal_publication.py" \
  "$PLUGIN/hooks/proposal_tracker_read.py" \
  "$PLUGIN/hooks/proposal_review.py" \
  "$PLUGIN/hooks/proposal_promotion_proof.py"

# 当前能力图只描述现行能力：已退役命令的名字不得出现在任何模块行里（2026-10-08 审查 F14）。
absent_from 'spec-github-bridge|spec-gitlab-bridge|sync-map|workspace_binding|spec-guard:handoff|spec-guard handoff|session_handoff' \
  "$ROOT/spec/CAPABILITY-MAP.md"

# ── broadened scan: every non-test file under plugins/spec-guard (R6) ──────
#
# The checks above only look at a fixed list of paths and a handful of
# hand-picked files. That scope has a hole: a *new* command or hook script
# that reuses a retired identifier, or that starts writing tracker Issues
# again, would ship silently — nothing above would ever see it. This scans
# every shipped, non-test file under the plugin instead.
#
# "non-test" = basename does not start with test_ or test- (this script's own
# name matches that pattern, so `find` excludes it without a special case),
# and the file is not inside a __pycache__ directory.
#
# Two files intentionally reference a retired name today, only to say it is
# NOT invoked (docs/lenses.md style negative statement). They are allowlisted
# below by exact path + the allowed line's own (trimmed) text, not by line
# number: line numbers already drifted once in this module (this exact
# proposal-promotion-proof.md line moved 30→33 when Task 1 edited the file
# above it), and matching by line number would turn every future edit above
# an allowed line into a false "active shipped surface still references..."
# failure — a false alarm (docs/lenses.md A1). Matching by path + text means
# only the allowed line itself, not its position, has to stay in the clear;
# a *different* retired-identifier line added anywhere in the same file still
# gets caught, since its text won't match any entry.
ALLOWLIST_PATH=(
  "plugins/spec-guard/references/proposal-promotion-proof.md"
  "plugins/spec-guard/hooks/proposal_submit.py"
  "plugins/spec-guard/hooks/proposal_submit.py"
)
ALLOWLIST_TEXT=(
  '`.agent/state.json`. It does not invoke `spec-github-bridge` or `/sync-map`.'
  'create = "gh issue create --title %s --label proposal --label %s --body %s" % ('
  'create = "glab issue create --title %s --label %s --description %s" % ('
)
ALLOWLIST_REASON=(
  "negative statement — says the prove action does not invoke the retired bridge or /sync-map, not a real call site"
  "printed next step — proposal-submit only prints this command for the user to run; it never executes it"
  "printed next step — proposal-submit only prints this command for the user to run; it never executes it"
)

trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

# $1=file path relative to $ROOT  $2=trimmed line text
# Echoes the matching entry's index and returns 0 on a match; returns 1 otherwise.
allowed_index() {
  local i=0 n=${#ALLOWLIST_PATH[@]}
  while [ "$i" -lt "$n" ]; do
    if [ "${ALLOWLIST_PATH[$i]}" = "$1" ] && [ "${ALLOWLIST_TEXT[$i]}" = "$2" ]; then
      printf '%s' "$i"
      return 0
    fi
    i=$((i + 1))
  done
  return 1
}

RETIRED_PATTERN='sync-map|spec-github-bridge|spec-gitlab-bridge|workspace_binding|bind-workspace'
ISSUE_WRITE_PATTERN='gh issue (create|edit)|glab issue (create|update)'
# `.agent/state.json` 的 `tracker` 字段随远端 tracker 模式一同退役
# （docs/retirements/state-tracker-field.md）：没有任何代码再写它、读它，或据它改变判断。
# 模式刻意覆盖多种重新引入的形态——带默认值的读取、单引号、下标、非字符串值、成员判断——
# 因为最可能被写回来的恰是 `get("tracker", "none")` 这种，窄模式会放它过去。
# verify-artifacts 自己那条「提醒用户删除」的探测不会被命中：它的正则里 `"tracker"` 后面紧跟
# 的是 `[`，不是空白或冒号，所以不需要 allowlist 条目（能匹配不到任何行的条目只会误导读者）。
# 能力历史快照里的 `"tracker": {...}` 在 test-capability-history.sh 中，按 test- 前缀被 find 排除。
STATE_FIELD_PATTERN='retired_tracker|["'"'"']tracker["'"'"'][[:space:]]*\]|get\(["'"'"']tracker["'"'"']|"tracker"[[:space:]]*:|'"'"'tracker'"'"'[[:space:]]*:|["'"'"']tracker["'"'"'][[:space:]]+in[[:space:]]'

scan_surface() {
  local pattern="$1" label="$2"
  local file lineno content rel trimmed idx
  while IFS= read -r file; do
    while IFS=: read -r lineno content; do
      [ -n "$lineno" ] || continue
      rel="${file#"$ROOT"/}"
      trimmed="$(trim "$content")"
      if idx="$(allowed_index "$rel" "$trimmed")"; then
        printf '  ⏭  %s:%s (allowlisted %s hit: %s)\n' "$rel" "$lineno" "$label" "${ALLOWLIST_REASON[$idx]}"
        continue
      fi
      printf '  ❌ %s references %s: %s:%s\n%s\n' "$rel" "$label" "$rel" "$lineno" "    $content"
      FAIL=$((FAIL + 1))
    done < <(grep -nE "$pattern" "$file" 2>/dev/null)
  # 扫描范围含 evals/ 与 scripts/：2026-10-04 的审查发现 evals/module-namespace.sh 一直在写
  # 退役的 tracker 字段，而只扫 $PLUGIN 永远看不到它。仓库里会装进消费者项目或在 CI 跑的
  # 脚本都算已发布表面。
  done < <(find "$PLUGIN" "$ROOT/evals" "$ROOT/scripts" -type f \
             -not -path '*/__pycache__/*' \
             -not -name 'test_*' \
             -not -name 'test-*' 2>/dev/null)
}

echo ''
echo '═══ broadened surface scan (all non-test files under plugins/spec-guard) ═══'
scan_surface "$RETIRED_PATTERN" 'retired identifier'
scan_surface "$ISSUE_WRITE_PATTERN" 'Issue-writing command'
scan_surface "$STATE_FIELD_PATTERN" 'retired state.json tracker field'

[ "$FAIL" -eq 0 ] || exit 1
printf '  ✅ legacy tracker bridge is absent from the distributed surface\n'
