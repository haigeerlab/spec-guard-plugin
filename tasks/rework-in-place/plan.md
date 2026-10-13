# Plan: rework-in-place

<!-- spec-guard: review approved -->

依据 [`spec/rework-in-place.md`](../../spec/rework-in-place.md)。本仓库评审节奏为合并审：Spec 与本 Plan 一起评审、一次批准
（2026-10-13，内容先在对话里给出，用户批准后写成文件）。分支 `claude/rework-in-place`，worktree
`.claude/worktrees/current-plugin-owner-aa5b98`，从 `4f5c441`（v0.58.2 验证记录合并）开出。本模块一个 PR，含 0.59.0 版本号；
合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

`verify-artifacts.sh` 加一段只读检查，规则文件加一节，命令文件与技能各补一句，文档与版本号。不新增命令、不改阶段判定。

## Architecture Decisions

- **判据不复制。** 未勾选项的正则从 `module_stage.py` 导入，与阶段判定同一条。
- **只看 `tasks/<id>/` 的直接子文件。** 不递归，避免把验收记录目录里的材料算进来。
- **没有可报告的内容就不输出。** 既有项目的输出因此逐字不变，除非它们确有带未勾选项的旁路文件。

## Task List

### Task 1：`verify-artifacts` 的旁路清单警告（先红）

`test-verify-artifacts.sh` 加 Spec「Testing strategy」列出的用例并确认失败；再改 `verify-artifacts.sh`。

- 验收：verify-artifacts 回归全绿；在本仓库运行没有新警告。
- 验证：`/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh`；`CLAUDE_PROJECT_DIR=$PWD /bin/bash plugins/spec-guard/hooks/verify-artifacts.sh`。
- 文件：`hooks/verify-artifacts.sh`、`hooks/test-verify-artifacts.sh`。

### Task 2：规则「返工与小模块」，命令文件与技能（先红）

`test_workflow_checkpoints.py` 加断言并确认失败；再改 `references/workflow-checkpoints.md`、`commands/add-module.md`、
`spec-guard-ops` 的 add-module 一节。

- 验收：`test_workflow_checkpoints.py` 与 `scripts/test-checkers.sh` 通过。
- 验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`；`/bin/bash scripts/validate.sh --quick`。
- 文件：上述三个文件与测试。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告

### Task 3：文档、CHANGELOG 与版本号

`docs/workflow.md`、`docs/troubleshooting.md`、CHANGELOG `[0.59.0]`；两份 `plugin.json` 与中英 README 的 `--ref` 改为 0.59.0。

- 验收：`validate.sh` 通过。
- 验证：`/bin/bash scripts/validate.sh`。
- 文件：上述文档、两份 `plugin.json`、`README.md`、`README.en.md`。

### Checkpoint 2（gate）：模块评审

提交走 `scripts/verify-and-commit.sh`，一个任务做完并提交后再开始下一个。展示验证结果与未验证项。推送本分支与开 PR 在
这个检查点由用户确认；合并由用户进行。

## 影响面

`verify-artifacts` 多一种警告；一份规则文件、一个命令文件、一份技能、三份文档。约定块模板不动，既有项目无须操作。
既有项目若本来就有带未勾选项的旁路文件，升级后会看到这条警告，校验结果不受影响。

## Risks and Mitigations

| 风险 | 应对 |
|---|---|
| 把正常放在任务目录里的清单误报为问题 | 只警告、不失败；警告文字说明含义；只有未勾选项才报 |
| 本仓库自己的两份旁路文件触发警告 | 已核对它们全是已勾选项；Task 1 的验收含在本仓库实跑一次 |

## Open Questions

- 无。
