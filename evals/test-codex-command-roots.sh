#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMANDS=(
  documentation-baseline
  documentation-impact
  documentation-verification
  history-integrity
  phase
  proposal-mainline-candidates
  proposal-mainline-review
  proposal-promotion-preflight
  proposal-promotion-proof
  proposal-review
  verify-artifacts
)

for command in "${COMMANDS[@]}"; do
  file="$ROOT/plugins/spec-guard/commands/$command.md"
  grep -Fq 'ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"' "$file" || {
    echo "$command lacks portable plugin-root bootstrap" >&2
    exit 1
  }
  grep -Fq 'codex plugin list --available --json' "$file" || {
    echo "$command cannot resolve an enabled Codex plugin" >&2
    exit 1
  }
done

for command in phase verify-artifacts; do
  file="$ROOT/plugins/spec-guard/commands/$command.md"
  if grep -Fq '../references/workflow-checkpoints.md' "$file"; then
    echo "$command retains a reference path invalid after Codex command migration" >&2
    exit 1
  fi
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PROJECT="$WORK/project"
mkdir -p "$PROJECT/spec" "$WORK/bin"
printf '%s\n' '<!-- BEGIN:spec-guard-codex-convention -->' > "$PROJECT/AGENTS.md"
printf '%s\n' '<!-- END:spec-guard-codex-convention -->' >> "$PROJECT/AGENTS.md"
printf '%s\n' '# Capability Map' '| Module id | Responsibility | Depends on |' '|---|---|---|' '| alpha | x | — |' '' 'Build order: alpha' > "$PROJECT/spec/CAPABILITY-MAP.md"
touch "$PROJECT/spec/alpha.md"
printf '%s\n' '#!/usr/bin/env bash' > "$WORK/bin/codex"
printf '%s\n' "printf '%s\\n' '{\"installed\":[{\"name\":\"spec-guard\",\"installed\":true,\"enabled\":true,\"source\":{}},{\"name\":\"spec-guard\",\"installed\":true,\"enabled\":true,\"source\":{\"path\":\"$ROOT/plugins/spec-guard\"}}]}'" >> "$WORK/bin/codex"
chmod +x "$WORK/bin/codex"
awk '/^```bash$/{capture=1; next} capture && /^```$/{exit} capture{print}' \
  "$ROOT/plugins/spec-guard/commands/phase.md" > "$WORK/phase-command.sh"
PHASE="$(cd "$PROJECT" && PATH="$WORK/bin:$PATH" CLAUDE_PLUGIN_ROOT='' PLUGIN_ROOT='' /bin/bash "$WORK/phase-command.sh")"
grep -q 'NEEDS_PLAN' <<<"$PHASE" || {
  echo 'phase command cannot resolve an enabled Codex plugin without a root environment variable' >&2
  exit 1
}

echo 'Codex migrated command root regression passed'
