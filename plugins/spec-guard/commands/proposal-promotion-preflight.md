---
description: 在人工接受后读取新鲜远端事实，预览是否允许创建 promotion 分支
allowed-tools: Bash
---

只在人工已明确写入 accepted 阶段之后运行：

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
命令本身不创建分支，也不更新 Issue、标签、能力图、模块 Spec、Plan、任务或 PR。
任何其他状态都应原样报告并停止；不得根据旧 checkout 或另一个 worktree 猜测。
