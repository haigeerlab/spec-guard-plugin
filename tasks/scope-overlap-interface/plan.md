# Plan: scope-overlap-interface

依据 [`spec/scope-overlap-interface.md`](../../spec/scope-overlap-interface.md)。本仓库评审节奏为分开审：Spec 已于 2026-10-22 单独批准
（用户批准事项 C162，Q1 A、Q2 A；`docs/design.md` 从独占清单移出，改为「只追加（quiet-injection 独占）」，已按原话改进 Spec 并记变更记录，
修订后的 Spec 于用户批准事项 C165 批准），本 Plan 单独交审。分支 `scope-overlap-interface`，worktree
`.claude/worktrees/current-plugin-owner-aa5b98-crew/scope-overlap-interface`。不改版本号与 CHANGELOG、不推送、不开 PR；合并由模块协调按用户原话做。

所需工具：无 UI 改动，不需要浏览器或电脑操作。不加新依赖。

## Overview

先把重叠判定从 `map_view.py` 原样挪进 `module_scope.py`（纯搬家，`/map` 回归前后都绿），再按先红后绿给 `module_scope.py` 加 `overlap` 子命令，
做改坏验证。接口文件 `interface.json` 是公共文件，发【公共变更请求】请模块协调按 Spec C3 落地，落地并同步后再让 `check-interface.py` 核对
`scopeOverlap` 并补检查器夹具。最后往 `docs/design.md` 追加 1.10 一段，同步集成分支跑完整检查。

## Architecture Decisions

- **共用函数放 `module_scope.py`，名叫 `overlap`。** `map_view.py` 已在顶层导入 `module_scope`，反过来 `overlap` 子命令要用 `map_view.build`
  取模块状态，所以 `module_scope` 只在子命令的函数里导入 `map_view`，避免循环导入。
- **模块状态只经 `map_view.build`。** 不在 `module_scope` 里重写「进行中／就绪」的判定；`build` 在开关为 on 时会扫本机 worktree（最多 10 秒），
  这是接受的代价，不另加参数绕开。
- **子命令的核心是一个纯函数**，输入「模块 → (来源, Spec 正文或读取错误)」与可选的 Build order，输出 `{"conflicts", "errors"}`；CLI 只负责解析参数、
  读文件、调 `build`。这样单元测试大多不用建 git 仓库。
- **`check-interface.py` 的改动排在接口文件落地之后**：它一核对 `scopeOverlap`，接口文件没落地时 `validate.sh` 就会红；所以 Task 3 等【公共变更请求】
  落地、`module-crew sync` 之后再做。
- **`docs/design.md` 只追加一段**，不改已有行；它不在本模块独占清单里，最终验收的越界检查会列出它，按 Spec 写明是已批准的例外。

## Task List

### Task 0：提交 Plan 与 todo

Plan 与 todo、修订后的 Spec 一起提交并交审。收到开工类【协调通知】后单独执行 `module-crew sync`，确认 Spec、Plan 带批准标记。

- 验收：`verify-and-commit.sh` 快档通过；sync 后 Spec 与 Plan 的标记都是 `approved`。

### Task 1：重叠判定挪进 `module_scope.py`（纯搬家，Spec C1 前半、C2）

- `module_scope.py` 新增 `overlap(a, b)`（`map_view._overlap` 原样，含文档串）；`map_view.py` 删 `_overlap`、改导入 `overlap`，`_concurrency` 改调它。
- `test_map_view.py` 里两例 `_overlap` 改为测 `module_scope.overlap`；改前改后 `test_map_view.py` 全绿。

- 验收：`test_map_view.py`、`test_module_scope.py` 全绿；`map_view.py` 里不再有 `_overlap`。

### Task 2：`overlap` 子命令（先红后绿，AC1～AC5）

先在 `test_module_scope.py` 加 `OverlapTests`，确认是红的（Spec「Testing strategy」所列：相同路径、目录包含、同名前缀不算、`--project` 并入与传入为准、
完成与挂起不参与、两个项目模块也比、各种 errors 不中断、`--project` 无能力图、开关 off／无配置结果相同、用法错误退出 2 无 JSON、Build order 排序，
项目模块缺边界进 errors（Q1 A））。再实现：`OVERLAP_ERRORS` 常量、纯函数、`overlap` 子命令（Spec C1、假设 1～9）。

- 验收：`test_module_scope.py`、`test_map_view.py` 全绿。

### Checkpoint 1（report）：改坏验证

在 scratchpad 里 `mktemp -d` 建的整仓副本（`git archive HEAD`）上各改一处，跑两个测试文件：
- `overlap` 改用字符串前缀判断 → 两个测试文件里「同名前缀不算」都变红；
- `--project` 的模块在 `--spec` 同名时不被替换 → 「传入为准」变红。

结果记进 todo，继续。

### Task 3：接口文件落地与接口检查（AC6）

- 发【公共变更请求】给模块协调：「文件」列 `plugins/spec-guard/interface.json`，内容即 Spec C3（版本 1.9→1.10，`gateTick` 之后加 `scopeOverlap`）；
  落地前发【等待其他会话】、任务列表停在本项。
- 收到落地通知后单独执行 `module-crew sync`，再先红后绿：`test-checkers.sh` 的 check-interface 夹具加两例（删掉 `scopeOverlap` → 报缺入口；
  `scopeOverlap.values.error` 少一个码 → 报取值不一致），然后改 `check-interface.py`（Spec C4）。

- 验收：`python3 scripts/check-interface.py` 通过；`test-checkers.sh` 全绿。

### Task 4：`docs/design.md` 追加 1.10 一段（AC6）

在「对外接口」一节 1.9 那段之后追加 Spec C5 那一段，不改已有行。

- 验收：`git diff crew/fix-batch -- docs/design.md` 只有新增行；`validate.sh --quick` 通过。

### Task 5：合入集成分支并跑完整检查

单独执行 `module-crew sync`；跑 Spec 的 Commands 全部七条；`module_scope.py check --module scope-overlap-interface --base crew/fix-batch` 核对越界。
`docs/design.md` 与 quiet-injection 冲突时以集成分支为底，只把本模块那一段追加放回去。

- 验收：七条命令全绿；越界只有 `docs/design.md`（已批准的只追加例外）。

### 最终验收（gate）

交最终验收【交审】：按 AC1～AC7 逐条给证据，附改动统计与越界检查。不含推送与开 PR。

## Risks and Mitigations

| 风险 | 影响 | 应对 |
|---|---|---|
| 接口文件落地要等模块协调 | Task 3 停住 | Task 1、2、Checkpoint 1 不依赖它，先做；等待期间发【等待其他会话】，不自己改 `interface.json` |
| `quiet-injection` 同时改 `docs/design.md` | sync 冲突 | 只追加一段；冲突以集成分支为底放回这一段 |
| `map_view.build` 在开关 on 时扫 worktree，测试变慢 | `test_module_scope.py` 耗时 | 带 `--project` 的用例只建最少的临时项目；纯函数用例不建仓库 |
| 循环导入 | 运行时报错 | `map_view` 只在子命令函数里导入；Task 2 有一例从命令行真跑 `--project` |
| module-crew 真接入后的批量审查 | 单元测试证明不了 | 照 Spec 写明未验证，留到 module-crew 那边的改动里验 |
