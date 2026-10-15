# Plan: compact-phase-injection

<!-- spec-guard: review approved -->

依据 [`spec/compact-phase-injection.md`](../../spec/compact-phase-injection.md)（2026-10-15 已批准）。本模块按分开审：Spec 已单独批准，
本 Plan 单独审。分支 `claude/compact-phase-injection`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `589c77e`（v0.60.4 验证记录
合并）开出。本模块一个 PR，含 0.61.0 版本号；合并后的 tag、Release、两边宿主同步与验证记录按 `docs/release-process.md` 另走。

所需工具：无 UI 改动。Task 1 要在临时目录里起两边宿主的真实会话（`claude -p --plugin-dir`、`codex exec`），会临时改动并恢复
`~/.codex/config.toml`，事前备份、事后逐字核对。

## Overview

先实测、再写测试、再实现：信任与触发的事实决定了说明怎么写，也可能让本模块停下。实现集中在 `phase-guard.sh` 的事件名参数与
`hooks.json` 新增一项，其余是文档。

## Architecture Decisions

- **事件由注册处告诉脚本，不由脚本猜。** `hooks.json` 的 `SessionStart` 一项调用 `phase-guard.sh SessionStart`；脚本据参数输出事件名、
  追加核对提醒。不带参数时一切照旧。
- **已有一项逐字不变。** Codex 的钩子信任按项记录（`config.toml` 的 `[hooks.state."spec-guard@…:hooks/hooks.json:user_prompt_submit:0:0"]`，
  值是该项的哈希）；`UserPromptSubmit` 一项一个字节都不改，它的信任就不受影响。新增的 `SessionStart` 一项需要用户单独信任一次。
- **测试防回归。** 不带参数的现有 298 例期望值一个不改。

## Task List

### Task 1：动手前的宿主实测（Spec Assumptions 8、9）

在临时目录里放一份改好 `hooks.json` 的插件副本（只改注册，`SessionStart` 一项先指向现有脚本），分别实测：

- **Codex**：用临时的 `CODEX_HOME` 或在备份后的真实配置上，确认新增一项后已有的 `user_prompt_submit` 信任记录仍然有效、新一项单独待信任；
  在临时项目里逼一次中途压缩（`-c model_auto_compact_token_limit=…`），看 `SessionStart(compact)` 是否触发、注入是否进对话。
- **Claude Code**：`claude -p --plugin-dir <副本>`，看插件钩子是否需要 `/hooks` 信任；`/compact` 后是否触发；尽量逼出一次一轮中途的
  自动压缩，测不出就记为未验证。
- **两边都测手动压缩**：手动 `/compact` 后是否触发；钩子输入能否区分手动与自动压缩（例如 Claude Code 输入里的 `trigger`）。手动压缩后
  用户的下一条消息还会触发现有注入，所以手动时会重复注入一次；能区分时在 todo 里记下，是否只在自动压缩时注入交用户在检查点决定。
- 结果记入 todo。**停下条件**：已有的 `UserPromptSubmit` 会因新增一项而失效或需要重新信任——停下交用户决定，不进入 Task 2。
- 验证：事前事后 `shasum ~/.codex/config.toml`；实测命令与观察写入 todo。
- 文件：只在临时目录；仓库不改。

### Task 2：测试先行（先红）

`test-phase-guard.sh` 新增第 15 段：带 `SessionStart` 参数时正常注入、python3 不可用、python3 跑不起来三种输出的 `hookEventName` 都是
`SessionStart`；正常注入末尾有核对提醒、其余内容与不带参数时逐字相同；无激活信号的项目带参数时照旧静默；未知参数按 `UserPromptSubmit`
处理。另加 `hooks.json` 的结构断言：两项都在，`SessionStart` 的 matcher 是 `compact`，命令带 `SessionStart` 参数，两处兜底的事件名与所在项
一致，`UserPromptSubmit` 一项与 `main` 上逐字相同。

- 验收：新段在旧代码上失败；现有 14 段不受影响。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`。
- 文件：`hooks/test-phase-guard.sh`。

### Task 3：实现

`phase-guard.sh` 读第一个参数定事件名（`SessionStart` 或其他一律 `UserPromptSubmit`），三处输出用它；为 `SessionStart` 时在注入末尾加
核对提醒。`hooks.json` 新增 `SessionStart` 一项。

- 验收：Task 2 新段全绿，现有 298 例期望值不改；ShellCheck 无告警；两处变异（忽略参数、提醒加到 `UserPromptSubmit`）各有断言变红。
- 验证：`verify-and-commit.sh` 全档（含 ShellCheck）；macOS `/bin/bash`。
- 文件：`hooks/phase-guard.sh`、`hooks/hooks.json`。

### Checkpoint 1（report）：钩子回归全绿，ShellCheck 无告警

### Task 4：文档、CHANGELOG 与版本号

`docs/design.md` 写明两个触发点与按项信任；`docs/troubleshooting.md` 加“压缩后没有注入”一行（信任新一项、宿主版本、按会话登记）；
`docs/commands.md` 或 `link-project` 说明里点出压缩后注入依赖按会话登记（若已有相应位置）；按 Task 1 结果改 README 安装表那一行；
`CHANGELOG.md` 新增 `[0.61.0]`，写清前提与升级后要信任新一项；两份 `plugin.json` 改为 0.61.0，中英 README 的 `--ref` 改为 v0.61.0。

- 验收与验证：`verify-and-commit.sh` 全档。
- 文件：`docs/design.md`、`docs/troubleshooting.md`、`README.md`、`README.en.md`、`CHANGELOG.md`、两份 `plugin.json`，可能还有 `commands/link-project.md`。

### Checkpoint 2（gate）：模块评审

展示验证结果、未验证项、实际改动的文件清单与文档建议。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- **Codex 用户升级后不信任新一项**：新一项被静默跳过，压缩后没有注入，与现在相同；已有注入不受影响。发版说明写清。
- **宿主对 `SessionStart` 输出的校验与 `UserPromptSubmit` 不同**：Task 1 实测时一并确认注入能进对话。
- **压缩后的注入里上下文提示**：读的是压缩后的大小（0.52 已处理压缩记录），由现有回归覆盖。
- 一轮中途的自动压缩在 Claude Code 上可能测不出，如实记为未验证。

## 返工：Codex 升级并信任后要重启（2026-10-15）

发版后的真实使用里，一个消费者项目的 Codex 会话升级到 0.61.0、新一项也已信任，但第 17 次压缩后没有注入：那个 Codex 应用是在
升级之前启动的。重启 Codex 后，第 18 次压缩后 0.3 秒内就出现了注入，位置、阶段与核对提醒都对。现有文档只写了“信任一次”，
没写要重启，照着做的人会以为没生效。

只改文档文字，不动钩子与测试，不改版本号：README 与 `docs/` 不在发布包里，合并即生效，不发版。0.61.0 的 CHANGELOG 段落
是已发布的记录，不回改。

### Task 5：补写“升级并信任后重启 Codex”

- 中英 README 安装表那一行的 Codex 一栏：信任新一项后重启 Codex（已在运行的 Codex 不会加载升级后新增的钩子）。
- `docs/troubleshooting.md`「压缩后没有阶段注入」的 Codex 一条：补上“信任了仍没有 → 重启 Codex”。
- 验收与验证：`verify-and-commit.sh`（只改文档类路径，走快档）。
- 文件：`README.md`、`README.en.md`、`docs/troubleshooting.md`，以及本 Plan 与 todo。

### Checkpoint 3（gate）：返工评审

展示改动文字与实际改动的文件清单。推送与开 PR 在此由用户确认，合并由用户进行。
