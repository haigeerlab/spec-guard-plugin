---
description: 只读核验模块声明的文档交付状态，不把它当作内容或代码验证
allowed-tools: Bash, Read, Write
---

先选择模块并查询：

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
PROJECT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
MODULE="<module-id>"
python3 -B "$ROOT/hooks/documentation_verification.py" \
  --project "$PROJECT" --module "$MODULE" --format json
```

`absent` 表示项目未启用基线，应静默跳过；`attention` 表示待决、未声明 outcome 或延后事项，属于提醒而非阻断；`ready` 仅表示所有需交付项已**声明** delivered；`invalid` 表示已有表格结构无效。不得把 `ready` 解释为文档内容、发布状态或代码符合度已经验证。

根据用户提供的真实交付事实预览 `Documentation outcome` 表；只有用户明确确认后才修改 Plan 或任何业务文档。不得扫描代码、Git diff、时间戳或权威文档正文来猜测文档状态。
