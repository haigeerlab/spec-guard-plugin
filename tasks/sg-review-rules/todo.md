# Todo: sg-review-rules

- [x] Task 1：新流程重要需求只看风险路径
- [x] Task 2：技术方案送审的三种高风险
- [x] Task 3：谁批技术方案与 /map 字段
- [x] Task 4：技术方案的宿主子会话与没有审查者
- [ ] Task 5：需求文档的三种审查记录
- [ ] Task 6：硬拦、确认停点提示与改动差异
- [ ] Checkpoint 1（report）：完整档与变异
- [ ] Task 7：规则文字
- [ ] Task 8：接口 1.27
- [ ] 最终验收（gate）：推送、开 PR、验收并同时问合并

## 证据
- 技术方案批准后回告 ecosystem-lead（2026-11-27）：消息 #23440（线程 `autopilot-m5-7`）；lead 回 #23443，hub `flow_check` 需求转 autopr-design（线程 `autopilot-m5-hub-req`），module-crew `_design` 需求转 mc-coord（线程 `autopilot-m5-mc-req`）。
- Task 1（2026-11-27）：`important()` 的 `multi-module`、`cross-module` 只对老流程执行。`test_sg_review_rules.py` 新建（`ImportantV2` 3 例，实现前 2 例红），登记进 `scripts/validate.sh`。`test_flow_v2.py` 7 处、`test_map_view.py` 1 处钉旧规则的断言改钉新规则（跨模块、批量插入、重叠不再抬升新流程档位；需要抬升的用例改用风险路径 `src/secret/`），不删断言；`test_important_requirement.py` 照旧全过。
- Task 2 与 Task 3（2026-11-27，合成一次提交：风险路径同时把需求抬成重要需求，旧 `design_approver` 又把重要需求交用户，两件分开改用例无法单独变绿）：`design_requirement()` 改为 `risk-path`、`irreversible`、`new-dependency`、`configured`，返回 `reasons`、`riskList`；新函数 `interface_has_content`、`is_dependency_file`；删掉 `important → user`、`old-files`、`impact-unknown`；技术方案阶段在没有风险清单时加一行「T4 路径：没有可读的风险路径清单，`risk-path` 未检查」；提示里的送审理由改成新文字，去掉已失效的「重要需求」分支。`design_approver()` 只看档位；`designForcedBy` 恒为 `null`；`DESIGN_APPROVAL_FIELDS` 加 `reason`、`reasons`、`riskList`，`DESIGN_ROUND_FIELDS` 加 `reportSha256`。
  用例：`DesignRequirement` 8 例、`RiskListHint` 2 例、`DesignApprover` 2 例，对改动前实现全部红（前两组 10 例 10 失败 5 报错；`DesignApprover` 2 例 2 失败）。`test_flow_v2.py` 改钉新规则 16 处（旧送审理由、重要需求一律交用户、`designForcedBy: important`；需要送审的夹具改用风险路径清单 `src/a/old.py` 或接口改动触发），`test_map_view.py` 3 处（新字段、`designForcedBy`）、`test_stop_rules.py` 1 处、`test-phase-guard.sh` 1 处（影响面没写路径改为接口改动触发）、`test-verify-artifacts.sh` 1 处（重要需求跟档位走，另加 design=reviewer 不警告 1 例），不删断言。verify-artifacts 的「只有第二审查者的放行」警告改为只看档位。`interface.json` 先写 `designApproval` 新字段与新判定的说明（版本号在 Task 8 升）。
- Task 4（2026-11-27）：`DESIGN_ROUND` 的 `report=` 接受 `none`，新函数 `design_round_match` 只在 `vendor=host|none` 时认 `none`（其余算写坏）；`design_round_records` 把 `none` 解析成 `report: None`。`review_mark.py` 加 `--state host-reviewed --blocking N`（0 时同时写 reviewer-approved 标记）、`--state no-reviewer`（状态 `unreviewed`），两者只认 `--target design`（需求文档在 Task 5 接上），沿用两轮上限与 criteria 一致检查；`--target design` 的档位检查改用 `effective_tier`；去掉「重要需求」单独的提示；轮次行的文件摘要用 `module_stage._text_digest`（唯一指纹实现），不在 review_mark 里另算。用例 `DesignHostRound` 6 例、`ElevatedTier` 2 例，对改动前实现 8 例 6 失败；`test_review_marker.py` 1 处钉旧规则的断言改钉新规则。
