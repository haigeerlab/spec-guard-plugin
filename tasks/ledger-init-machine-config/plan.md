# Plan: ledger-init-machine-config

<!-- spec-guard: review approved -->

依据 [`spec/ledger-init-machine-config.md`](../../spec/ledger-init-machine-config.md)（已批准）。本仓库评审节奏为分开审：Spec 已批准，本 Plan 单独交审。
分支 `claude/ledger-init-machine-config`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `7444242`（#360 合并）开出。
本模块一个 PR，含 0.71.0 版本号；未发布的 `stdin-timing-test` 一起发。发版后另开一个收尾 PR 放证据。

所需工具：无 UI 改动；真实 Epiq 核对用已装的固定运行时（`~/.spec-guard/local-ticket-ledger/runtime`，Epiq 1.11.0），在临时 `EPIQ_GLOBAL_DIR` 与临时仓库里做，不碰本机设置。

## Overview

只改 `hooks/local_ledger_runtime.py`、它的单测和三份说明文档：三项初始化参数改为可选；Epiq 拒绝时报清理过的 message；初始化警告另报条数与编号；
`status` 只读地报告机器级设置。每个代码任务先写失败的单测再改实现。

## Architecture Decisions

- **清理只在一处。** 新增一个模块内函数做「控制字符换空格、合并空白、遮掉任意位置 URL 的 userinfo、限 300 字」，只给 `read_mcp_tool_result` 用；`redact_url` 不动。
- **以 Epiq 为准。** 我们不比较用户给的值和机器值，冲突由 Epiq 判断并给出 message；`machineSetup` 只是给 agent 看的事实。
- **读机器设置用与 `storage_check` 相同的目录解析**（`EPIQ_GLOBAL_DIR` 优先），`lstat` 判断普通文件后再读，限 64 KiB。

## Task List

### Task 0：提交已批准的 Plan 与 todo

- 验收：`verify-and-commit.sh` 快档通过并提交。
- 文件：`tasks/ledger-init-machine-config/plan.md`、`todo.md`。

### Task 1：拒绝时报出清理过的 message（先红）

单测：带 message 的拒绝报 `Epiq refused: <message>`；控制字符被替换、`https://user:SECRET@host` 与文本中段的 `ssh://token@host` 都被遮掉、超过 300 字截断加 `…`；
没有 message、message 不是字符串时仍是 `MCP tool response is unsuccessful`。先确认失败，再改 `read_mcp_tool_result`。

- 验收：新单测绿，原有单测不变。
- 文件：`hooks/local_ledger_runtime.py`、`hooks/test_local_ledger_runtime.py`。

### Task 2：三项可选与警告编号（先红）

单测：`project_init_arguments` 三项都不给只有 `repoRoot`、只给一项只带那一项、空字符串报错、`auto_sync` 非布尔报错；
`initialize` 命令行不给三项时也调用 `initialize_project`（不再出 `user-setup-required`），给了的原样传入；
`initialize_project` 返回 `warningCount`、`warningCodes`（`[init:15] x`、`[init:15] y`、`no code` → 3、`["init:15"]`），`warnings` 仍为 `true`，正文不出现；
文本输出有警告时多一行条数与编号。现有「三项必填」的单测按新契约改写。

- 验收：新单测绿；`grep` 不再有 `user-setup-required`（除 CHANGELOG 旧条目）。
- 文件：同上。

### Task 3：status 的 machineSetup（先红）

单测：`config.json` 不存在 → `absent`；合法 → `read` 与三项取值（空字符串记为 null，`autoSync` 非布尔记为 null）；只有部分项；非法 JSON、不是对象、
超过 64 KiB、是目录、是符号链接 → `unknown`；`EPIQ_GLOBAL_DIR` 生效；读取前后文件修改时间不变；status 原有 `state` 与退出码不变。文本输出写明已设置的项与取值、缺的项。

- 验收：新单测绿，`test_local_ledger_runtime.py` 全绿。
- 文件：同上。

### Task 4：真实 Epiq 三种情形

用临时 `EPIQ_GLOBAL_DIR` 和三个临时 git 仓库，跑工作区版本的 `local_ledger_runtime.py initialize --confirm-initialize`：
1. 机器设置 `userName` 为 A（另两项也有），传 `--user-name B`：退出码 1，诊断里有 Epiq 的「already set up with userName」原话；
2. 同一机器设置，不传三项：初始化成功，`config.json` 三项不变；`status` 的 `machineSetup` 为 `read` 且取值正确；
3. 空的机器设置，三项都传：成功，`config.json` 写入了这三项。
结果记进 todo；临时目录跑完即删。

- 验收：三种情形都符合预期。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警

### Task 5：说明文档

`commands/local-ticket-ledger.md`、`skills/local-ticket-ledger-ops/SKILL.md`、`references/local-ticket-ledger-runtime.md`：初始化前看 `status` 的 `machineSetup`；
机器已有的项告诉用户「这是整机设置，初始化改不了；要改，在 Epiq 的 TUI 里用 `:config`」，不再传；只问缺的；`unknown` 时照旧三项都问。示例命令写明三项可省略。
参考文档里「输出只报告是否有警告」改为条数与编号。

- 验收：`validate.sh` 通过。

### Task 6：CHANGELOG 与 0.71.0 版本号

把顶部 `## [未发布]` 并入新的 `## [0.71.0] - <日期>`：本版 2 个模块；变更写本模块，维护者工具保留 `stdin-timing-test` 那条。两份 `plugin.json` 改为 0.71.0，
中英 README 的 `--ref` 改为 v0.71.0。

- 验收：`validate.sh` 通过（含清单版本一致）。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

列出实际改动、验证结果与未验证项；拟回告：发版后告诉 session-protocol 契约负责人版本号（原生会话消息，草稿先给用户看）。

### 发版后的验证

PR 合并后按 `docs/release-process.md` 发 0.71.0：tag、发布包、Release、两边宿主升级与 Codex smoke、证据 JSON；在两边安装副本上各跑一次 `status --format json`，看到 `machineSetup`。
然后在账本里关闭 CH92E11，按批准的草稿回告对方。
