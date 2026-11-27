# Todo: sg-design-outline

- [x] Task 1：三种情况的判定与批次缓存
- [x] Task 2：全新四节判失败
- [ ] Task 3：两条警告与阶段提示
- [ ] Checkpoint 1（report）：完整档与变异
- [ ] Task 4：骨架与规则文字
- [ ] Task 5：版本与 CHANGELOG
- [ ] 最终验收（gate）：推送、开 PR、验收并同时问合并

## 证据
- 技术方案（2026-11-27）：Codex 两轮（第 1 轮 3 条阻断，第 2 轮全部解决、5 条建议），用户「批准；单独发」。
- 留作后续（不在本模块做）：第 2 轮没有阻断时我按 `reviewer-reviewed` 记，阶段提示随后显示「待审」而不是「待用户批」——没阻断的复审轮次在 design=human 下应直接显示待用户批。
- Task 1（2026-11-27）：`module_stage` 加 `design_outline_case`（new／important／cross）与 `_cached_batches`（键为根目录、HEAD、能力图 mtime 与大小，失败不缓存）；`overall_design()` 把以 `<!-- spec-guard: overall-design` 开头却匹配不上的行判 `invalid`。`test_sg_design_outline.py` 新建（`OutlineCase` 5 例、`BatchCache` 1 例），对改动前实现 6 例全红，登记进 `scripts/validate.sh`；`test_sg_gate_flow`、`test_flow_v2`、`test_map_view` 照旧全过。
- Task 2（2026-11-27）：`DOC_SECTIONS` 加 `design-new`（技术选型、架构图、目录结构、数据模型）与 `design-interfaces`（模块接口）；`flow_doc_problems` 在 `design_outline_case` 的 `new` 为真时按六节加四节查，缺了照现有写法判失败。`doc-skeletons.md` 同时加上两种情况的章节表与重要需求的写法（`SkeletonTest` 要求每组章节都在骨架里，所以和 Task 4 的骨架部分一起做）。用例 `NewDesignSections` 2 例（对改动前实现红）、`Unchanged` 2 例。
