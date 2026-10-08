---
description: 挂起一个在等外部条件的已开工模块（让出当前位置、保留顺序），或明确恢复它；先预览后确认，可选设一个提醒
allowed-tools: Bash
---

阶段交接、确认或停止前，读取并遵循 `spec-guard-ops` 的共享检查点规则；按实际路径预告下一步，已有授权不重复询问。

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
python3 -B "$ROOT/hooks/module_suspend.py" --project "$PROJECT" --suspend <module-id>
```

## 什么时候用

一个模块的代码做完了，只剩要等的东西（某天复核、发版后观察、外部结果），这期间又要做别的模块。挂起后：

- 选当前模块时跳过它，接着做 Build order 里下一个；它**留在原来的位置**，不移动；
- 阶段提示每轮列出 `Suspended: <id>`，只报告这个事实；
- 它不算"做到一半"，所以随后 `/spec-guard:add-module` 不需要 `--interrupt`；
- **永远不会自动恢复。** 插件不记录原因、日期或条件，也不判断该不该回来。

只能挂起已开工的模块（有 Plan 和 todo，且至少一项未勾选）。还没开工的模块不需要挂起，调整顺序即可。临时插一件急事、
做完就回来，用 `add-module --interrupt`（插队），不是挂起。

## 挂起与恢复

默认只预览：打印 `tasks/<id>/todo.md` 的改前改后，以及挂起或恢复后的当前模块。用户确认后加 `--confirm`，
只改这一个文件的一行 `<!-- spec-guard: suspended -->` 并读回核对：

```bash
python3 -B "$ROOT/hooks/module_suspend.py" --project "$PROJECT" --suspend <module-id> --confirm
python3 -B "$ROOT/hooks/module_suspend.py" --project "$PROJECT" --resume <module-id> --confirm
```

恢复只去掉标记，不改 `.agent/state.json`；模块回到 Build order 原位。另一个模块正做到一半时，预览会说明恢复后
它显示为 Paused、等那个模块做完再回来（与插队相同）。拒绝（退出码 2、不写文件）：不是有效 module id、不在能力图上、
没有 Plan 或 todo、没有未勾选项、已挂起（挂起时）或未挂起（恢复时）。

## 提醒（可选）

挂起确认后问用户一句："要不要设一个提醒？"不要从对话里推断日期或内容。用户同意时：

- **时间和内容由用户说**，写进提醒的内容要能独立看懂（哪个项目、哪个模块、要做什么、恢复命令）；
- 用宿主的**持久**提醒能力创建，创建后读回确认。Claude Code 桌面版用定时任务的一次性触发（`fireAt`）；
  只在当前会话有效的定时器（随会话结束失效）不算；
- 宿主没有这种能力时，请用户自己设，不要用别的方式凑；
- 插件不保存提醒，提醒建不成也不影响挂起。
