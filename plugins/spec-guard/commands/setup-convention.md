---
description: 在当前项目落地本地多 Spec 目录约定
argument-hint: "[local] [--dry-run] [--replace] [--dispatch|--no-dispatch]"
allowed-tools: Bash
---

执行确定性安装脚本；它只支持本地文件式工作流，不会认证或访问远端 tracker。先预览：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/setup-convention.sh" $ARGUMENTS --dry-run
```

原样转述预览输出，并等待用户明确确认后，才去掉 `--dry-run` 再运行一次；用户参数里已有 `--dry-run` 时只预览。
缺省模式为 `local`。`--replace` 仅替换已有受管声明块；已有声明块的标记重复、缺失或顺序错误时，脚本拒绝并
不改动任何文件。
**实验性**：省钱效果未经证明。对照实验里派活没有减少主会话轮次，opus 父代理加 sonnet 子代理仍比不派贵 15%–54%，所以规则默认由主代理自己做，只有预计需要大量探索或调试的 task 才考虑派。
`--dispatch` 在约定块的基础模板之后加一段可选规则：`/build` 把 todo 中非 Checkpoint 的 task 交给一个子代理做
RED → GREEN → 回归 → 构建，交出完整任务块与 plan 的 Architecture Decisions，派活 prompt 带 tier-guard 档位标记；
任务块不完整、属于停止条件、L3、或所选模型不比主会话便宜时不派；验收、提交、勾选与问人留在主代理。默认关闭，
不带开关时约定块与基础模板逐字相同。开关状态存在块里（规则段首行 `<!-- spec-guard: build-task-dispatch -->`）：
`--replace` 时块内有这一行就保持开启，关闭须显式 `--no-dispatch`；两者同时给出时拒绝。已有块不带 `--replace`
时开关不生效。预览里的 `build-task-dispatch rule:` 一行写明状态与来源，转述时不要省略。规则只是引导，
spec-guard 不检测、也不要求安装 tier-guard。Codex（`--host=codex`）上同样可用：Codex 默认的 workspace-write 沙箱不允许写 `.git`，主代理每次提交都会申请提权，需要你审批。
GitHub 与 GitLab tracker 模式已退役，脚本会拒绝它们且不写文件。
若 teardown 留有 .agent/state.json.disabled，setup 会在预览阶段拒绝新建空状态；确认要恢复时，
先人工核对并将其改回 .agent/state.json。两个文件并存时也先人工核对，不自动选择副本。

成功后原样转述脚本输出，并提醒用户提交受影响的声明块、`spec/`、`tasks/` 和
`.agent/state.json`。旧 remote tracker state 是历史记录，不得用本命令覆盖。
