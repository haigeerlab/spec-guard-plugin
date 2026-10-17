# Plan: checkout-role

<!-- spec-guard: review approved -->

依据 [`spec/checkout-role.md`](../../spec/checkout-role.md)。本仓库评审节奏为分开审：Spec 经 delegate 只读审查、改为展示层方案后，于 2026-10-18
获批（`3ac942b`），本 Plan 单独交审。分支 `claude/module-concurrency`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`。按批量发版约定
不改版本号、不推送、不开 PR；验收后进入最后一个模块 `crew-interface`，并把 `worktree` 字段与角色命令的定稿告诉 module-crew。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

由内向外：先做角色标记的读写（纯本地文件与 git 路径），再接阶段提示的展示层，然后是 `/map` 的 worktree 扫描，最后写命令说明与文档。每一步先写失败的测试。

## Architecture Decisions

- **新文件 `hooks/checkout_role.py`** 承担标记的路径、读取、写入与 CLI；`role(root)` 是阶段提示唯一的入口，开关不是 on 时不调用 `read_role`。
- **阶段提示的改动集中在 `describe()` 末尾组装输出之前的一处**：拿到全局的 `stage`、`current`、`review_step` 等之后，开关为 on 时按角色改「本 checkout」块、
  评审行和「下一步」。`project_stage`、`module_state` 的代码与调用参数不动；Checkpoint 1 用 `git diff` 核对这两个函数。
- **展示层的角色逻辑写成独立函数**（例如 `role_view(...)`），输入是已经算好的全局结果与 X 的 `module_state`，输出是要加的行和替换的「下一步」，方便单独测试。
- **worktree 扫描写在 `checkout_role.py`**（`scan_worktrees(root, deadline)`），`map_view._concurrency()` 只调用一次；git 调用统一走现有的超时包装。
- **测试分工**：角色读写与展示层用 Python 单元测试（`test_checkout_role.py`，直接调用 `describe()` 与 `role_view()`），开关 off 时的端到端不变用
  `test-phase-guard.sh`；`/map` 的字段用 `test_map_view.py`。新测试文件登记进 `scripts/validate.sh`。
- **与 PR #345 的关系**：本模块新增的提示行用英文。如果在本模块验收前 #345 已合入 main，验收前先把它合进本分支、解决冲突，并让新增几行跟随产物语言；否则在
  `crew-interface` 收尾或最终合并时处理（Spec 假设 8）。

## Task List

### Task 0：提交已批准的 Plan 与 todo

Plan 获批后用 `review_mark` 记批准，和 todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：角色标记的读写与命令行（先红后绿）

先写 `test_checkout_role.py` 的读写用例（Spec 测试策略第一组：各自 git 目录、不进 `git status`、`--project` 与 cwd 不同、预览／确认／读回、`clear`、
模块不在能力图、父仓库子目录、bare、符号链接、超长、内容无效不回显、off 时 `set`／`clear` 退出 3、读回不一致退出 4、off 时零读取），确认是红的；再实现
`role_path`、`read_role`、`role` 与 CLI。登记测试文件。

- 验收：新用例全绿；`test_python_compat`、`check-tests-registered.py` 通过。

### Task 2：阶段提示的展示层（先红后绿）

先写失败的用例：
- 单元测试：模块角色 X 的六种状态（NEEDS_SPEC、NEEDS_PLAN 且 Spec 待审、BUILDING、已完成、挂起、不在能力图）；另有半完成模块、state.json 的 activeModule 无效或指向别处时，
  全局两行照旧、「下一步」只指向 X；X 已完成时不含切换模块、activeModule、push、merge；全局当前模块的评审行与外部审查提示不出现；协调角色在待审、批准后已修订、构建中三种
  情况下的「下一步」，都不含 `/build`；标记无效时一行固定措辞。
- `test-phase-guard.sh`：开关 off、未设置、配置无效时，checkout 里放了角色标记，注入与没有标记时逐字节相同。

再实现 `role_view` 并接进 `describe()`。

- 验收：新旧用例全绿；phase-guard 回归原有用例不变。

### Task 3：`/map` 的 worktree 字段与表格后缀（先红后绿）

先在 `test_map_view.py` 写失败的用例：主仓库加三个 worktree（Spec 测试策略的 `/map` 一组），覆盖各字段、`duplicates`、todo 缺失与不可读、detached、已删除目录被跳过、
本地就绪与已完成的模块也带后缀；开关 off 时零扫描（计数替身）、字段与后缀都不出现。再实现 `scan_worktrees` 并接进 `_concurrency()` 与 `render`。

- 验收：新旧用例全绿。

### Checkpoint 1（report）：一次性整份比对、核对选模块代码未动、三套核心回归与改坏验证

- 一次性整份比对：改动前提交（`3ac942b`）的 hooks 与当前版本，在开关不是 on 的夹具（含放了角色标记的 checkout）上对比阶段提示与 `/map`，去掉动态字段后逐字节相同；
- `git diff 3ac942b -- plugins/spec-guard/hooks/module_stage.py` 里 `project_stage`、`module_state` 两个函数没有改动；
- 改坏验证四处（Spec 测试策略所列），各自确认变红后复原；
- 三套核心回归全绿，ShellCheck 无告警。

结果记进 todo。

### Task 4：命令说明、Codex 技能、共享规则与文档

- 新增 `commands/checkout-role.md`（参照 `review-mark.md` 的插件根定位片段与预览／确认写法）；
- `skills/spec-guard-ops/SKILL.md` 加 checkout-role 一节；
- 共享规则「协调会话的批准与合并」一节补一句：协调会话由角色标记 `coordinator` 标出，外部审查由协调会话向用户提议；`test_workflow_checkpoints.py` 加一条断言；
- `docs/design.md` 文件表加 `checkout_role.py`，`docs/commands.md` 命令总表加一行；CHANGELOG「未发布」小节「新增」加一条；
- 如果 `validate.sh` 要求新命令在别处登记（清单、命令表），按它的报错补齐。

- 验收：`validate.sh` 全档通过；`check-no-parallel-surface.py` 通过。

### Checkpoint 2（gate）：模块验收

在正文列出：实际改动的文件（标出超出预计的）；在一个演示仓库（主仓库加两个 worktree）里 `checkout-role` 预览与写入的原文、模块与协调两种角色下的阶段提示原文、
`/map` 的 worktree 字段与表格原文；整份比对与代码核对结果；验证结果与未验证项；文档建议；拟回告 module-crew 的内容；与 PR #345 的处理状态。

用户验收后勾选并提交，进入 `crew-interface`。

- 验收：用户验收通过。

## 影响面

- 新增：`hooks/checkout_role.py`、`hooks/test_checkout_role.py`、`commands/checkout-role.md`；
- 修改：`hooks/module_stage.py`、`hooks/map_view.py`、`hooks/test-phase-guard.sh`、`hooks/test_map_view.py`、`hooks/test_workflow_checkpoints.py`、
  `references/workflow-checkpoints.md`、`skills/spec-guard-ops/SKILL.md`、`scripts/validate.sh`、`docs/design.md`、`docs/commands.md`、CHANGELOG；
- 本模块的 Plan 与 todo。不改 `project_stage`、`module_state`、`interface.json`、约定块模板。

## Risks and Mitigations

- **改阶段提示是本批风险最高的一处。** 全局计算不动，角色逻辑独立成函数，off 时零调用；整份比对与 `git diff` 双重核对。
- **与 PR #345 冲突。** 按 Architecture Decisions 的约定处理；验收时报告当时的状态。
- **worktree 测试依赖本机 git 版本。** 用例只用 `git worktree add/list/remove` 的基本功能；`--porcelain -z` 需要较新的 git，若本机不支持，按 Spec 改用逐行解析并在 todo 里写明。
- **负载高时带超时的用例偶发失败。** 如遇，按前一个模块的做法确认是负载原因、等负载下降后重跑，不改代码。

## Open Questions

- 无。
