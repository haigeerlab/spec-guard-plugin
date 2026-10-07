---
description: 在人工接受后读取新鲜远端事实，预览是否允许创建 promotion 分支
allowed-tools: Bash
---

只在人工已把 Issue 标签改成 `proposal-stage:accepted` 之后运行。它重新读取远端 Proposal 池与
Issue 阶段，并做一次新鲜评审（基线未漂移、模块还不在能力图中、依赖齐全、锚点有效）；
不读取策略文件或验收记录：

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
python3 -B "$ROOT/hooks/proposal_promotion_proof.py" \
  --project . --proposal-id "<proposal-id>" \
  --platform "<github|gitlab>" --target "<target>"
~~~

仅当 JSON state 为 ready 时，baseCommit 才是人工创建 promotion 分支可使用的起点。`in-map` 表示模块已在远端能力图里：
已晋级的 Proposal 不需要再预检，改跑 `/spec-guard:proposal-promotion-proof`。
`/spec-guard:add-module --proposal` 在插入前会通过 `promotion_base` 运行同一预检，因此本命令是可选的只读预览。
命令本身不创建分支，也不更新 Issue、标签、能力图、模块 Spec、Plan、任务或 PR。
任何其他状态都应原样报告并停止；不得根据旧 checkout 或另一个 worktree 猜测。

非 ready 状态附带的 `diagnostic` 会尽量透传下层已给出的具体原因，例如缺 Proposal 是
`publication-absent`、缺 tracker Issue 是 `tracker-absent`、基线已漂移是
`proposal-baseline-drifted`；只有没有更具体原因时才是折叠后的
`promotion-preflight-<state>`。详见 `references/proposal-promotion-proof.md`。
