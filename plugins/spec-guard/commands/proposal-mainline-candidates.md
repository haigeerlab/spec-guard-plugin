---
description: 仅在已验证主链模块边界读取远端 Proposal 候选；不接受或写入任何对象
allowed-tools: Bash
---

主链分支（policy 的 `reviewRef`）必须包含远端默认分支的最新提交。若结果是
`mainline-review-commit-not-ancestor`，说明主链分支落后：在主链 checkout 上运行
`git fetch origin && git merge --ff-only origin/<默认分支>` 后再试；不能快进时停止并报告，不要改用其他分支。

只有正在主链的调用者，且边界确为 module-deliver 或 module-advance，才运行：

~~~bash
ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"
if [ -z "$ROOT" ] && command -v codex >/dev/null 2>&1; then
  ROOT="$(codex plugin list --available --json 2>/dev/null | python3 -c '
import json, sys
try:
    plugins = json.load(sys.stdin).get("installed", [])
except (TypeError, ValueError):
    plugins = []
for plugin in plugins:
    if plugin.get("name") == "spec-guard" and plugin.get("installed") and plugin.get("enabled"):
        source = plugin.get("source")
        path = source.get("path") if isinstance(source, dict) else None
        if isinstance(path, str) and path:
            print(path)
            break
')"
fi
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "spec-guard 插件未安装或未启用" >&2; exit 2; }
python3 -B "$ROOT/hooks/proposal_mainline_review.py" \
  --project . --platform "<github|gitlab>" --target "<target>" \
  --authority-id "<authority-id>" --boundary "<module-deliver|module-advance>" \
  --current-module-id "<module-id>"
~~~

原样报告 JSON。candidate-list 只是待人工审阅的排序候选，绝不等于 accepted。
若结果为 blocked、unknown、invalid 或 stale，停止，不从其他 worktree 补充事实；按 `diagnostic` 说明原因：
`proposal-pool-unknown` 是远端快照读不到，`mainline-review-commit-not-ancestor` 是本地主链未包含远端默认
分支，其余代码见 `references/proposal-mainline-review.md`。`skipped` 列出未成为候选的 Proposal 及原因。
本命令不会创建或修改 Issue、标签、能力图、分支、任务或 PR。

要记录主链人工裁决，追加 Proposal id、decision 和 observations JSON：

~~~bash
ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"
if [ -z "$ROOT" ] && command -v codex >/dev/null 2>&1; then
  ROOT="$(codex plugin list --available --json 2>/dev/null | python3 -c '
import json, sys
try:
    plugins = json.load(sys.stdin).get("installed", [])
except (TypeError, ValueError):
    plugins = []
for plugin in plugins:
    if plugin.get("name") == "spec-guard" and plugin.get("installed") and plugin.get("enabled"):
        source = plugin.get("source")
        path = source.get("path") if isinstance(source, dict) else None
        if isinstance(path, str) and path:
            print(path)
            break
')"
fi
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "spec-guard 插件未安装或未启用" >&2; exit 2; }
python3 -B "$ROOT/hooks/proposal_mainline_review.py" \
  --project . --platform "<github|gitlab>" --target "<target>" \
  --authority-id "<authority-id>" --boundary "<module-deliver|module-advance>" \
  --current-module-id "<module-id>" --proposal-id "<proposal-id>" \
  --decision "<accept|needs-revision|defer|reject>" --observations-json "[]"
~~~

accept 只会产生 accepted-candidate，绝不会改写 accepted 标签或 attestation。
