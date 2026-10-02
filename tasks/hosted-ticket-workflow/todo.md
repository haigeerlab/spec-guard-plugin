# hosted-ticket-workflow tasks

- [x] 两平台只读目标校验与完整查重，验证未知和冲突不触发创建。
- [x] 单条授权创建、稳定标记、读回与不确定写入的跨会话对账。
- [x] 评论留痕及 PR/MR 交付后逐项验证、关闭和读回。
- [x] Claude/Codex 入口、审查批次目标与剩余数量、使用文档。
- [ ] 假提供方和受控真实目标验证、Local/Proposal/退役 bridge 回归。

验证进度：假提供方、真实 GitHub 只读目标、完整 `scripts/validate.sh` 及退役 bridge
回归已通过。真实 GitHub/GitLab 写入、评论和关闭需指定受控目标与精确内容，尚未执行；
宿主实际加载新 skill 的行为也尚未观察到，不以源码测试冒充该证据。
