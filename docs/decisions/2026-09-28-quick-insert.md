# 决策：新需求默认用快速插入，Proposal 改为选用

状态：已批准（2026-09-28，用户决定）。`module-insert` 模块的 Spec 已写好，尚未实现。

## 背景

Proposal 要走九步才能把一个需求插进能力图：写 Proposal、合进 main、开 Issue、评审、主链裁决、人工接受、预检、
晋级、证明。这些步骤各自防的是多人协作时的问题，比如多个 worktree 各写一版、写作期间别人改了能力图、需要追查
谁接受了哪个版本。

实际使用者主要是个人或小团队。用户的常用做法是：在一个模块做完的检查点，把理顺的需求上下文交给 agent，问插在
哪，让它直接改能力图。这很灵活，缺的只是校验。

## 决策

- **新增快速插入命令 `/spec-guard:add-module`，作为新增模块的默认方式。** 只在检查点可用；复用现有解析器做校验，
  预览能力图的改动，用户确认后才写入。详见 [`spec/module-insert.md`](../../spec/module-insert.md)。
- **Proposal 九步保留，改为选用。** 需要留下经过评审的决定记录，或多人确认时使用。
- **本仓库也适用。** 此前 `CAPABILITY-MAP.md` 的目标规定新需求以 Proposal 提出；现改为默认快速插入，需要留痕时
  走 Proposal。`module-insert` 本身按此直接插入，未经 Proposal。关闭的 PR #49（Proposal 草稿生成命令）由本决策取代。

## 影响

- 能力图的 `## 目标` 改写了一次，目标摘要随之变化，所有已发布 Proposal 的新鲜度判定会变为过期。本仓库已发布的
  两份（`collaboration-messaging`、`local-ticket-ledger`）都已晋级，不受影响。
  [`2026-09-28-single-capability-map.md`](2026-09-28-single-capability-map.md) 定的「目标以后只追加」仍然成立：这次
  改写是因为目标里写的规则本身变了，不是为了加模块。
- 快速插入只改变 Build order，不改目标和已有行，不会让已发布 Proposal 判为过期。
