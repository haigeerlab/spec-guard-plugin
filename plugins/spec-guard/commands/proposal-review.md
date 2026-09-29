---
description: 读取远端默认分支上一个已发布 Proposal 及其 Issue 阶段，只读报告新鲜度与阶段
allowed-tools: Bash
---

任何分支都可以运行；它只读取远端默认分支快照和 GitHub/GitLab 上的 Proposal Issue：

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
python3 -B "$ROOT/hooks/proposal_review.py" \
  --project . --proposal-id "<proposal-id>" \
  --platform "<github|gitlab>" --target "<owner/repo 或 GitLab project id>"
~~~

原样报告 JSON。`awaiting-review` 与 `in-review` 表示可由人把 Issue 标签改成 `proposal-stage:accepted`；`stale` 表示能力图或基线已变化，
需要作者按新基线重新发布；`absent` 表示远端默认分支上没有该 Proposal，或没有对应 Issue。
`accepted` 与 `promoted-claim` 只是观察到的 Issue 标签，既不是晋级授权，也不是晋级证明。
本命令不会创建或修改 Issue、标签、能力图、Proposal、分支、任务或 PR。
