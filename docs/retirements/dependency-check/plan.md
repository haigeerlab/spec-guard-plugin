# Plan: dependency-check

<!-- spec-guard: review approved -->

依据 [`spec/dependency-check.md`](../../spec/dependency-check.md)。本项目按分开审：Spec 已于 2026-10-19 批准，本 Plan 单独交审。
分支 `claude/dependency-check`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `scope-authorization` 的分支末端
`74fa713` 开出（依赖它的「需要的外部条件」）。#376 合并后先把最新 `main` 合进来，再开本模块的 PR；本模块的 PR 含 0.78.0 版本号，
合并后在合并提交上打 tag，按 `docs/release-process.md` 发版。

需要的外部条件：无（不装依赖、不联网；只用仓库已有的 `python3`、`git` 与检查脚本）。

## Overview

核对逻辑放进一个独立的 Python 模块并先写单测，再让 verify-artifacts 调它、加端到端用例，最后补规则半句、文档、CHANGELOG 与版本号。

## Architecture Decisions

- **逻辑放进 `hooks/dependency_check.py`，不内嵌在 verify-artifacts 里。** Spec 的 Contract 写的是「python 内嵌，风格同 AC 编号检查」；
  但这项逻辑有清单解析、包名规范化、Plan 一节的截取、git 差异几块，内嵌在 shell 字符串里没法单独测、也难读。改成独立模块，
  verify-artifacts 用 `python3 -B "$HOOKDIR/dependency_check.py" --project .` 调它、读它逐行输出的结果，提示文字与 Spec 一致，
  对用户可见的行为不变。这一点与 Spec 字面不同，交审时说明。
- **Plan 一节的截取与「需要的外部条件」提示共用一个判据**：`dependency_check.py` 提供 `external_conditions(plan_text)`，返回那一节的
  文字或 `None`；verify-artifacts 里 `scope-authorization` 那段改为调用它，避免两份正则走偏。
- **git 调用固定几次**：每个模块一次 `git log --diff-filter=A --format=%H -- spec/<id>.md` 取起点；一次 `git diff --name-only <起点>`
  加一次 `git ls-files --others --exclude-standard` 找改过的清单；改过的清单用 `git show <起点>:<path>` 取旧内容。读不出就给「未验证」。
- **pyproject.toml 用行级读法**：只认 `[project]` 的 `dependencies = [ ... ]`（可跨行）、`[project.optional-dependencies]` 下各组、
  `[tool.poetry.dependencies]` 与 `[tool.poetry.group.<名>.dependencies]` 表里的键（Poetry 表里的 `python` 键不算包）；其他写法归
  「改了，未逐项核对」。兼容系统 Python 3.9（不用 `tomllib`）。

## Task List

### Task 1：核对模块的单测（先红）

新增 `hooks/test_dependency_check.py`，覆盖：三类清单的新增识别、只改版本不算、PEP 503 规范化、完整词匹配（`zod-form` 不算列出
`zod`）、Plan 一节的两种截取方式与允许范围、锁文件与其他清单的分类、读不懂的 pyproject 写法归类、`node_modules/` 跳过。
在 `scripts/validate.sh` 的单测清单里登记。

- 验收：新单测在没有实现时失败（导入失败或断言失败）；`test-registration-check` 认得它。
- 验证：`python3 -B plugins/spec-guard/hooks/test_dependency_check.py`。
- 文件：`hooks/test_dependency_check.py`、`scripts/validate.sh`。

### Task 2：实现 `dependency_check.py`

纯函数（解析、规范化、比对、分类）加一个读 git 与文件的入口，命令行输出每个模块一行结果。

- 验收：Task 1 全绿；两处变异各有断言变红（不做 PEP 503 规范化；按子串而不是完整词匹配）；在系统 `/usr/bin/python3`（3.9）上
  单测同样通过。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`hooks/dependency_check.py`。

### Task 3：接进 verify-artifacts 与端到端用例

`verify-artifacts.sh` 加一段调用 `dependency_check.py` 并把结果转成 `warn`；`scope-authorization` 那段改用 `external_conditions()`。
`test-verify-artifacts.sh` 加端到端用例：临时 git 仓库提交 Spec 后在工作区改清单，覆盖 Spec Testing strategy 各项与退出码不变。

- 验收：新用例全绿；「需要的外部条件」原有 7 例保持绿；本仓库实跑没有新提示（进行中模块没改依赖清单）。
- 验证：`verify-and-commit.sh` 全档。
- 文件：`hooks/verify-artifacts.sh`、`hooks/test-verify-artifacts.sh`。

### Checkpoint 1（report）：核对模块与 verify-artifacts 回归全绿

### Task 4：规则半句、文档、CHANGELOG 与版本号

共享检查点规则「最终验收」那行补半句；`commands/verify-artifacts.md`、`docs/commands.md` 写明这一项与范围；CHANGELOG 把现有
「未发布」一节并入新的 `[0.78.0] - 2026-10-19`，写 `scope-authorization`、`dependency-check` 两个模块（含升级后可能多出的两类提示）
与已在「未发布」里的计时用例修复；两份 `plugin.json` 改为 0.78.0，中英 README 的 `--ref` 改为 v0.78.0。

- 验收与验证：`verify-and-commit.sh` 全档；`check-readme-sync.py` 通过。
- 文件：`references/workflow-checkpoints.md`、`commands/verify-artifacts.md`、`docs/commands.md`、`CHANGELOG.md`、两份 `plugin.json`、
  两份 README。

### Checkpoint 2（gate）：最终验收

按 AC1–AC6 逐条给证据（单测与端到端用例名、临时仓库实跑输出），展示未验证项、实际改动的文件清单（含新增依赖与锁文件：应为「无」）
与文档建议。推送与开 PR 在此由用户确认，合并由用户进行；合并后的 0.78.0 发版（tag、Release、两边宿主、证据 PR）与发版后通知
decision-inbox 整改会话、抄送协调人，也在此一并确认。

## Risks

- **行级读 pyproject 误判**：只认列出的几种写法，其余一律归「改了，未逐项核对」，宁可少报逐项、不报错的包名。
- **Plan 文字里包名碰巧出现**（比如 Plan 正文提到 `react` 但不在那一节）：只取「需要的外部条件」那一节的文字，节外的不算。
- **与 #376 的冲突**：本分支叠在 #376 上；#376 若有改动，先合入再继续，不改写已推送的提交。
- **CHANGELOG 已有「未发布」一节**：并入 0.78.0，不留两个「未发布」。
