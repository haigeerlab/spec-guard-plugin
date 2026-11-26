# Plan: rework-scope-baseline

<!-- spec-guard: review pending -->

Spec：[spec/rework-scope-baseline.md](../../spec/rework-scope-baseline.md)（2026-11-26 批准，Q1 A）。Codex 第一轮 3 条阻断（R1-1～R1-3），已按下面改。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 架构决定

- **一个新函数**（`hooks/module_scope.py`）：
  - `rework_info(root, module) -> dict | None`：`{"base", "start"}`，不在返工或第一次开工时为 None。
    1. 「全部勾完」= todo 有任务（已勾或正式延期，`module_stage.deferred_items`）且没有未勾选项（`module_stage.UNCHECKED`，与阶段判定同一个正则）；只剩正式延期、一个已勾选项都没有也算（R1-2）。
    2. `git log -n 200 --format=%H -- tasks/<id>/todo.md` 从新到旧读出各提交上的 todo（`git show <c>:<path>`）。找最新的「有未勾选项」提交 O（工作区 todo 有未勾选项时，工作区就是最新的「有未勾选项」状态）；没有 O → None。
    3. 从 O 往更旧找最近的「全部勾完」提交 D；没有 D → None（第一次开工）。
    4. D 与 O 之间（含 O）最旧的有未勾选项的提交 R → `{"base": R^, "start": R}`；只有工作区有未勾选项、HEAD 的 todo 是 D 的状态 → `{"base": HEAD, "start": None}`。
    5. 这样返工任务全部勾完之后（例如 Codex 最终验收前后），仍按这一轮返工的基线算，不会退回原基线（R1-1）；下一轮返工出现新的 D、O 时换成新的。
    6. git 读不到、`R^` 不存在 → None。
  - `scope_base(root, module) -> str | None`：`rework_info` 有值就用它的 `base`，否则 `default_base`（原有判定，一字不改）。
  - `check` 命令不给 `--base` 时改用 `scope_base`。
- **调用点**（Spec 假设 2、3）：`module_stage.scope_overreach`、`module_stage.t4_hits`（`base or scope_base(...)`）、`module_stage.acceptance_step`、`review_mark._outside` 改用 `scope_base`；
  `review_mark._merge_at_base`、`module_stage.module_baseline` 不改。
- **提示写明基线**（假设 4，R1-3）：`scope_overreach` 在 `rework_info` 有值时，越界一行末尾加「（返工：从提交 `<start 前 12 位>` 起算）」/ "(rework: counted from commit `<12>`)"——写返工开始的提交 R，不写它的父提交；返工还没提交时写「（返工：还没提交，与 HEAD 比较）」/ "(rework: not committed yet, compared with HEAD)"。越界事实（状态码）不变；第一次开工的模块文字逐字不变。
- **测试放哪**：`test_module_scope.py` 加 `ReworkBase`（git 夹具：模块做完 → 别的模块合入 → 返工），`test_flow_v2.py` 加提示文字一例，`test_review_marker.py` 加 `_merge_at_base` 仍用原基线一例；不新建测试文件。

## 任务

- **Task 0**：提交 Spec 批准、能力图新行、Plan 与 todo。验证：`verify-and-commit` 快档。
- **Task 1**：`rework_info` 与 `scope_base`。先写会红的 `ReworkBase`：第一次开工返回 None、`scope_base` 等于 `default_base`（AC1）；做完后别的模块合入、再返工只改边界内 → `base` 是返工第一个提交的父提交、`start` 是它、`classify` 不含别的模块的文件（AC2）；返工改了边界外文件照样在 `outside`（AC2）；返工任务全部勾完并提交后仍是这一轮的基线（R1-1）；只在工作区返工 → HEAD、`start` 为 None；返工两次取最近（AC3）；只剩正式延期、没有已勾选项的历史提交算全部勾完（AC4、R1-2）；不是 git 仓库 → None（AC5）。再实现。验证：`test_module_scope.py`。
- **Task 2**：接到调用点与提示。`check` 命令默认基线；`scope_overreach`、`t4_hits`、`acceptance_step`、`_outside` 改调；返工时越界一行写返工开始的提交、只在工作区时写与 HEAD 比较（AC7、R1-3），两种各一例。用例：`test_flow_v2.py` 返工提示文字、第一次开工文字不变；`test_review_marker.py` `_merge_at_base` 与「碰了老文件」仍用原基线（AC6）。先红后实现。验证：这三个测试文件、`test-phase-guard.sh`。
- **Checkpoint 1（report）**：完整档三条检查全绿；在临时副本里变异（`rework_info` 用 D 而不是 `R^`；不认正式延期；返工勾完后退回原基线；`_merge_at_base` 改用 `scope_base`），各自让对应用例变红，还原后全绿；用已安装的 0.96.1 与本分支对本仓库跑阶段提示与 verify-artifacts，逐字比对（本仓库现在没有在返工的模块，应相同）。
- **Task 3**：规则与文档。共享检查点规则「返工与小模块」补一句；CHANGELOG「未发布」；版本 0.96.1 → 0.96.2（两份 plugin.json、两份 README 的 `--ref`）。验证：快档。
- **Checkpoint 2（gate）**：重跑完整档；推送、开 PR；最终验收与合并合成一问；发 0.96.2 另取授权。拟回告：无（不改对外字段）。

## 返工：merge 过默认分支（2026-11-26，Spec 假设 8～10，Q2 A、Q3 A）

预先声明不变（四行仍为「无」）。

- **`module_scope.rework_info` 多给一个键 `trimmed`**（假设 8）：算出返工基线 `base` 之后——
  1. 默认分支：延迟导入 `verification.default_branch`（verification 导入 module_stage，module_stage 导入本模块，所以只能在函数里导入）；读不到 → `trimmed` 为 None。
  2. 当前分支（`git symbolic-ref --quiet --short HEAD`）就是默认分支的本地分支（`refs/remotes/origin/main` 对应 `main`）→ None：直接在默认分支上返工时始终保留返工基线，即使远端跟踪分支停在返工中途（R3-1）。
  3. `git merge-base HEAD <默认分支>` 得 M；读不到、M 等于 HEAD、M 等于 `base`，或 `git merge-base --is-ancestor <base> M` 不成立 → None。
  4. 否则 `trimmed = M`。只在工作区返工时 `base` 是 HEAD，M 不可能是它的后代，自然为 None。
- **`scope_base`**：返工时返回 `trimmed or base`；第一次开工照旧 `default_base`（Q3 A，一字不改）。六个调用点都经它，不用改。
- **提示**（假设 9，R3-2）：`_rework_note` 现在的返工说明是「；返工：从提交 `<12>` 起算」（不带括号）。`trimmed` 有值时完整文字为
  「；返工：从提交 `<12>` 起算（已扣除默认分支上的提交）」/ "; rework: counted from commit `<12>` (commits already on the default branch left out)"；没有时文字逐字不变。用例对整行做精确断言。
- **测试**：`test_module_scope.py` 加 `ReworkMergeBase`，git 夹具带一个本地 `main`，在 `rw` 分支上返工：
  - merge 情形：只改边界内 → `classify` 的 `outside` 为空、不含别的模块文件；返工改了边界外的文件 → 只报它（AC9）。
  - rebase 情形：结果同上，且 `trimmed` 为 None（AC10）。
  - 两段返工：第一段 merge 进 `main`（todo 仍有未勾选项），别的模块再合入 `main`，从 `main` 开新分支续做 → 只比较第二段（AC11）。
  - 直接在 `main` 上返工 → `trimmed` 为 None；带 `origin/HEAD` 时，远端跟踪分支停在返工中途、本地 `main` 继续领先 → 仍为 None，且早先返工改的边界外文件照样报（AC11、R3-1）；没有 `main`、没有 origin → None（AC11）。
  - 正常返工分支、默认分支取自 `origin/HEAD`（远端跟踪分支）时照样扣除（AC9）。
  - 第一次开工的模块 merge 过 `main` → `scope_base` 仍等于 `default_base`（AC12）。
  - `test_flow_v2.py` 的 `ReworkOverreachTest` 加一例提示文字（AC12）。

### 返工任务

- **Task 4**：`trimmed` 与 `scope_base`。先写会红的 `ReworkMergeBase`，再实现。验证：`test_module_scope.py`、`test_flow_v2.py`。
- **Task 5**：提示、规则与版本。`_rework_note`；共享检查点规则「返工与小模块」那段补一句（返工分支同步过默认分支时，扣除已在默认分支上的提交）；CHANGELOG「未发布」；版本 0.96.2 → 0.97.0（两份 plugin.json、两份 README 的 `--ref`）。验证：`test_flow_v2.py`、快档。
- **Checkpoint 3（report）**：完整档三条全绿；变异（临时副本）：去掉「不等于 HEAD」、去掉「当前分支是默认分支」、去掉祖先判断、`scope_base` 不用 `trimmed`，各让对应用例变红，还原后全绿；已安装的 0.96.2 与本分支对本仓库的阶段提示、verify-artifacts 逐字比对。
- **Checkpoint 4（gate）**：推送、开 PR；最终验收与合并合成一问；发 0.97.0 等第 2 件（删退役接口）做完后另取授权。拟回告：给 lead「返工越界改为扣除默认分支上的提交」。

## 外部审查意见

<!-- spec-guard: codex-review round=1 blocking=3 sha256=7c42309c609e -->
<!-- spec-guard: codex-review round=2 blocking=0 sha256=d92bdcf5b050 -->
<!-- spec-guard: codex-review round=3 blocking=2 sha256=e9be620ab690 -->
