#!/usr/bin/env bash
# 仓库完整性校验。CI 和本地共用。
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
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

echo ""
echo "═══ 校验器自身的回归 ═══"
bash scripts/test-checkers.sh || F=1
python3 -B scripts/test_pre_push_environment.py || F=1
echo ""

# 指纹算法供能力图与 Proposal 校验共用；免费，所以进这一层。
echo "═══ 指纹算法自检 ═══"
python3 plugins/spec-guard/hooks/spec-digest.py --selftest || F=1
echo ""

echo "═══ Proposal 与本地结构回归 ═══"
/bin/bash evals/test-codex-command-roots.sh || F=1
/bin/bash evals/test-codex-skill-teardown-history.sh || F=1
python3 -B plugins/spec-guard/hooks/test_documentation_baseline.py || F=1
python3 -B plugins/spec-guard/hooks/test_documentation_impact.py || F=1
python3 -B plugins/spec-guard/hooks/test_documentation_verification.py || F=1
python3 -B plugins/spec-guard/hooks/test_proposal_contract.py || F=1
python3 -B plugins/spec-guard/hooks/test_collab_entry.py || F=1
python3 -B plugins/spec-guard/hooks/test_native_collab_entry.py || F=1
python3 -B plugins/spec-guard/hooks/test_collaboration_backend.py || F=1
python3 -B plugins/spec-guard/hooks/test_ticket_entry.py || F=1
python3 -B plugins/spec-guard/hooks/test_local_ledger_adapters.py || F=1
python3 -B plugins/spec-guard/hooks/test_local_ledger_runtime.py || F=1
python3 -B plugins/spec-guard/hooks/test_local_ticket_portability.py || F=1
python3 -B plugins/spec-guard/hooks/test_local_ticket_publish.py || F=1
python3 -B plugins/spec-guard/hooks/test_local_ticket_providers.py || F=1
python3 -B plugins/spec-guard/hooks/test_hosted_ticket_read.py || F=1
python3 -B plugins/spec-guard/hooks/test_hosted_ticket_write.py || F=1
python3 -B plugins/spec-guard/hooks/test_collaboration_runtime.py || F=1
python3 -B plugins/spec-guard/hooks/test_native_collaboration_runtime.py || F=1
python3 -B plugins/spec-guard/hooks/test_native_collaboration_adapters.py || F=1
python3 -B plugins/spec-guard/hooks/test_native_collaboration_cutover.py || F=1
python3 -B plugins/spec-guard/hooks/test_native_collaboration_activate.py || F=1
python3 -B plugins/spec-guard/hooks/test_native_collaboration_rollback.py || F=1
python3 -B plugins/spec-guard/hooks/test_native_collaboration_retire.py || F=1
python3 -B plugins/spec-guard/hooks/test_host_config_removal.py || F=1
python3 -B plugins/spec-guard/hooks/test_proposal_publication.py || F=1
python3 -B plugins/spec-guard/hooks/test_proposal_submit.py || F=1
python3 -B plugins/spec-guard/hooks/test_proposal_tracker_read.py || F=1
python3 -B plugins/spec-guard/hooks/test_proposal_review.py || F=1
python3 -B plugins/spec-guard/hooks/test_proposal_promotion_proof.py || F=1
python3 -B plugins/spec-guard/hooks/test_module_insert.py || F=1
/bin/bash plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh || F=1
echo ""

echo "═══ Capability history ledger regression ═══"
/bin/bash plugins/spec-guard/hooks/test-capability-history.sh || F=1
echo ""

echo "═══ Checkpoint contract discoverability ═══"
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py || F=1
echo ""

echo "═══ Python 3.9 兼容（macOS 自带 python3）═══"
python3 -B plugins/spec-guard/hooks/test_python_compat.py || F=1
echo ""

echo "═══ Hook 入口命令回归 ═══"
/bin/bash plugins/spec-guard/hooks/test-hook-entry.sh || F=1

echo ""
echo "═══ Setup/teardown regression ═══"
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh || F=1
echo ""

echo "═══ History verification regression ═══"
/bin/bash plugins/spec-guard/hooks/test-history-verification.sh || F=1
echo ""

echo "═══ History migration regression ═══"
/bin/bash plugins/spec-guard/hooks/test-history-migration.sh || F=1
echo ""

echo "═══ Codex 真实宿主 smoke 判决器自检（不调用 Codex）═══"
/bin/bash evals/codex-plugin-smoke.sh --selftest || F=1
/bin/bash evals/module-namespace.sh --selftest || F=1
echo ""

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
