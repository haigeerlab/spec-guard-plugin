# Plan: crew-interface

<!-- spec-guard: review approved -->

依据 [`spec/crew-interface.md`](../../spec/crew-interface.md)。本仓库评审节奏为分开审：Spec 已于 2026-10-18 单独批准（`a31864a`，用户决定不做外部审查），
本 Plan 单独交审。分支 `claude/module-concurrency`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`。

这是本批 7 个模块的最后一个：按 `docs/release-process.md`「一个需求跨多个模块时只在最后一个模块的 PR 里改版本号」，版本号在本模块升到 0.68.0。
**推送、开 PR、合并、打 tag 都不在本 Plan 的授权里**，Checkpoint 2 验收时单独问；发版后的步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

先扩展一致性检查（先写会失败的检查用例），再写 `interface.json` 1.1，然后是对外说明和版本号，最后做收尾核对。

## Architecture Decisions

- **取值常量**：`module_scope.SCOPES = ("exclusive", "own", "outside")`、`checkout_role.ROLE_KINDS = ("module", "coordinator")`；`covers()` 与 `read_marker()`
  里的字面量改为引用它们，行为不变（两个模块的单元测试原样全绿即为证明）。`moduleConcurrency` 的取值取自 `project_config.CONCURRENCY`。
- **`check-interface.py` 的扩展**：对四个新入口逐个核对「命令里引用的脚本存在」，以及取值集合与上面的常量一致；`interface` 版本号只校验格式（与现在相同）。
  `scripts/test-checkers.sh` 的 `mkifc` 夹具同时放上新入口引用的几个脚本占位文件。
- **`interface.json` 的说明文字用英文**，与 1.0 一致；新入口的命令数组与各脚本的真实参数逐一对照（Checkpoint 1 用实跑核对）。
- **只加不改的一次性比对**：用临时脚本从新文件里去掉新增的键、把 `interface` 还原为 `"1.0"`，与 `v0.67.1` 的 `interface.json` 解析后比较相同；结果记进 todo。
  长期断言放在 `test-checkers.sh`：`mapView` 的 1.0 键（`command`、`schemaVersion`、`contract`、`exitCodes`、`values`）仍在。

## Task List

### Task 0：提交已批准的 Plan 与 todo

Plan 获批后用 `review_mark` 记批准，和 todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：取值常量与一致性检查（先红后绿）

先在 `scripts/test-checkers.sh` 的 check-interface 一段加用例，确认是红的：
- 正例：带四个新入口的夹具通过；
- 反例：`scopeCheck` 引用的脚本不存在；`scopeCheck.values.scope` 少一个取值；`checkoutRole.values.role` 多一个种类；`moduleConcurrency.values` 少一个取值；
  `mapView` 缺 1.0 的某个键——各自报错。

再加常量、改 `covers()`、`read_marker()` 引用它们，扩展 `check-interface.py`。此时仓库里的 `interface.json` 还是 1.0，`check-interface.py` 对它会因缺新入口而报错，
所以本任务与 Task 2 一起提交。

- 验收：`test-checkers.sh` 全绿；`test_module_scope.py`、`test_checkout_role.py` 原样全绿。

### Task 2：`interface.json` 1.1

按 Spec 假设 2、3 写入四个顶层入口与 `mapView.concurrency`，`interface` 改为 `"1.1"`。逐条实跑新入口的命令（在临时项目里开关为 on），确认参数、退出码与文件一致。
与 Task 1 一起提交。

- 验收：`check-interface.py` 通过；一次性比对（去掉新增后与 v0.67.1 相同）通过。

### Checkpoint 1（report）：三套核心回归、改坏验证与实跑核对

- 三套核心回归与 ShellCheck；
- 改坏验证：删掉 `scopeCheck` 命令里脚本路径的一个字符、把 `SCOPES` 改掉一个值，各自确认 `check-interface.py` 报错，复原；
- 新入口命令的实跑结果记进 todo。

### Task 3：对外说明、版本号与 CHANGELOG

- `docs/design.md`「对外接口」列出新入口，并加一小节「规划层与运行层」：spec-guard 读写什么、module-crew 读写什么、交接点在哪；
- README 中英文各加一节「多模块并行（可选）」，并把 Codex 安装命令的 `--ref` 改为 `v0.68.0`（`check-readme-sync.py` 核对两份一致）；
- 两份 `plugin.json` 改为 `0.68.0`；
- CHANGELOG：「未发布」改为 `[0.68.0] - 2026-10-18`，导语写明本版的 7 个模块，并加一条「新增」说明 interface 1.1；
- 运行 `/bin/bash evals/codex-plugin-smoke.sh --selftest`（改了 Codex manifest 的版本号）。

- 验收：`validate.sh` 全档通过；smoke 自检通过。

### Checkpoint 2（gate）：模块验收与本批收尾

先做收尾核对并记进 todo：
- `evals/hint-english-diff.sh v0.67.1`：英文提示与 0.67.1 逐字节相同、中文无英文标签；
- 用 `v0.67.1` 的 hooks 与当前版本，在开关不是 on 的夹具（含角色标记、并行边界、worktree）上整份比对阶段提示与 `/map`；
- 本机 macOS `/bin/bash` 跑完整校验与两套 hook 回归（发版流程要求）。

在正文列出：实际改动的文件；`interface.json` 1.1 的全文；收尾核对结果；本批 7 个模块的总结（各自交付了什么、提交范围）；未验证项；拟回告 module-crew 的内容。
用户验收后勾选并提交，然后**单独询问**是否推送并开 PR（PR 合并由用户进行），以及之后的发版步骤。

- 验收：用户验收通过。

## 影响面

- 修改：`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`scripts/test-checkers.sh`、`hooks/module_scope.py`、`hooks/checkout_role.py`、
  `docs/design.md`、`README.md`、`README.en.md`、两份 `plugin.json`、`CHANGELOG.md`；
- 本模块的 Plan 与 todo。

## Risks and Mitigations

- **`interface.json` 写错，使用方按它调用失败。** 一致性检查核对脚本与取值，Task 2 逐条实跑命令。
- **README 中英文不同步。** `check-readme-sync.py` 会拦下；两份同一次提交。
- **负载高时带超时的用例偶发失败。** 按前面的做法确认原因、等负载下降后重跑，不改代码。

## Open Questions

- 无。
