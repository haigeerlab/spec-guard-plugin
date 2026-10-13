# Plan: review-marker-legacy-projects

<!-- spec-guard: review approved -->

依据 [`spec/review-marker-legacy-projects.md`](../../spec/review-marker-legacy-projects.md)（2026-10-13 用户评审通过，批准标记已写入）。
本仓库评审节奏为分开审：本 Plan 单独评审。分支 `claude/review-marker-legacy-projects`，worktree
`.claude/worktrees/current-plugin-owner-aa5b98`，从 `5a18239`（#288 合并）开出。本模块一个 PR，含 0.57.1 版本号；合并后的
tag、Release、两边宿主同步与验证记录按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

三处小改动：`module_stage.py` 里 Next gate 的后半句按 Plan 的评审状态取；`review_mark.py` 放宽一种拒绝并改写拒绝信息；
规则文本与文档各补两条。判定代码不动。

## Architecture Decisions

- **Plan 的评审状态只取一次。** `review_hint` 已经读过 Plan 的状态，改为把它一并返回，`describe` 据此选 Next gate 的后半句，
  不再读一遍文件。
- **Spec 状态仍用同一个函数判。** `review_mark.py` 改用 `file_review_state`（文件不存在即 `none`），与阶段提示同一份判据。
- **已批准路径不动。** Plan 为 `approved` 时 Next gate 的文字、Spec 为 `approved` 时批准 Plan 的行为，期望值都不改。
- 共同验证命令：

  ```bash
  python3 -B plugins/spec-guard/hooks/test_review_marker.py
  /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
  /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
  ```

## Task List

### Task 1：Next gate 的中性措辞（先红）

`test-phase-guard.sh` 第 13 段：现有 Next gate 用例的 Plan 都没有标记，把它们的期望改为中性措辞并断言不含“keep going”；
新增 Plan 已批准时与 0.57.0 逐字相同的用例。确认失败后改 `module_stage.py`。

- 验收：phase-guard 回归全绿；已批准用例的期望文字未改。
- 文件：`hooks/module_stage.py`、`hooks/test-phase-guard.sh`。

### Task 2：Spec 没有标记时允许单独批准 Plan（先红）

`test_review_marker.py`：把“Spec 无标记时拒绝”改为成功、Spec 文件逐字未变、输出含“只记录 Plan 的批准”的说明；
新增 Spec 为待审核、已修订、标记无效时各拒绝一例，拒绝信息含单独确认的要求；Spec 文件不存在时允许。确认失败后改
`review_mark.py`。

- 验收：单测全绿；在临时项目里实跑一次“Spec 无标记 → 单独批准 Plan”。
- 文件：`hooks/review_mark.py`、`hooks/test_review_marker.py`。

### Checkpoint 1（report）：三套核心回归与单测全绿，ShellCheck 无警告

### Task 3：规则文本、命令与文档（先红）

`test_workflow_checkpoints.py` 先加两条规则的关键词断言并确认失败；再改 `references/workflow-checkpoints.md`、
`commands/review-mark.md`、`spec-guard-ops` 的 review-mark 一节、`docs/commands.md` 的拒绝条件、`docs/troubleshooting.md` 的
Next gate 一行、CHANGELOG。

- 验收：`test_workflow_checkpoints.py` 与 `scripts/test-checkers.sh` 通过。
- 文件：上述六个文件与测试。

### Task 4：版本号

两份 `plugin.json` 改为 0.57.1，中英 README 的 `--ref` 改为 v0.57.1，CHANGELOG 标题 `[0.57.1]`。

- 验收：`validate.sh` 的清单一致性通过。
- 文件：两份 `plugin.json`、`README.md`、`README.en.md`、`CHANGELOG.md`。

### Checkpoint 2（gate）：模块评审

提交走 `scripts/verify-and-commit.sh`，pre-push 钩子兜底。展示全部验证结果与未验证项。
批准本 Plan 即授权推送本分支并开本模块的 PR；合并由用户进行。发版后的宿主行为验证属于合并后的步骤。

## Risks and Mitigations

| 风险 | 应对 |
|---|---|
| 改 Next gate 文字误伤已批准路径 | 已批准用例的期望文字不改，作为逐字不变的回归 |
| 放宽拒绝后 Spec 为待审核时也被放行 | 待审核、已修订、标记无效各有一条拒绝用例 |
| 本仓库在用的是已安装的 0.57.0，看不到工作区的新行为 | 用工作区源码与临时项目验证，不把本仓库的注入当回归结果 |

## Open Questions

- 无。
