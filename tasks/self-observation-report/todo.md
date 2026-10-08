# Todo: self-observation-report

- [x] Task 1：注入事件读取——Claude 附件与 Codex developer 消息，只取 spec-guard 段，跳过子代理／子线程，阶段与建议行，--since；登记 validate.sh — 10 例先红（模块不存在）后绿，3.9 通过；真实数据 Claude 2947 段（LEGACY_TRACKER_RETIRED 442、MAP_INVALID 114 与 Spec 实测一致），Codex 1623 段，无法解析 0；JSONL 读取需要行号，故只复用 parse_iso，逐行读取自写
- [ ] Task 2：信号、指纹与输出——S1 重复未变、S2 诊断态、归一化指纹跨项目合并、--json、项目哈希与 --reveal、无法观测一节
- [ ] Checkpoint 1（gate）：真实数据验收——报告给用户看，S2 次数独立核对，默认输出无真实路径，牙齿检查
- [ ] Task 3：维护者流程文档——docs/maintainer-workflow.md「自观测报告」一节
- [ ] Checkpoint 2（gate）：模块评审；Plan 获批即授权推送与开 PR，合并由用户进行
