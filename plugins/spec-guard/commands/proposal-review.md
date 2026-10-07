---
description: 读取远端默认分支上一个已发布 Proposal 及其 Issue 阶段，只读报告新鲜度与阶段
allowed-tools: Bash
---

任何分支都可以运行；它只读取远端默认分支快照和 GitHub/GitLab 上的 Proposal Issue：

~~~bash
ROOT="${CLAUDE_PLUGIN_ROOT}"
[ -n "$ROOT" ] || ROOT="${PLUGIN_ROOT:-}"
WHY="宿主没有把插件根目录代入命令，环境里也没有 CLAUDE_PLUGIN_ROOT 或 PLUGIN_ROOT"
if [ -z "$ROOT" ]; then
  if ! command -v codex >/dev/null 2>&1; then
    WHY="${WHY}；也没有 codex 可查询"
  else
    LIST="$(codex plugin list --available --json 2>/dev/null)"; RC=$?
    ROOT="$(printf '%s' "$LIST" | python3 -c '
import json, sys
try:
    plugins = json.load(sys.stdin).get("installed", [])
except (AttributeError, TypeError, ValueError):
    sys.exit(3)
for plugin in plugins:
    if isinstance(plugin, dict) and plugin.get("name") == "spec-guard" and plugin.get("installed") and plugin.get("enabled"):
        source = plugin.get("source")
        path = source.get("path") if isinstance(source, dict) else None
        if isinstance(path, str) and path:
            print(path)
            sys.exit(0)
sys.exit(4)
')"
    case $? in
      0) ;;
      4) WHY="${WHY}；codex plugin list 没有列出已启用且带路径的 spec-guard" ;;
      *) WHY="${WHY}；codex plugin list 查询失败（退出码 ${RC}）或输出无法解析" ;;
    esac
  fi
fi
[ -n "$ROOT" ] || { echo "spec-guard 无法定位插件根目录：${WHY}。这是定位失败，不代表插件未安装。" >&2; exit 2; }
[ -d "$ROOT" ] || { echo "spec-guard 插件根目录不存在：${ROOT}（插件可能刚更新或被移除，重开会话后再试）。" >&2; exit 2; }
python3 -B "$ROOT/hooks/proposal_review.py" \
  --project . --proposal-id "<proposal-id>" \
  --platform "<github|gitlab>" --target "<owner/repo 或 GitLab project id>"
~~~

原样报告 JSON。`awaiting-review` 与 `in-review` 表示可由人把 Issue 标签改成 `proposal-stage:accepted`；`stale` 表示能力图或基线已变化，
需要作者按新基线重新发布；`in-map` 表示远端能力图里已经有这个模块（`proposal-module-already-present`）：若是本 Proposal
已晋级，下一步运行 `/spec-guard:proposal-promotion-proof`，`proved` 后用 `/spec-guard:proposal-closeout` 收尾；若是与已有模块
重名，换一个 module id 重新发布。本命令不判断是哪一种，判断交给晋级证明；`absent` 表示远端默认分支上没有该 Proposal，或没有对应 Issue。
`accepted` 与 `promoted-claim` 只是观察到的 Issue 标签，既不是晋级授权，也不是晋级证明。
读到了 Proposal 的结果都带 `moduleId`：这是 Proposal 要加入能力图的模块，与 `proposalId` 不一定相同，转述时按它称呼模块。
本命令不会创建或修改 Issue、标签、能力图、Proposal、分支、任务或 PR。
