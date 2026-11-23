# Document skeletons（新流程模块）

新流程（S110）的模块在需求文档里写一行流程标记，档位四选一：

```text
<!-- spec-guard: flow v2 tier=normal -->
```

| 档位 | 含义 | 要写的文档 |
|---|---|---|
| `bug` | 修缺陷 | 只写需求文档：复现步骤、预期结果、回归用例 |
| `small` | 小改动 | 只写需求文档：需求各节，再加「做法」「回归用例」 |
| `normal` | 普通需求 | 需求文档、技术方案、回归测试文档、Plan |
| `important` | 重要需求（新模块、跨模块、碰高风险路径） | 同 `normal`；技术方案由用户批 |

档位由 agent 在复述需求时提出，用户确认需求时一并确认。规则判为重要需求时，档位写得再低也按 `important` 处理。
没有流程标记的模块按原来的 Spec → Plan → todo 走，不需要这些文档。

章节标题用二级标题（`## `），中文或英文任选一种；内容不涉及时写「不涉及」，不要删掉章节。

## 需求文档 `spec/<id>.md`

| 中文 | English |
|---|---|
| 目标 | Objective |
| 给谁用 | Users |
| 使用场景 | Scenarios |
| 业务规则和异常情形 | Rules and exceptions |
| 不做什么 | Out of scope |
| 成功标准 | Success criteria |
| 待定问题 | Open questions |

成功标准带编号（`S1`、`S2`…），每条写到能验证。

`small` 在上面各节之后再加：

| 中文 | English |
|---|---|
| 做法 | Approach |
| 回归用例 | Regression cases |

`bug` 只写这三节：

| 中文 | English |
|---|---|
| 复现步骤 | Steps to reproduce |
| 预期结果 | Expected result |
| 回归用例 | Regression cases |

## 技术方案 `tasks/<id>/design.md`

| 中文 | English |
|---|---|
| 现状调研 | Current state |
| 影响面 | Impact |
| 实现方案 | Implementation |
| 接口和数据改动 | Interface and data changes |
| 风险与回滚 | Risks and rollback |
| 方案取舍 | Alternatives |

现状调研写明查了哪些、哪些没查；影响面列出会改到的已有文件。

## 回归测试文档 `tasks/<id>/regression.md`

| 中文 | English |
|---|---|
| 用例清单 | Cases |
| 成功标准对照 | Success criteria coverage |
| 受影响的老功能 | Affected existing features |

用例的字段格式见 regression-doc-check。

## Plan `tasks/<id>/plan.md`

| 中文 | English |
|---|---|
| 任务 | Tasks |
| 检查点 | Checkpoints |

新流程模块的 Plan 只留任务列表（每个任务写验证方式）与检查点；架构决定和风险写在技术方案里。todo 照旧。
