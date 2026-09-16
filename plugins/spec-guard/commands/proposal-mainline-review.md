---
description: 在验证后的主链模块边界提交显式 Proposal 裁决；只读且绝不写 Issue 阶段
allowed-tools: Bash
---

先通过 proposal-mainline-candidates 发现 Proposal，再由主链人工明确选择 decision：

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

observations 只能使用 package-boundary-conflict、public-contract-conflict、anchor-conflict、
unmerged-public-contract-change、dependency-suggestion 或 anchor-suggestion 之一；moduleIds
只能引用当前模块、Proposal 自身、其声明依赖或锚点。不能放入代码、路径、Issue 正文、token
或自由文本。accept 的结果只是 accepted-candidate。由受保护的人类流程另行写
attestation 和 accepted Issue 阶段；本命令不得写入它们。
