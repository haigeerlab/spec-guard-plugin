---
description: 用户判定用法草案的一个里程碑通过后，记下确认：先预览后确认，只在草案里写一行确认记录
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
FROM="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PROJECT="$(python3 -B "$ROOT/hooks/project_link.py" follow --from "$FROM" --session "${CLAUDE_CODE_SESSION_ID:-}")" || exit 2
python3 -B "$ROOT/hooks/milestone_mark.py" --project "$PROJECT" --draft spec/usage/<需求>.md --milestone M<n>
```

有项目指向时 `follow` 会跟随到被指向的项目：stderr 出现「本次操作的是被指向的项目」时，回复用户时照原文转述这一句；它退出 2 时照原文报告诊断，不要改用会话目录重试。

## 什么时候用

阶段提示报「里程碑停点」时：一个里程碑的模块都已完成，还没有确认记录。先按共享检查点规则「用法草案」一节的「里程碑停点」，
把这个里程碑的每个典型用法实际跑一遍、把命令与输出摆给用户，由用户判定。

- **用户明确说本里程碑通过之后**，才用本命令；「看起来还行」「继续」不算，先问清楚。批准来源以所装协作插件的规定为准；没装只认当前对话里的明确判定。
- 用户说不通过时不用本命令：在本里程碑的模块 todo 里追加任务（共享检查点规则「返工与小模块」），或回头改草案与后面还没开工的模块。
- 不得为了消除阶段提示而自行确认；记录是给后续会话的，不是授权来源。

## 记录是什么

草案 `## Milestones` 表之后一行一个里程碑，列出确认时它的模块：

```text
<!-- spec-guard: milestone M1 confirmed module-a, module-b -->
```

确认后里程碑表里这一行的模块变了（例如 add-module 后归进来一个新模块），记录失效，新模块做完后阶段提示会再停一次；
再确认时旧行原地替换。`/spec-guard:verify-artifacts` 对写坏的记录判失败，对失效的记录只提醒。

## 预览与确认

默认只预览：列出里程碑的模块与各自阶段、要跑的典型用法、将写入的那一行与 diff、确认后阶段提示转到哪。把预览给用户看过、
得到明确确认后，才在同一条命令后加 `--confirm`；写入只改这一份草案并读回核对：

```bash
python3 -B "$ROOT/hooks/milestone_mark.py" --project "$PROJECT" --draft spec/usage/<需求>.md --milestone M<n> --confirm
```

已有有效记录时说明无需改动并正常退出。拒绝（退出码 2、不写文件）：`--draft` 不是 `spec/usage/` 下的草案、草案或能力图读不了、
里程碑不存在、模块不在能力图上、有模块还没完成、前面还有没确认的里程碑。
不执行任何 Git 或远端操作，不改 todo、`.agent/state.json` 或能力图。
