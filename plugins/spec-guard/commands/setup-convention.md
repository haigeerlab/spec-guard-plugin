---
description: 在当前项目落地本地多 Spec 目录约定
argument-hint: "[local] [--dry-run] [--replace]"
allowed-tools: Bash
---

执行确定性安装脚本；它只支持本地文件式工作流，不会认证或访问远端 tracker。先预览：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/setup-convention.sh" $ARGUMENTS --dry-run
```

原样转述预览输出，并等待用户明确确认后，才去掉 `--dry-run` 再运行一次；用户参数里已有 `--dry-run` 时只预览。
缺省模式为 `local`。`--replace` 仅替换已有受管声明块；已有声明块的标记重复、缺失或顺序错误时，脚本拒绝并
不改动任何文件。
GitHub 与 GitLab tracker 模式已退役，脚本会拒绝它们且不写文件。
若 teardown 留有 .agent/state.json.disabled，setup 会在预览阶段拒绝新建空状态；确认要恢复时，
先人工核对并将其改回 .agent/state.json。两个文件并存时也先人工核对，不自动选择副本。

成功后原样转述脚本输出，并提醒用户提交受影响的声明块、`spec/`、`tasks/` 和
`.agent/state.json`。旧 remote tracker state 是历史记录，不得用本命令覆盖。
