# Plan: open-commitments

<!-- spec-guard: review approved -->

依据 [`spec/open-commitments.md`](../../spec/open-commitments.md)（已批准，`21a7bdf1ac05`）。本仓库评审节奏为分开审：Spec 已单独批准，
本 Plan 单独交审。分支 `claude/open-commitments`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `e77af2e` 开出；
能力图新行与 Spec 已在 `901167f` 提交。本模块一个 PR，含 0.69.0 版本号；合并后的发版步骤按 `docs/release-process.md` 另走。
对应的账本事项：《外部需求：未了承诺落盘与读回（open-commitments，0.69.0）》（HP2G7RV，`waiting-on-me`）。

所需工具：无 UI 改动，不需要浏览器或电脑操作；宿主实测用 `claude -p --plugin-dir` 与 Codex smoke。

## Overview

三块改动：共享检查点规则新增「未了的承诺」一节、两份约定块模板各新增两行；`phase-guard.sh` 新增 `SessionStart fresh`
（会话开始与清空后只出一句读回提醒）并在压缩后的核对提醒里补账本一句，都只在项目根有 `.epiq/project.json` 时生效；
`hooks.json` 新增一项 `SessionStart`（matcher `startup|clear`）。外加文档与 0.69.0 版本号。

## Architecture Decisions

- **钩子只看一个文件在不在。** `[ -f "$PROJECT/.epiq/project.json" ]` 用 bash 内建判断，不读 `.epiq` 下的其他内容，不调 Epiq；
  这样不和 Epiq 的存储格式耦合，也守住「只依赖 bash、git、python3」。
- **`fresh` 只出一句，不出阶段摘要。** 阶段摘要由随后的 `UserPromptSubmit` 给，避免同一轮注入两遍；判断顺序沿用现有激活与指向
  文件解析，未激活、没有账本时在启动 python3 之前静默退出 0。
- **账本一句按语言分两份字面量**，沿用 `hint-language-follow` 的做法；没有账本时压缩后的核对提醒保持 0.68.0 的原字面量，
  逐字节回归。
- **规则只有一个出处，模板只新增行**，与 0.63.1 相同。

## Task List

### Task 0：提交已批准的 Plan 与 todo

- 验收：`verify-and-commit.sh` 快档通过并提交。
- 验证：`/bin/bash scripts/verify-and-commit.sh -- -m "<信息>"`。
- 文件：`tasks/open-commitments/plan.md`、`tasks/open-commitments/todo.md`。

### Task 1：规则「未了的承诺」与模板行（先红）

`test_workflow_checkpoints.py` 加 Spec「Testing strategy」列出的关键词断言并确认失败；再在 `references/workflow-checkpoints.md`
的「需求来源与回告」之后新增一节（记录五项与三个标签、写入规矩、两道闸门、没启用账本、隐私），两份模板与
`docs/convention-block.md` 各新增两行。

- 验收：`test_workflow_checkpoints.py` 通过；`validate.sh --quick` 通过；`git diff` 显示两份模板只有新增行。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`；`/bin/bash scripts/validate.sh --quick`。
- 文件：`references/workflow-checkpoints.md`、`templates/claude-block-local.md`、`templates/codex-block-local.md`、
  `docs/convention-block.md`、`hooks/test_workflow_checkpoints.py`。

### Task 2：钩子的读回提醒（先红）

`test-phase-guard.sh` 先加断言并确认失败：

- `SessionStart fresh`：有 `.epiq/project.json` 时事件名为 `SessionStart`、只输出读回提醒（`zh-CN` 与默认英文各一例，不含阶段摘要）；
  没有账本、项目未激活时无输出且退出 0；经指向文件解析的项目按目标项目根判断账本；
- `SessionStart`（压缩）：有账本时核对提醒含账本一句（中英各一例）；没有账本时与 0.68.0 逐字节相同；
- `UserPromptSubmit`：有无账本输出相同；
- `hooks.json`：三项都在，新一项 matcher 为 `startup|clear`、调用 `phase-guard.sh SessionStart fresh`，两处兜底的事件名为
  `SessionStart`；原有两项逐字不变。

再改 `phase-guard.sh` 与 `hooks.json`。

- 验收：phase-guard 回归全绿；ShellCheck 无警告。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`；`shellcheck plugins/spec-guard/hooks/phase-guard.sh`。
- 文件：`hooks/phase-guard.sh`、`hooks/hooks.json`、`hooks/test-phase-guard.sh`。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告

### Task 3：宿主实测新一项钩子会触发

临时项目（启用约定并放一个 `.epiq/project.json`）里：

- Claude：`claude -p --plugin-dir <工作区插件目录>` 跑一轮，从会话记录确认 `SessionStart`（startup）注入了读回提醒；
- Codex：用 `evals/codex-plugin-smoke.sh` 建的临时消费者项目跑一轮新会话，确认同样的注入（需要信任新的一项钩子时如实记录）。

`/clear` 只能在交互会话里触发，放到发版后的验证。任一宿主不触发时停下报告，不在本模块改方案。

- 验收：两边新会话的实测结果记入 todo，包括没测到的部分。
- 文件：无仓库文件改动（只记 todo）。

### Task 4：文档、CHANGELOG 与版本号

`docs/workflow.md` 一段“有人在等的事”；`docs/design.md` 钩子表与数据流补新的 `SessionStart` 一项及“只判断账本文件是否存在”；
CHANGELOG `[0.69.0]`（写明 Codex 要单独信任新的一项钩子）；两份 `plugin.json` 改为 0.69.0，中英 README 的 `--ref` 改为 v0.69.0，
README 补一句 Codex 信任说明。

- 验收：`validate.sh` 通过（清单版本一致）。
- 验证：`/bin/bash scripts/validate.sh`。
- 文件：`docs/workflow.md`、`docs/design.md`、`CHANGELOG.md`、`plugins/spec-guard/.claude-plugin/plugin.json`、
  `plugins/spec-guard/.codex-plugin/plugin.json`、`README.md`、`README.en.md`。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

最终 gate 列出实际改动的文件、验证结果与未验证项，并列出拟回告：

- 对象：session-protocol 契约负责人（最近会话 `local_a9d06942-9b64-4887-b490-0088b10b8c75`），渠道 Claude 原生会话消息（内部）；
- 内容：0.69.0 的版本号、改了什么、怎么升级、对方仓库要启用约定与账本才有钩子提醒；
- 发送时机：发版之后；发送后在 HP2G7RV 评论记录并以“已告知”关闭。

### 发版后的验证

按 Spec「Testing strategy」两边宿主各跑一次真实会话：中途收到需求 → 当场记账本 → `/clear` → 新会话找回事项与回复对象 →
内部告知直接发、答应日期先问用户。结果如实记入 todo，记录放 `docs/releases/`。
