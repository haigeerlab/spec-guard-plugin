---
description: 查看当前 agent-skills 链路状态
allowed-tools: Bash
---

阶段交接、确认或停止前，读取并遵循 `spec-guard-ops` 的共享检查点规则；按实际路径预告下一步，已有授权不重复询问。

跑一次链路探测并把结果**格式化**报给用户（不要原样贴 JSON）：

```bash
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
PROJECT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
CLAUDE_PROJECT_DIR="$PROJECT" bash "$ROOT/hooks/phase-guard.sh"
```

解析出 `hookSpecificOutput.additionalContext`，原样呈现当前阶段、当前模块、全局计数与建议下一步。阶段含义：

| 阶段 | 含义 |
|---|---|
| `IDLE` | 还没有能力图 |
| `MAP_ONLY` | 有能力图，还没有任何模块 Spec |
| `NEEDS_SPEC` | 当前模块缺 `spec/<id>.md` |
| `NEEDS_PLAN` | 当前模块有 Spec，缺 `tasks/<id>/plan.md` |
| `BUILDING` | 当前模块的 `tasks/<id>/todo.md` 还有未勾选项 |
| `MODULE_DONE` | `.agent/state.json` 的 `activeModule` 指向一个已完成模块（已有 Plan 且没有未勾选项），但能力图中还有别的模块未完成；下一步点名 Build order 中第一个未完成的模块及其阶段，并建议把 `activeModule` 改成它 |
| `DONE` | 能力图中每个模块都已有 Plan 且没有未勾选项。新需求默认用 `/spec-guard:add-module`，需要留痕的评审决定时走 Proposal；若 `activeModule` 仍指向已完成的模块，会多一行提示可以清除 |
| `MAP_INVALID` | 能力图无法按严格规则解析 |
| `UNKNOWN` | 阶段无法计算（例如任务文件无法读取） |

`- Paused:` 行表示有被暂停的模块：当前模块以外、todo 既有已勾又有未勾项的模块（显式插队留下的）。它出现在 `NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING`、`MODULE_DONE` 下，`MODULE_DONE` 的下一步会指回它；没有被暂停的模块时不输出。

当前模块取 `.agent/state.json` 的 `activeModule`（须是能力图中的模块），否则取 Build order 中第一个未完成的模块。
阶段只依据本地文件，不读取 tracker、GitHub 或 Git 历史。

**无输出**说明当前项目没装约定，提示用户跑 `/spec-guard:setup-convention`。

> 上面那串 `${CLAUDE_PROJECT_DIR:-…toplevel…}` 不是啰嗦：原先写的是 `$(pwd)`，
> 而 Bash 的工作目录在会话里是会被 `cd` 改掉的。从子目录跑时 hook 找不到
> CLAUDE.md，静默退 0 —— 本命令于是报「没装约定」并劝用户跑
> `/spec-guard:setup-convention`，那一步会在**子目录里**再建一套 spec/ tasks/ .agent/。
> 假警报本身已经违反本插件第一条不变量，它还会引出一次破坏性操作。
