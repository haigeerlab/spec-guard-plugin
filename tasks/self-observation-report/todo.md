# Todo: self-observation-report

- [x] Task 1：注入事件读取——Claude 附件与 Codex developer 消息，只取 spec-guard 段，跳过子代理／子线程，阶段与建议行，--since；登记 validate.sh — 10 例先红（模块不存在）后绿，3.9 通过；真实数据 Claude 2947 段（LEGACY_TRACKER_RETIRED 442、MAP_INVALID 114 与 Spec 实测一致），Codex 1623 段，无法解析 0；JSONL 读取需要行号，故只复用 parse_iso，逐行读取自写
- [x] Task 2：信号、指纹与输出——S1 重复未变、S2 诊断态、归一化指纹跨项目合并、--json、项目哈希与 --reveal、无法观测一节 — 21 例新增先红（19 缺函数、1 python3 文本未识别）后绿，共 31 例，3.9 通过；Spec 补 python3 故障文本与 S2 不进 S1；指纹单一来源检查拦下 hashlib 截断写法，改用 CRC-32 短 id 并同步 Spec
- [x] Checkpoint 1（gate）：真实数据验收——报告给用户看，S2 次数独立核对，默认输出无真实路径，牙齿检查 — 发现并修正两处判据（用户确认）：S1 比原文而非归一化文本（推进中的 BUILDING 曾被误报 908 次）；时间门槛由跨 2 个自然日改为首末间隔 ≥24 小时。14 天窗口最终 5 项：BUILDING 287、LEGACY_TRACKER_RETIRED 222、MAP_INVALID 114、SPECED 46、DONE 40。MAP_INVALID 独立 grep 114 一致；python3 故障注入 0（grep 到的 37 处均为工具输出）；229 个真实项目路径无一出现在文本或 JSON 输出；变异（去阈值、去脱敏、归一化比较、跨度 1 小时）均变红
- [ ] Task 3：维护者流程文档——docs/maintainer-workflow.md「自观测报告」一节
- [ ] Checkpoint 2（gate）：模块评审；Plan 获批即授权推送与开 PR，合并由用户进行
