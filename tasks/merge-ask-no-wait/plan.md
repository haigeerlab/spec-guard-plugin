# Plan: merge-ask-no-wait

<!-- spec-guard: review approved -->

Spec：[spec/merge-ask-no-wait.md](../../spec/merge-ask-no-wait.md)（2026-11-25 批准，Q1 选 A）。Plan：Codex 两轮后仍有未解决项，交用户，2026-11-25 用户「Plan 批准」。

## 架构决定

- **共享规则新起一段**，紧接 merge-flow-f3 那一段（`workflow-checkpoints.md`「Plan 检查点分级」，「合并永远由用户在对话里决定：」那一行）之后，原句一字不动。
  新段在文件里写成**一个物理行**（和上面那段一样），下面的引用只是为了好读才折行：

  > 合并的时机与 CI（规范 v1.7）：最终验收的交审消息里就问合并，不等 CI 跑完、不等 PR 变 CLEAN，合成一问「验收通过、合并吗？」
  > （按钮「验收通过并合并」「只验收，先不合」；选后者之后照旧再问一次合并）；验收没过不问合并。开 PR 后，宿主有 PR 监控功能
  > 时提议打开，用户批准才开，宿主没有就跳过。会话不自己等 CI：不用后台 `--watch`、定时任务或唤醒、
  > 循环，也不反复查检查状态；要等时告诉用户「跑完叫我」并结束本轮。下次被叫醒或用户回来时，先核实已合并（PR 是 merged、
  > 主干指向合并提交）、记下合并提交再告诉用户；没合并就照实说状态。

  规则里不点名宿主的工具或开关（Spec 假设 3）；Claude 桌面版的 Auto-fix 只在 Spec 里作为例子。
  单独一段而不是接在原句后面，和两条现有回归的关系：
  - `test_no_remote_write_is_authorized_by_default` 从全文删掉「合并永远由用户在对话里决定：」到「任何 Plan 都不能代替用户这句话。」这一段再查禁用词；
    新段在这句之后，不会被删掉，仍要过禁用词检查，所以新段里不出现「自动合并」「默认推送」等禁用词。Task 1 跑这条用例确认仍绿。
  - `ORIGINALS` 只检查列出的三句原文在全文中逐字存在、且「approved」那句在其余两句之前；新段不改这三句，也不插在它们中间。Task 1 跑这一组确认仍绿。
- **最终验收停点**（`node-rules.md`「## 最终验收」）在「批了会怎样」那条之后加一条：
  「合并在这条交审消息里一起问（共享规则「合并的时机与 CI」）：问题是「验收通过、合并吗？」，按钮「验收通过并合并」「只验收，先不合」；不等 CI 跑完。」
- **发版流程**（`docs/release-process.md` 第 4 条）在「agent 核实已合并（第 5 条）再告诉用户合并提交。」之后加一句：
  「agent 不自己等 CI（不用 `--watch`、定时或循环），等用户叫或宿主通知。」长期授权原文不动。
- **回归**：
  - `test_workflow_checkpoints.py` 新增 `test_merge_timing_and_ci_waiting`：取「合并的时机与 CI（规范 v1.7）：」开头到行尾的整段（一个物理行），锁
    「最终验收的交审消息里就问合并」「不等 CI 跑完」「验收通过、合并吗？」「验收通过并合并」「只验收，先不合」「选后者之后照旧再问一次合并」「验收没过不问合并」「提议打开」「用户批准才开」
    「宿主没有就跳过」「`--watch`」「定时任务」「循环」「跑完叫我」「先核实已合并」「记下合并提交再告诉用户」；并断言这一段排在 merge-flow-f3 那一行之后。
  - `test_stop_rules.py` 在 `NodeRules` 里新增一例：`node_rules("final-gate")` 含「验收通过、合并吗？」「验收通过并合并」「只验收，先不合」「不等 CI 跑完」。

## 任务

- **Task 0**：提交本 Plan 与 todo。验证：`verify-and-commit` 快档。
- **Task 1**：先写两条回归、跑红，再改共享规则与 `node-rules.md` 跑绿；改 `docs/release-process.md` 第 4 条；CHANGELOG「未发布」加一条（并进 0.95.0，不升版本号）。
  验证：`python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`python3 -B plugins/spec-guard/hooks/test_stop_rules.py`；
  用一个最终 gate 的临时项目跑 `phase-guard.sh`，确认注入的停点规则里有新的一条；`verify-and-commit` 完整档。

## 会改哪些文件

- 新增：`tasks/merge-ask-no-wait/{plan,todo}.md`。
- 修改：`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/references/node-rules.md`、`docs/release-process.md`、
  `plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`plugins/spec-guard/hooks/test_stop_rules.py`、`CHANGELOG.md`。都在 Spec 的并行边界内。
- 新增依赖、锁文件改动：无。

## 风险

- **合成一问带两件事**：用户只想验收时要点第二个按钮；规则写明选后者之后照旧再问合并，不会被当成拒绝合并。
- **宿主 PR 监控的说法**：只在 Claude 桌面版上见过 Auto-fix；规则只写「宿主有 PR 监控功能时」与「没有就跳过」，不点名任何宿主的功能或开关。

## 检查点

- Checkpoint 1（report）：本机三套检查全绿。变异（AC4）：用一个临时脚本逐个处理两条新用例锁的每个短语——在草稿副本里删掉它、跑对应用例、
  确认变红、还原；全部短语都要变红，逐条结果记进 todo，不停下。
- Checkpoint 2（gate）：Plan 获批即授权推送本分支、开 PR（不授权其他远端写入）。开 PR 后，宿主有 PR 监控时提议打开，用户批准才开（Spec「先问再做」）。
  然后交最终验收，按新规则在同一条消息里问「验收通过、合并吗？」；验收证据含本机三套检查（`validate.sh`、phase-guard、verify-artifacts 各自的结果）
  和 PR 上 `CI required` 的结果（AC5），没跑完就照实写，不自己等；之后被用户叫或收到宿主通知时补记 `CI required` 的结论（不论合没合并）。
  用户说合并后按 F3 执行，不自己等 CI，下次被叫醒时核实已合并、记下合并提交；AC6 的过程记进 todo。
  本 Plan 不授权任何回告或账本操作：回告 ecosystem-lead、关闭账本 EVQX96F 都不在本检查点里，验收时作为拟回告与收尾单独交用户决定。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 外部审查意见

<!-- spec-guard: codex-review round=1 blocking=5 sha256=33ff8469a3ee -->
<!-- spec-guard: codex-review round=2 blocking=0 sha256=bd7852e6a199 -->
