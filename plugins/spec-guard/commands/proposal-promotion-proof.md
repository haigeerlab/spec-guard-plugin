---
description: 晋级合并后从远端默认分支只读证明 Proposal module 已按声明纳入能力图
allowed-tools: Bash
---

只在 promotion 已合并到远端默认分支后运行。它会重新读取远端 Proposal、策略、acceptance
attestation 与 Issue 阶段，确认接受仍然有效后再证明：

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
python3 -B "$ROOT/hooks/proposal_promotion_proof.py" \
  --project . --proposal-id "<proposal-id>" \
  --platform "<github|gitlab>" --target "<target>" --prove
~~~

原样报告 JSON。只有 `proved` 才是晋级证明，并给出 promotion commit 与 module id。`not-accepted`
表示 Issue 阶段或 attestation 不满足；`invalid` 表示首次纳入该 module 的提交不符合声明（职责、依赖、
位置，或 diff 超出能力图、模块 Spec 与 Plan）；`unknown` 表示远端无法安全读取。
本命令不会把结果写回 Issue，也不创建或修改分支、能力图、Spec、Plan、任务或 PR。
