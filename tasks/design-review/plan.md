# Plan: design-review

<!-- spec-guard: review approved -->

Spec：[spec/design-review.md](../../spec/design-review.md)（2026-11-25 批准，Q1 A、Q2 A；写 Plan 时补了停点种类与两个测试文件的边界）。Plan 与修订后的 Spec：2026-11-25 用户「Plan 和 Spec 修订都批准」（预先声明全为无本应交 Codex，因同时修订 Spec 交用户一并批）。

## 架构决定

- **审查报告的读法放在 `review_mark.py`**，不改 `codex_review.py`（它只认 codex 后端，Spec、Plan 的 Codex 轮次继续用它）。新函数 `inspect_design(report, root, relative)`：
  - 认 delegate 报告：有结论；`reviewer: {vendor, backend, same_vendor, selection}`；`criteria` 为 `design-v1`；报告审的路径含 `tasks/<id>/design.md`；
  - 阻断数 = `recheck.items` 中 `status == "unresolved"` 的条数 + `findings` 中 `severity != "suggestion"` 的条数；
  - `selection == "none"` → 返回 `unreviewed`，不当报告无效；
  - 返回 `{status, blocking, suggestions, sha256（完整 64 位）, vendor, sameVendor, criteria}`。
- **`review_mark.py --target design`**：只用于新流程 `normal`／`important` 模块的 `tasks/<id>/design.md`；状态 `pending`／`approved`（用户）／`reviewer-reviewed`／`reviewer-approved`。
  - 轮次行 `<!-- spec-guard: design-review round=<n> blocking=<k> sha256=<12 位> vendor=<v> same-vendor=<true|false> criteria=<c> -->`，与 Codex 轮次行分开解析；
  - `reviewer-approved` 要求本轮阻断为 0；两轮都有阻断后拒绝第三轮，提示交用户；两轮 `criteria` 不同 → 拒绝；
  - `unreviewed` 报告记一行 `blocking=0 vendor=none`，状态仍为 `pending`（交用户批，Q1 A）；
  - 批准标记与指纹沿用 `spec-digest.py`（同 Spec、Plan），`approved` 只在用户明确批准后写（预览／确认两步不变）。
- **`module_stage.py`**：
  - `design_requirement(root, module)` → `important`／`required`（原因 `old-files`／`cross-module`）／`configured`／`none`。
    「已有文件」：取技术方案「影响面」一节里反引号括起的路径，在开工基线（`spec/<id>.md` 首次提交的父提交；读不到时用 `HEAD`）里 `git cat-file -e` 存在即算；
    「跨模块」复用 `important()` 里那段并行边界判定（抽成函数共用，不改判定）。
  - `design_approval(root, module)` → Spec 假设 8 的对象（老模块、bug、small 为 `None`）。
  - 阶段值不变。技术方案存在但没放行时，阶段提示的「批准」一行写「技术方案待审（第二审查者）」或「技术方案待你批」，下一步给出审查命令（`--author-host` 由宿主决定：
    Claude Code 写 `claude-code`，Codex 写 `codex`，沿用现有判断宿主的办法）或交审要求，并提示先不写回归文档。
  - `stop_node` 加 `design-review`：要用户批时停在这里；`NODE_TITLES` 加「技术方案交审」。
- **`map_view.py`**：每个模块加 `designApproval`（取 `design_approval`），文件读不了时同其他字段整体失败（退出 4）。
- **`project_config.py`**：`designReview` 取值 `on`／`off`，默认 `off`，不注入阶段提示；不合法时只这个键失效。
- **verify-artifacts.sh**：调 `module_stage.py` 取技术方案的标记与轮次检查结果（不在 shell 里重写判据）：标记或轮次行写坏、两轮 `criteria` 不同 → 失败；
  重要需求只有 `reviewer-approved` → 警告。

## 任务

- **Task 0**：提交本 Plan 与 todo，以及 Spec 的边界修订。验证：`verify-and-commit` 快档。
- **Task 1**：`designReview` 配置键。先在 `test_project_config.py` 写正反例跑红，再改 `project_config.py`、`commands/config.md`。验证：该测试文件。
- **Task 2**：`inspect_design` 与 `review_mark --target design`。先在 `test_review_marker.py` 写用例跑红：只有 `unresolved` 复查条目时阻断数不为 0（AC5）、`selection=none`、
  两轮上限、`criteria` 不一致、`reviewer-approved` 要阻断为 0；再实现。验证：`test_review_marker.py`。
- **Task 3**：`design_requirement`、`design_approval`、阶段提示与停点。先在 `test_flow_v2.py`、`test_stop_rules.py` 写 AC2（五种情形加只列新文件）、AC3、AC4、AC6～AC8 跑红，
  再实现；`test-phase-guard.sh` 加阶段提示的正反例（老模块与 bug、small 输出不变）。验证：这三个测试。
- **Task 4**：`/map --json` 的 `designApproval`、`interface.json` 1.20、`check-interface.py`、`docs/commands.md`。先在 `test_map_view.py` 写字段用例并改字段集合，跑红再实现。
  验证：`test_map_view.py`、`check-interface.py`。
- **Task 5**：verify-artifacts 的检查（假设 11），`test-verify-artifacts.sh` 加正反例。验证：`test-verify-artifacts.sh`。
- **Task 6**：规则文字：`workflow-checkpoints.md` 加「技术方案审查」一小节、`node-rules.md` 加「## 技术方案交审」；`test_workflow_checkpoints.py` 锁要点短语，
  `test_stop_rules.py` 的章节列表加这一节。验证：两个测试文件。

## 会改哪些文件

- 新增：`tasks/design-review/{plan,todo}.md`。
- 修改：`plugins/spec-guard/hooks/{module_stage.py,review_mark.py,map_view.py,project_config.py,verify-artifacts.sh}`、`plugins/spec-guard/commands/config.md`、
  `plugins/spec-guard/references/{workflow-checkpoints.md,node-rules.md}`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`docs/commands.md`，
  以及测试 `test_flow_v2.py`、`test_map_view.py`、`test_review_marker.py`、`test_project_config.py`、`test-phase-guard.sh`、`test-verify-artifacts.sh`、`test_stop_rules.py`、`test_workflow_checkpoints.py`。
  都在（修订后的）Spec 并行边界内。
- 新增依赖、锁文件改动：无。

## 风险

- **delegate 报告的真实形状**：本 Plan 按 #22369、#22372 的字段写，没拿到过一份 `--profile design` 的真报告。Task 2 先用 `/delegate:review --dry-run` 和 delegate 的回归样例核对字段名；
  对不上就停下，按「先问再做」问 delegate-owner，不自己猜。
- **「已有文件」的判定**：影响面里的路径写法不统一（相对路径、目录、带行号）。只认反引号里的路径，去掉 `:行号` 后缀；目录按其中是否已有文件判；写不出路径时按「必审」（宁可多审，Q5）。
- **阶段提示变长**：只在新流程模块的技术方案待审或待批时多一行；老模块输出由 AC1 的回归锁住。
- **共享判据两边一致**：verify-artifacts 调同一个 Python 函数，不复制判据（项目不变量）。

## 检查点

- Checkpoint 1（report）：Task 1～3 完成后，本机三套检查全绿；变异：把阻断数改回只数 `findings`、去掉「影响面列已有文件」的判定，各自让回归变红后还原。记进 todo，不停下。
- Checkpoint 2（gate）：全部任务完成后，本机三套检查与 `check-interface.py` 全绿。Plan 获批即授权推送本分支、开 PR。开 PR 后宿主有 PR 监控时提议打开，用户批准才开。
  然后交最终验收，同一条消息里问「验收通过、合并吗？」，证据含 PR 上 `CI required` 的结果（没跑完照实写，不自己等）；
  拟回告（发 autopr-design 核对 `designApproval` 取值、发 delegate-owner 核对轮次行与阻断数口径）在验收时给出原文，由用户批准验收时同意。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无
