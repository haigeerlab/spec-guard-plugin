# Plan: test-registration-check

<!-- spec-guard: review approved -->

依据 [`spec/test-registration-check.md`](../../spec/test-registration-check.md)（2026-10-13 用户评审通过，批准标记已写入）。
本仓库评审节奏为分开审：本 Plan 单独评审。分支 `claude/test-registration-check`，worktree
`.claude/worktrees/great-bouman-4da4d6`，叠在 `claude/jovial-merkle-a6344c`（#295，补登记三个漏掉的单测）之上：检查器要在
那三个文件已登记的前提下才能通过。#295 先合并，本模块的 PR 再对 `main` 开出。维护者工具，不进插件发布包，不发版。

所需工具：无 UI 改动，无宿主行为改动。

## Overview

新增 `scripts/check-tests-registered.py`，在 `test-checkers.sh` 里先写它的正反用例，接进 `validate.sh` 的结构检查段，
`docs/maintainer-workflow.md` 补一处说明。

## Architecture Decisions

- **按文件系统查，不按 `git ls-files`。** 与 `check-acceptance-wired.py` 一致，夹具目录不需要是 git 仓库；还没
  `git add` 的新测试也会被查到。查找时跳过 `__pycache__`、`node_modules` 与以 `.` 开头的目录。
- **匹配用完整相对路径加边界。** 路径前后不能是字母、数字、`_`、`-`、`.`、`/`，所以同前缀的另一个文件、`.pyc`、
  更长的目录前缀都不会被当成已登记。
- **注释判定只看整行。** 去掉行首空白后以 `#` 开头的行不参与匹配；shell 与 YAML 都适用。行尾注释不处理（Spec 的
  “不保证”已写明不判断这一步是否真的执行）。
- **豁免写成检查器里的两个常量**，各带一句原因；没有配置文件，也没有命令行开关。
- **CHANGELOG**：在文件顶部加 `[未发布]` 一节，写进“维护者工具”，下次发版时随版本号一起改标题。这样不靠人记得补写。
- 共同验证命令：

  ```bash
  python3 scripts/check-tests-registered.py
  /bin/bash scripts/test-checkers.sh
  /bin/bash scripts/validate.sh
  ```

## Task List

### Task 1：检查器与它的回归（先红）

先在 `scripts/test-checkers.sh` 加 Spec 假设 9 的九个用例并确认因检查器不存在而失败，再写
`scripts/check-tests-registered.py` 到全绿。

- 验收：`test-checkers.sh` 全绿；检查器在本仓库通过并报出查了多少个文件；`/usr/bin/python3`（3.9）下结果相同。
- 文件：`scripts/check-tests-registered.py`（新）、`scripts/test-checkers.sh`。

### Task 2：接进 validate.sh 并在真仓库上验证

在结构检查段紧跟 `check-acceptance-wired.py` 加一行调用。然后在工作区临时去掉 `validate.sh` 里一个已登记的测试步骤，
确认 `validate.sh --quick` 失败并报出那个文件，恢复后再通过。

- 验收：`validate.sh --quick` 与完整 `validate.sh` 通过；上述改坏实测的输出记进 todo；`test_validate_quick.py` 仍通过。
- 文件：`scripts/validate.sh`。

### Task 3：判据逐条改坏

在一份草稿副本上把检查器的判据逐条改坏（去掉边界判断、把注释行算进去、改成只比文件名、把验收测试与豁免目录也
查进去、去掉“零个文件判失败”、去掉“读不到运行器判失败”、把 `verify-and-commit.sh` 加回运行器），每次确认 `test-checkers.sh` 有对应
用例变红。哪条判据没有用例拦住，就补用例。

- 验收：每条判据对应的变红用例记进 todo。
- 文件：必要时 `scripts/test-checkers.sh`。

### Task 4：文档

`docs/maintainer-workflow.md` 加一两句：新增测试文件必须在 `validate.sh` 或 CI 里登记，由本检查器看守；需要外部运行时
的测试按验收测试命名并写运行指引。`CHANGELOG.md` 加 `[未发布]` 一节。

- 验收：`validate.sh --quick` 通过。
- 文件：`docs/maintainer-workflow.md`、`CHANGELOG.md`。

### Checkpoint 1（gate）：模块评审

提交走 `scripts/verify-and-commit.sh`（暂存了 `.sh`，会跑 ShellCheck），pre-push 钩子兜底。展示全部验证结果与未验证项。
批准本 Plan 即授权推送本分支；PR 在 #295 合并后对 `main` 开出，合并由用户进行。

## Risks and Mitigations

| 风险 | 应对 |
|---|---|
| 工作区里有不该查的 `test_*` 文件（虚拟环境、缓存、嵌套 checkout）导致误报 | Task 2 在真仓库上跑；跳过的目录只有上面列出的几类，出现其他情况先停下问，不顺手加豁免 |
| `test_validate_quick.py` 把工作区复制到临时目录跑快档，复制品里缺文件导致检查器失败 | Task 2 即跑它；它按 `git ls-files` 复制，被跟踪的测试与运行器都在 |
| 检查器把 `validate.sh` 里夹具用的路径字符串当成登记 | 目前没有这样的字符串；`test-checkers.sh` 不是运行器，里面的夹具路径不参与匹配 |
| #295 未合并时本 PR 的 diff 含那三行 | 等 #295 合并后再对 `main` 开本 PR |

## Open Questions

- 无。
