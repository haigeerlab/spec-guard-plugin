#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# verify-and-commit.sh —— 检查全部通过才提交已暂存的内容
#
# 为什么需要：「校验没过却照样提交」出现过 4 次，每次写法不同 ——
# `;` 连接、日志路径写错、`validate.sh | tail -1 && git commit` 被管道吞掉退出码。
# 记得规则防不住新写法；这里成败只看每套检查自己的退出码，输出一律进日志。
#
# 用法: bash scripts/verify-and-commit.sh [--suite NAME]... -- <git commit 参数>
#   快档（只改文档类路径）: validate --quick、verify-artifacts 回归、本仓库 verify-artifacts
#   全套: validate、phase-guard、verify-artifacts 回归、本仓库 verify-artifacts（暂存了 .sh 时加 shellcheck），并行跑
#   --suite 可再加: validate-quick setup-teardown pre-push shellcheck 等
#   提交成功后把 tree 与档位记进 git 共用目录，供 pre-push 跳过重复检查（scripts/verified_trees.py）
#   只提交已暂存的内容，不做 git add、不推送。退出码: 0 已提交 · 1 拒绝或检查失败 · 2 用法错误
# ─────────────────────────────────────────────────────────────
set -euo pipefail

usage() { echo "用法: verify-and-commit.sh [--suite NAME]... -- <git commit 参数>" >&2; exit 2; }

known_suite() {
  case "$1" in validate|validate-quick|phase-guard|verify-artifacts|repo-artifacts|setup-teardown|pre-push|shellcheck) return 0 ;; esac
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

# ── 选档位与套件 ──
#   快档：暂存的全是 spec/、tasks/、docs/ 与 plugins/、.github/ 以外的 *.md（判断在 verified_trees.py）。
#   全套：其余任何情况。validate.sh 已包含 setup/teardown 与 pre-push 回归，不再按路径加跑。
TIER="$(git diff --cached --name-only | python3 scripts/verified_trees.py tier)"
if [ "$TIER" = quick ]; then
  SUITES=(validate-quick verify-artifacts repo-artifacts)
else
  TIER=full
  SUITES=(validate phase-guard verify-artifacts repo-artifacts)
  if git diff --cached --name-only | grep '\.sh$' >/dev/null; then SUITES+=(shellcheck); fi
fi
add_suite() {
  local s
  for s in "${SUITES[@]}"; do [ "$s" = "$1" ] && return 0; done
  SUITES+=("$1")
}
for s in ${EXTRA[@]+"${EXTRA[@]}"}; do add_suite "$s"; done

run_suite() {  # $1=套件名
  case "$1" in
    validate)         /bin/bash scripts/validate.sh ;;
    validate-quick)   /bin/bash scripts/validate.sh --quick ;;
    phase-guard)      /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh ;;
    verify-artifacts) /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh ;;
    repo-artifacts)   CLAUDE_PROJECT_DIR="$ROOT" /bin/bash plugins/spec-guard/hooks/verify-artifacts.sh ;;
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
if [ "$TIER" = quick ]; then label="快档（只改了文档类路径）"; else label="全套"; fi
echo "── verify-and-commit: ${label}: ${SUITES[*]} ──"
# 各套件并行跑：每套一个子进程、一份日志、一个退出码，逐项等待、逐项判定。
PIDS=()
for s in "${SUITES[@]}"; do
  (
    began=$(date +%s)
    run_suite "$s" >"$LOG_DIR/$s.log" 2>&1 </dev/null
    rc=$?
    echo $(( $(date +%s) - began )) >"$LOG_DIR/$s.seconds"
    exit "$rc"
  ) &
  PIDS+=($!)
done
FAILED=()
i=0
for s in "${SUITES[@]}"; do
  log="$LOG_DIR/$s.log"
  if wait "${PIDS[$i]}"; then
    # ShellCheck 通过时不输出任何内容，日志末行只剩 npm 的提示，不能拿来当摘要
    if [ "$s" = shellcheck ]; then summary="无告警"; else summary="$(tail -n 1 "$log" | sed 's/^ *//')"; fi
    printf '  ✅ %s（%ss）—— %s\n' "$s" "$(cat "$LOG_DIR/$s.seconds" 2>/dev/null || echo '?')" "$summary"
  else
    printf '  ❌ %s（日志: %s）\n' "$s" "$log"
    { grep -E '❌|FAIL|Error|失败' "$log" || true; } | head -n 8 | sed 's/^/     /'
    FAILED+=("$s")
  fi
  i=$((i + 1))
done

if [ "${#FAILED[@]}" -gt 0 ]; then
  echo "❌ 没有提交：${FAILED[*]} 未通过。日志目录: ${LOG_DIR}" >&2
  exit 1
fi
echo "✅ 全部通过，提交已暂存的内容（日志目录: ${LOG_DIR}）"
git commit "$@"
# 记下这次通过检查的 tree，推送时 pre-push 据此跳过重复检查；写不进去只提醒，不影响已完成的提交。
python3 scripts/verified_trees.py record "$TIER" || true
