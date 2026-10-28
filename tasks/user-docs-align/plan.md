# Plan: user-docs-align

<!-- spec-guard: review approved -->

依据 [`spec/user-docs-align.md`](../../spec/user-docs-align.md)（2026-10-28 用户在本会话批准：「Spec 批准；Q1 A」）。批准节奏为分开审，
本 Plan 单独交审。分支 `claude/docs-align-0850`（从 `origin/main` `39ea08bc` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
只改文档，不改版本号、不发版。

## Overview

按文件分组改：README 中英 → `docs/commands.md` → `docs/workflow.md` → 其余三份（concepts、troubleshooting、convention-block）。
每个 task 先对着源码或 CHANGELOG 核对要写的说法，核对位置记进 todo，再改；每个 task 单独提交（`scripts/verify-and-commit.sh`，
只改文档时走快档）。

## Architecture Decisions

1. **按文件分 task，不按 AC 分。** 同一个文件的几处改动放在一次提交里，避免同一文件反复改、反复冲突；todo 里每个 task 写明覆盖哪些 AC。
2. **不写 CHANGELOG。** 先例 docs-refresh 只改文档、没写 CHANGELOG 条目；本模块不改插件包，下一个发版模块写「文档」一节时可以顺带提一句。
3. **链接检查用一次性脚本，不入库。** AC21 要求相对链接有效；仓库里没有现成的链接检查器，用放在 scratchpad 的小脚本查本模块改过的文件
   （相对路径存在、`#锚点` 能对上标题），结果记进 todo。不新增维护者工具（超出范围）。
4. **README 中英逐段对译。** 中文先改，英文按同一结构改；`check-readme-sync.py` 只核对版本号和部分结构，内容一致靠逐段对照。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：README 中英（AC1、AC9、AC13、AC16、AC19、AC20）

- config 一行改为不列全部键的说法；多模块并行一节的「从本版起」改为具体版本；对外接口一节去掉 1.1 的细节，指向 `interface.json` 与 design.md；
  安装表 Codex 一格的升级说明移到「更新」一节；Codex 启用说法与其他文档统一；数据与隐私第一条拆成短句。
- 验证：`check-readme-sync.py` 通过；中英两版段落一一对应。

### Task 2：`docs/commands.md`（AC1、AC2、AC4、AC5、AC10、AC17）

- config 表加 `autonomyTier`；phase 一节写平时一行与何时完整、上下文提醒改为只在模块边界；verify-artifacts 一节按 `verify-artifacts.sh` 列实际检查项（含
  预先声明格式）；开头不再指向源码目录；`/map --json` 字段说明改指 `interface.json` 的 `mapView`。
- 核对：`project_config.py`（键与默认值）、`phase-guard.sh`／`module_stage.py`（一行摘要、模块边界）、`verify-artifacts.sh`（逐项）、`interface.json`。

### Task 3：`docs/workflow.md`（AC2、AC3、AC4、AC11、AC12、AC14、AC15、AC16）

- 「从零到交付」步骤连续，账本与 PR 对账移到步骤之后、加小标题；第 84 行按主题拆开；补「预先声明」一段；快速插入步骤与 `DONE` 一行加需求确认；
  上下文提示一段改为模块边界；「可以一次审完」加前提；补 AC 编号、中文检查点、最终验收表格与提交、复制块四项；「项目级审查」一节压缩，
  `--replace` 那段移出合并；Codex 说法统一。
- 核对：`references/workflow-checkpoints.md`、`references/node-rules.md`、`module_stage.py`（检查点判据、建议下一步）、CHANGELOG 0.74～0.85。

### Task 4：concepts、troubleshooting、convention-block（AC5、AC6、AC7、AC8、AC16、AC18、AC19）

- concepts 设计原则表的 Proposal 一行如实描述；troubleshooting 新增「只看到一行 spec-guard 提示」，加 `Project config: ignored`，hook 信任与 README 一致，
  去掉 0.57.1 来历，Codex 说法统一；convention-block 去掉同步脚本说明。
- 核对：`hooks/hooks.json`（信任项）、`project_config.py`（ignored 行）、`proposal-closeout` 与 `module-insert.py`（远端与能力图写入）。

### Checkpoint 1（report）：整体检查

- `/bin/bash scripts/validate.sh` 通过；链接检查无断链；`git diff --stat origin/main -- plugins/spec-guard` 为空；结果记入 todo。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、AC1～AC22 逐条证据、文档改动表与提交表、Spec 中途改动（如有）。通过后推送并开本模块 PR（批准本 Plan 即授权推送与开 PR），
  合并由用户进行。

## Files likely touched

- 文档：`README.md`、`README.en.md`、`docs/commands.md`、`docs/workflow.md`、`docs/concepts.md`、`docs/troubleshooting.md`、`docs/convention-block.md`
- 记录：`spec/CAPABILITY-MAP.md`（已写入新行与变更记录）、`spec/user-docs-align.md`、`tasks/user-docs-align/plan.md`、`tasks/user-docs-align/todo.md`
- 不碰：`plugins/spec-guard/` 下所有文件、CHANGELOG、历史记录目录、维护者文档。
- 新增依赖、锁文件改动：无。

## 风险

- **改说法时又写错。** 缓解：每处先核对源码再写，核对位置记进 todo；最终验收逐条给证据。
- **旧词回归或同步检查失败。** `validate.sh` 含现行文字的旧词回归（评审、审核、审批）与约定块同步检查；改 convention-block 时只动块外的说明，块内保持与模板逐字节一致。
- **压缩「项目级审查」一节丢信息。** 缓解：压缩后的说明链到共享检查点规则里对应的细则；删掉的句子在最终验收里列出，确认细则那边都有。
