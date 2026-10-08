---
description: 协作能力已移到独立插件 agent-relay：检查它是否可用并转交，未安装时给出安装与迁移指引
allowed-tools: Bash
---

本命令是过渡入口，将在 0.54.0 移除。协作（本机信箱、会话路由、跨宿主委派）现在由独立插件 agent-relay 提供，
Spec Guard 不再执行任何协作操作。

先只读检查 agent-relay：

```bash
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
python3 -B "$ROOT/hooks/agent_relay_probe.py" --host claude
```

按输出的 `state` 处理：

- `ready`：告诉用户协作由 agent-relay 提供，查看、安装运行时或接入宿主用 `/agent-relay:collaboration`，日常加入、
  看消息、发消息用 `agent-relay:collab` skill，按名字联系会话用 `agent-relay:session-routing`，创建审查或开发会话用
  `agent-relay:session-delegation`。到此为止，不在 Spec Guard 里继续。
- `runtime-not-ready`：原样转述 `message`（其中是 agent-relay 自己的初始化提示），不代为安装。
- `not-installed`、`incompatible`：原样转述 `message`，工作流照常使用。
- `unknown`：原样转述 `message`；这表示检查本身失败，不能说成未安装。

无论哪种状态，都补一句：用过 Spec Guard 内置协作的话，旧的信箱与委派数据没有被删除，迁移和旧宿主条目的清理步骤见
`docs/migrations/2026-10-07-collaboration-split.md`。不读取、不修改旧数据，也不修改任何宿主配置或权限文件。
