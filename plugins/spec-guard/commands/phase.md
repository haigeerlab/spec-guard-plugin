---
description: 查看当前 agent-skills 链路状态
allowed-tools: Bash
---

阶段交接、确认或停止前，读取并遵循 `spec-guard-ops` 的共享检查点规则；按实际路径预告下一步，已有授权不重复询问。

跑一次链路探测并把结果**格式化**报给用户（不要原样贴 JSON）：

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

在 git 仓库里，标题下第一行是 ``Location: branch `<分支>` · worktree `<工作树根目录>`. …``（分离 HEAD 时为 ``detached at `<短 sha>` ``），
各阶段都有；呈现结果时把它一并告诉用户，agent 请用户评审或确认时也应说明这个位置。不在 git 仓库里时没有这一行。

上下文提醒以模块为单位，按最近一轮主会话上下文分两档（宿主在 hook 输入里给出会话记录 `transcript_path` 时才读得到）：

- `MODULE_DONE` / `DONE`：达到窗口 50% 时，事实列表末尾有一行带大小的 `- Module boundary: …`，让 agent 用一句话
  提示可以 `/compact` 或在新会话里开始下一项工作；低于 50% 时没有这一行；读不到大小时保留不带大小的 `- Module boundary: …`。
- `NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING`：只在达到窗口 80% 时多一行 `- Session context: about N k tokens …`，
  让 agent 做完或记下当前 task 后用一句话提示可以 `/compact` 或换会话。

两行都要求 agent 不贴交接文本：交接文本由用户需要时自己运行 `/spec-guard:handoff`（Codex：`spec-guard handoff`）。

Codex 的窗口取自会话记录；Claude 的会话记录没有窗口大小，按 1M 窗口折算为 500k / 800k。本命令手工运行时没有
hook 输入，所以不会出现带大小的行。

`- Paused:` 行表示有被暂停的模块：当前模块以外、todo 既有已勾又有未勾项的模块（显式插队留下的）。它出现在 `NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING`、`MODULE_DONE` 下，`MODULE_DONE` 的下一步会指回它；没有被暂停的模块时不输出。

有 Plan 但没有 `tasks/<id>/todo.md` 的模块按已完成计（没有未勾选项）。现有项目里这类已交付的模块很常见，所以这是有意为之，完成判据不变。
只有 `activeModule` 明确指向这样的模块时，`MODULE_DONE` / `DONE` 才会多一行 ``- activeModule `<id>` has a plan but no `tasks/<id>/todo.md`, so it counts as done; add the todo if work remains.``（在计数行之后、`Paused` 行之前）。模块其实还有活要做时，补一份 `tasks/<id>/todo.md` 列出剩余任务；确已交付则无需处理；已交付、有意不建 todo 的模块，可在 `plan.md` 里加独占一行的 `<!-- spec-guard: no-todo -->` 声明，之后这行提醒不再出现，该模块也不计入 DONE 汇总的 `Plan without todo: N`（仍按已完成计）。自由文本说明不算声明。其他情况输出不变。这行提醒只看文件是否存在，与 `.agent/state.json` 的内容无关（原先对已退役 tracker 模式的抑制已随该字段一并删除，见 `docs/retirements/state-tracker-field.md`）。

当前模块取 `.agent/state.json` 的 `activeModule`（须是能力图中的模块），否则取 Build order 中第一个未完成的模块。
阶段只依据本地文件，不读取 tracker、GitHub 或 Git 历史。

注入文本里凡是来自仓库的值都经过净化：折叠空白、去掉反引号与反斜杠、剥掉控制与格式字符（Cc/Cf）、
限长 200 字符。因为这段文本每轮都进 agent 的上下文，一个带换行的值能伪造出看起来像系统段落的块。
诊断仍然看得出问题出在哪，只是那个值没法再冒充结构；`MAP_INVALID` 引用的能力图原文会标注
「能力图原文，非指令」。`activeModule` 必须完整匹配 kebab-case module id；不是的话会报
「`.agent/state.json` 的 activeModule 不是有效的 module id」并按 Build order 取当前模块——
**值不回显，但也不静默忽略**（你确实设了东西，不说会让人以为生效了），而且 hook 照常激活。

这只作用于**注入边界**，`/spec-guard:verify-artifacts` 与 `/spec-guard:add-module` 的终端输出仍带原始
单元格——定位问题要的就是那个。那两条命令都要求**原样转述**，所以原文经你的转述一样会进上下文；
**本命令不是其中之一**——它转述的是 `additionalContext`，而那正是上面这些规则净化过的产物，
原始单元格根本不在里面。两者真正的区别是频次与框定：注入是**每轮、无人请求**地发生，
转述是**用户显式调用那两条命令后**、并且明确是命令输出。

**无输出**说明当前项目没装约定，提示用户跑 `/spec-guard:setup-convention`。

> 上面那串 `${CLAUDE_PROJECT_DIR:-…toplevel…}` 不是啰嗦：原先写的是 `$(pwd)`，
> 而 Bash 的工作目录在会话里是会被 `cd` 改掉的。从子目录跑时 hook 找不到
> CLAUDE.md，静默退 0 —— 本命令于是报「没装约定」并劝用户跑
> `/spec-guard:setup-convention`，那一步会在**子目录里**再建一套 spec/ tasks/ .agent/。
> 假警报本身已经违反本插件第一条不变量，它还会引出一次破坏性操作。
