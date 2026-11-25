# Plan: plan-auto-approve

<!-- spec-guard: review approved -->

Spec：[spec/plan-auto-approve.md](../../spec/plan-auto-approve.md)（2026-11-25 批准，Q1 A、Q2 A）；Codex 审两轮仍有阻断，交用户；2026-11-25 用户「Plan 和 Spec 修订都批准」（Spec 修订：假设 10）。

## 架构决定

- **路线和批准分开判**（R1-1）：
  - `codex_route(root, module, "plan")` 对新流程模块固定返回 `"auto"`（路线，不看文件在不在）；
  - `effective_review(root, module, "plan", raw)` 对新流程模块：`plan.md` 存在时返回 `("approved", "auto")`，不看文件里的标记；不存在时返回 `("none", None)`，阶段照旧是 `NEEDS_PLAN`。
  `stop_node`、阶段提示、`map_view`、`review_mark` 都读这两个函数，不各自判断。
- **review-mark 的拦截位置**（R1-7）：模块 id 与能力图校验通过后、读任何文件和进入各状态分支之前，`--target plan`／`both` 遇到新流程模块就拒绝（`plan-auto`，退出 2），
  不论 `--state`、文件在不在、标记坏没坏、带不带 `--confirm`。
- **阶段提示**：新流程模块在 `NEEDS_PLAN` 不出 `plan-review` 停点；构建中的 gate 一行在批准人是 `auto` 时写「Plan 已自动批准」。需求确认与技术方案审查的判断排在前面，不动。
- **新流程的范围（Q1 A）**：`module_scope.flow_scope(root, module)` 返回 `{"status", "scope"}`：
  - 来源：需求文档的「并行边界」+ 技术方案影响面的路径（复用 `module_stage.impact_paths`；在开工基线或工作区里是目录的按目录前缀算，判断不了按文件算）；本模块文档与流程文件照 `covers`／`classify` 现有规则；
  - `status` 分四种（R1-4）：`ok`（有范围）；`none`（bug、small 没有并行边界：不查越界，只记一行「越界：没有并行边界，未检查」）；
    `unknown`（normal、important 既没有并行边界、影响面也写不出路径：停下，补影响面）；`invalid`（并行边界写坏或读不了：停下，同现有 `boundary-invalid`）。
  - `classify` 对新流程模块不认预先声明，流程文件一律算 `flow`。
- **用到范围的入口都改走 `flow_scope`**（R1-3）：阶段提示的 `scope_overreach`；`module_scope.py check`（新流程模块不论接管档位都检查；`none` 退出 3 并说明未检查，`unknown`／`invalid` 退出 4）；
  最终验收的 `review_mark._outside`（新流程模块用 `flow_scope`，`none` 时不判越界，其余约束不变）。老模块三处的判定一字不改。
- **预先声明在新流程里不起作用**（R1-5）：
  - `module_scope.py declared` 的字段集合不变（R2-1）：新流程模块有 Plan 时 `planApproved: true`、`approvedCommit: null`（自动批准没有批准提交），老模块输出一字不改；
    预先声明照旧解析和报告（写坏时照旧退出 4，这是文件事实），但不授权任何路径；
  - `validate-declared` 对新流程模块不报 `bad`，改报 `ignored <id>`，verify-artifacts 据此警告「新流程 Plan 的预先声明不起作用」。
- **T4 独立于越界**（R1-2、R1-6）：
  - 构建中用 `module_scope.changed_files(root, base)` 单独取改动文件，命中 T4 且模块不是重要需求时停在中途 gate；`flow_scope` 是 `none`／`unknown`／`invalid` 时照样查 T4；
  - 读不到风险路径清单时出「T4 路径：没有可读的风险路径清单，未检查」、不停下；
  - 拿不到改动列表时（R2-3）：需求文档还没提交（没有开工基线）、基线不是有效提交、或 git 列改动失败，都出一行「越界与 T4：没有开工基线可比（原因），未检查」，不当成「没有改动」；
    不停下（探测失败只降级、不当事实，项目不变量），同现有越界检查的「未判定」；
  - `important()` 的风险路径来源加技术方案影响面，**只对新流程模块**；老模块即使有 `design.md` 也不读。
- **共享判据与 verify-artifacts**（R1-8）：越界与 T4 的判定只在 `module_scope.flow_scope`、`module_stage.t4_hits` 两个函数里，阶段提示、`check` 命令、最终验收都调它们。
  verify-artifacts 和现在一样不查构建中的改动（takeover-scope-check 也只在阶段提示里查），它调 `flow_scope` 查新流程模块的范围本身：`invalid` 判失败，`unknown` 警告；
  另外警告新流程 Plan 带批准标记、预先声明不起作用。
- **`map_view`**：`reviewApprovedBy.plan` 取 `effective_review` 的批准人（新增 `auto`）；`codexRoute.plan` 取 `codex_route`（新增 `auto`）；`awaitingReview` 跳过新流程模块的 Plan。
  `review.plan` 仍报文件里的原始标记（R2-2）。`APPROVED_BY`、`CODEX_ROUTE` 两组取值与 `declared` 在新流程下的含义进 `interface.json` 1.21。

## 任务

- **Task 0**：提交本 Plan 与 todo。验证：`verify-and-commit` 快档。
- **Task 1**：自动批准本身与 `plan-auto`。先写会红的用例：
  - `test_flow_v2.py`：没有 Plan（`NEEDS_PLAN`、批准人为空）、没有标记的 Plan、带旧标记（`pending`／`approved`／`codex-approved`）的 Plan，三种情形的阶段、停点与 gate 一行（AC2）；
  - `test_review_marker.py`：`plan`／`both` 在文件缺失、标记写坏、带 `--confirm` 时都退出 2、拒绝码 `plan-auto`、Spec 与 Plan 字节不变（AC3）；
  - `test_stop_rules.py`：新流程 `NEEDS_PLAN` 不是 `plan-review`，老模块仍是。
  再实现。验证：这三个测试文件。
- **Task 2**：`/map --json` 与接口 1.21。`test_map_view.py` 写无 Plan、有 Plan 两种情形的 `reviewApprovedBy.plan`、`codexRoute.plan` 与 `awaitingReview`；
  同一个用例里 Plan 带旧 `pending` 标记，断言 `review.plan == "pending"`、`reviewApprovedBy.plan == "auto"`、`codexRoute.plan == "auto"`、`awaitingReview` 不列它（R2-2）。先红后实现；
  `interface.json`、`check-interface.py`、`docs/commands.md`。验证：`test_map_view.py`、`check-interface.py`。
- **Task 3**：新流程的范围与三个入口。先写会红的用例：
  - `test_module_scope.py`：`flow_scope` 的四种状态（含边界写坏、normal 影响面为空）；`classify` 对新流程不认预先声明；`check` 命令对只有影响面、没有并行边界的模块能检查；
    `declared` 对新流程模块给出 `planApproved: true`、`approvedCommit: null`，老模块字段集合不变；`validate-declared` 报 `ignored`；
  - `test_review_marker.py`：merge=auto 的新流程模块只有影响面、没有并行边界时，最终验收的范围检查不拒绝；改到范围外仍拒绝；
  - `test_flow_v2.py`（git 夹具）：AC4（越界停下、补进影响面后不报、技术方案变 `revised`、预先声明不授权）、AC5（bug 无边界只记一行、有边界按它查）。
  再实现。验证：这三个测试文件、`test-phase-guard.sh`。
- **Task 4**：T4。先写会红的用例：
  - `test_important_requirement.py`：同样的 T3／T4 影响面，新流程模块判为重要需求、老模块不变；
  - `test_flow_v2.py`：不是重要需求的模块改 T4 文件停下；没有并行边界的 bug 改 T4 文件时同时出「越界未检查」和 T4 停下；已是重要需求、技术方案已由用户批准、改的正是影响面里的 T4 路径时**不**停下；
    用户同意后把路径补进影响面，模块转为重要需求、技术方案转为待用户批；风险路径清单读不了只记一行；
    需求文档未提交、改动列表取不到时出「未检查」一行、不当成没有改动（R2-3）。
  再实现。验证：这两个测试文件。
- **Task 5**：verify-artifacts（C5）。`test-verify-artifacts.sh` 加正反例：新流程 Plan 带标记警告、预先声明不起作用警告、新流程并行边界写坏失败、normal 无范围警告，老模块输出不变。
  验证：`test-verify-artifacts.sh`。
- **Task 6**：规则文字（C6，R1-10）。`workflow-checkpoints.md`「批准标记」一节加「新流程 Plan 自动批准」，写明：
  - 自动批准授权什么：改本仓库文件、跑测试与构建、本地提交、推送本分支与开 PR（Q2 A）；不授权合并（F3 由用户决定）、发布、以及「只在这几类情况停下问用户」里的其余操作；
  - 越界与 T4 停下后怎么放行：说明原因交用户；同意就补进技术方案影响面或并行边界，技术方案按 design-review 重新审或批，T4 路径使模块转为重要需求、由用户批；不同意就撤回改动。
  `node-rules.md`「Plan 交审」加「新流程模块的 Plan 不交审」，「中途 gate」加上面的放行步骤。`test_workflow_checkpoints.py` 逐条锁这些短语。验证：该测试文件、`test_stop_rules.py`。

## 检查点

- Checkpoint 1（report）：Task 1～4 完成后，本机三套检查全绿。变异各自让回归变红后还原，每个变异写明在哪两个入口看到红（R1-8、R2-4）：
  - `effective_review` 不再给新流程 Plan `auto`：阶段提示（`test_flow_v2`）与 `/map --json`（`test_map_view`）；
  - `classify` 对新流程照旧认预先声明：阶段提示（`test_flow_v2`）与 `check` 命令（`test_module_scope`）；
  - T4 检查去掉「不是重要需求」的条件：阶段提示（`test_flow_v2` 的「已是重要需求、改的是影响面里的 T4 路径不停下」，R1-9）与 `check` 命令（`test_module_scope` 的同一情形）。
  记进 todo，不停下。
- Checkpoint 2（gate）：全部任务完成后，本机三套检查与 `check-interface.py` 全绿。推送本分支、开 PR（Plan 批准即授权）；开 PR 后提议打开宿主 PR 监控，用户批准才开。
  然后交最终验收，同一条消息里问「验收通过、合并吗？」，证据含 PR 上 `CI required` 的结果（没跑完照实写，不自己等）；合并前核实 `CI required` 通过，没通过不合并；
  拟回告（发 autopr-design 核对 `reviewApprovedBy.plan=auto`、`codexRoute.plan=auto`、`declared.autoApproved`）在验收时给出原文。

## 会改哪些文件

- 新增：`tasks/plan-auto-approve/{plan,todo}.md`。
- 修改：`plugins/spec-guard/hooks/{module_stage.py,module_scope.py,review_mark.py,map_view.py,verify-artifacts.sh}`、`plugins/spec-guard/references/{workflow-checkpoints.md,node-rules.md}`、
  `plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`docs/commands.md`，以及 Spec 并行边界里列的九个测试文件。都在 Spec 的并行边界内。
- 新增依赖、锁文件改动：无。

## 风险

- **已有新流程模块的 Plan 会突然不再等批准**：这正是本模块的目的；老模块由 AC1 的回归锁住。已经在构建中的新流程模块，如果影响面写得不全，会第一次看到越界提示——这是有意的「照拦」，不是误报。
- **影响面里的路径写法不统一**：只认反引号里的路径，复用 design-review 的读法；目录靠基线或工作区判断，判断不了时按文件算（更严，宁可多拦）。
- **`important()` 读技术方案后，更多新流程需求被判为重要**：只对新流程模块多了「影响面列了 T3／T4 路径」这一条来源；老模块由新旧对照用例锁住。
- **`module_scope` 与 `module_stage` 互相导入**：沿用现有的「函数内延迟导入」写法，不调整模块结构。
- **`declared` 的输出多一个字段**：只加不改，老模块为 `false`；接口 1.21 写明。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 外部审查意见

<!-- spec-guard: codex-review round=1 blocking=11 sha256=33bd35226a2b -->

第 1 轮处理（2026-11-25）：
- R1-1～R1-10 采纳，改动见上面的「架构决定」「任务」「检查点」（各处标了 R1-n）。
- R1-11（CI 没跑完就问合并）不采纳：「最终验收的交审消息里就问合并，不等 CI 跑完」是用户已批准的 F3 规范 v1.7（merge-ask-no-wait，#491）。本 Plan 的做法是证据照实写 CI 进度，
  合并前核实 `CI required` 通过、没通过不合并，AC8 的证据在合并前补齐。已在 Checkpoint 2 写明「合并前核实」。
- 对 R1-8 的说明：verify-artifacts 现在不查构建中的改动（takeover-scope-check 也只在阶段提示里查）。Spec 假设 10 的「两边调同一个函数」按「判据只写一处」落实：
  构建中的越界与 T4 由阶段提示、`check` 命令、最终验收三处共用，verify-artifacts 用同一个 `flow_scope` 查范围本身。
<!-- spec-guard: codex-review round=2 blocking=4 sha256=48bdee479683 -->

第 2 轮处理（2026-11-25）：上一轮 8 条已解决；仍未解决 3 条，新意见 4 条。
- R2-1（`declared` 别加新字段）、R2-2（`review.plan` 保留原始标记并断言）、R2-3（拿不到改动列表时的处理）、R2-4（变异写明观察入口）采纳，见上文标注。R2-1 同时解决了上一轮 R1-5 的残留。
- R1-8（verify-artifacts 也要调共享判据）仍未解决：verify-artifacts 从来不查构建中的改动。这里按「判据只写一处」落实，并提议修订 Spec 假设 10 的文字，交用户与本 Plan 一起批。
- R1-11（CI 没跑完就问合并）仍不采纳，理由同第 1 轮：这是用户已批准的 F3 规范 v1.7。
- 两轮仍有阻断，按规则交用户批。注：第 2 轮轮次行记的是 `blocking=4`，只数了新发现，没算 3 条仍未解决的复查条目（Codex 轮次的计数口径缺口，design-review 只修了技术方案一侧）。
