# Plan: usage-draft-gate

<!-- spec-guard: review approved -->

Spec：[spec/usage-draft-gate.md](../../spec/usage-draft-gate.md)（2026-11-22 批准）。

## 架构决定

- **判据只有一处**：`usage_draft.missing(project)`。用 `git log --format=%H -n 100 -- spec/CAPABILITY-MAP.md` 列提交，对每个提交取
  `git show <sha>:spec/CAPABILITY-MAP.md` 与 `<sha>^` 的版本，用 `capability_map` 的解析器求「这个提交新出现的模块」；工作区的能力图对 HEAD
  再算一次（未提交的一批）。模块是否完成由调用方传入（`module_stage` 已算好的状态），`usage_draft` 不反向依赖 `module_stage`，避免循环导入。
- **调用点**：verify-artifacts（每次跑）、阶段提示（只在当前模块 NEEDS_SPEC 时调用，平时不多读 git）、add-module（`--confirm` 写入后只看工作区那一批）。
- **阶段提示怎么接**：`stop_node` 在 NEEDS_SPEC 且当前模块属于缺草案的批时返回 `map-review`；建议下一步（中英两套）换成先写草案。
  状态码的事实里加上「缺草案的批」，状态变了会重发完整内容。
- **读不到 git**：`missing` 返回 unverified；阶段提示按「不变」处理，verify-artifacts 报未判定。

## 任务

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`、verify-artifacts 0 失败。
- **Task 1**：`usage_draft.missing` 与单测（AC1）。在现有的 `test_usage_draft.py` 里先写临时 git 仓库的六种情形并确认失败，再实现。
- **Task 2**：verify-artifacts 一项（AC2）。`test-verify-artifacts.sh` 先加情形并确认失败，再实现。
- **Task 3**：阶段提示（AC3）。`test-phase-guard.sh` 新增第 27 段（PARTS=27）：中英各一例、补上草案后逐字相同、无批量插入不变；先确认失败，再改 `module_stage.py`。
- **Task 4**：add-module 提醒（AC4）。`test_module_insert.py` 先加连续插两个、有草案、只插一个三例，再改 `module-insert.py`。
- **Task 5**：规则与说明（AC5）。`workflow-checkpoints.md`「用法草案」加补写段落与「机器在哪提醒」；`test_workflow_checkpoints.py` 断言；
  `commands/add-module.md`、`skills/spec-guard-ops/SKILL.md`（add-module、verify-artifacts）、`docs/commands.md`（verify-artifacts 表）。验证：`validate.sh --quick`。

## 会改哪些文件

- 新增：`tasks/usage-draft-gate/{plan,todo}.md`。
- 修改：`hooks/usage_draft.py`、`hooks/verify-artifacts.sh`、`hooks/test-verify-artifacts.sh`、`hooks/module_stage.py`、`hooks/test-phase-guard.sh`、
  `hooks/module-insert.py`、`hooks/test_module_insert.py`、`hooks/test_usage_draft.py`、`references/workflow-checkpoints.md`、`hooks/test_workflow_checkpoints.py`、`commands/add-module.md`、
  `skills/spec-guard-ops/SKILL.md`、`docs/commands.md`。
- 不改：版本号、CHANGELOG、README、接口。新增依赖、锁文件：无。

## 风险

- **阶段提示回归面**：只在 NEEDS_SPEC 且判缺时变；用「补上草案后逐字相同」「无批量插入不变」守住。
- **每轮多几次 git 调用**：只在 NEEDS_SPEC 时算，最多 100 个提交，每个提交两次 `git show`；本仓库能力图提交很多，实测耗时记进 Checkpoint 1，
  超过 1 秒就改成只看最近 30 个提交并在 Spec 里写明（会交用户复审）。
- **本仓库自己**：S101 批次有草案覆盖，usage-draft-gate 单独插入；装上后本仓库不应出现新警告，Checkpoint 1 实测。
- **叠加分支**：基于 #461 的分支；#461 合并后 rebase 到 main 再开 PR。
- **shell 改动**：提交前跑 ShellCheck。

## 检查点

- Checkpoint 1（report）：完整检查（validate、phase-guard、verify-artifacts、smoke 自检、ShellCheck）；变异验证两处（判据不看完成状态、
  阶段提示不看草案覆盖）各让回归变红；临时项目实跑：add-module 连插两个 → 提醒 → 提交 → 阶段提示先出草案 → 写草案 → 恢复原样；
  本仓库跑 verify-artifacts 与阶段提示无新警告并记耗时。记进 todo 后继续。
- Checkpoint 2（gate）：最终验收；通过后推送，#461 合并后 rebase 到 main 开本模块 PR，合并由用户进行。本模块不发版。

## 未决问题

- 无。
