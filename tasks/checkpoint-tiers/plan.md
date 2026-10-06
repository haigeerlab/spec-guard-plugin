# Plan: checkpoint-tiers

依据 [`spec/checkpoint-tiers.md`](../../spec/checkpoint-tiers.md)（2026-10-06 用户评审通过）。分支
`claude/checkpoint-tiers`，worktree `.claude/worktrees/hello-226c46`。

## Overview

只改规则文本：共享检查点规则新增三节并补"交付前"一句，两份约定块模板各加一行，`docs/workflow.md` 一段，CHANGELOG。
先在 `test_workflow_checkpoints.py` 写静态断言并看它变红，再改文本。本 Plan 自己按新规则标注检查点。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Architecture Decisions

- **规则只有一个出处。** 细则只写在 `references/workflow-checkpoints.md`；模板、`docs/workflow.md` 只放一句话和指向，避免多处漂移。
- **静态测试不冒充行为验收。** 断言只检查规则可被找到、关键约束在场、没有默认授权推送的表述；宿主是否遵守由本 Plan 的执行
  和交付后的约定块更新来观察。
- 共同验证命令：

  ```bash
  python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
  /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
  /bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
  ```

## Task List

### Task 1: 共享检查点规则（第 2–6 条）

**Description:** 先写断言（三节标题、关键规则词、反向用例），再在合同中加三节并补"交付前"一句。

**Acceptance criteria:**
- [ ] 断言先红：三节不存在
- [ ] 合同含 `## Plan 检查点分级`、`## 按需求批量前置审`、`## UI 自验`；`gate`／`report` 定义、未标注按 `gate`、异常停点永远停、
      合并永远由用户、"批量批准"、80% 停下并给交接文本、浏览器／电脑操作、Claude 桌面应用例外、缺工具提前提醒
- [ ] 反向：合同不含把推送设为默认授权的表述

**Verification:** 测试先红后绿：共同验证命令

**Dependencies:** None

**Files likely touched:** `plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`

**Estimated scope:** Medium

### Task 2: 约定块模板与文档（第 1、7 条）

**Description:** 两份模板各加一行；`docs/workflow.md` 一段；CHANGELOG `[未发布]`。

**Acceptance criteria:**
- [ ] 断言先红：模板不含 `gate`／`report`
- [ ] 两份模板都含 `gate`／`report` 并指向共享检查点规则；`setup-convention` 相关回归通过
- [ ] `docs/workflow.md` 说明三条规则并链接合同

**Verification:** 测试先红后绿：共同验证命令；validate.sh

**Dependencies:** Task 1

**Files likely touched:** `plugins/spec-guard/templates/claude-block-local.md`、`plugins/spec-guard/templates/codex-block-local.md`、
`docs/workflow.md`、`CHANGELOG.md`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`

**Estimated scope:** Small

### Checkpoint 1（report）: 规则落地

- [ ] 共同验证命令与 validate.sh 全绿
- [ ] 牙齿检查：草稿副本里删掉"未标注按 `gate`"一句、在合同中加入"默认授权推送"，各自看到断言变红
- [ ] 结果记入 todo 后直接继续

### Checkpoint 2（gate）: 交付

- [ ] 五维审查，处理发现
- [ ] 本 Plan 获批即授权：推送本分支并开模块 PR；模块 PR 合并后开发版 PR（v0.49.0）；发版 PR 合并后一次走完 tag → Release → 宿主升级 → 证据 PR。合并由用户进行
- [ ] 交付后在本仓库运行 `setup-convention --replace`，确认约定块更新、阶段注入不变（该改动随证据 PR 提交）

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| agent 不遵守文本规则 | 仍在 `report` 处停下或越过 `gate` | 未标注按 `gate` 兜底；交付后用真实会话观察 |
| 规则文字被误读为默认授权推送 | 远端写入未经确认 | 反向断言；合同明写"只有 Plan 写明时" |
| 模板改动不触达已有项目 | 已有项目看不到新规则 | CHANGELOG 写明需 `--replace` |

## Open Questions

- 无。
