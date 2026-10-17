# Plan: module-scope-boundary

<!-- spec-guard: review approved -->

依据 [`spec/module-scope-boundary.md`](../../spec/module-scope-boundary.md)。本仓库评审节奏为分开审：Spec 已于 2026-10-18
单独批准（用户决定不做外部审查，Spec 里已写拒绝标记），本 Plan 单独交审。分支 `claude/module-concurrency`，worktree
`.claude/worktrees/current-plugin-owner-aa5b98`。按批量发版约定不改版本号、不推送、不开 PR，验收后直接进入 `map-startable`。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

由内向外做：先写解析与路径归属（纯函数），再写读 git 的 `check` 和读项目的 `validate`，然后接进 verify-artifacts，最后写共享规则和文档。
每一步都先写失败的测试。

## Architecture Decisions

- **新文件 `hooks/module_scope.py` 是唯一的判据。** 解析、路径归属、`check`、`validate` 都在里面；verify-artifacts 只调 `validate`，
  以后 `map_view.py` 只调 `parse`。
- **模块清单取自能力图解析器 `capability_map.py`，「未完成」取自 `module_stage.module_state`**（`stage != "DONE"`），与阶段提示同一份判据。
  能力图读不了时 `validate` 报「未验证」行，不当作通过。
- **git 调用集中在一个小函数里**，用 `subprocess.run([...], capture_output=True)`，不经过 shell；未跟踪文件用
  `git ls-files --others --exclude-standard`。路径都按 `/` 分隔的相对路径处理。
- **目录覆盖按路径段判断**：`apps/bill/` 覆盖 `apps/bill/x`，不覆盖 `apps/billing/x`。
- **输出格式**：`validate` 每行以 `ok `、`warn `、`bad ` 开头，后面跟固定措辞和模块 id，verify-artifacts 按前缀转成 ✅／⚠️／❌，
  和挂起标记、评审标记两段的写法一致。`check --format json` 的结构：
  `{"module": id, "base": ref, "files": [{"path": p, "status": "A|M|D|?", "scope": "exclusive|own|outside"}], "outside": n}`。
- **Python 3.9 兼容**：沿用仓库现有写法（`from __future__ import annotations`）。

## Task List

### Task 0：提交已批准的 Plan 与 todo

Plan 获批后用 `review_mark` 记批准，和 todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：解析与路径归属（先红后绿）

新建 `test_module_scope.py`，写解析与 `covers` 的用例（Spec 测试策略第一、二组），确认是红的（模块不存在）；再实现 `parse`、`Scope`、
`ScopeError`、`covers`。把 `test_module_scope.py` 登记进 `scripts/validate.sh` 的测试清单（`check-tests-registered.py` 会查）。

- 验收：新用例全绿；`test_python_compat` 通过；`check-tests-registered.py` 通过。

### Task 2：越界检查 `check`（先红后绿）

写 `check` 的用例：临时 git 仓库，在基线之后改独占内文件、本模块流程文件、外部文件，再加一个未跟踪文件和一个删除；断言文本与 JSON
分类正确；开关 off 退出 3；Spec 没有这一节退出 4、格式错退出 4；`--base` 无效退出 2。确认是红的后实现。

- 验收：用例全绿。

### Task 3：`validate` 与 verify-artifacts（先红后绿）

- `test_module_scope.py` 加 `validate` 用例：开关 off 无输出；on 时未完成模块缺这一节出 warn、格式错出 bad、正确出 ok；已完成模块不检查；
  能力图读不了时出「未验证」。
- `test-verify-artifacts.sh` 加正反例：off（含一份格式错误的并行边界）时输出与没有这段代码时逐字相同；on 时正确、缺失、格式错各一例，
  退出码分别为 0、0、1。
- 确认是红的后实现 `validate`，并在 `verify-artifacts.sh` 里加一段调用。

- 验收：两套用例全绿，verify-artifacts 原有用例不变。

### Task 4：phase-guard 不受影响的回归

在 `test-phase-guard.sh` 的 project-config 段加一例：开关 on、夹具 Spec 带并行边界一节时，阶段提示与无配置时逐字节相同。预期直接绿
（本模块不改 phase-guard）；先在夹具里不设开关跑一次，确认断言能比对到同一份输出。

- 验收：phase-guard 回归全绿。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告，并做两次改坏验证

- 让 `covers` 改成字符串前缀判断，确认「不覆盖同名前缀」变红；
- 让 `validate` 在开关 off 时也检查，确认 verify-artifacts「off 逐字相同」变红。

两处都复原，结果记进 todo。

### Task 5：共享规则（先红后绿）

- `test_workflow_checkpoints.py` 加断言：有 `## 并行边界（moduleConcurrency 为 on 时）` 一节，位于「并行评估」之后、「按需求批量前置审」之前；
  节首写明不是 `on` 时不适用；写到 `独占`、`公共`、四类公共文件、`module_scope.py check`、`--base`、「超出并行边界」、Spec 交审要点；
  「最终验收列出实际改动的文件」一条提到并行边界；约定块模板仍不出现 `moduleConcurrency`。
- 确认是红的后写规则。

- 验收：用例全绿；`check-no-parallel-surface.py` 通过。

### Task 6：设计文档与 CHANGELOG

`docs/design.md` 文件表加 `module_scope.py` 一行；CHANGELOG「未发布」小节「新增」加一条。

- 验收：`validate.sh` 全档通过。

### Checkpoint 2（gate）：模块验收

在正文列出：实际改动的文件（标出超出预计的）；`check` 在一个演示仓库里的文本与 JSON 输出原文；verify-artifacts 在 on 时三种情况的输出
原文；新规则一节的全文；验证结果与未验证项；文档建议。

用户验收后勾选并提交，直接进入 `map-startable`。

- 验收：用户验收通过。

## 影响面

- 新增：`hooks/module_scope.py`、`hooks/test_module_scope.py`；
- 修改：`hooks/verify-artifacts.sh`、`hooks/test-verify-artifacts.sh`、`hooks/test-phase-guard.sh`、`hooks/test_workflow_checkpoints.py`、
  `references/workflow-checkpoints.md`、`scripts/validate.sh`（登记测试）、`docs/design.md`、CHANGELOG；
- 本模块的 Plan 与 todo。

## Risks and Mitigations

- **`check` 的接口会被 module-crew 调用，以后改起来牵连别的插件。** 参数、退出码和 JSON 结构在 Spec 里写定，有用例锁住；
  到 `crew-interface` 再登记进 `interface.json`。
- **仓库里有带空格或非 ASCII 的路径。** git 输出加 `-z` 按 NUL 分隔读取，用例里放一个中文文件名。
- **能力图很大时 `validate` 慢。** 只读未完成模块的 Spec，每份读一次；verify-artifacts 本来就要解析能力图。

## Open Questions

- 无。
