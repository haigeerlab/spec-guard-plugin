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
FROM="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PROJECT="$(python3 -B "$ROOT/hooks/project_link.py" follow --from "$FROM" --session "${CLAUDE_CODE_SESSION_ID:-}")" || exit 2
CLAUDE_PROJECT_DIR="$PROJECT" bash "$ROOT/hooks/phase-guard.sh"
```

有项目指向时 `follow` 会跟随到被指向的项目：stderr 出现「本次操作的是被指向的项目」时，回复用户时照原文转述这一句；它退出 2 时照原文报告诊断，不要改用会话目录重试。

解析出 `hookSpecificOutput.additionalContext`，原样呈现当前阶段、当前模块、全局计数与建议下一步。阶段含义：

| 阶段 | 含义 |
|---|---|
| `IDLE` | 还没有能力图 |
| `MAP_ONLY` | 有能力图，还没有任何模块 Spec |
| `NEEDS_SPEC` | 当前模块缺 `spec/<id>.md` |
| `NEEDS_PLAN` | 当前模块有 Spec，缺 `tasks/<id>/plan.md` |
| `BUILDING` | 当前模块的 `tasks/<id>/todo.md` 还有未勾选项 |
| `MODULE_DONE` | `.agent/state.json` 的 `activeModule` 指向一个已完成模块（已有 Plan 且没有未勾选项），但能力图中还有别的模块未完成；下一步点名 Build order 中第一个未完成的模块及其阶段，并建议把 `activeModule` 改成它 |
| `DONE` | 能力图中每个模块都已有 Plan 且没有未勾选项。新需求默认用 `/spec-guard:add-module`，需要留痕的审查决定时走 Proposal；若 `activeModule` 仍指向已完成的模块，会多一行提示可以清除 |
| `MAP_INVALID` | 能力图无法按严格规则解析 |
| `UNKNOWN` | 阶段无法计算（例如任务文件无法读取） |

在 git 仓库里，标题下第一行是 ``Location: branch `<分支>` · worktree `<工作树根目录>`. …``（分离 HEAD 时为 ``detached at `<短 sha>` ``），
各阶段都有；呈现结果时把它一并告诉用户，agent 请用户审阅或确认时也应说明这个位置。不在 git 仓库里时没有这一行。

`.agent/config.json` 的 `artifactLanguage` 恰好是 `zh-CN` 时，说明文字改用中文（hint-language-follow）：例如
``位置: 分支 `<分支>` · worktree `<目录>`。…``、`- 能力图: 已有`、`建议下一步: …`、`- 模块边界: …`。
标题行 `## spec-guard local workflow`、阶段代码、命令、路径、模块 id 与标记行不变；阶段行中文写 `当前阶段: **<阶段>**`，
英文写 `Current stage: **<阶段>**`。未设、其他语言或配置无效时，输出为英文（quiet-injection 起英文输出里不再夹固定的中文标签；
停点规则正文只有中文，能力图无效时引用的解析器诊断原样保留）。

完整输出末尾有一行 `<!-- spec-guard-state: <8 位十六进制> -->`（quiet-injection）。它由阶段、当前模块、Spec 与 Plan 的批准状态、
停点、checkout 角色、挂起与暂停的模块、有无未合进上游的提交、项目配置行、位置行、跟随指向的项目、提示语言算出，不含未勾选数与
上下文用量。每轮 hook 从会话记录里找最近一次 spec-guard 注入（Claude 的 `hook_additional_context` 附件、Codex 的 developer 消息，
不认用户或助手消息里的文字）：状态码相同就只给一行
``spec-guard: <阶段> · `<模块>` · <N> unchecked · branch `<分支>` (unchanged; see the earlier phase hint for details)``
（中文为「未勾选 <N> · 分支 …（状态未变，完整说明见此前的阶段提示）」），后面可能另起一行附模块边界行或记账提醒。新会话、压缩之后、
会话记录读不到或找不到上一次注入、状态码不同，都给完整内容；`MAP_INVALID`、`UNKNOWN` 这类诊断不带状态码，每轮完整。
本命令手工运行时没有会话记录，所以总是完整输出。

上下文提醒只在模块边界出现（宿主在 hook 输入里给出会话记录 `transcript_path` 时才读得到大小）：`MODULE_DONE` / `DONE`，以及当前模块
还没有 Spec 的 `NEEDS_SPEC`，达到窗口 70% 时事实列表末尾有一行带大小的 `- Module boundary: …`，让 agent 把一条可直接复制的
命令单独放进代码块：接着做相关工作时是 `/compact`，换到不相关工作时是 `/clear`；低于 70% 或读不到大小时没有这一行。模块进行中
（`NEEDS_PLAN`、`BUILDING`）不再提醒，上下文交给宿主管理（quiet-injection，决定 D6）。

命令写法按宿主给（codex-command-wording）：Claude Code 里 `/compact` 后面带 agent 填好的一句聚焦说明，插件命令写作
`/spec-guard:add-module` 这类斜杠命令和 `/build`、`/plan`；Codex 的 `/compact` 不能带参数，只给 `/compact`，插件命令写作 `` `$spec-guard-ops` ``
加动作、`` `$incremental-implementation` ``、`` `$planning-and-task-breakdown` ``。宿主按 `SPEC_GUARD_HOST`（`codex`／`claude`）、
hook 输入（带 `turn_id` 或会话记录首条为 `session_meta` 即 Codex）、环境（有 `CLAUDE_PROJECT_DIR` 为 Claude，否则有
`PLUGIN_ROOT` 为 Codex）依次判断；都判断不了时沿用改前的写法。

这一行要求 agent 不贴交接文本，也不建议开新会话。刚压缩过时按压缩后的大小判断：Claude 取压缩记录里压缩后的 token 数，
Codex 的压缩记录没有大小，按低于阈值处理；压缩后已有新读数时用新读数。

Codex 的窗口取自会话记录；Claude 的会话记录和 hook 输入都没有窗口大小，按读数估算：会话记录尾部有读数超过 200k 就按 1M 窗口
（700k 起提醒），否则按 200k 窗口（140k 起提醒），这一行写明「estimated」／「估算」。本命令手工运行时没有 hook 输入，所以不会出现带大小的行。

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
