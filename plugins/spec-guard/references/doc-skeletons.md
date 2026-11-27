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
| `important` | 重要需求（碰高风险路径） | 同 `normal`；技术方案按档位的 design 项：reviewer 时由第二审查者放行，否则用户批 |

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

### 需求文档里的两行可选标记（sg-gate-flow）

都写在流程标记行下面、各占一行，都在需求的批准指纹里（确认后改动就要重新确认）：

```text
<!-- spec-guard: release-preauth yes -->
<!-- spec-guard: overall-design spec/overall/<名字>.md -->
```

- `release-preauth yes`：档位把发版交给 autopilot（`release` 是 `auto-confirm`／`auto`）时，用户在需求确认时答「做完自动发版」才写；只认 `yes`。
- `overall-design`：需求确认时定了要总体技术方案才写；同一需求的模块指向同一个文件，路径只能是 `spec/overall/<kebab-case>.md`。

需求文档的审查记录写在「外部审查意见」一节，由 review-mark 写，不手写（sg-review-rules）：

```markdown
<!-- spec-guard: requirement-review reviewer=host blocking=<阻断数> sha256=<12 位> -->
<!-- spec-guard: requirement-review reviewer=none sha256=<12 位> reason=<一行原因> -->
```

delegate 审的那一轮照旧是 `codex-review` 行。三种都带审查时整份文件 sha256 的前 12 位；只记一轮。

## 总体技术方案 `spec/overall/<名字>.md`

全新项目或全新模块的需求共用一份，能力图批准之后、第一个模块开工之前写，只由用户批（`review-mark --target overall`）。章节：

| 中文 | English |
|---|---|
| 现状调研 | Current state |
| 影响面 | Impact |
| 技术选型 | Technology choices |
| 架构 | Architecture |
| 目录结构 | Directory layout |
| 数据模型 | Data model |
| 实现方案 | Implementation |
| 接口和数据改动 | Interface and data changes |
| 风险与回滚 | Risks and rollback |
| 方案取舍 | Alternatives |

各节写多细、要不要画图，由技术方案大纲（自动驾驶模块 6）细化；本版只检查文件、标记与批准，不检查章节。

## 技术方案 `tasks/<id>/design.md`

| 中文 | English |
|---|---|
| 现状调研 | Current state |
| 影响面 | Impact |
| 实现方案 | Implementation |
| 接口和数据改动 | Interface and data changes |
| 风险与回滚 | Risks and rollback |
| 方案取舍 | Alternatives |

现状调研写明查了哪些、哪些没查；影响面列出会改到的已有文件。上面六节是改已有功能的写法，下面两种情况另加章节，可以叠加（sg-design-outline）：

**全新项目或全新模块**：需求文档恰好有一行格式正确、路径有效的 `overall-design` 行时（重复、写坏或路径不合规的不算），六节之外再加四节，缺一节 verify-artifacts 判失败；用不上的写「不涉及」：

| 中文 | English |
|---|---|
| 技术选型 | Technology choices |
| 架构图 | Architecture diagram |
| 目录结构 | Directory layout |
| 数据模型 | Data model |

架构图、数据模型用 Mermaid 这类能放进文档、能对比版本的文本格式。

**一次插入多个模块**：同一批插入能力图 2 个及以上模块时加一节，画出与同批模块之间的接口；没有直接接口时写「无直接接口」并说明原因。缺了或只有注释时警告：

| 中文 | English |
|---|---|
| 模块接口 | Module interfaces |

**重要需求**（生效档位 `important`）：「方案取舍」至少比较两种做法，每种一个列表项（`-`、`*`、`+` 或 `1.` 开头）；少于 2 条时警告。

## 回归测试文档 `tasks/<id>/regression.md`

| 中文 | English |
|---|---|
| 用例清单 | Cases |
| 成功标准对照 | Success criteria coverage |
| 受影响的老功能 | Affected existing features |

### 用例格式

每条用例一个三级标题 `### R<n>: <标题>`（冒号中英文都行），下面每行一个字段，字段名中英文任选：

| 中文 | English | 必填 |
|---|---|---|
| `- 步骤：` | `- Steps:` | 是 |
| `- 预期：` | `- Expected:` | 是 |
| `- 执行方式：` | `- Method:` | 是：`command`、`script`、`ai-operate`、`manual` 之一 |
| `- 命令：` | `- Command:` | 执行方式为 `command`／`script` 时必填，其他时不写 |
| `- 证据：` | `- Evidence:` | 是：证据形式，如「运行输出」「截图」「用户原话」 |

字段可以跨行：缩进的续行并入上一个字段；命令可以写在字段行下面的代码块里。同一份文档里编号不重复。

```markdown
## 用例清单

### R1: 保存后提示成功
- 步骤：打开编辑页，改标题，点保存
- 预期：提示「已保存」，刷新后标题是新的
- 执行方式：command
- 命令：`python3 -m pytest tests/test_save.py`
- 证据：运行输出

## 成功标准对照

| 成功标准 | 用例 |
|---|---|
| S1 | R1 |

## 受影响的老功能

### R2: 导出不受影响
- 步骤：导出一份报表
- 预期：与改动前相同
- 执行方式：script
- 命令：`./scripts/export-check.sh`
- 证据：运行输出
```

- **成功标准对照**：需求文档 `## 成功标准` 里每条 `S<n>` 至少对应一条用例；表里不能出现需求文档没有的 `S<n>` 或不存在的 `R<n>`。
- **受影响的老功能**：这一节同样写 `### R<n>` 用例（编号与用例清单连续）。技术方案的影响面列了开工前就有的文件时，这一节至少要有一条用例；否则写「不涉及」。
- **`bug`、`small`**：用例写在需求文档的 `## 回归用例` 一节，格式同上。`small` 有成功标准时，在这一节里也放一张对照表，开工前写好；
  `bug` 修完补一条用例（构建中阶段提示会提醒，todo 全勾时还没有用例 verify-artifacts 判失败）。`bug` 需求文档的批准指纹不算「回归用例」一节的内容，
  所以修完补用例不会让已确认的需求变成要重新确认；改了复现步骤或预期结果照旧要重新确认。
- **检查在哪里**：verify-artifacts 把不合格式的地方判失败（问题代码固定，如 `case-command-missing`、`criterion-uncovered`）；
  写 Plan 和构建期间阶段提示多一行列出前三个问题。解析只在 `hooks/regression_view.py` 一处，其他插件读 `regression_view.py --json`（见 `interface.json` 的 `regressionView`）。

### 多模块需求的整体联调回归

一个需求拆成多个模块、写了用法草案 `spec/usage/<需求>.md` 时，跨模块的联调用例写在 `spec/usage/<需求>.regression.md`：

- `## 用例清单`：用例格式同上；
- `## 成功标准 → 联调用例`：对照用法草案里的 `S<n>`，只放跨模块的成功标准，不要求每条都有；
- `## 涉及的模块`：能力图上的模块 id，每行一个（如 `` - `a` ``）。

它不是用法草案，不参与里程碑；verify-artifacts 查格式、涉及的模块在能力图上、对照表里的 `S<n>` 在用法草案里有。

## Plan `tasks/<id>/plan.md`

| 中文 | English |
|---|---|
| 任务 | Tasks |
| 检查点 | Checkpoints |

新流程模块的 Plan 只留任务列表（每个任务写验证方式）与检查点；架构决定和风险写在技术方案里。todo 照旧。

## 项目追加章节

项目特有的内容（前端的浏览器兼容、后端的数据迁移、游戏的试玩清单……）用 `.agent/config.json` 的 `projectSections` 声明，例如：

```json
{"version": 1, "projectSections": {"design": ["浏览器兼容"], "regression": ["视觉回归"]}}
```

文档种类只能是 `requirement`（需求文档）、`design`（技术方案）、`regression`（回归测试文档）。声明后，新流程模块的这几份文档在上面的骨架章节之外必须带上这些章节
（同样是二级标题，内容可以写「不涉及」）；`bug`、`small` 只写一份需求文档，只要求 `requirement` 的追加章节。用 `/spec-guard:config` 设置。
