#!/usr/bin/env bash
# The legacy tracker bridge must be removed from the shipped plugin, not merely
# hidden from a phase suggestion.  Released evidence and retirement documents
# are intentionally outside this assertion.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
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

absent_from 'spec-github-bridge`|spec-gitlab-bridge`|/sync-map' \
  "$ROOT/README.md" "$ROOT/AGENTS.md" "$ROOT/docs/design.md" "$ROOT/docs/maintainer-workflow.md"

absent_from 'spec-github-bridge|spec-gitlab-bridge|sync-map|gitlab_tracker|workspace_binding|\.agent/state\.json' \
  "$PLUGIN/hooks/proposal_contract.py" \
  "$PLUGIN/hooks/proposal_publication.py" \
  "$PLUGIN/hooks/proposal_tracker_read.py" \
  "$PLUGIN/hooks/proposal_review.py" \
  "$PLUGIN/hooks/proposal_promotion_proof.py" \
  "$PLUGIN/hooks/proposal_boundary_guidance.py"

[ "$FAIL" -eq 0 ] || exit 1
printf '  ✅ legacy tracker bridge is absent from the distributed surface\n'
