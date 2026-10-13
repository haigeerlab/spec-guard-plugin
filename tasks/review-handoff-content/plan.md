# Plan: review-handoff-content

<!-- spec-guard: review approved -->

依据 [`spec/review-handoff-content.md`](../../spec/review-handoff-content.md)。本仓库评审节奏自本模块起为合并审：Spec 与本 Plan
一起评审、一次批准。分支 `claude/review-handoff-content`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，
从 `df30884`（v0.58.0 验证记录合并）开出。本模块一个 PR，含 0.58.1 版本号；合并后的 tag、Release、两边宿主同步与验证记录
按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

三处改动互不依赖：规则文字与模板、`review_mark.py` 的输出、接入脚本的结尾输出。本模块不新增命令，也没有会被检查器
拦下的新引用，所以按任务逐个提交。

## Architecture Decisions

- **规则只有一个出处。** 细则写在 `references/workflow-checkpoints.md`；模板、命令文件、技能与文档只放要点和指向。
- **提醒不是闸门。** `review_mark.py` 只加输出，不加拒绝条件；现有用例的退出码与写入结果是不变性的回归。
- **静态测试不冒充行为验收。** agent 是否照做，由发版后的真实会话观察。
- 共同验证命令：

  ```bash
  python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
  python3 -B plugins/spec-guard/hooks/test_review_marker.py
  /bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
  ```

## Task List

### Task 1：规则文字与约定块模板（先红）

`test_workflow_checkpoints.py` 加断言并确认失败；再改 `references/workflow-checkpoints.md` 的「评审状态标记」与「评审节奏」、
两份约定块模板与 `docs/convention-block.md`；在本仓库运行 `setup-convention --replace` 更新约定块（先 dry-run）。

- 验收：`test_workflow_checkpoints.py` 与 `check-readme-sync` 通过；本仓库约定块已更新。
- 验证：上面第一条命令；`/bin/bash scripts/validate.sh --quick`。
- 文件：`references/workflow-checkpoints.md`、两份 `templates/*-block-local.md`、`docs/convention-block.md`、
  `hooks/test_workflow_checkpoints.py`、`AGENTS.md` 的约定块。

### Task 2：`review_mark.py` 的提醒（先红）

`test_review_marker.py` 加用例并确认失败：`approved` 的预览含文件行数与提醒、Spec 含指纹，`pending` 不含。再改脚本输出。

- 验收：单测全绿；原有用例一条不改。
- 验证：上面第二条命令。
- 文件：`hooks/review_mark.py`、`hooks/test_review_marker.py`。

### Task 3：接入完成时的输出（先红）

`test-setup-teardown.sh` 加断言并确认失败：输出含 `separate` 与 `combined` 的说明。再改 `setup-convention.sh` 的结尾输出。

- 验收：setup／teardown 回归全绿。
- 验证：上面第三条命令。
- 文件：`hooks/setup-convention.sh`、`hooks/test-setup-teardown.sh`。

### Checkpoint 1（report）：三套核心回归与上述测试全绿，ShellCheck 无警告

### Task 4：命令文件、技能、文档与版本号

`commands/review-mark.md`、`spec-guard-ops` 的 review-mark 一节、`docs/workflow.md`、`docs/commands.md` 同步规则要点；
CHANGELOG `[0.58.1]`；两份 `plugin.json` 与中英 README 的 `--ref` 改为 0.58.1。

- 验收：`validate.sh` 通过（清单一致性、检查器回归）。
- 验证：`/bin/bash scripts/validate.sh`。
- 文件：上述文档、两份 `plugin.json`、`README.md`、`README.en.md`、`CHANGELOG.md`。

### Checkpoint 2（gate）：模块评审

提交走 `scripts/verify-and-commit.sh`，一个任务做完并提交后再开始下一个；pre-push 钩子兜底。展示全部验证结果与未验证项。
批准本 Plan 即授权连续执行 Task 1–4、推送本分支并开本模块的 PR；合并由用户进行。发版后的真实会话验证属于合并后的步骤。

## 影响面

- 插件发布包：一份规则文件、两份约定块模板、`review_mark.py` 的输出、`setup-convention.sh` 的结尾输出、一个命令文件、一份技能。
- 行为：既有项目不重新运行 `setup-convention --replace` 就只受规则文件与命令输出的变化影响；评审状态与阶段判定不变。
- 本仓库：`.agent/config.json` 改为合并审（随规划产物一起提交）；`AGENTS.md` 的约定块随 Task 1 更新。

## Risks and Mitigations

| 风险 | 应对 |
|---|---|
| 规则变长后 agent 把整份长文件贴进对话 | 规则写明“短文件贴全文、长文件给要点加位置”；发版后看真实会话的实际输出 |
| 提醒被当成新的拒绝条件而改坏写入行为 | 现有 23 条用例的退出码与写入结果不改 |
| 另一个会话正在把 `test_module_suspend.py` 登记进 `validate.sh` | 本模块不改 `validate.sh`；若合并时有冲突，按两边都保留处理 |

## Open Questions

- 无。
