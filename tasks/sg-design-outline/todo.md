# Todo: sg-design-outline

- [x] Task 1：三种情况的判定与批次缓存
- [x] Task 2：全新四节判失败
- [x] Task 3：两条警告与阶段提示
- [ ] Checkpoint 1（report）：完整档与变异
- [ ] Task 4：骨架与规则文字
- [ ] Task 5：版本与 CHANGELOG
- [ ] 最终验收（gate）：推送、开 PR、验收并同时问合并

## 证据
- 技术方案（2026-11-27）：Codex 两轮（第 1 轮 3 条阻断，第 2 轮全部解决、5 条建议），用户「批准；单独发」。
- 留作后续（不在本模块做）：第 2 轮没有阻断时我按 `reviewer-reviewed` 记，阶段提示随后显示「待审」而不是「待用户批」——没阻断的复审轮次在 design=human 下应直接显示待用户批。
- Task 1（2026-11-27）：`module_stage` 加 `design_outline_case`（new／important／cross）与 `_cached_batches`（键为根目录、HEAD、能力图 mtime 与大小，失败不缓存）；`overall_design()` 把以 `<!-- spec-guard: overall-design` 开头却匹配不上的行判 `invalid`。`test_sg_design_outline.py` 新建（`OutlineCase` 5 例、`BatchCache` 1 例），对改动前实现 6 例全红，登记进 `scripts/validate.sh`；`test_sg_gate_flow`、`test_flow_v2`、`test_map_view` 照旧全过。
- Task 2（2026-11-27）：`DOC_SECTIONS` 加 `design-new`（技术选型、架构图、目录结构、数据模型）与 `design-interfaces`（模块接口）；`flow_doc_problems` 在 `design_outline_case` 的 `new` 为真时按六节加四节查，缺了照现有写法判失败。`doc-skeletons.md` 同时加上两种情况的章节表与重要需求的写法（`SkeletonTest` 要求每组章节都在骨架里，所以和 Task 4 的骨架部分一起做）。用例 `NewDesignSections` 2 例（改动前实现没有 `design-new`，用例在加载时就报错）、`Unchanged` 2 例。
- Task 3（2026-11-27）：`module_stage` 加 `design_outline_findings`（`alternatives` 带实际条数，`interfaces` 分缺失与为空）、`design_outline_problems`（只出警告）、`design_outline_line`（只在 `NEEDS_REGRESSION`，每条一行，事实带条数与种类进状态码），列表项只认不缩进、不在代码块里的 `-`、`*`、`+`、`1.`，只有注释的项不算；`verify-artifacts.sh` 接上 `design_outline_problems`。用例 `Alternatives` 3 例、`ModuleInterfaces` 2 例、`OutlineHint` 3 例，对改动前实现 8 例全红（1 失败 21 报错）；`test_flow_v2`、`test_sg_review_rules`、`test_stop_rules`、`test_map_view`、verify-artifacts 148 例照旧全过。
