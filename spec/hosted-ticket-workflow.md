# Spec: hosted-ticket-workflow

登记：Proposal `hosted-ticket-workflow` 已发布于 PR #124，并由 Issue #125 的
`proposal-stage:accepted` 标签接受。本模块按 Proposal 声明追加在
`audit-handoff` 后；此 Spec 展开其验收意图，不改变 Proposal 生命周期。

## 目标与假设

项目审查收束后的已确认缺陷，以及用户直接提出的缺陷，可按明确选择的目标进入
GitHub 或 GitLab 普通 Issue：查重、取得稳定身份、记录处理和验证，并在代码交付后
逐项核对收尾。Local 继续使用现有 Epiq `ticket` 入口。代码仓库的 Git remote、旧
`.agent/state.json` 和 Proposal Issue 都不能决定日常缺陷事项目标。

假设审查报告已有稳定的批次和发现编号。直接受理的缺陷在首次远端写入前取得稳定
请求编号。GitHub/GitLab 目标必须明确到主机、仓库或项目及可见性；一次批次的
选择沿用至该批次结束，后续改选不迁移已入账事项。

## 行为契约

### 目标与只读查重

1. 对每项已确认缺陷，先读本批次或本事项已选目标。未选目标、Local 账本归属
   未知、远端不可读或可见性未知时，报告“待入账”和需要补齐的事实，不猜测
   GitHub/GitLab，也不创建事项。仅要求审查的用户收到报告，不触发写入。
2. 按根因和稳定来源标记查询目标内开放及已关闭的普通 Issue。结果至少区分
   `found`、`absent`、`unknown`、`conflict`；分页不完整、认证失败或多个匹配
   不能当作 `absent`。GitHub PR 不算 Issue，GitLab 系统或私有 note 不算公开
   讨论证据。准确匹配时复用原事项，并读回 ID、URL 与当前状态。
3. 一批发现跨多个目标时拆成目标明确的子批次；同一发现不能因切换目标而被
   隐式写到两个 Tracker。Local 项目即使通过 GitHub PR 交付，也沿原 Local
   事项处理。

### 创建、恢复与讨论

1. 只有完整查重为 `absent` 才准备新 Issue。展示目标、可见性、标题、正文、
   影响、验收条件和脱敏后的稳定来源标记；对这次外部发布取得授权后才写入。
   不把 Local 私有编号、原始日志、内部路径或敏感证据自动复制到远端。
2. 写入前保留最小私有意图：目标、稳定请求编号和拟发布内容摘要。它只用于
   响应丢失后的对账，不存完整敏感正文，也不成为第二份事项账本。按来源与
   目标串行化受管写入；读回远端 ID、URL、标记和内容后才报告“已入账”。
   超时、服务端失败、标记冲突或读回不完整时报告 `unknown/conflict`，先按
   标记对账，不凭一次空查询自动重发。
3. 远端 Issue 是已入账事项的事实源。实质范围变化先以可读讨论留下决定，再
   依据平台当前事实处理正文；评论也须读回。审查报告或直接事项上下文只记录
   目标身份、状态与下一步。两个独立 clone 的外部并发不在绝对防重保证内。

### 修复与交付收尾

1. 修复复用 agent-skills 的诊断、TDD、增量实现和复审；既有 bug 不自动新建
   能力模块。PR/MR 创建时记录其覆盖的事项范围。合并后逐项读回合并提交、
   验证或验收证据以及 Issue 当前状态。
2. 合并不等于关闭。只有该事项全部范围已交付、验证通过且有关闭授权，才关闭
   并读回；部分交付、待部署、权限失败或结果未知保持未完成结论。平台自动
   关闭或人工改动以读回事实为准，不使用自动关闭关键字制造虚假完成。
3. 每个检查点报告已入账、待入账、处理中、待验证及待关闭数量；审查已结束后
   普通“继续”进入最近预告的事项或修复步骤，不重新开启无界审查。

## 项目结构与命令边界

- 在现有 `plugins/spec-guard/hooks/` 中实现窄范围的 GitHub/GitLab 普通 Issue
  读取与写入入口；只抽取与 Epiq 解耦的传输辅助，不调用 Local 移交发布器、
  旧 tracker bridge 或 Proposal 读取器。
- Claude 命令、Codex `ticket` skill 与共享审查检查点呈现相同的处理语义；
  不新增项目级 Tracker 配置、后台监听、双向同步、自动迁移或 phase 状态。
- 实施和验证以 `tasks/hosted-ticket-workflow/plan.md` 为准。聚焦测试使用
  假提供方和隔离项目；完整回归执行 `/bin/bash scripts/validate.sh`、
  `/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh` 和
  `/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh`。

## 验收与边界

- Local 路径保持原有行为；GitHub 与 GitLab 各完成查重、授权创建、读回、
  讨论、交付核对及关闭的正反场景，不需要 Epiq 运行时。
- 分页截断、403、重复标记、响应丢失、跨会话恢复、linked worktree 并发、
  部分合并和平台自动关闭均不虚报“已入账”或“已关闭”。
- 每个平台至少一次经精确目标与内容授权的受控真实往返；未获授权或目标
  不可用时明确记为“真实远端未验证”，不以模拟测试代替。
- 不修改 Proposal Issue、阶段标签或生命周期；不恢复旧 bridge。外部写入
  每次先展示目标和内容并取得授权，未知结果先对账。
