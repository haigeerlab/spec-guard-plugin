# 项目级审查发现对账（2026-10-03）

## 范围与裁决

- 原审查基准：`a33b8f9`；本次对账基准：`5eea400`（PR #138 合并后的远端 `main`）。
- 原审查按 16 个用户能力域检查入口、实现、测试与文档；本文件只对其中有行动或验收缺口的发现收口，不把 33 个模块数当作 33 项已验收能力。
- `已修源码` 表示目标改动已进入 `main`，不自动表示新版已安装或真实宿主已验收；`未验证` 不等于功能失败。
- 本轮没有创建 tag、GitHub Release 或更新正式安装副本。下列临时消费者测试只使用合成数据。

## 发现项状态

| 编号 | 原发现与优先级 | 当前裁决及证据 | 尚需动作 |
| --- | --- | --- | --- |
| A01 | 有 Plan 无 `todo.md` 被计为 `DONE`，原审查 P1 | **按明确设计保留。** [plan-without-todo Spec](../../spec/plan-without-todo.md)记录用户决定：旧远端 tracker 项目不能因缺本地 Todo 被改判未完成；本地模式对 active module 提醒，产物校验汇总警告。[阶段判据](../../plugins/spec-guard/hooks/module_stage.py)仍按此实现。原审查把 13 个历史模块直接当作新模式缺陷，范围过宽。 | 新模块规划仍必须生成本地 Todo；若将来改变完成判据，须单独评审兼容规则和 Spec。 |
| A02 | 托管普通 Issue 缺真实双平台往返，原审查 P1 | **部分验收。** GitHub 私有合成目标已完成创建、评论、PR 合并、关闭和读回。[模块记录](../../tasks/hosted-ticket-workflow/todo.md)明确：私有 GitLab 目标只读找回已关闭的既有事项，没有重新执行当前源码的写入链路。2026-10-03 再查重得到 `unknown`；mGit CLI API 返回 401 token expired，故本次是**环境不允许验证**。 | 凭据恢复后，先完整查重和根因核对；仅在有独立范围、精确内容及逐次授权时做 GitLab 合成往返。不得从 401 推断产品失败。 |
| A03 | Claude 拆除入口未默认预览，原审查 P2 | **已修源码。** [PR #134](https://github.com/haigeerlab/spec-guard-plugin/pull/134) 要求先运行 `--dry-run`、展示预览，预览失败即停；[现行入口](../../plugins/spec-guard/commands/teardown-convention.md)与回归已更新。 | 真正删除消费者受管块仍须看过预览后的单次确认；命令文字回归不能单独证明所有宿主回复。 |
| A04 | 产物校验二次汇总失败可能显示零警告，原审查 P2 | **已修源码。** [PR #134](https://github.com/haigeerlab/spec-guard-plugin/pull/134) 使辅助脚本失败时输出“未验证”；[失败注入回归](../../plugins/spec-guard/hooks/test-verify-artifacts.sh)覆盖目标分支。 | 发布前沿完整校验再运行一次。 |
| A05 | 托管评论预览可过期、关闭的 `verified` 易被误读为 CI 通过，原审查 P2 | **已修源码。** [PR #131](https://github.com/haigeerlab/spec-guard-plugin/pull/131) 将评论预览绑定 Issue 范围并把关闭事实限定为远端已关闭；[现行 skill](../../plugins/spec-guard/skills/hosted-ticket-workflow/SKILL.md)要求人工核对交付和验证事实。 | 真实 GitLab 写入仍按 A02 单列。 |
| A06 | Ubuntu CI 不能代表每次 macOS Bash 3.2 验收，原审查 P2 | **验证边界保留。** [CI](../../.github/workflows/ci.yml)明确只持续运行 Ubuntu；[维护流程](../maintainer-workflow.md)要求 macOS `/bin/bash`。本轮工作区三条 macOS 校验已通过，见下节。 | 统一发布前仍须对最终待发布提交复核并记录；不能把 Ubuntu CI 说成 macOS CI。 |
| A07 | 一次性维护工作进入能力图，增加模块状态与解释成本，原审查 P2 | **设计债已设准入边界。** [工作流](../workflow.md)规定局部 bug 不必新建能力模块；已发布图和历史保留，避免破坏 Proposal 基线。 | 新增模块时执行“独立用户能力”评审；不为清理统计数字批量删除旧模块。 |
| A08 | 历史导入底层命令无日常入口，原审查 P3 | **按用户决定保留内部。** [能力历史 Spec](../../spec/capability-history.md)与[维护流程](../maintainer-workflow.md)说明 `import --confirm` 只供维护者处理已退役证据；用户入口只给只读预览。 | 实际导入旧证据仍需逐次确认，不因工具存在自动执行。 |
| A09 | 早期模块 Spec 单读时可能误导，原审查 P3 | **文档修订完成。** [module-insert](../../spec/module-insert.md)与[proposal-promotion-proof](../../spec/proposal-promotion-proof.md) 顶部新增现行修订指针，保留原始决策文字；四个目标文件已逐一确认存在。 | 本轮仓库完整校验已通过；后续若修订这些契约，继续保留历史与现行边界。 |
| A10 | XATS/native 双传输及 XATS 依赖成本，原审查 P2 | **有意过渡，非本轮删除项。** [日落决定](../decisions/2026-09-28-xats-sunset.md)规定 native 转正门槛、一个 minor 的 XATS 退出节奏与反向出口；[协作 Spec](../../spec/collaboration-messaging.md)明示 XATS 依赖未锁定的剩余风险。 | 门槛达到后走独立 Proposal；不能凭一次宿主验收提前退役默认传输。 |
| A11 | 项目审查交接主要靠静态指令测试，原审查 P2 | **宿主效果证据有限。** [共享检查点](../../plugins/spec-guard/references/workflow-checkpoints.md)要求有限批次和明确停点；本次对话在“继续”后已进入预告修复，但不能把这一观察单独归因于插件。 | 最终版在隔离消费者项目分别执行 Claude/Codex 多轮试验；不能用静态文字断言替代。 |
| A12 | Local 事项回复可回显完整内部 ID，后续宿主验收发现 | **已修源码、未发布。** [PR #137](https://github.com/haigeerlab/spec-guard-plugin/pull/137) 收紧 Claude 命令和共用 skill；隔离合成 Claude Code MCP 试验中目标读取工具实际执行，候选回复含标题与短编号、未回显完整 ID。 | 统一发布并更新安装副本后，再核对真实账本上的 Claude 回复；事项保持开放。 |
| A13 | Local 账本与归档恢复的可选真实运行时验收未在常规 `validate.sh` 中执行 | **本轮已实测。** 用固定 Epiq 1.11.0 运行时，在隔离临时仓库执行 `test_local_ledger_acceptance.py`（`state: passed`）和 `test_local_ticket_restore_acceptance.py`（1 项通过），均退出 0；工作仓库状态未被测试改动。 | 此证据仅覆盖临时合成项目，真实用户数据迁移仍需目标与授权。 |

## 发布停点

PR #138 已合并，两个 Manifest 在 `main` 上为 `0.38.3`，但没有 `v0.38.3` tag 或 Release。本轮继续处理审查遗留项；统一发布须在最终源码、macOS 验证、真实宿主可验证范围和未验证清单固定后单独执行。

## 本轮验证

在 macOS 系统 `/bin/bash` 下，对本轮工作区运行：

- `scripts/validate.sh`：退出 0；其内部的 Codex smoke 判决器是 self-test，不代表真实 Codex 宿主已运行。
- `plugins/spec-guard/hooks/test-phase-guard.sh`：退出 0，80 个用例。
- `plugins/spec-guard/hooks/test-verify-artifacts.sh`：退出 0，19 个用例。
- `evals/codex-plugin-smoke.sh --selftest`：退出 0，只验证判决器对机器事件和未执行路径的区分。

这几项不能代替 A02 的 GitLab 写入往返、A11 的双宿主多轮交接或 A12 的发布后真实账本回复。
