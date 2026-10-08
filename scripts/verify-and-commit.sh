#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# verify-and-commit.sh —— 检查全部通过才提交已暂存的内容
#
# 为什么需要：「校验没过却照样提交」出现过 4 次，每次写法不同 ——
# `;` 连接、日志路径写错、`validate.sh | tail -1 && git commit` 被管道吞掉退出码。
# 记得规则防不住新写法；这里成败只看每套检查自己的退出码，输出一律进日志。
#
# 用法: bash scripts/verify-and-commit.sh [--suite NAME]... -- <git commit 参数>
#   套件: validate phase-guard verify-artifacts（每次都跑）
#         setup-teardown pre-push shellcheck（按已暂存路径自动加跑，或用 --suite 指定）
#   只提交已暂存的内容，不做 git add、不推送。退出码: 0 已提交 · 1 拒绝或检查失败 · 2 用法错误
# ─────────────────────────────────────────────────────────────
set -euo pipefail

usage() { echo "用法: verify-and-commit.sh [--suite NAME]... -- <git commit 参数>" >&2; exit 2; }

known_suite() {
  case "$1" in validate|phase-guard|verify-artifacts|setup-teardown|pre-push|shellcheck) return 0 ;; esac
  return 1
}

EXTRA=()
SEP=false
while [ "$#" -gt 0 ]; do
  case "$1" in
    --) shift; SEP=true; break ;;
    --suite)
      [ "$#" -ge 2 ] || usage
      known_suite "$2" || { echo "未知套件: $2" >&2; usage; }
      EXTRA+=("$2"); shift 2 ;;
    *) echo "未知参数: $1" >&2; usage ;;
  esac
done
[ "$SEP" = true ] || { echo "缺少 --：git commit 的参数写在 -- 之后" >&2; usage; }

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if ! git diff --quiet; then
  echo "❌ 已跟踪的文件里还有未暂存的改动 —— 检查的内容会和提交的不一样。先暂存或撤掉：" >&2
  git diff --name-only | sed 's/^/     /' >&2
  exit 1
fi
if git diff --cached --quiet; then
  echo "❌ 没有已暂存的改动，没有可提交的内容" >&2
  exit 1
fi

# ── 选套件：基础三套 + 按已暂存路径 + --suite ──
SUITES=(validate phase-guard verify-artifacts)
add_suite() {
  local s
  for s in "${SUITES[@]}"; do [ "$s" = "$1" ] && return 0; done
  SUITES+=("$1")
}
while IFS= read -r path; do
  case "$path" in
    plugins/spec-guard/hooks/setup-convention.sh|plugins/spec-guard/hooks/teardown-convention.sh|\
    plugins/spec-guard/hooks/managed-block.py|plugins/spec-guard/hooks/test-setup-teardown.sh|\
    plugins/spec-guard/templates/*)
      add_suite setup-teardown ;;
  esac
  case "$path" in
    scripts/install-git-hooks.sh|scripts/test_pre_push_environment.py) add_suite pre-push ;;
  esac
  case "$path" in *.sh) add_suite shellcheck ;; esac
done < <(git diff --cached --name-only)
for s in ${EXTRA[@]+"${EXTRA[@]}"}; do add_suite "$s"; done

run_suite() {  # $1=套件名；在当前 shell 里运行，输出进日志
  case "$1" in
    validate)         /bin/bash scripts/validate.sh ;;
    phase-guard)      /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh ;;
    verify-artifacts) /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh ;;
    setup-teardown)   /bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh ;;
    pre-push)         python3 -B scripts/test_pre_push_environment.py ;;
    shellcheck)
      # 与 CI 同一条命令；npx 不可用时退出码非零，按失败处理，不跳过
      shopt -s nullglob
      local files=(plugins/spec-guard/hooks/*.sh scripts/*.sh evals/*.sh evals/*/*.sh)
      shopt -u nullglob
      npx --yes shellcheck@4.1.0 -S warning "${files[@]}" ;;
  esac
}

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/verify-and-commit.XXXXXX")"
echo "── verify-and-commit: ${SUITES[*]} ──"
FAILED=()
for s in "${SUITES[@]}"; do
  log="$LOG_DIR/$s.log"
  if (run_suite "$s") >"$log" 2>&1 </dev/null; then
    # ShellCheck 通过时不输出任何内容，日志末行只剩 npm 的提示，不能拿来当摘要
    if [ "$s" = shellcheck ]; then summary="无告警"; else summary="$(tail -n 1 "$log" | sed 's/^ *//')"; fi
    printf '  ✅ %s —— %s\n' "$s" "$summary"
  else
    printf '  ❌ %s（日志: %s）\n' "$s" "$log"
    { grep -E '❌|FAIL|Error|失败' "$log" || true; } | head -n 8 | sed 's/^/     /'
    FAILED+=("$s")
  fi
done

if [ "${#FAILED[@]}" -gt 0 ]; then
  echo "❌ 没有提交：${FAILED[*]} 未通过。日志目录: ${LOG_DIR}" >&2
  exit 1
fi
echo "✅ 全部通过，提交已暂存的内容（日志目录: ${LOG_DIR}）"
git commit "$@"
