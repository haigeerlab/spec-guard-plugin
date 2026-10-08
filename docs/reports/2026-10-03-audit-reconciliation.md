# 项目级审查发现对账（2026-10-03）

## 范围与裁决

- 原审查基准：`a33b8f9`；本次对账基准：`e79ee81`（PR #140 合并后的远端 `main`）。
- 原审查按 16 个用户能力域检查入口、实现、测试与文档；本文件只对其中有行动或验收缺口的发现收口，不把 33 个模块数当作 33 项已验收能力。
- `已修源码` 表示目标改动已进入 `main`，不自动表示新版已安装或真实宿主已验收；`未验证` 不等于功能失败。
- 本轮没有创建 tag、GitHub Release 或更新正式安装副本。下列临时消费者测试只使用合成数据。

## 发现项状态

| 编号 | 原发现与优先级 | 当前裁决及证据 | 尚需动作 |
| --- | --- | --- | --- |
| A01 | 有 Plan 无 `todo.md` 被计为 `DONE`，原审查 P1 | **按明确设计保留。** [plan-without-todo Spec](../../spec/plan-without-todo.md)记录用户决定：旧远端 tracker 项目不能因缺本地 Todo 被改判未完成；本地模式对 active module 提醒，产物校验汇总警告。[阶段判据](../../plugins/spec-guard/hooks/module_stage.py)仍按此实现。原审查把 13 个历史模块直接当作新模式缺陷，范围过宽。 | 新模块规划仍必须生成本地 Todo；若将来改变完成判据，须单独评审兼容规则和 Spec。 |
| A02 | 托管普通 Issue 缺真实双平台往返，原审查 P1 | **受控往返已有真实证据；当前源码验证强度 MODERATE。** GitHub 私有合成目标已完成创建、评论、PR 合并、关闭和读回。GitLab 私有合成事项于 2026-10-02 创建并关闭，期间合成 MR 合并、对应流水线成功；本轮重新读回这些远端状态。创建与关闭均晚于 `31f55b1`，而从该提交到 `e79ee81`，创建实现及 GitLab 适配器未变，关闭实现只增添 `verifiedFact: remote-issue-closed` 返回字段。2026-10-03 的当前源码评论发布读回为 `verified`，重试预览为 `found`；全部 5 条 notes 中标记恰好出现一次。[模块记录](../../tasks/hosted-ticket-workflow/todo.md)中的较早只读结论是此前时点的证据。 | 没有在 `e79ee81` 再次执行 GitLab 创建或关闭写入，故不称为该提交的全新端到端验收；现有同根因合成事项不应为重复验收而重建。若后续改动创建或关闭路径，再按改动范围安排受控写入验收。 |
| A03 | Claude 拆除入口未默认预览，原审查 P2 | **已修源码。** [PR #134](https://github.com/haigeerlab/spec-guard-plugin/pull/134) 要求先运行 `--dry-run`、展示预览，预览失败即停；[现行入口](../../plugins/spec-guard/commands/teardown-convention.md)与回归已更新。 | 真正删除消费者受管块仍须看过预览后的单次确认；命令文字回归不能单独证明所有宿主回复。 |
| A04 | 产物校验二次汇总失败可能显示零警告，原审查 P2 | **已修源码。** [PR #134](https://github.com/haigeerlab/spec-guard-plugin/pull/134) 使辅助脚本失败时输出“未验证”；[失败注入回归](../../plugins/spec-guard/hooks/test-verify-artifacts.sh)覆盖目标分支，PR #140 合并树上的完整校验与聚焦回归均通过。 | 若待发布源码树再变化，重新执行对应验证。 |
| A05 | 托管评论预览可过期、关闭的 `verified` 易被误读为 CI 通过，原审查 P2 | **已修源码。** [PR #131](https://github.com/haigeerlab/spec-guard-plugin/pull/131) 将评论预览绑定 Issue 范围并把关闭事实限定为远端已关闭；[现行 skill](../../plugins/spec-guard/skills/hosted-ticket-workflow/SKILL.md)要求人工核对交付和验证事实。当前源码的 GitLab 评论发布与重试查重已按 A02 实测。 | 评论读回不代表 CI 或代码交付通过；创建、关闭验收边界仍按 A02 单列。 |
| A06 | Ubuntu CI 不能代表每次 macOS Bash 3.2 验收，原审查 P2 | **PR #140 合并树已在 macOS 验证。** [CI](../../.github/workflows/ci.yml)明确只持续运行 Ubuntu；[维护流程](../maintainer-workflow.md)要求 macOS `/bin/bash`。PR #140 合并提交 `e79ee81` 与本地测试 HEAD 的树哈希均为 `680105f`；该树的三条 macOS 校验均退出 0，见下节。 | 本报告合并后最终待发布提交会变化，发布前仍须复核其 macOS 校验；不能把 Ubuntu CI 说成 macOS CI。 |
| A07 | 一次性维护工作进入能力图，增加模块状态与解释成本，原审查 P2 | **设计债已设准入边界。** [工作流](../workflow.md)规定局部 bug 不必新建能力模块；已发布图和历史保留，避免破坏 Proposal 基线。 | 新增模块时执行“独立用户能力”评审；不为清理统计数字批量删除旧模块。 |
| A08 | 历史导入底层命令无日常入口，原审查 P3 | **按用户决定保留内部。** [能力历史 Spec](../../spec/capability-history.md)与[维护流程](../maintainer-workflow.md)说明 `import --confirm` 只供维护者处理已退役证据；用户入口只给只读预览。 | 实际导入旧证据仍需逐次确认，不因工具存在自动执行。 |
| A09 | 早期模块 Spec 单读时可能误导，原审查 P3 | **文档修订完成。** [module-insert](../../spec/module-insert.md)与[proposal-promotion-proof](../../spec/proposal-promotion-proof.md) 顶部新增现行修订指针，保留原始决策文字；四个目标文件已逐一确认存在。 | 本轮仓库完整校验已通过；后续若修订这些契约，继续保留历史与现行边界。 |
| A10 | XATS/native 双传输及 XATS 依赖成本，原审查 P2 | **有意过渡，非本轮删除项。** [日落决定](../decisions/2026-09-28-xats-sunset.md)规定 native 转正门槛、一个 minor 的 XATS 退出节奏与反向出口；[协作 Spec](../retirements/collaboration-messaging/spec.md)明示 XATS 依赖未锁定的剩余风险。 | 门槛达到后走独立 Proposal；不能凭一次宿主验收提前退役默认传输。 |
| A11 | 项目审查交接主要靠静态指令测试，原审查 P2 | **双宿主合成多轮验收，验证强度 MODERATE。** Claude Code 与 Codex 均实际读取[共享检查点](../../plugins/spec-guard/references/workflow-checkpoints.md)，首轮覆盖预定 2/2 模块并冻结发现；第二轮仅发送“继续”后均未重扫或写入。Codex 沿预告只读核对 Local 账本；Claude 因首轮留下多个待选步骤且原授权仅限只读，停在范围选择。[PR #140](https://github.com/haigeerlab/spec-guard-plugin/pull/140) 已合并且 Ubuntu CI 成功；具体运行证据见下节。 | 本次只覆盖合成项目的审查收束和下一步边界；不声称所有交接场景或尚未安装的 v0.38.3 整包通过。规则与入口后续变动时须复测。 |
| A12 | Local 事项回复可回显完整内部 ID，后续宿主验收发现 | **已修源码、未发布。** [PR #137](https://github.com/haigeerlab/spec-guard-plugin/pull/137) 收紧 Claude 命令和共用 skill；隔离合成 Claude Code MCP 试验中目标读取工具实际执行，候选回复含标题与短编号、未回显完整 ID。 | 统一发布并更新安装副本后，再核对真实账本上的 Claude 回复；事项保持开放。 |
| A13 | Local 账本与归档恢复的可选真实运行时验收未在常规 `validate.sh` 中执行 | **本轮已实测。** 用固定 Epiq 1.11.0 运行时，在隔离临时仓库执行 `test_local_ledger_acceptance.py`（`state: passed`）和 `test_local_ticket_restore_acceptance.py`（1 项通过），均退出 0；工作仓库状态未被测试改动。 | 此证据仅覆盖临时合成项目，真实用户数据迁移仍需目标与授权。 |

## 发布停点

PR #140 已合并；两个 Manifest 在 `main` 上为 `0.38.3`，但没有 `v0.38.3` tag 或 Release。PR #140 合并树已通过本轮 macOS 校验；统一发布仍须单独执行，发布前复核最终提交，发布后对 A12 做正式安装版的真实账本回复验收。

## 本轮验证

GitLab 补充验收（2026-10-03，限已授权的私有合成事项）：

- 凭据恢复后，当前源码的 Issue 查重返回 `absent` 和 `rootCauseReviewRequired: true`；根因核对发现已有同用途的已关闭合成事项，因此没有新建重复 Issue。
- 当前源码的 `comment-preview` 生成预览；在用户对确切正文单独授权后，`comment-publish --confirm` 对同一预览返回 `verified`。随后 `comment-preview` 返回 `found`；独立 API 读回确认该评论标记恰好出现一次，事项仍为 `closed`。这证明本次评论的作用域和重试查重路径执行过，不证明创建或关闭写入路径已由当前源码重跑。
- 已有合成 Issue 的创建与关闭事件均晚于 `31f55b1`；合成 MR 的 `merged` 状态、合并提交及对应 pipeline 的 `success` 本轮再次独立读回。源码比较确认，自该受控往返前的提交到 PR #140 合并树，创建实现与 GitLab 适配器未变；关闭实现只新增读回成功时的事实字段。当前源码的 `close-preview` 返回 `already-closed`。本轮没有新建 Issue、分支或 MR，没有再次合并或关闭，也没有删除项目内容。
- 当前源码的四组托管事项本地测试共 39 项通过，覆盖读、写、动作与入口；它们不能替代真实创建和关闭的当前源码验收。

A11 双宿主合成多轮验收（2026-10-03）：

- 在隔离临时 Git 项目中建立两模块夹具：README 与模块 Spec 要求 `used < limit`，实现却为 `used <= limit`，现有测试仅覆盖低于限额；另一模块为正常标签格式。两宿主的首轮提示均限定只读审查这两个模块，第二轮仅发送“继续”。两次运行前后夹具 Git 状态均干净。
- Claude Code 2.1.288 在实际会话中读取 `spec-guard-ops/SKILL.md` 与 `workflow-checkpoints.md`，首轮报告覆盖 2/2、稳定发现、未验证项及下一检查点；第二轮没有重扫、建单或改文件，因首轮给出多个后续选项且用户只授权只读审查，保留待选范围。正常模式试验明确允许只读访问插件规则目录；一次因权限无法读取规则的尝试不计入验收。
- Codex CLI 0.154.0 在实际会话中读取相同 skill 与规则，首轮报告覆盖 2/2；直接边界断言失败、原有两个测试函数直接运行通过，`pytest` 未安装，故未声称 pytest 套件通过。第二轮实际调用 `local_ledger_runtime.py status --format json`，得到 `uninitialized`，仅针对已发现问题推进，不重新扫描、建单或改文件。
- A11 所依赖的四份文件（共享规则、操作 skill、Claude/Codex 约定模板）在两宿主的安装目录均与本工作区源码逐字一致，但安装版标识仍为 0.38.2。此证据证明限定场景的宿主行为，不能外推到所有输入、完整 0.38.3 安装包或真实事项交付；Claude 与 Codex 对合成缺陷的优先级也不一致，仍须人工复核分级。

PR #140 已合并于 `e79ee81`，其树哈希与本地测试 HEAD 均为 `680105f06133d1159c1ea74ced80f2b4cb7db9db`。在 macOS 系统 `/bin/bash` 下，对该源码树运行：

- `scripts/validate.sh`：退出 0；其内部的 Codex smoke 判决器是 self-test，不代表真实 Codex 宿主已运行。
- `plugins/spec-guard/hooks/test-phase-guard.sh`：退出 0，80 个用例。
- `plugins/spec-guard/hooks/test-verify-artifacts.sh`：退出 0，19 个用例。
- `evals/codex-plugin-smoke.sh --selftest`：退出 0，只验证判决器对机器事件和未执行路径的区分。

这些检查和本次 GitLab 评论验收不能代替 A02 尚未重跑的创建／关闭写入或 A12 的发布后真实账本回复；A11 的合成双宿主证据仅覆盖上列场景。
