---
description: 在当前项目落地本地多 Spec 目录约定
argument-hint: "[local] [--dry-run] [--replace [--accept-removals]]"
allowed-tools: Bash
---

执行确定性安装脚本；它只支持本地文件式工作流，不会认证或访问远端 tracker。先预览：

```bash
FROM="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PROJECT="$(python3 -B "${CLAUDE_PLUGIN_ROOT}/hooks/project_link.py" follow --from "$FROM" --session "${CLAUDE_CODE_SESSION_ID:-}")" || exit 2
CLAUDE_PROJECT_DIR="$PROJECT" bash "${CLAUDE_PLUGIN_ROOT}/hooks/setup-convention.sh" $ARGUMENTS --dry-run
```

有项目指向时 `follow` 会跟随到被指向的项目：stderr 出现「本次操作的是被指向的项目」时，回复用户时照原文转述这一句；它退出 2 时照原文报告诊断，不要改用会话目录重试。

原样转述预览输出，并等待用户明确确认后，才去掉 `--dry-run` 再运行一次；用户参数里已有 `--dry-run` 时只预览。
缺省模式为 `local`。`--replace` 仅替换已有受管声明块；已有声明块的标记重复、缺失或顺序错误时，脚本拒绝并
不改动任何文件。项目自己的规则写进块内的本地段：独占一行的 `<!-- BEGIN:spec-guard-local -->` 与
`<!-- END:spec-guard-local -->` 之间的行在 `--replace` 后原样保留在新块末尾（本地段最多一个，标记无效时拒绝）。
`--replace --dry-run` 逐行列出 `will remove:` 与 `will add:`；要删除的行不在现行模板或已退役的派活规则段里时标着
`[needs --accept-removals]`，真正替换会拒绝并不改文件。原样转述这些行，让用户决定把它们移进本地段，还是明确同意
删除后加 `--accept-removals` 重跑；从旧版模板升级时，旧模板的行同样需要这一步。从 0.83.2 及更早的模板升级时，删掉的行大多是交审、验收这类停点规则：它们已移到插件的 `references/node-rules.md`，阶段提示到了节点会附上，确认后加 `--accept-removals` 即可；想留哪一行就先移进本地段。
块里每条标记（块标记、本地段标记）前后各留一个空行，符合 oxfmt、Prettier 等 Markdown 格式化器的规则；空行有变化时预览多一行 `will adjust blank lines: add N, remove M`，这不需要 `--accept-removals`；块完全不用改时才报 `block content unchanged`。本地段内部原样保留。
派活规则段已退役：`--dispatch`／`--no-dispatch` 会被拒绝（退出 2，不写文件）。旧块里还带着规则段
（首行 `<!-- spec-guard: build-task-dispatch -->`）时，`--replace` 移除整段、不需要 `--accept-removals`，预览单列一行
`retired build-task-dispatch rule section will be removed`，转述时不要省略。
GitHub 与 GitLab tracker 模式已退役，脚本会拒绝它们且不写文件。
若 teardown 留有 .agent/state.json.disabled，setup 会在预览阶段拒绝新建空状态；确认要恢复时，
先人工核对并将其改回 .agent/state.json。两个文件并存时也先人工核对，不自动选择副本。

成功后原样转述脚本输出，并提醒用户提交受影响的声明块、`spec/`、`tasks/` 和
`.agent/state.json`。旧 remote tracker state 是历史记录，不得用本命令覆盖。
