# Plan: formal-deferral

<!-- spec-guard: review approved -->

依据 [`spec/formal-deferral.md`](../../spec/formal-deferral.md)（2026-11-02 用户在本会话批准：「批准」，能力图新行同时确认写入）。
分支 `claude/formal-deferral`（从 `origin/main` `b73ee179` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
本模块改版本号到 0.86.0。

## Overview

先在 `module_stage` 里立唯一的延期判据，让 `UNCHECKED`／`OPEN_ITEM` 排除合格延期项，所有导入它们的地方随之一致；
再分别补阶段提示、`/map`（表格、延期项一节、JSON、interface.json）、verify-artifacts 的失败与迁移提示，最后改规则、模板、
文档与版本号。每个任务先写在旧代码上失败的测试。

## Architecture Decisions

1. **一个判据、两个出口。** `module_stage` 新增 `DEFERRED`（匹配一行合格延期项）与 `deferred_items(text) -> [(item, resume_when)]`。
   `UNCHECKED` 与 `OPEN_ITEM` 改为在 `[ ]` 后加否定前瞻，排除合格延期项；否定前瞻与 `DEFERRED` 共用同一段正则文本（一个常量拼出两者），
   不写两份。
   - 合格：`[ ]` 后空白，`(延期|deferred)`（不区分大小写）`\s*[：:]`，事项（非空），`[；;]`，`(恢复条件|resume when)`（不区分大小写）
     `\s*[：:]`，至少一个非空白字符。
   - 检查点排除：事项以 `检查点`／`Checkpoint` 开头，或事项在第一个冒号前带 `（gate）`／`（report）`，按 `gate_checkpoints` 现有的
     `CHECKPOINT_KEYWORD`／`CHECKPOINT_TIER` 判；这类行不算延期（`UNCHECKED` 照常匹配）。
2. **调用点逐个核对**（2026-11-02 在 `b73ee179` 上 grep）：

   | 调用点 | 用的 | 跟着变是否正确 |
   |---|---|---|
   | `module_stage.module_state` 的 `open`／`half`／`suspended`／`stage` | `UNCHECKED` | 是：只剩延期项为 DONE，不算做到一半，挂起标记按过期 |
   | `module_stage.at_final_gate`、`first_open_is_gate` | `OPEN_ITEM` | 是：延期项排在最终 gate 前也能到最终验收 |
   | `gate_tick.py` 剩余计数、`at_final_gate` | `OPEN_ITEM` | 是：「left」不含延期项 |
   | `map_view._todo_progress`（其他 worktree）、`map_view` 的 `progress` | `UNCHECKED`／`state["open"]` | 是：`total` 不含延期项 |
   | `module-insert.py` 的做到一半与暂停进度 | `state["open"]`、`half` | 是 |
   | `module_suspend.py` 的 `nothing-open` | `state["open"]` | 是：只剩延期项时不能挂起，提示里说明它已算完成 |
   | `verify-artifacts.sh` 挂起标记过期（127-134） | `UNCHECKED` | 是 |
   | `verify-artifacts.sh` 旁路清单（219-239） | `UNCHECKED` | **否**：合格延期写在旁路文件里会不再被数到，警告消失。改为另数 `DEFERRED` 与含「延期」的未勾选项，补一句延期说法 |

   以上之外没有别的脚本自己匹配 `[ ]`（`gate_tick.BOX` 只在已定位的最终 gate 行上替换）。
3. **`module_state` 增加 `deferred` 列表**；阶段提示与 `/map` 从这里取，不重新读文件。
4. **阶段提示**：计数行在挂起之后追加 ` · 延期 <n>`／` · Deferred <n>`（全项目合计）；DONE 建议两种语言各加一个有延期时的分支，
   指向 `/spec-guard:map`（Codex 话术照现有 `cmd` 表）。quiet-injection 的一行提示不加字段（每轮注入保持短）；状态码随计数行变化。
5. **`/map`**：表格状态格 `已完成（延期 n）`／`done (deferred n)`；表格后「延期项／Deferred items」一节按 Build order 列 `模块 · 事项 · 恢复条件`，
   经 `safe_fragment` 截断与清洗（与 gate 标题同样处理）；JSON 加 `deferred`、`deferredTotal`；`interface.json` 1.11 → 1.12，写明口径变化，
   `validate.sh` 现有的接口一致性检查补新字段。
6. **verify-artifacts**：新增一节「延期写法」——失败：带延期前缀但不合格（缺恢复条件或为空）、检查点写成延期；警告：todo.md 里含
   「延期」或 `deferred` 的未勾选项不合格式（给改写示例）。判定都导入 `module_stage`，脚本里不写正则。
7. **规则与文档**：`references/workflow-checkpoints.md` 补一条延期规则（`test_workflow_checkpoints.py` 锁定）；`templates/claude-block-local.md`、
   `codex-block-local.md` 各加一行；`docs/design.md` 阶段判据、`docs/workflow.md`、README 中英、CHANGELOG 0.86.0（含「口径变化」升级须知）。
8. **口径变化通知**：Checkpoint 2 前给总负责人发一条：哪些状态会变（只剩合格延期项的模块 → done，下游 → ready；JSON 只增字段、
   `schemaVersion` 不变、interface 1.12）；现有自由文本写法不改写就不变。对方各项目的具体影响面由对方核对。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：判据与阶段（AC：只剩延期项为 DONE，下游 ready；写错的不放行）

- 文件：`hooks/module_stage.py`；新测试 `hooks/test_formal_deferral.py`（判据正反、`module_state` 的 `open`／`deferred`／`stage`／`suspended`、
  `at_final_gate`、`first_open_is_gate`）；`test_gate_tick.py`、`test_module_suspend.py`、`test_module_insert.py` 各补一例。
- 验证：新用例改前红、改后绿；这几个测试文件全部通过。

### Task 2：阶段提示（两边脚本正反回归）

- 文件：`hooks/module_stage.py`；`hooks/test-phase-guard.sh` 加：只剩延期项为 DONE 且建议说明延期、计数行带延期、缺恢复条件仍为 BUILDING、无延期时逐字节不变。
- 验证：新用例改前红、改后绿；`test-phase-guard.sh` 通过。

### Task 3：`/map` 与接口

- 文件：`hooks/map_view.py`、`interface.json`、`scripts/validate.sh`（如需）；`test_map_view.py` 加表格、延期项一节、JSON、下游 ready 用例。
- 验证：新用例改前红、改后绿；`test_map_view.py`、`validate.sh` 的接口检查通过。

### Task 4：verify-artifacts

- 文件：`hooks/verify-artifacts.sh`；`hooks/test-verify-artifacts.sh` 加：缺恢复条件失败、检查点延期失败、自由文本警告、旁路文件里的延期警告、合格写法通过。
- 验证：新用例改前红、改后绿；`test-verify-artifacts.sh` 通过；改了 `.sh`，按 CI 参数跑 ShellCheck。

### Task 5：规则、模板与文档

- 文件：`references/workflow-checkpoints.md`、`hooks/test_workflow_checkpoints.py`、两份 `templates/*-block-local.md`、`docs/design.md`、`docs/workflow.md`。
- 验证：`test_workflow_checkpoints.py` 与模板相关回归通过；`validate.sh --quick` 通过。

### Task 6：版本号与 CHANGELOG（PR 最后一个内容提交）

- 文件：两份 `plugin.json`、`README.md`、`README.en.md`、`CHANGELOG.md`（0.86.0，升级须知写口径变化与迁移写法）。
- 验证：`check-readme-sync.py`、`check-manifests.py` 通过。

### Checkpoint 1（report）：发布前完整检查

- macOS 系统 `/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 并记录主机；ShellCheck；改了 Codex 用的 hook，
  跑 `evals/codex-plugin-smoke.sh --selftest`。
- 变异：判据去掉「必须有恢复条件」、`UNCHECKED` 不排除延期项、DONE 建议不区分延期，三处各在草稿副本上改坏，确认测试变红后还原。
- 给总负责人发口径变化通知（决定 8）。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、成功标准的证据、文档表、改动与提交表、Spec 中途改动（如有）、口径通知已发。通过即同时授权：推送、开 PR；
  你合并后由我核对合并并按发版步骤一次做完。

### 发版（合并后，按 Checkpoint 2 的授权）

- 核对 PR 已合并、`main` 指向合并提交；打 `v0.86.0`、推 tag；打包、发 Release、下载比对 SHA-256；
- 刷新 Claude 与 Codex 安装副本并核对（挑一处本版确实改了的代码）；Codex 先请你在命令行版 `codex` 的 `/hooks` 重新批准，再跑真实 smoke；
- `proposal_closeout.py scan`；写证据、开收尾 PR；告诉总负责人已发版。任一步失败就停下说明。

## Files likely touched

- 插件包：`hooks/module_stage.py`、`hooks/map_view.py`、`hooks/verify-artifacts.sh`、`interface.json`、`references/workflow-checkpoints.md`、
  `templates/claude-block-local.md`、`templates/codex-block-local.md`、两份 `plugin.json`；
  测试 `hooks/test_formal_deferral.py`（新）、`test_gate_tick.py`、`test_module_suspend.py`、`test_module_insert.py`、`test_map_view.py`、
  `test_workflow_checkpoints.py`、`test-phase-guard.sh`、`test-verify-artifacts.sh`
- 仓库：`scripts/validate.sh`（如需）、`docs/design.md`、`docs/workflow.md`、`README.md`、`README.en.md`、`CHANGELOG.md`；收尾 PR：`docs/releases/v0.86.0-*.json`
- 记录：`spec/CAPABILITY-MAP.md`（已写入）、`spec/formal-deferral.md`、本 Plan、`tasks/formal-deferral/todo.md`
- 新增依赖、锁文件改动：无。不碰 `spec-digest.py`、`capability_map.py`。新测试文件要在测试注册清单里登记（`test-registration-check`）。

## 风险

- **口径变化影响其他插件**：module-crew 的进度与 start prepare 读 `/map`；只增字段、`status` 取值不变，变的是部分模块的取值。用决定 8 的通知兜住，
  Spec 的成功标准要求发版前已通知。
- **本仓库自身**：本仓库 todo 里没有以「延期／Deferred」开头的未勾选项（Task 1 前 grep 确认），阶段不应变化；Checkpoint 1 用 `/map` 前后比对确认。
- **正则误伤**：普通项正文里出现「延期」二字但不在开头，不算延期；用例覆盖。
- **两边脚本很慢**（phase-guard 约 2.5 分钟）：开发中只跑新增的那几例附近，完整跑放在提交时的完整档。
