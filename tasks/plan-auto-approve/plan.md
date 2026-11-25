# Plan: plan-auto-approve

<!-- spec-guard: review pending -->

Spec：[spec/plan-auto-approve.md](../../spec/plan-auto-approve.md)（2026-11-25 批准，Q1 A、Q2 A）。

## 架构决定

- **「新流程 Plan 自动批准」只在一处判定**：`module_stage.effective_review(root, module, "plan", raw)` 对新流程模块返回 `("approved", "auto")`，不看文件里的标记；
  `codex_route(root, module, "plan")` 对新流程模块返回 `"auto"`。`stop_node`、阶段提示、`map_view`、`review_mark` 都读这两个函数，不各自判断。
- **review-mark**：`--target plan`／`both` 遇到新流程模块，在读文件之前就拒绝，拒绝码 `plan-auto`，退出 2。
- **阶段提示**：新流程模块在 `NEEDS_PLAN` 不出 `plan-review` 停点；构建中的 gate 一行在 `plan_review == "approved"` 且批准人是 `auto` 时写「Plan 已自动批准」。
  需求确认与技术方案审查的判断排在前面，不动。
- **越界（Q1 A）**：在 `module_scope.py` 新增 `flow_scope(root, module)`，返回新流程模块可以改的范围：
  - 需求文档的「并行边界」（有就用，解析失败按没有）；
  - 技术方案影响面的路径（复用 `module_stage.impact_paths`）：在开工基线或工作区里是目录的，按目录前缀算；
  - 本模块文档与流程文件照 `covers` 和 `classify` 现有规则。
  `classify` 对新流程模块不认预先声明，流程文件一律算 `flow`。`scope_overreach` 遇到新流程模块，不论接管档位都走这条路；没有任何范围（bug、small 也没有并行边界）时
  出「越界：没有并行边界，未检查」一行、不停下。基线读不到时沿用现有的「未判定」一行。
- **T4**：
  - `important()` 的风险路径来源加上技术方案影响面（T3、T4 都算，同现有判定）；
  - 构建中，`classify` 列出的改动文件命中 T4 而模块不是重要需求时，出越界那样的一行并停在中途 gate；读不到风险路径清单时出「T4 路径：没有可读的风险路径清单，未检查」、不停下。
  T4 判定放在 `module_stage.py`，和越界一起由 `scope_overreach` 返回，状态码随事实变化。
- **`map_view`**：`reviewApprovedBy.plan` 取 `effective_review` 的批准人（新增 `auto`）；`codexRoute.plan` 取 `codex_route`（新增 `auto`）；`awaitingReview` 跳过新流程模块的 Plan。
  `APPROVED_BY`、`CODEX_ROUTE` 两组取值进 `interface.json` 1.21。
- **verify-artifacts**：在新流程文档检查那段 Python 里加一条：新流程 Plan 带批准标记 → 警告。

## 任务

- **Task 0**：提交本 Plan 与 todo。验证：`verify-and-commit` 快档。
- **Task 1**：自动批准本身（C1 的批准部分、C3）。先在 `test_flow_v2.py` 写 AC2 的阶段提示与停点用例、在 `test_review_marker.py` 写 AC3 的 `plan-auto` 拒绝，跑红后实现；
  `test_stop_rules.py` 加新流程 `NEEDS_PLAN` 不是 `plan-review` 的反例。验证：这三个测试文件。
- **Task 2**：`/map --json` 与接口 1.21（C4、C7）。`test_map_view.py` 写 `auto` 与 `awaitingReview` 用例，先红后实现；`interface.json`、`check-interface.py`、`docs/commands.md`。
  验证：`test_map_view.py`、`check-interface.py`。
- **Task 3**：越界（C1 越界部分、C2）。`test_module_scope.py` 写 `flow_scope` 与「预先声明不授权」的用例，`test_flow_v2.py` 写 AC4、AC5 的阶段提示用例（git 夹具），先红后实现。
  验证：这两个测试文件、`test-phase-guard.sh`。
- **Task 4**：T4（C1 的 T4 部分）。`test_important_requirement.py` 写影响面列 T4 即重要需求，`test_flow_v2.py` 写构建中改 T4 文件停下、清单读不了只记一行，先红后实现。
  验证：这两个测试文件。
- **Task 5**：verify-artifacts 警告（C5），`test-verify-artifacts.sh` 加正反例。验证：`test-verify-artifacts.sh`。
- **Task 6**：规则文字（C6）：`workflow-checkpoints.md`「批准标记」一节加「新流程 Plan 自动批准」，`node-rules.md`「Plan 交审」与「中途 gate」各加一行；
  `test_workflow_checkpoints.py` 锁要点短语。验证：该测试文件、`test_stop_rules.py`。

## 检查点

- Checkpoint 1（report）：Task 1～4 完成后，本机三套检查全绿；变异：`effective_review` 不再给新流程 Plan `auto`、`classify` 对新流程照旧认预先声明、T4 检查去掉「不是重要需求」的条件，
  各自让回归变红后还原。记进 todo，不停下。
- Checkpoint 2（gate）：全部任务完成后，本机三套检查与 `check-interface.py` 全绿。推送本分支、开 PR（Plan 批准即授权）；开 PR 后提议打开宿主 PR 监控，用户批准才开。
  然后交最终验收，同一条消息里问「验收通过、合并吗？」，证据含 PR 上 `CI required` 的结果（没跑完照实写，不自己等）；拟回告（发 autopr-design 核对 `reviewApprovedBy.plan=auto`、`codexRoute.plan=auto`）在验收时给出原文。

## 会改哪些文件

- 新增：`tasks/plan-auto-approve/{plan,todo}.md`。
- 修改：`plugins/spec-guard/hooks/{module_stage.py,module_scope.py,review_mark.py,map_view.py,verify-artifacts.sh}`、`plugins/spec-guard/references/{workflow-checkpoints.md,node-rules.md}`、
  `plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`docs/commands.md`，以及 Spec 并行边界里列的九个测试文件。都在 Spec 的并行边界内。
- 新增依赖、锁文件改动：无。

## 风险

- **已有新流程模块的 Plan 会突然不再等批准**：这正是本模块的目的；老模块由 AC1 的回归锁住。已经在构建中的新流程模块，如果影响面写得不全，会第一次看到越界提示——这是有意的「照拦」，不是误报。
- **影响面里的路径写法不统一**：只认反引号里的路径，复用 design-review 的读法；目录靠基线或工作区判断，判断不了时按文件算（更严，宁可多拦）。
- **`important()` 读技术方案后，更多需求被判为重要**：只多了「影响面列了 T3／T4 路径」这一条来源，判定口径不变；`test_important_requirement.py` 锁住其余来源不变。
- **`module_scope` 与 `module_stage` 互相导入**：沿用现有的「函数内延迟导入」写法，不调整模块结构。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无
