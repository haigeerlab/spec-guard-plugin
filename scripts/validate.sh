#!/usr/bin/env bash
# 仓库完整性校验。CI 和本地共用。
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
# --quick: only the structural checks (each well under a second); no regression suites. Used by
# verify-and-commit for docs-only commits; CI and pre-push run the full set.
QUICK=false
case "${1:-}" in
  "") ;;
  --quick) QUICK=true ;;
  *) echo "用法: validate.sh [--quick]" >&2; exit 2 ;;
esac
F=0
say(){ printf "  %s %s\n" "$1" "$2"; }
# 仅扫描本 checkout 的跟踪文件及未忽略的新文件，不穿透嵌套 Git checkout。
repo_files(){ git ls-files --cached --others --exclude-standard -- "$1"; }

echo "═══ 结构 ═══"
for p in .claude-plugin/marketplace.json \
         plugins/spec-guard/.claude-plugin/plugin.json \
         plugins/spec-guard/hooks/hooks.json \
         plugins/spec-guard/hooks/phase-guard.sh; do
  [ -f "$p" ] && say "✅" "$p" || { say "❌" "$p 缺失"; F=1; }
done

echo ""
echo "═══ JSON 语法 ═══"
while IFS= read -r j; do
  python3 -m json.tool "$j" >/dev/null 2>&1 && say "✅" "$j" || { say "❌" "$j 解析失败"; F=1; }
done < <(repo_files '*.json')

echo ""
echo "═══ marketplace ↔ Claude / Codex plugin 一致性 ═══"
python3 scripts/check-manifests.py || F=1

echo ""
echo "═══ 公开安装元数据 ═══"
/bin/bash evals/test-public-metadata.sh || F=1

echo ""
echo "═══ Shell 语法 ═══"
while IFS= read -r s; do
  bash -n "$s" 2>/dev/null && say "✅" "$s" || { say "❌" "$s 语法错误"; F=1; }
done < <(repo_files '*.sh')

echo ""
echo "═══ 可执行位 ═══"
while IFS= read -r s; do
  [ -x "$s" ] && say "✅" "$s" || { say "❌" "$s 缺执行位（git update-index --chmod=+x ${s}）"; F=1; }
done < <(repo_files '*.sh')

echo ""
echo "═══ bash 3.2 兼容（macOS 自带 bash）═══"
# shellcheck disable=SC2046
python3 scripts/check-bash32.py $(repo_files '*.sh') || F=1

echo ""
echo "═══ gh --json 字段是否真实存在 ═══"
# shellcheck disable=SC2046
python3 scripts/check-gh-json-fields.py \
  $(find plugins scripts -type f \( -name "*.md" -o -name "*.sh" \)) $(find plugins -type f -name "*.py") || F=1

echo ""
echo "═══ 管道 + grep -q（SIGPIPE 陷阱）═══"
# shellcheck disable=SC2046
python3 scripts/check-grep-pipe.py $(repo_files '*.sh') || F=1

echo ""
echo "═══ 用户可见输出里的命令名 ═══"
python3 scripts/check-command-names.py || F=1
python3 scripts/check-no-parallel-surface.py || F=1
python3 scripts/check-acceptance-immutable.py || F=1
python3 scripts/check-command-parity.py || F=1
python3 scripts/check-command-table.py || F=1
python3 scripts/check-acceptance-wired.py || F=1
python3 scripts/check-decision-supersession.py || F=1
python3 scripts/check-collaboration-boundary.py || F=1

echo ""

# 指纹算法供能力图与 Proposal 校验共用；免费，所以进这一层。
echo "═══ 指纹算法自检 ═══"
python3 plugins/spec-guard/hooks/spec-digest.py --selftest || F=1
python3 scripts/check-digest-single-source.py || F=1
echo ""

# 本机状态只经 state_paths.py（runtime-state-layout）；免费，所以进这一层。
echo "═══ 本机状态路径 ═══"
python3 scripts/check-state-paths.py || F=1
echo ""

if [ "$QUICK" = false ]; then
# 回归段：互不共享状态的测试交给运行器同时跑（validate-parallel-files），每步输出按原顺序完整打印，
# 任一步失败即整体失败并列出失败步骤。SG_VALIDATE_JOBS=1 时逐条串行，供排查用。
# 三个最慢的测试仍按测试类分进程并行跑（slow-test-speedup）；少跑一个用例也算失败。
# test_self_report 换 TMPDIR 再跑一遍：外部 TMPDIR 不在临时前缀下时结果也必须一样；目录建在 git 目录里
# （不在 /tmp、/var/folders 下），运行器结束后只删 mktemp 刚建、带固定前缀的那个目录。
SR_TMP="$(mktemp -d "$(git rev-parse --absolute-git-dir)/sg-self-report-tmpdir.XXXXXX")" || SR_TMP=""
if [ -n "${SR_TMP}" ]; then
  SR_STEP="TMPDIR=$(printf %q "${SR_TMP}") python3 -B scripts/test_self_report.py"
else
  SR_STEP="echo '  ❌ 无法在 git 目录里建临时目录（mktemp）'; exit 1"
fi
python3 -B scripts/run_steps_parallel.py \
  --section '═══ 校验器自身的回归 ═══' \
  'bash scripts/test-checkers.sh' \
  'python3 -B scripts/test_pre_push_environment.py' \
  'python3 -B scripts/test_verify_and_commit.py' \
  'python3 -B scripts/test_validate_quick.py' \
  'python3 -B scripts/test_run_tests_parallel.py' \
  'python3 -B scripts/test_run_steps_parallel.py' \
  --section '═══ Proposal 与本地结构回归 ═══' \
  '/bin/bash evals/test-codex-command-roots.sh' \
  '/bin/bash evals/test-codex-skill-teardown-history.sh' \
  'python3 -B plugins/spec-guard/hooks/test_documentation_baseline.py' \
  'python3 -B plugins/spec-guard/hooks/test_documentation_impact.py' \
  'python3 -B plugins/spec-guard/hooks/test_documentation_verification.py' \
  'python3 -B plugins/spec-guard/hooks/test_proposal_contract.py' \
  'python3 -B scripts/run_tests_parallel.py plugins/spec-guard/hooks/test_module_cost_report.py' \
  'python3 -B plugins/spec-guard/hooks/test_capability_map.py' \
  'python3 -B scripts/test_self_report.py' \
  "${SR_STEP}" \
  'python3 -B plugins/spec-guard/hooks/test_session_context.py' \
  'python3 -B plugins/spec-guard/hooks/test_ticket_entry.py' \
  'python3 -B plugins/spec-guard/hooks/test_hosted_ticket_entry.py' \
  'python3 -B plugins/spec-guard/hooks/test_local_ledger_adapters.py' \
  'python3 -B plugins/spec-guard/hooks/test_local_ledger_runtime.py' \
  'python3 -B scripts/run_tests_parallel.py plugins/spec-guard/hooks/test_local_ticket_portability.py' \
  'python3 -B plugins/spec-guard/hooks/test_local_ticket_publish.py' \
  'python3 -B plugins/spec-guard/hooks/test_local_ticket_providers.py' \
  'python3 -B plugins/spec-guard/hooks/test_local_ticket_imports.py' \
  'python3 -B plugins/spec-guard/hooks/test_hosted_ticket_read.py' \
  'python3 -B plugins/spec-guard/hooks/test_hosted_ticket_write.py' \
  'python3 -B plugins/spec-guard/hooks/test_hosted_ticket_actions.py' \
  'python3 -B plugins/spec-guard/hooks/test_host_config_removal.py' \
  'python3 -B plugins/spec-guard/hooks/test_agent_relay_probe.py' \
  'python3 -B plugins/spec-guard/hooks/test_proposal_publication.py' \
  'python3 -B plugins/spec-guard/hooks/test_proposal_submit.py' \
  'python3 -B plugins/spec-guard/hooks/test_proposal_tracker_read.py' \
  'python3 -B plugins/spec-guard/hooks/test_proposal_review.py' \
  'python3 -B scripts/run_tests_parallel.py plugins/spec-guard/hooks/test_proposal_promotion_proof.py' \
  'python3 -B plugins/spec-guard/hooks/test_module_insert.py' \
  'python3 -B plugins/spec-guard/hooks/test_module_stage_sanitization.py' \
  'python3 -B plugins/spec-guard/hooks/test_tracker_default.py' \
  'python3 -B plugins/spec-guard/hooks/test_proposal_closeout.py' \
  'python3 -B plugins/spec-guard/hooks/test_proposal_closeout_providers.py' \
  'python3 -B plugins/spec-guard/hooks/test_proposal_closeout_local.py' \
  '/bin/bash plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh' \
  --section '═══ Capability history ledger regression ═══' \
  '/bin/bash plugins/spec-guard/hooks/test-capability-history.sh' \
  --section '═══ Checkpoint contract discoverability ═══' \
  'python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py' \
  --section '═══ Python 3.9 兼容（macOS 自带 python3）═══' \
  'python3 -B plugins/spec-guard/hooks/test_python_compat.py' \
  --section '═══ Hook 入口命令回归 ═══' \
  '/bin/bash plugins/spec-guard/hooks/test-hook-entry.sh' \
  --section '═══ Setup/teardown regression ═══' \
  '/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh' \
  --section '═══ History verification regression ═══' \
  '/bin/bash plugins/spec-guard/hooks/test-history-verification.sh' \
  --section '═══ History migration regression ═══' \
  '/bin/bash plugins/spec-guard/hooks/test-history-migration.sh' \
  --section '═══ Codex 真实宿主 smoke 判决器自检（不调用 Codex）═══' \
  '/bin/bash evals/codex-plugin-smoke.sh --selftest' \
  '/bin/bash evals/module-namespace.sh --selftest'
[ $? -eq 0 ] || F=1
case "${SR_TMP}" in */sg-self-report-tmpdir.??????) rm -rf -- "${SR_TMP}" ;; esac
echo ""
fi

echo "═══ 发布证据记录回归 ═══"
/bin/bash evals/test-release-evidence.sh || F=1
/bin/bash evals/test-release-package.sh || F=1
echo ""

echo "═══ README 内嵌声明块 ↔ templates ═══"
python3 scripts/check-readme-sync.py || F=1
echo ""

echo "═══ 命令 frontmatter ═══"
while IFS= read -r c; do
  grep -q -- "---" <<<"$(head -1 "$c")" && say "✅" "$c" || { say "❌" "$c 缺 frontmatter"; F=1; }
done < <(find plugins/*/commands -name "*.md" 2>/dev/null)

echo ""
[ "$F" -eq 0 ] && echo "校验通过 ✅" || echo "校验失败 ❌"
exit $F
