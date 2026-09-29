---
description: 在人工接受后读取新鲜远端事实，预览是否允许创建 promotion 分支
allowed-tools: Bash
---

只在人工已把 Issue 标签改成 `proposal-stage:accepted` 之后运行。它重新读取远端 Proposal 池与
Issue 阶段，并做一次新鲜评审（基线未漂移、模块还不在能力图中、依赖齐全、锚点有效）；
不读取策略文件或验收记录：

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
  --platform "<github|gitlab>" --target "<target>"
~~~

仅当 JSON state 为 ready 时，baseCommit 才是人工创建 promotion 分支可使用的起点。
`/spec-guard:add-module --proposal` 在插入前会通过 `promotion_base` 运行同一预检，因此本命令是可选的只读预览。
命令本身不创建分支，也不更新 Issue、标签、能力图、模块 Spec、Plan、任务或 PR。
任何其他状态都应原样报告并停止；不得根据旧 checkout 或另一个 worktree 猜测。

非 ready 状态附带的 `diagnostic` 会尽量透传下层已给出的具体原因，例如缺 Proposal 是
`publication-absent`、缺 tracker Issue 是 `tracker-absent`、基线已漂移是
`proposal-baseline-drifted`；只有没有更具体原因时才是折叠后的
`promotion-preflight-<state>`。详见 `references/proposal-promotion-proof.md`。
