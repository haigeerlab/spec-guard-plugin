# Plan: cn-checkpoint-gates

<!-- spec-guard: review approved -->

依据 [`spec/cn-checkpoint-gates.md`](../../spec/cn-checkpoint-gates.md)。分开审：Spec 已批准，本 Plan 单独审。
分支 `claude/gate-cn-checkpoint`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `7c2e672`（0.80.1 合并）开出。
本模块一个 PR，不含版本号（冻结期间不发版）。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Task List

### Task 1：判据认中文写法（先红）

`test_map_view.py` 先加用例并确认失败：五份演练 todo 的形状（gates.total 依次 1、1、1、1、2）、「检查点 1：…」中间未标不算、
「Task 1：…（report）」不算检查点、「最终验收」无级别不算、`nextGate` 指向「最终验收（gate）」。再改 `module_stage.py` 的
`CHECKPOINT` 与 `gate_checkpoints`。

- 验收：新用例先红后绿；原有 `Checkpoint` 用例不改且通过（AC1～AC3）。
- 验证：`python3 -B plugins/spec-guard/hooks/test_map_view.py`。
- 文件：`hooks/module_stage.py`、`hooks/test_map_view.py`。

### Task 2：phase-guard 正反回归

`test-phase-guard.sh` 加两例：中文 todo 的「下一个 gate」指向「最终验收（gate）」；只剩它没勾时按最终 gate 处理（修订过的 Spec
在最终验收一并复审的提示成立）。反例：「最终验收」无级别时不出现「下一个 gate」。

- 验收：新用例通过，原有用例不改（AC3）。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`。
- 文件：`hooks/test-phase-guard.sh`。

### Task 3：接口 1.6、规则文字与 CHANGELOG

`interface.json` 升到 1.6，改写 `gates` 与 `appearsWhen`；共享检查点规则第一句补中文写法与「不算检查点」那句，
`test_workflow_checkpoints.py` 加断言（先红）；`CHANGELOG.md` 加「[未发布]」段一条；两份 `plugin.json` 不动。

- 验收：检查器与 `test_workflow_checkpoints.py` 通过（AC4、AC5）。
- 文件：`interface.json`、`references/workflow-checkpoints.md`、`hooks/test_workflow_checkpoints.py`、`CHANGELOG.md`，
  以及检查器若写死 1.5 的地方。

### Checkpoint 1（report）：变异核对与演练实测

在副本上把识别正则改回只认 `Checkpoint`，确认中文用例变红；用工作区的 `map_view.py --json` 读演练仓库 `crew-rehearsal`
（只读），记下五个模块的 `gates.total`。结果记入 todo。

### Checkpoint 2（gate）：模块最终验收

按交审小项呈现验证结果、AC 逐条证据、改动文件与提交表。推送与开 PR 在此由用户确认，合并由用户进行。

## Risks

- 中：识别范围变大，冒号前标了级别的普通任务会被当成 report 检查点（Spec 第 4 条）；回归覆盖它不计入 gate。
- 低：消费方用 `gates.total` 算基准，数会变大；PR 合并后通知接入协调人与 decision-inbox。
