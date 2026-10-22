# 文档交付核验协议

此协议汇总模块已经**声明**的文档结果，并对声明要更新的仓库内文档用 git 核一下它改没改过。它不会检查文档正文、链接可访问性、外部发布状态或代码符合度。

仅在项目有有效文档基线、且模块影响表有效时使用。没有基线的项目结果为 `absent`，不会收到提醒。

## Plan outcome 表

当模块的 `Documentation impact` 中存在 `update` 或 `create` 时，可在同一模块 Plan 中写一张：

```markdown
## Documentation outcome

| Concern | Outcome | Evidence | Rationale |
|---|---|---|---|
| architecture | delivered | `docs/architecture.md#module-boundary` | 边界已由架构负责人确认。 |
| integration-contract | deferred | — | 等待外部 API 审查。 |
```

`Outcome` 仅可为：

- `delivered`：必须给出用户提供的证据指针；该指针不是自动验真的结果；
- `deferred`：必须说明为何没有在本模块交付；
- `pending`：必须说明待决原因。

表只可包含对应的 `update`/`create` 关注点，且每项至多一行。

## 按基线状态核验

对决定为 `update` 且声明 `delivered` 的关注点，按基线里它那一行的 `Status` 与 `Authority` 区分（结果写在 outcome 的 `check`）：

- **外部文档**（`Authority` 是 URL）：只要求证据非空，`check` 为 `unverified`（未核验），不算提醒。
- **`target`**（已批准、未完全实现的目标）：不要求改。改过为 `target-changed` 并给出 `added`、`removed` 行数，验收消息里把差异原样附上由用户看；有删除行时另加一条提醒——删改未实现的目标即改需求，须单独交用户批准。没改过为 `target-unchanged`。
- **其余状态**（现状类）：文件须确被改过。改过为 `changed`；没改过为 `unchanged` 并加一条提醒。

“改过”的判据：自第一个加入 `spec/<module-id>.md` 的提交以来，工作区里这份文件与那次提交不同（`git diff --numstat <该提交> -- <路径>`，含之后的提交、暂存与未暂存改动；`Authority` 的 `#锚点` 先去掉）。不在 git 仓库里、Spec 还没提交、git 命令失败时为 `unknown` 并加一条写明原因的提醒，不当作没改过。`create`、`deferred`、`pending` 为 `not-checked`。

## 核验状态

- `absent`：没有启用文档基线；
- `invalid`：基线、影响记录或 outcome 结构无效；
- `attention`：存在模块级 `pending`、尚未声明 outcome、outcome 为 `deferred`/`pending`，或上一节的提醒（现状类没改过、`target` 有删除行、`unknown`）；
- `ready`：所有需交付项均已声明 `delivered`，没有待决决定，也没有上一节的提醒。

`attention` 是提醒，不是开发、Issue 或 PR 的硬阻断。`ready` 不得解释为“文档正确”“文档已发布”或“代码实现符合文档”；外部文档始终是未核验。

项目有基线时，阶段提示会在最终验收那一轮提醒先跑本核验，把结果写进验收结果。
