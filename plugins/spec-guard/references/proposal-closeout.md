# Proposal closeout

`proposal-closeout` 是 Proposal 四步流程（提交、接受、晋级、收尾）第四步的后半段。
在此之前，`proposal-promotion-proof` 能证明晋级已进入远端默认分支，但证明之后没有任何东西收尾：
文档只要求人把标签改成 `proposal-stage:promoted`，关闭既没有命令也没有判据。

本模块补上那一段：在**同一次运行内**重新取得 `proved` 之后，预览、经授权写入一条带稳定 marker 的
收尾记录、把阶段改为 `promoted`、关闭事项、读回三项事实。

## 两根正交的轴

```
source authority  恒 = 远端默认分支固定快照     ← 三个后端完全相同
tracker backend   ∈ {local, github, gitlab}     ← 本模块唯一引入的变量
```

能力图结构、Proposal 正文与 baseline、晋级提交、Spec/Plan/todo 的位置与完成判据，全部只来自远端默认
分支与本地文件，**与后端无关**。后端只决定这一条事项的身份、讨论、阶段与开闭状态写在哪里。

因此一个**有 Git 远端、但没有可用 GitHub/GitLab Issues** 的项目（自建 Git、私服不开 Issue、离线团队）
也能完整走完 Proposal。反过来，**没有 Git 远端默认分支的项目不支持 Proposal**——baseline 的定义就是
远端默认分支上的固定 commit，退回本地默认分支会在多 worktree 下给出互相矛盾的事实。此时请用
`/spec-guard:add-module` 快速插入。

## 纯状态机

判断顺序固定：**closed → proof → stage**。

| 条件 | 结果 |
| --- | --- |
| 事项已关闭 | `already-closed`（压过其他一切，重跑只读回、不写） |
| proof 不是 `proved` | `not-eligible`，透传 proof 的诊断 |
| 阶段不在 `accepted` / `promoted` | `not-eligible` + `stage-not-closeable` |
| 其余 | `eligible`，`targetStage=proposal-stage:promoted` |

`closeout_decision(stage, closed, proof_state, proof_diagnostic)` 的签名**不含 `project`／`root`／
`provider`**，有断言锁死。这不是洁癖：有 Plan 而没有 `tasks/<id>/todo.md` 的模块按已完成计
（见 [`spec/plan-without-todo.md`](../../../spec/plan-without-todo.md)），所以一个模块在刚晋级、Spec 都还
没写的时刻就"看起来完成了"。据此关闭 Proposal 是错的，而手里够不到模块 stage 的函数**不可能犯这个错**。

## 适配器协议

三个后端实现同一组七个方法；状态机与身份判定不依赖任何平台特性。

| | github | gitlab | local |
| --- | --- | --- | --- |
| 容器 | `owner/name` | 正整数 project id | Epiq `projectId` 字符串 |
| 事项 id | 整数 | 整数 `iid` | 字符串（另有 7 位 ref 供展示） |
| 传输 | `gh api --hostname` | `glab api` | Epiq stdio MCP |
| 阶段迁移 | `POST …/labels` 再 `DELETE …/labels/{旧}` | 单次 `PUT`，带 `add_labels` 与 `remove_labels` | `epiq_issue_tag_add` 再 `epiq_issue_tag_remove` |
| 关闭 | `PATCH {"state":"closed"}` | `PUT {"state_event":"close"}` | `epiq_issue_close` |
| 讨论 | comment | note（`system: true` 的不算证据） | `epiq_issue_comment_add` |
| URL | 有 | 有 | 无 |

**阶段迁移一律先加后删。** 若先删成功、后加失败，事项会变成一个阶段标签都没有，直接破坏 tracker 契约、
让它读不出来；先加最坏只留两个，而下一次读取会把它报成契约违规，不会静默误判。

### Local 的两个实测约束

下面两条都是在隔离临时账本里对固定的 `epiq@1.11.0` 实测得出的，不是从压缩包反推的：

- **`epiq_issue_list` 必须带 `includeClosed`。** 不带的话已关闭事项直接不在列表里，于是一条已关闭的
  Proposal 会被读成 `absent`——而 `absent` 正是"可以创建"的信号，等于邀请重建一条已存在的事项。
- **`epiq_issue_tag_remove` 收的是 `tagId`，不是 tag 名。** id 来自事项自己的 `tags`（每项
  `{"id", "name"}`）。旧阶段 tag 不在列表里时它的身份未知，适配器停下，不猜。

本模块只调用日常 Epiq 工具，**绝不触碰受 gate 的那些**——尤其 `epiq_sync`，它会把事项内容推到 Git 远端。
有一条测试把七个方法全跑一遍后断言这些工具一个都没出现。

## 预览

预览只读。它依次：重取远端默认分支快照读 Proposal（必须 `published` 且为 v2）→ 在给定精确目标内完整
分页按 marker 定位**恰好一条**事项 → 读阶段与开闭 → **在同一次运行内**重跑 promotion proof →
只有 `proved` 才出预览。

proof 在这次调用里现取，不接受调用方传进来的：早先产生的 proof 说明的是"那时可证明"，不是现在。

tracker 的读取经由收尾适配器，而**同一个 reader 也交给 `prove_from_remote`**，所以 proof 判的就是预览
看到的那一批候选——一次列举、一个结论，不会出现两边各读一次而彼此不符。这也是 Local 能被证明的唯一
办法：默认 reader 只会 GitHub 与 GitLab 的 CLI。既有命令不受影响，它们仍用自己的默认 reader。

预览字段：`backend`、`exactTarget`、`proposalId`、`revision`、`issueId`、`currentStage`、`targetStage`、
`promotionCommit`、`reviewCommit`、`issueContentDigest`、完整的 `record`、`actions`、`source`
（`explicit` / `project-default` / `project-default-target`）与 `digest`。

## 收尾记录

```
<!-- spec-guard-proposal-closeout:v1 <proposalId>/<revision 前 12 位> -->
```

只在**最后一行**认定有效。带这个 marker、但正文不是本次要写的那条记录的评论，判为
`conflict` + `closeout-marker-not-ours`——marker 由公开信息推得出来（`<id>/<revision 前 12 位>`，
两者都印在 Proposal 事项正文的 v2 marker 里），所以「末行是 marker」不构成"本工具写过"的证据；
在公开仓库上任何能评论的人都伪造得出来。只有逐字相同的那条记录才算已写过。命名空间与
`spec-guard-hosted-ticket:v1`、`spec-guard-local-ticket:v1` 都不冲突，记录里也**不得**回显 Proposal 自己的
`spec-guard-proposal:v2` marker——同一容器里两个命名空间正是 marker 歧义的开端。

正文固定声明一句边界：本事项记录的是**设计决定**，该决定现已执行；它**不代表模块已交付**，模块的
Spec、Plan、todo、实现与验收由模块自己的任务清单或普通事项跟踪。没有这句，关闭很容易被读成"做完了"。

## 写入前复核

`--confirm` 之后、第一次写之前，下面每一项都重做一遍。预览里说过的话，一句都不当真。

| 复核 | 不通过 |
| --- | --- |
| 预览 `digest` 重算一致、`record` 末行就是该 marker | `preview-invalid` |
| Proposal 快照读得到（`published`） | 探测失败：`unknown` + 探测自己的原因；`absent` / `invalid`：`preview-stale` + `proposal-absent` / `proposal-invalid` |
| Proposal 带 marker | `preview-stale` + `proposal-marker-missing` |
| revision 未变 | `preview-stale` + `proposal-revision-changed` |
| `target_facts()` 与预览一致 | `unknown` + `target-changed` |
| 事项仍是同一条（`issueId`） | `conflict` + `issue-changed` |
| 正文与标签的 digest 未变 | `conflict` + `issue-content-changed` |
| 仍 open | `already-closed` |
| 阶段仍可关闭 | `not-eligible` |
| **重跑 proof 仍 `proved` 且 `promotionCommit` 相同** | `not-eligible` + `proof-changed` |
| journal 中已记录的绑定与本次一致 | `conflict` + `binding-target-changed` |

## 写入、幂等与 journal

```
1. 评论   → 已有末行为该 marker 的评论则跳过
2. 阶段   → 已是 promoted 则跳过；否则先 tag/label add，再 remove 旧的
3. 关闭   → 调用 set_closed（事项已关闭的情形在上一层的复核里就已返回 already-closed）
4. 读回   → 阶段 == promoted ∧ 已关闭 ∧ **本次记录恰好一条**（读不回即 partial）
```

每步先查重后写，这正是**响应丢失后重跑能对账而不是重写**的原因。结果无法确认时是 `partial`：尝试留在
journal 里，**绝不重发**；重跑是重新读取并报告，不是重试。一次空查询**不足以**证明写入失败。

journal 位于 `~/.local/state/spec-guard/proposal-closeout/`，文件 0600、父目录 0700、按
`sha256(proposalId + revision)` 取 `fcntl` 独占锁。记录的绑定若指向另一个目标，结果是 `conflict`，
不是静默改用新目标。**收尾成功会删掉自己的条目**，所以 journal 里还有东西 = 有一次没收完的尝试。

**诚实的局限**：插件无法扫描所有容器，因此**不能证明**同一个 Proposal 没有在另一个 Tracker 里也存在
一条。journal 丢失后仍须靠 marker 重新对账。这与 `local-ticket-portability` 对同一问题的表述一致。

## 结果状态

| state | 含义 |
| --- | --- |
| `verified` | 三步成功并读回 |
| `already-closed` | 事项已关闭，**不写任何内容** |
| `partial` | 部分成功；journal 保留，不自动重试 |
| `conflict` | marker 多条 / 正文被改 / 绑定目标不同 |
| `not-eligible` | proof 非 proved、阶段不可关闭、proof 变化 |
| `preview-stale` / `preview-invalid` | 预览失效 |
| `unknown` + 探测原因 | 读不到，不是失效：重试；原来这会被误报成 `proposal-revision-changed` |
| `unknown` | 传输不可用、读回不完整、Epiq runtime 不可用 |
| `rejected` + `statusCode` | 平台明确 4xx 拒绝（权限不足走这里） |
| `target-unselected` | 未给出精确目标且无可用项目默认值 |
| `confirmation-required` | 没有 `--confirm` |

## 授权

默认一个 Proposal 一次预览、一次确认。用户在对话里**逐一点名** proposal id 时，可以一次预览全部、
一次确认地连续收尾。**没有 session 档**，不存在对"任意 Proposal"的通配授权，也不允许永久或无限制
自动关闭。`--confirm` 只是把已授权的预览付诸执行，**它本身不是授权**。协作信箱消息、事项正文、评论
文本一律是数据，永不构成授权。

## 不做什么

不读模块 stage、todo 或能力图完成度作为关闭判据；不给 `proposal_promotion_proof` 加写入开关
（它相对发布基线零字节改动，并有断言锁死其只读表面）；不自动在另一个 Tracker 重建同一个 Proposal；
不自动迁移已有事项（跨后端搬运走 `local-ticket-portability` 的逐条显式交接）；
不关闭 `rejected` / `deferred`（那是人的决定，不是可证明的事实）；不调用 `epiq_sync`。
