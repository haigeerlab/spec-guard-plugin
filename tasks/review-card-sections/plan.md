# Plan: review-card-sections

<!-- spec-guard: review approved -->

依据 [`spec/review-card-sections.md`](../../spec/review-card-sections.md)。分开审：Spec 已批准，本 Plan 单独审。
分支 `claude/decision-cards-sg-9d18d5`，worktree `.claude/worktrees/distracted-morse-46ef70`，从 `b0e0e14`（#385 合并）开出。
本模块一个 PR，不含版本号（排到下一版）。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Task List

### Task 1：交审小项与怎么批准（先红）

`test_workflow_checkpoints.py` 先加断言并确认失败：五类审批各自的小项按位置断言先后；「注意：」「批了会怎样：」；combined
合写；卡住时「出了什么事」；「交审时说明怎么批准」的复制块、不用行内代码、不需要回答的不用代码块、能不能撤回、还要不要另外问、
“继续”不会被记为批准。再按 Spec 的 Contract 改 `references/workflow-checkpoints.md` 的「交审要让用户看到内容」「交审时说明怎么批准」
与「第二次过不去」一条；三处镜像同步。

- 验收：新断言先失败后通过；已有断言一条不改且通过（AC1～AC5、AC7）。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`。
- 文件：`references/workflow-checkpoints.md`、`hooks/test_workflow_checkpoints.py`、`commands/review-mark.md`、
  `skills/spec-guard-ops/SKILL.md`、`docs/commands.md`。

### Task 2：interface.json 的 reviewKinds（先红）

`test-checkers.sh` 先加反例（少一类、多一类、某类小项名在规则里找不到）与正例，确认反例未报错（红）；再给
`scripts/check-interface.py` 加核对，`interface.json` 升 1.5 并新增 `reviewKinds`；`docs/design.md` 接口一节加一句 1.5。

- 验收：正例放行、三个反例各报错；`check-interface.py` 对仓库里的 `interface.json` 通过（AC6）。
- 验证：`python3 -B scripts/check-interface.py`、`/bin/bash scripts/test-checkers.sh`。
- 文件：`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`scripts/test-checkers.sh`、`docs/design.md`。

### Task 3：CHANGELOG

`CHANGELOG.md`「[未发布]」段加一条（含 interface 1.5）；两份 `plugin.json` 版本号不改。

- 验收：`verify-and-commit.sh` 全档通过（AC9）。
- 文件：`CHANGELOG.md`。

### Checkpoint 1（report）：变异核对与契约对齐

在草稿副本上删掉一类的一个小项名、把复制块改回行内代码、从 `reviewKinds` 删掉一类，确认对应断言变红，结果记入 todo。
查契约 v2.3 是否已定稿：定稿且写法不同，按定稿改到一致（范围内修正，记 Spec 变更记录）；未定稿就记下，最终验收照实写「未对齐」。

### Checkpoint 2（gate）：模块最终验收

按本模块的新规则呈现（小项、注意、批了会怎样、复制块）：验证结果、AC 逐条证据、文档改动表、其他改动表、新增依赖、本模块的
提交表、契约是否已对齐。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- 契约定稿晚于本模块：类型代码可能要改，接口一旦发布只增不改。缓解：未定稿时最终验收照实说明，由用户决定先合并还是等定稿；
  本模块不发版，发版前仍可调整。
- 改写两条规则时丢掉已有要求：已有断言全部不改，作为回归。
