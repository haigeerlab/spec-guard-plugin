# Plan: changed-files-at-acceptance

<!-- spec-guard: review pending -->

依据 [`spec/changed-files-at-acceptance.md`](../../spec/changed-files-at-acceptance.md)。合并审：Spec 与本 Plan 一起评审、一次批准。
分支 `claude/changed-files-at-acceptance`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `8d015d8`（v0.60.0 验证记录
合并）开出。本模块一个 PR，含 0.60.1 版本号；合并后的 tag、Release、两边宿主同步与验证记录按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

只改文字：一处规则、两份模板各一行、三处文档与版本号。没有新命令，也没有会被检查器拦下的新引用，按任务逐个提交。

## Architecture Decisions

- **规则只有一个出处。** 细则写在 `references/workflow-checkpoints.md` 的「Plan 检查点分级」；模板与文档只放要点和指向。
- **只定内容，不定格式。** 规则说清单里必须有什么，不规定用表格还是列表，也不规定命令。
- **模板只新增行。** 已有的行逐字不变，升级的项目不会被 `setup-convention --replace` 拒绝。
- **静态测试不冒充行为验收。** agent 是否照做，由发版后的真实会话观察。

## Task List

### Task 1：规则文字与约定块模板（先红）

`test_workflow_checkpoints.py` 加一例并确认失败；再改 `references/workflow-checkpoints.md`、两份约定块模板与
`docs/convention-block.md`；在本仓库用工作区源码运行 `setup-convention.sh local --host=codex --replace`（先预览，只应新增一行）。

- 验收：新断言先失败后通过；`test-setup-teardown.sh` 通过；本仓库约定块只多一行。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`；`/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh`；
  `/bin/bash scripts/validate.sh --quick`。
- 文件：`references/workflow-checkpoints.md`、两份 `templates/*-block-local.md`、`docs/convention-block.md`、
  `hooks/test_workflow_checkpoints.py`、`AGENTS.md` 的约定块。

### Task 2：文档、CHANGELOG 与版本号

`docs/workflow.md` 补一句；`CHANGELOG.md` 新增 `[0.60.1]`；两份 `plugin.json` 改为 0.60.1，中英 README 的 `--ref` 改为 v0.60.1。

- 验收：清单一致性与 README 同步检查通过。
- 验证：`verify-and-commit.sh` 全档（`validate.sh`、阶段钩子回归、`verify-artifacts` 回归）。
- 文件：`docs/workflow.md`、`CHANGELOG.md`、两份 `plugin.json`、`README.md`、`README.en.md`。

### Checkpoint 1（gate）：模块评审

展示验证结果、未验证项，以及按本模块新规则列出的实际改动文件清单。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- 规则文字再多一条，agent 每次到检查点要多带一点内容。范围压在最终验收一处与任务结果半句话，不扩到其他检查点。
- 发版后的真实会话可能不照做。那是规则文字的效果问题，如实记录，不靠加机制补。
