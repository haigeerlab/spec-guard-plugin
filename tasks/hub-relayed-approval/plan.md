# Plan: hub-relayed-approval

<!-- spec-guard: review approved -->

依据 [`spec/hub-relayed-approval.md`](../../spec/hub-relayed-approval.md)，Spec 于 2026-10-18 在本会话经用户批准（含假设 4：总协调按契约转交的也算）。
本仓库评审节奏为分开审，本 Plan 单独交审。分支 `claude/peaceful-mendeleev-f5f652`，worktree `.claude/worktrees/practical-lalande-567c30`。
按「一个模块一个 PR」：Spec、Plan、规则、脚本提示、文档、CHANGELOG 与 0.70.0 版本号在同一个 PR，版本号放最后一个提交。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

先写断言并确认是红的，再改共享规则、review-mark 命令、Codex 技能与 `review_mark.py` 的两句提示；用 `git diff` 证明约定块模板一字未改；最后文档、CHANGELOG 与版本号。

## Architecture Decisions

- **新一节的位置**：`## 经收件枢纽转来的批准`，放在「协调会话的批准与合并」之前（它是通用规则，不依赖开关；协调会话一节引用它）。
- **`CoordinatorApprovalTests.ORIGINALS[0]` 改为新措辞**：该句是本模块有意修改的对象；`test_three_pointers` 照旧要求这一条指向协调会话一节，另加指向新一节。
- **断言测关键短语**，其中「答复告知」「协调通知」「回显核对」「事项号」「明确批准这一份」「不解析」必须精确命中；另断言 `approved` 一条不再含「用户于当前对话明确批准」。
- **`review_mark.py` 只改字符串**，不改拒绝条件与写入；`test_review_marker.py` 断言新提示含 decision hub 与 item number，旧的「has seen the content」断言保持。
- 约定块模板与 `docs/convention-block.md` 不动，Checkpoint 1 用 `git diff origin/main -- plugins/spec-guard/templates/ docs/convention-block.md` 为空证明。

## Task List

### Task 0：提交已批准的 Spec、能力图、Plan 与 todo

Plan 获批后用 `review_mark` 记批准，与能力图新行、Spec、todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：共享规则（先红后绿）

`test_workflow_checkpoints.py` 新增 `HubRelayedApprovalTests`（新一节位置与关键词、`approved` 一条两种来源并指向新一节、协调会话一节第一条指向新一节且模块会话仍不能自写），
更新 `ORIGINALS[0]`；确认红。再改 `references/workflow-checkpoints.md`：`approved` 一条、「标记不是授权来源」一条、新一节、协调会话一节第一条与第三条。

- 验收：用例全绿；`check-no-parallel-surface.py` 通过。

### Task 2：review-mark 命令、Codex 技能与脚本提示（先红后绿）

`test_workflow_checkpoints.py` 加断言：`commands/review-mark.md` 与 `skills/spec-guard-ops/SKILL.md` 写到两种来源并指向新一节；`test_review_marker.py` 加断言：已批准预览提到 decision hub 与 item number。
确认红后改这三个文件。

- 验收：两套用例全绿。

### Checkpoint 1（report）：三套核心回归、模板未改与改坏验证

- 约定块模板与 `docs/convention-block.md` 相对 `origin/main` 的 diff 为 0 行；
- 改坏验证：删掉新一节「答复告知」那句、删掉「回显核对」那句、把 `approved` 一条改回「用户于当前对话明确批准」，对应断言变红；都复原；
- `verify-and-commit.sh` 全档（三套核心回归）通过。结果记进 todo。

### Task 3：文档、CHANGELOG 与版本号

`docs/commands.md`、`docs/workflow.md` 各补一句；CHANGELOG `[0.70.0]`（变更一条：「已批准」接受契约转来的【用户答复】，不放宽门槛）；两份 `plugin.json` 改为 0.70.0，
中英 README 的 `--ref` 改为 v0.70.0。

- 验收：`validate.sh` 通过；macOS `/bin/bash` 跑完整三套并记录主机与结果。

### Checkpoint 2（gate）：模块验收；推送与开 PR 在此由用户确认

列出实际改动的文件、验证结果与未验证项（真实协调会话行为留给联合演练第 2 批）。用户确认后推送并开 PR；**合并由用户进行**。合并后的 tag、推送 tag、
GitHub Release 与宿主同步按 `docs/release-process.md`，打 tag 前单独请用户明确授权。

### 发版后的验证

宿主同步（Claude marketplace、Codex `--ref v0.70.0`）与发版证据，在一个收尾 PR 里提交；通知接入协调人「已发版」。

## 影响面

`references/workflow-checkpoints.md`、`commands/review-mark.md`、`skills/spec-guard-ops/SKILL.md`、`hooks/review_mark.py`、`hooks/test_workflow_checkpoints.py`、
`hooks/test_review_marker.py`、`docs/commands.md`、`docs/workflow.md`、`CHANGELOG.md`、两份 `plugin.json`、`README.md`、`README.en.md`、`spec/`、`tasks/hub-relayed-approval/`。

## 风险

- 另一个会话「spec-guard-plugin插件负责人」可能同时在做 0.69.0 收尾或别的模块：开 PR 与改版本号前核对 `origin/main`，有冲突先协调，不抢版本号。
- `open-commitments` 的「发版后的验证」未勾，本模块合并后它仍是当前模块；那一项归另一个会话，本模块不代勾。
- 规则只靠文字，真实会话能否守住要看联合演练；单测只证明文字在。
