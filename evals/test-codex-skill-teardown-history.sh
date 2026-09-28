#!/usr/bin/env bash
# spec-guard-ops（Codex 路由）必须能预览并执行 teardown，也必须有 history 的
# correct 路由；否则 Codex 用户没有入口做 Claude 侧 /spec-guard:teardown-convention
# 与 /spec-guard:history-integrity correct 能做的事（R4 前半）。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$REPO_ROOT/plugins/spec-guard/skills/spec-guard-ops/SKILL.md"

[ -f "$SKILL" ] || { echo "missing $SKILL" >&2; exit 1; }

TEARDOWN_SECTION="$(awk '/^## teardown$/{flag=1; next} /^## /{flag=0} flag' "$SKILL")"
[ -n "$TEARDOWN_SECTION" ] || {
  echo "spec-guard-ops lacks a teardown section" >&2
  exit 1
}
grep -Fq 'hooks/teardown-convention.sh' <<<"$TEARDOWN_SECTION" || {
  echo "teardown section does not invoke hooks/teardown-convention.sh" >&2
  exit 1
}
grep -Fq -- '--dry-run' <<<"$TEARDOWN_SECTION" || {
  echo "teardown section lacks a --dry-run preview step" >&2
  exit 1
}
grep -Fq '确认' <<<"$TEARDOWN_SECTION" || {
  echo "teardown section does not require explicit user confirmation before the real run" >&2
  exit 1
}

HISTORY_SECTION="$(awk '/^## history$/{flag=1; next} /^## /{flag=0} flag' "$SKILL")"
[ -n "$HISTORY_SECTION" ] || {
  echo "spec-guard-ops lacks a history section" >&2
  exit 1
}
grep -Fq 'capability-history.py" correct --confirm' <<<"$HISTORY_SECTION" || {
  echo "history section does not invoke capability-history.py correct --confirm" >&2
  exit 1
}
grep -Fq '确认' <<<"$HISTORY_SECTION" || {
  echo "history correct route does not require explicit user confirmation" >&2
  exit 1
}

# 真实回环：在真实的 Codex（AGENTS.md）项目里，把 skill 给出的 teardown 命令行原样跑一遍，
# 证明其中每个参数都是 teardown-convention.sh 实际接受的，而不是靠读脚本源码推断。
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
ROOT="$REPO_ROOT/plugins/spec-guard"
PROJECT="$WORK/project"
mkdir -p "$PROJECT"
git -C "$PROJECT" init -q >/dev/null

CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$ROOT/hooks/setup-convention.sh" local --host=codex >/dev/null
grep -Fq 'BEGIN:spec-guard-codex-convention' "$PROJECT/AGENTS.md" || {
  echo "test fixture: setup-convention.sh did not install the Codex convention block" >&2
  exit 1
}

DRY_LINE="$(grep 'teardown-convention.sh' <<<"$TEARDOWN_SECTION" | grep -- '--dry-run' | head -1)"
[ -n "$DRY_LINE" ] || {
  echo "no --dry-run teardown-convention.sh invocation found in the teardown section" >&2
  exit 1
}
DRY_OUT="$(eval "$DRY_LINE")" || {
  echo "skill's dry-run teardown invocation failed against a real Codex project: $DRY_LINE" >&2
  exit 1
}
grep -Fq 'dry-run' <<<"$DRY_OUT" || {
  echo "dry-run invocation did not produce dry-run output: $DRY_OUT" >&2
  exit 1
}
grep -Fq 'BEGIN:spec-guard-codex-convention' "$PROJECT/AGENTS.md" || {
  echo "dry-run must not modify AGENTS.md" >&2
  exit 1
}

REAL_LINE="$(grep 'teardown-convention.sh' <<<"$TEARDOWN_SECTION" | grep -v -- '--dry-run' | head -1)"
[ -n "$REAL_LINE" ] || {
  echo "no real (non-dry-run) teardown-convention.sh invocation found in the teardown section" >&2
  exit 1
}
eval "$REAL_LINE" >/dev/null || {
  echo "skill's real teardown invocation failed against a real Codex project: $REAL_LINE" >&2
  exit 1
}
if grep -Fq 'BEGIN:spec-guard-codex-convention' "$PROJECT/AGENTS.md"; then
  echo "real teardown invocation did not remove the AGENTS.md convention block" >&2
  exit 1
fi

echo 'Codex spec-guard-ops teardown/history route regression passed'
