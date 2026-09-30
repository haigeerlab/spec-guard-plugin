# Proposal contract v1

Proposal 是尚未进入能力图的独立需求的设计记录。它不是 task、PR 或
`.agent/state.json` 的替代品；GitHub/GitLab 只保存它的讨论与阶段标签，且本协议不写入
tracker。

## Published location and identity

已发布的 Proposal 位于 `spec/proposals/<proposal-id>.md`。`proposal-id` 必须匹配
`^[a-z][a-z0-9-]{2,62}$`。第一行及其后的 identity marker 固定为：

```markdown
# Proposal: 简短标题
<!-- spec-guard-proposal:v1 id=<proposal-id> -->
```

marker 必须完整地单独占一行，文档中恰好一次。fenced code block 中的示例不参与解析。

## Document grammar

文档必须按以下顺序恰好包含四个顶级段：

1. `## Summary`：非空的自由文本，说明这是为什么独立的能力。
2. `## Capability map baseline`：下面的字段表及模块摘要表。
3. `## Change`：下面的 `new-module` 字段表。
4. `## Tracker contract`：marker 和标签命名空间。

`Capability map baseline` 的字段表是：

| Field | Value |
| --- | --- |
| Remote | `origin` 之类的 Git remote 名称 |
| Default branch | 不带 `refs/` 前缀的默认分支名 |
| Commit | 40–64 位小写十六进制 Git object id |
| Capability map | `spec/CAPABILITY-MAP.md` |
| Goal digest | `spec-digest.py` 产生的 12 位摘要 |
| Build order | 已固定 commit 中完整的 `Build order: ...` 值 |

紧随字段表的是 `### Module digests` 及其完整模块表：

| Module id | Row digest |
| --- | --- |
| existing-module | `spec-digest.py` 产生的 12 位摘要 |

摘要由将来固定的远端默认分支 commit 复算；当前 worktree、其他 worktree 或未提交
文件都不是共享基准。`spec-digest.py` 是唯一允许的摘要算法。

`Change` 只支持一个 v1 类型：

| Field | Value |
| --- | --- |
| Type | `new-module` |
| Module id | 基线中不存在的 kebab-case id |
| Responsibility | 非空单行职责 |
| Depends on | `—` 或以逗号分隔的、无重复的基线 module id |
| Build-order anchor | `after:<baseline-module-id>` 或 `end` |

每个依赖和 `after:` 锚点都必须在结果 Build order 中位于新模块之前；`v1` 不支持改动、
删除或重排既有模块，也不支持批量 Proposal。

`Tracker contract` 的字段表固定为：

| Field | Value |
| --- | --- |
| Proposal id | 与文档 identity marker 中的 id 相同 |
| Identity label | `proposal` |
| Stage label namespace | `proposal-stage:` |

普通 Proposal Issue 的正文必须恰好含一次完整 marker，并带有 `proposal` 与恰好一个阶段
标签。允许的阶段是 `proposal-stage:draft`、`proposal-stage:published`、
`proposal-stage:in-review`、`proposal-stage:accepted`、`proposal-stage:rejected` 和
`proposal-stage:promoted`。标签是唯一可变阶段事实；不要将其复制到 Proposal 文档或
`.agent/state.json`。

## Proposal v2 revision

新 Proposal 使用完整 v2 marker：

~~~markdown
<!-- spec-guard-proposal:v2 id=<proposal-id> revision=sha256:<64-hex> -->
~~~

revision 是规范化文档内容的 SHA-256。计算时 marker 的 revision 值以 64 个零替换；
因此修改文档内容却不更新 marker 会被拒绝。v2 在 Summary 后增加 Integration intent
字段表：Problem、In scope、Out of scope、Safety boundaries、Initial dependency
assumptions、Acceptance intent。

v1 Proposal 继续可读，不会被自动重写或删除；它不能进入新的接受或 promotion
流程，直到作者发布有新 revision 的 v2 文档。v2 Issue 必须匹配完整 marker，不能复用
同一 id 的旧 revision。阶段还允许 proposal-stage:needs-revision 和
proposal-stage:deferred。

## Draft template

agent 直接按下面的模板写 `spec/proposals/<proposal-id>.md`，再运行 `/spec-guard:proposal-submit`。
模板省略了 `## Capability map baseline` 一节：baseline 与标记里的 revision 由 `proposal-submit`
从远端默认分支的固定快照补全并写回，不要手算；revision 先写 64 个 `0`。改了草稿后重跑即重算。
`<...>` 处替换为实际内容，Integration intent 六项与 Change 五项的要求见上文。

~~~markdown
# Proposal: <简短标题>
<!-- spec-guard-proposal:v2 id=<proposal-id> revision=sha256:0000000000000000000000000000000000000000000000000000000000000000 -->

## Summary

<要解决什么问题，为什么它是一个独立模块。>

## Integration intent

| Field | Value |
| --- | --- |
| Problem | <问题> |
| In scope | <范围内> |
| Out of scope | <范围外> |
| Safety boundaries | <安全边界> |
| Initial dependency assumptions | <依赖假设> |
| Acceptance intent | <验收意图> |

## Change

| Field | Value |
| --- | --- |
| Type | new-module |
| Module id | <new-module-id> |
| Responsibility | <非空单行职责> |
| Depends on | — |
| Build-order anchor | end |

## Tracker contract

| Field | Value |
| --- | --- |
| Proposal id | <proposal-id> |
| Identity label | proposal |
| Stage label namespace | proposal-stage: |
~~~

## Minimal example

```markdown
# Proposal: Add proposal tracker reads
<!-- spec-guard-proposal:v1 id=proposal-tracker-read -->

## Summary

Read a Proposal Issue without creating or modifying it.

## Capability map baseline

| Field | Value |
| --- | --- |
| Remote | origin |
| Default branch | main |
| Commit | 0123456789abcdef0123456789abcdef01234567 |
| Capability map | spec/CAPABILITY-MAP.md |
| Goal digest | 0123456789ab |
| Build order | proposal-contract → proposal-publication |

### Module digests

| Module id | Row digest |
| --- | --- |
| proposal-contract | 0123456789ab |
| proposal-publication | abcdef012345 |

## Change

| Field | Value |
| --- | --- |
| Type | new-module |
| Module id | proposal-tracker-read |
| Responsibility | Read one Proposal Issue as a tracker fact. |
| Depends on | proposal-contract |
| Build-order anchor | after:proposal-contract |

## Tracker contract

| Field | Value |
| --- | --- |
| Proposal id | proposal-tracker-read |
| Identity label | proposal |
| Stage label namespace | proposal-stage: |
```
