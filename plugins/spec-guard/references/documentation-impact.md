# 模块文档影响协议

模块文档影响记录回答的是：**这个模块怎样对待已显式声明的上游文档？** 它不判断代码是否实现文档，也不证明文档已经出版。

只有项目有有效的 `docs/DOCUMENTATION-BASELINE.md` 时才启用。项目级标为 `not-applicable` 的关注点不需要也不得出现在模块表中；其余关注点都必须得到模块级决定。

## 模块 Spec

在 `spec/<module-id>.md` 中恰好放置一张表：

```markdown
## Documentation impact

| Concern | Decision | Rationale |
|---|---|---|
| product-direction | follow | 本模块仍在既有产品范围内。 |
| architecture | update | 模块边界需写回架构文档。 |
| developer-entry | follow | 现有构建与测试入口不变。 |
| integration-contract | create | 新公开接口需要明确的契约。 |
```

`Decision` 只能是：

- `follow`：遵循权威文档，本模块不计划修改它；
- `update`：计划更新基线所指向的文档；
- `create`：计划形成新的或此前未成形的文档交付物；
- `pending`：尚未形成决定，保留为未收口事实；
- `not-applicable`：该关注点对**本模块**无影响，必须说明原因。

项目级 `not-applicable` 与模块级 `not-applicable` 不同：前者说明项目没有该类关注点，后者说明该项目有该关注点、但当前模块不涉及它。

## 模块 Plan

当且仅当决定为 `update` 或 `create`，在 `tasks/<module-id>/plan.md` 中恰好放置：

```markdown
## Documentation delivery

| Concern | Planned artifact | Rationale |
|---|---|---|
| architecture | `docs/architecture.md` | 描述新的模块边界。 |
| integration-contract | `docs/api.md` | 发布新接口的契约。 |
```

`update` 的 `Planned artifact` 必须等于基线中的 `Authority`；`create` 可指定新的预期交付物。`update` 指向基线状态为 `target` 的文档时只能补充：标注已实现的部分、补充约束，不得删改未实现的目标；要改目标就是改需求，单独交用户批准。这张表是计划，不是交付证据：它不能表示文档已更新、内容正确或代码符合文档。实际交付证据与交付前提醒由后续核验模块处理。

表里有 `update` 或 `create` 时，最终验收前要在同一份 Plan 里补一张 `Documentation outcome` 表，写明每项实际交付了什么；
没有这张表，[文档交付核验](documentation-verification.md)会判 `attention`，并在第一行点名缺表。可以把补表写成 Plan 最后一个普通任务。空模板：

```markdown
## Documentation outcome

| Concern | Outcome | Evidence | Rationale |
|---|---|---|---|
| <concern> | delivered／deferred／pending | <证据指针，deferred、pending 写 —> | <说明> |
```

每个 `update`／`create` 关注点一行，取值与证据要求见[文档交付核验](documentation-verification.md)的「Plan outcome 表」。

在 Spec 阶段、Plan 还没写时，影响表里只要有 `update` 或 `create`，检查就会报 `module plan must be a regular file`。这是预期结果：报到这一句说明 Spec 里的影响表已通过校验，只是 Plan 交付还没检查，不能当作完整的 `valid`。影响表里没有 `update`、`create`（全部为 `follow`、`pending` 或 `not-applicable`）时直接得到 `valid`。Plan 获批后要再跑一次，必须得到完整的 `valid`。Plan 已经写了还报这一句（例如它是符号链接），才是异常。

解析器只读取基线、当前模块 Spec 和当前模块 Plan；不会读取业务代码、Git diff、时间戳或权威文档正文。
