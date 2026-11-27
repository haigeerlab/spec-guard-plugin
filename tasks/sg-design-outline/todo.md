# Todo: sg-design-outline

- [x] Task 1：三种情况的判定与批次缓存
- [x] Task 2：全新四节判失败
- [x] Task 3：两条警告与阶段提示
- [x] Checkpoint 1（report）：完整档与变异
- [x] Task 4：骨架与规则文字
- [x] Task 5：版本与 CHANGELOG
- [x] 最终验收（gate）：推送、开 PR、验收并同时问合并

## 证据
- 技术方案（2026-11-27）：Codex 两轮（第 1 轮 3 条阻断，第 2 轮全部解决、5 条建议），用户「批准；单独发」。
- 留作后续（不在本模块做）：第 2 轮没有阻断时我按 `reviewer-reviewed` 记，阶段提示随后显示「待审」而不是「待用户批」——没阻断的复审轮次在 design=human 下应直接显示待用户批。
- Task 1（2026-11-27）：`module_stage` 加 `design_outline_case`（new／important／cross）与 `_cached_batches`（键为根目录、HEAD、能力图 mtime 与大小，失败不缓存）；`overall_design()` 把以 `<!-- spec-guard: overall-design` 开头却匹配不上的行判 `invalid`。`test_sg_design_outline.py` 新建（`OutlineCase` 5 例、`BatchCache` 1 例），对改动前实现 6 例全红，登记进 `scripts/validate.sh`；`test_sg_gate_flow`、`test_flow_v2`、`test_map_view` 照旧全过。
- Task 2（2026-11-27）：`DOC_SECTIONS` 加 `design-new`（技术选型、架构图、目录结构、数据模型）与 `design-interfaces`（模块接口）；`flow_doc_problems` 在 `design_outline_case` 的 `new` 为真时按六节加四节查，缺了照现有写法判失败。`doc-skeletons.md` 同时加上两种情况的章节表与重要需求的写法（`SkeletonTest` 要求每组章节都在骨架里，所以和 Task 4 的骨架部分一起做）。用例 `NewDesignSections` 2 例（改动前实现没有 `design-new`，用例在加载时就报错）、`Unchanged` 2 例。
- Task 3（2026-11-27）：`module_stage` 加 `design_outline_findings`（`alternatives` 带实际条数，`interfaces` 分缺失与为空）、`design_outline_problems`（只出警告）、`design_outline_line`（只在 `NEEDS_REGRESSION`，每条一行，事实带条数与种类进状态码），列表项只认不缩进、不在代码块里的 `-`、`*`、`+`、`1.`，只有注释的项不算；`verify-artifacts.sh` 接上 `design_outline_problems`。用例 `Alternatives` 3 例、`ModuleInterfaces` 2 例、`OutlineHint` 3 例，对改动前实现 8 例全红（1 失败 21 报错）；`test_flow_v2`、`test_sg_review_rules`、`test_stop_rules`、`test_map_view`、verify-artifacts 148 例照旧全过。
- Checkpoint 1（2026-11-27）：Task 1～3 的提交都走完整档且全绿。变异在临时副本里做（`mktemp -d` 固定前缀，跑完按前缀删除），10 个：new 不看路径、写坏的前缀行当作没有、条数门槛改成 1、认 `1)` 编号、只有注释的项算内容、提示不限阶段、事实不带条数、缓存不看 HEAD、全新不加四节、cross 不看同批人数——10 个全部变红；还原后 `test_sg_design_outline.py` 18 例全过。
- Task 4（2026-11-27）：`workflow-checkpoints.md`「技术方案审查」开头加「写什么」一段（三种情况、全新的判据、四节判失败、后两种只警告）；`node-rules.md`「技术方案交审」加一句（四节要点放进「实现方案」、写出比较了哪几种做法与接口要点，这一节 1026 字节）；`docs/workflow.md` 补一句（骨架在 Task 2 已改）。`test_workflow_checkpoints.py` 新增 `DesignOutlineRulesText` 3 例，对改动前的规则文件 16 处失败；原有断言不动，全部通过。
- Task 5（2026-11-27）：版本 0.99.0 → 0.100.0（两份 plugin.json、两份 README 的 `--ref`），CHANGELOG 写 `[0.100.0]`（含升级要补四节）；接口仍是 1.27。用例 `Release` 2 例；因为它读仓库自己的 CHANGELOG 与 README，按 validate 的要求把 `test_sg_design_outline.py` 从全套回归段移到 `DOC_REGRESSIONS`。
- 最终验收（2026-11-27）：R1～R9 按回归文档的命令逐条跑过全部通过（`test_sg_design_outline.py` 8 组、`test_workflow_checkpoints`、`SkeletonTest`、`check-interface.py`）；R11 三条最小验证在 Task 5 的完整档提交里全绿。R10 下游复核：autopilot-hub `origin/main` `cfe2f1d` 里没有技术方案章节名，也不调用 verify-artifacts 脚本；module-crew `origin/main` `d9d3cd4` 的 `module_crew/protocol.py:747` `_DESIGN_POINTS` 未变，不含新章节名。
- 越界与重新批准（2026-11-27）：用户第一次回「验收通过并合并」后，阶段提示的越界检查查出两份 `plugin.json` 不在影响面（影响面写的是「两份 `plugin.json`」简写）；我撤回「没有越界」的说法，停在中途 gate。用户「A：补进影响面」→ 改成完整路径 → Codex 第 3 轮复审无意见 → 用户「批准」。
  推送分支 `claude/sg-design-outline`，PR #528 已绑定，验收时 head 为 `b3c6a6be`；合并前验证没有结论（没有非作者执行），在验收消息里写明。用户回「验收通过并合并」。
