# hosted-ticket-workflow tasks

- [x] 两平台只读目标校验与完整查重，验证未知和冲突不触发创建。
- [x] 单条授权创建、稳定标记、读回与不确定写入的跨会话对账。
- [x] 评论留痕及 PR/MR 交付后逐项验证、关闭和读回。
- [x] Claude/Codex 入口、审查批次目标与剩余数量、使用文档。
- [x] 假提供方和受控真实目标验证、Local/Proposal/退役 bridge 回归。

验证进度：假提供方、真实 GitHub 与 GitLab 只读目标、完整 `scripts/validate.sh`、
阶段与产物回归及退役 bridge 回归已通过；Claude 插件源码校验通过。GitLab 只读
核对覆盖公开项目的有限元数据、现行 `work_items` Issue URL 和小型项目的完整扫描。
GitLab 交付提交回退的引用接口也已用公开项目的 main 当前及历史提交只读核对。
真实 GitHub 私有测试目标已完成普通 Issue 创建、两次评论、合成 PR 合并、关闭及
独立读回；该仓库无 CI，验收仅证明受控手工链路。私有 GitLab 项目已有同根因测试
Issue 和已合并 MR：当前工作区源码只读找回 Issue 并识别为已关闭，
且独立读回合并提交、成功的 main 流水线及证据文件；因此没有重复创建事项。
这不等于当前工作区源码重新执行了 GitLab 写入路径。2026-10-03 在隔离 Codex
配置和临时消费者项目中，从当前工作区本地 marketplace 安装候选插件；安装副本的
`hosted-ticket-workflow/SKILL.md` 与工作区逐字一致。真实 `codex exec` 的机器事件
显示宿主读取了该完整 skill，并正确识别第一个只读脚本及 Local/Proposal 边界。
Claude Code 在默认沙箱内尝试工作区 `--plugin-dir` 时返回 `Not logged in`；后续
在沙箱外确认 CLI 已登录，并从同一候选源码读取了完整 Skill。发布 v0.38.1 后，
已安装 Claude 插件在合成临时项目的 `UserPromptSubmit` 机器事件中注入 `MAP_ONLY`。
这证明安装版阶段 hook 执行，不等于真实事项回复或 GitLab 写入路径已验证。
