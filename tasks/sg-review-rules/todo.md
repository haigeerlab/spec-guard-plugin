# Todo: sg-review-rules

- [x] Task 1：新流程重要需求只看风险路径
- [ ] Task 2：技术方案送审的三种高风险
- [ ] Task 3：谁批技术方案与 /map 字段
- [ ] Task 4：技术方案的宿主子会话与没有审查者
- [ ] Task 5：需求文档的三种审查记录
- [ ] Task 6：硬拦、确认停点提示与改动差异
- [ ] Checkpoint 1（report）：完整档与变异
- [ ] Task 7：规则文字
- [ ] Task 8：接口 1.27
- [ ] 最终验收（gate）：推送、开 PR、验收并同时问合并

## 证据
- 技术方案批准后回告 ecosystem-lead（2026-11-27）：消息 #23440（线程 `autopilot-m5-7`）；lead 回 #23443，hub `flow_check` 需求转 autopr-design（线程 `autopilot-m5-hub-req`），module-crew `_design` 需求转 mc-coord（线程 `autopilot-m5-mc-req`）。
- Task 1（2026-11-27）：`important()` 的 `multi-module`、`cross-module` 只对老流程执行。`test_sg_review_rules.py` 新建（`ImportantV2` 3 例，实现前 2 例红），登记进 `scripts/validate.sh`。`test_flow_v2.py` 7 处、`test_map_view.py` 1 处钉旧规则的断言改钉新规则（跨模块、批量插入、重叠不再抬升新流程档位；需要抬升的用例改用风险路径 `src/secret/`），不删断言；`test_important_requirement.py` 照旧全过。
