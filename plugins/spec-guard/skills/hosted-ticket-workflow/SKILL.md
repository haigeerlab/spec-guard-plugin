---
name: hosted-ticket-workflow
description: 在明确选用 GitHub 或 GitLab 普通 Issue 时，逐项查重、授权创建、记录讨论，并在代码交付后核对关闭；Local 事项继续用 ticket skill。
---

# 托管日常事项

仅处理用户或审查批次明确选用的 GitHub/GitLab **普通缺陷 Issue**。先从报告或用户
请求取得稳定编号、平台、主机、项目、可见性和根因；一个批次沿用已选目标，后续
改选只影响新事项。不凭 Git remote、旧 `.agent/state.json` 或 Proposal Issue 推断
目标。Local 继续使用 `ticket` skill 的 Epiq 路径；没有明确托管目标时先补目标，
只读审查到报告为止。

从当前启用的插件解析 `ROOT`（Codex 采用 `spec-guard-ops` 的解析环境；Claude
使用 `CLAUDE_PLUGIN_ROOT`）。以下脚本均在 `$ROOT/hooks/`，命令里的编号和目标
须替换为本次事实，不能从示例照抄。

## 查重与创建

1. 先运行 `python3 -B "$ROOT/hooks/hosted_ticket_read.py" --platform <github|gitlab>
   --host <host> --target <project> --visibility <visibility> --request-id <stable-id>
   --title <title>`。它完整分页读取开放及关闭事项，排除 GitHub PR，返回
   `found/absent/unknown/conflict`。`unknown/conflict` 停在待入账并给出原因；
   `found` 读回并沿用已有 ID/URL。
2. `absent` 仍带 `rootCauseReviewRequired`：精确标记与同名查重不能证明没有
   同根因的异名事项。用平台查询与逐项阅读检查可能相关的开放和关闭事项；查询
   不完整或根因有歧义时停止，不传 `--root-cause-reviewed`。审查报告保留
   “待入账”及候选，不重复创建。
3. 准备已脱敏的标题和正文文件。`python3 -B "$ROOT/hooks/hosted_ticket.py"
   preview --platform … --host … --target … --visibility … --request-id …
   --title … --body-file <file>` 只读输出**精确**目标、正文、来源标记与 digest。
   向用户展示目标可见性和完整拟发布内容；对该次外部写入取得授权。内部路径、
   Local 私有编号、凭据和敏感日志不得直接进入公开 Issue。
4. 内容与目标未变、根因已核对且有这次授权后，使用相同参数运行 `publish`，
   追加预览的 `--expected-digest <digest> --root-cause-reviewed --confirm`。
   只有读回 `verified/found` 及稳定 ID/URL 后才标“已入账”。`rejected` 报实际
   4xx；结果未知时脚本保存不含正文的私有意图，下一次先按标记对账，绝不自动
   重发。平台不提供跨独立 clone 的原子防重；多个匹配报告冲突。

## 讨论与交付收尾

- 范围或验收发生实质变化时，先准备可读决定记录，并用稳定事件编号运行
  `python3 -B "$ROOT/hooks/hosted_ticket_action.py" comment-preview --platform …
  --host … --target … --visibility … --issue-id <id> --event-id <stable-id>
  --body-file <file>`；展示内容并取得该次授权后，运行同参数的
  `comment-publish --expected-digest <digest> --confirm`。评论按标记读回；结果未知
  时不自动发第二条。无关的错字修正可以使用平台原生编辑，但不能抹掉实质决定。
- PR/MR 创建后，记录它覆盖哪些 Issue；合并后**逐项**核对平台的 merged 状态、
  合并提交、CI／验收结果、事项剩余范围和当前 Issue 状态。仅合并不等于完成；
  部分覆盖、待部署、验收失败或结果未知均保持开放。先把修复与验证记录写回
  Issue，并按上一步读回。平台已自动关闭时仍可记录核对结果，但不能把关闭状态
  当成验收通过。
- 全部范围已交付且验证通过时，使用
  `python3 -B "$ROOT/hooks/hosted_ticket_action.py" close-preview --platform …
  --host … --target … --visibility … --issue-id <id> --delivery-id <pr-or-mr-iid>
  --coverage-complete --validation-file <evidence-file>`。脚本会读回 PR/MR 的合并
  提交；`validation-file` 必须来自刚核对的真实 CI／验收事实，布尔参数本身不是
  证据。展示精确 Issue、交付和验证信息，取得关闭授权后再以同参数运行
  `close-publish --expected-digest <digest> --confirm`，读回关闭状态。平台自动关闭
  报 `already-closed`，仍需核对实际剩余条件；不可把它写成自动验收通过。

每个检查点按[共享检查点规则](../../references/workflow-checkpoints.md)报告已处理和
剩余数量、真实验证与未验证项、下一停点。修复代码复用 agent-skills 的诊断、TDD、
增量实现和代码复审；普通 bug 不自动建立新能力模块。新发布、评论或关闭需要
各自的精确授权，“继续”不扩大上次授权范围。Proposal 生命周期保持只读，旧
tracker bridge 不恢复。
