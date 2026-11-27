# 技术方案: sg-design-outline

<!-- spec-guard: review pending -->

需求文档：`spec/sg-design-outline.md`（用户 2026-11-27「确认需求」）。照已批总体技术方案第 7 节模块 6 那一行，不重新选型。

## 现状调研

查了下面这些（spec-guard 主干 `bed62906` 加本分支）：
- **章节定义**：`module_stage.DOC_SECTIONS`（`module_stage.py:87`）每种文档一组中英文章节，`design` 是六节。`test_flow_v2.SkeletonTest` 要求每一组的每一节都以 `| 中文 | English |` 出现在 `references/doc-skeletons.md` 里。
- **章节检查**：`flow_doc_problems()`（`:555`）按 `wanted` 组查每份已存在文档的章节，缺了判失败（`缺章节：…`）；章节可以只写「不涉及」。`verify-artifacts.sh:98-102` 调它，加上 `design_review_problems`、`plan_auto_problems`、`overall_problems`；遍历能力图里的全部新流程模块，不按完成状态跳过。
- **全新的判据**：`overall_design()`（`:149`）读需求文档的 `overall-design` 行：没有返回 `None`，重复或路径不合规返回 `{"path": None, "status": "invalid"}`，其余返回带路径的状态。
- **跨模块的判据**：`usage_draft.batches(project)`（`usage_draft.py:178`）返回 `[(提交, [这次新加的模块])]`，git 读不了时抛 `UsageDraftError`；`important()` 的 `multi-module` 就用它。
- **阶段提示里单独一行的写法**：`risk_list_line()`（`:1265`，模块 5 加的）只在 `NEEDS_REGRESSION` 出一行、进状态码，接在 `_describe_body` 的 `regression_line` 后面。
- **列表项与章节正文**：`regression_view._section_lines(text, names)` 给出某一节的行（带是否在代码块里）；`_section_has_content()`（`module_stage.py`）判一节有没有非空、非注释的内容。
- **下游**：hub 主干（`d1e0f2a5`）不读技术方案章节，也不跑 verify-artifacts 脚本；module-crew（`1797dd12`）`module_crew/protocol.py:747` 的 `_DESIGN_POINTS` 是 session-protocol 契约 v2.10 里「技术方案」交审消息的固定小项（现状调研、影响面、实现方案、风险与回滚、回归用例、受影响的老功能、未决问题），按名字核对交审消息，和文件章节无关。

没查的：已装 spec-guard 的其他项目里有没有带 `overall-design` 行的模块（这一行 0.98.0 才有，2026-11-27 发布）。

## 影响面

路径都从仓库根目录写起；越界检查按这里引用的路径判定范围。

| 文件 | 改什么 |
|---|---|
| `plugins/spec-guard/hooks/module_stage.py` | `DOC_SECTIONS` 加 `design-new`（四节）与 `design-interfaces`（模块接口）两组；`flow_doc_problems` 对全新的技术方案多查四节；新函数 `design_outline_case`、`design_outline_problems`、`design_outline_line`；`_describe_body` 接上提示行与状态码 |
| `plugins/spec-guard/hooks/verify-artifacts.sh` | 多调一个 `design_outline_problems` |
| `plugins/spec-guard/references/doc-skeletons.md` | 技术方案一节按三种情况给章节表 |
| `plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/references/node-rules.md` | 「技术方案审查」与「技术方案交审」写明三种情况 |
| `plugins/spec-guard/hooks/test_sg_design_outline.py`（新）、`plugins/spec-guard/hooks/test_flow_v2.py`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`plugins/spec-guard/hooks/test-verify-artifacts.sh` | 正反例；钉旧文字的断言改钉新文字，不删断言 |
| `scripts/validate.sh` | 登记新测试文件 |
| `docs/workflow.md` | 使用者说明一句 |
| `CHANGELOG.md` | 写本模块的条目（标题按发版方式：单独发写 `[0.100.0]`，和模块 7 一起发写 `[未发布]`） |
| 两份 `plugin.json`、`README.md`、`README.en.md`（**条件**） | 只在单独发 0.100.0 时升版本号与 `--ref`；和模块 7 一起发时本模块不改 |

## 实现方案

### 1. 判定（需求规则 1～4）

`design_outline_case(root, module)` 返回 `None`（老流程，或生效档位是 bug、small）或 `{"new": bool, "important": bool, "cross": bool}`：
- `new`：`overall_design()` 不是 `None` 且 `path` 不是 `None`（恰好一行、路径合规），不看状态；
- `important`：`effective_tier()["tier"] == "important"`；
- `cross`：`usage_draft.batches()` 里有一批同时含本模块和至少一个别的模块；抛 `UsageDraftError` 时为 `False`。`batches()` 的结果按项目根目录在本进程内缓存（模块级字典），一次阶段描述或一次 verify-artifacts 遍历只跑一次 `git diff` 加 `git log -p`。

### 2. 全新：四节判失败（需求规则 5～7、14）

- `DOC_SECTIONS["design-new"] = {"zh": ("技术选型", "架构图", "目录结构", "数据模型"), "en": ("Technology choices", "Architecture diagram", "Directory layout", "Data model")}`。
- `flow_doc_problems` 的 `wanted`：`kind == "design"` 且 `case["new"]` 时为 `("design", "design-new")`，否则照旧 `("design",)`。走现有的缺章节判失败，输出格式不变（多出的章节名接在后面）。
- 已完成的模块同样查（`flow_doc_problems` 本来就不按完成状态跳过）。

### 3. 重要需求与跨模块：两条警告（需求规则 8～10a）

`design_outline_problems(root, module)` 返回 `[(level, message)]`，只在技术方案存在时查：
- `important` 时数「方案取舍」（`Alternatives`）一节的列表项：用 `regression_view._section_lines`，不在代码块里、不是注释、匹配 `^(?:[-*+]|\d+[.)])\s+` 的行（不认缩进的续行）。少于 2 条（含这一节写成段落）→ `("warn", "`tasks/<id>/design.md` 是重要需求，「方案取舍」只列了 N 种做法，至少比较两种")`。
- `cross` 时找「模块接口」（`Module interfaces`）一节：没有，或 `_section_has_content` 为假 → `("warn", "`tasks/<id>/design.md` 所在需求一次插入了多个模块，缺「模块接口」一节（画出与同批模块之间的接口；没有直接接口写「无直接接口」并说明原因）")`。
- `DOC_SECTIONS["design-interfaces"] = {"zh": ("模块接口",), "en": ("Module interfaces",)}` 只为骨架测试与标题匹配，不进 `wanted`（缺了是警告，不是失败）。

`verify-artifacts.sh` 把它接在 `design_review_problems` 后面。

### 4. 阶段提示（需求规则 8、10、10a）

`design_outline_line(root, module, stage, zh)` 仿 `risk_list_line`：只在 `NEEDS_REGRESSION` 且技术方案存在时，把 `design_outline_problems` 的每条警告各写一行（以「- 技术方案大纲：」开头），返回 `(fact, lines)`；`fact` 是每条警告的规范化记录（种类，加上「方案取舍」的实际条数、「模块接口」是缺失还是为空），进状态码：渲染文字里会变的东西都在里面，比如 0 条改成 1 条、仍在警告时状态码也会变。其他阶段返回 `(None, "")`。

### 5. 规则文字（需求规则 11、12）

- `doc-skeletons.md` 技术方案一节：六节表照旧，后面加「全新项目或全新模块（需求文档恰好有一行格式正确、路径有效的 `overall-design` 行；重复、写坏或路径不合规的不算）再加四节」的表，与「一次插入多个模块时加『模块接口』」的表，写明图用 Mermaid 这类文本格式、重要需求的方案取舍至少两种做法。
- `workflow-checkpoints.md`「技术方案审查」开头加一段「写什么」，列三种情况与判法（「全新」同样写成恰好一行、格式正确、路径有效）；`node-rules.md`「技术方案交审」一句：全新时多出的四节要点放在「实现方案」一项里写，重要需求写出比较了哪几种做法，跨模块的写出与同批模块之间的接口要点。三处都由规则测试钉住。**不新增交审小项**：小项名由 session-protocol 契约定，module-crew 按名字核对。

### 6. 接口

不新增 `/map --json` 字段、不改 `review-mark`，`interface.json` 不升版本（需求 S7）。

## 接口和数据改动

| 位置 | 改动 | 旧调用方 |
|---|---|---|
| verify-artifacts 输出 | 有 `overall-design` 行的模块，技术方案缺四节时新增失败；重要需求、跨模块时可能新增两种警告 | hub 不跑这个脚本（`orchestrator/flow.py:83` 的 `verify_artifacts` 是它自己的函数，只读 `/map --json`）；使用者项目若在 CI 里跑 verify-artifacts，缺四节时会看到失败 |
| 阶段提示 | `NEEDS_REGRESSION` 可能多一两行「技术方案大纲」，状态码随之变 | 不读 |
| `DOC_SECTIONS` | 新增两组 | 只在本仓库内用 |

## 风险与回滚

- **已有 `overall-design` 行的模块升级后判失败**：这一行 0.98.0 才有，本仓库没有模块用过；其他项目可能有极少数，补上四节（可写「不涉及」）即可，CHANGELOG 写明。
- **列表项计数误判**：写法不是列表时会多提醒；只是警告，不挡流程。
- **批次判定要跑 git**：`batches()` 一次 `git diff` 加一次 `git log -p`。模块 5 起新流程的 `important()` 不再调用它，所以对新流程这是新增的开销。缓解：只在 `NEEDS_REGRESSION` 的提示和 verify-artifacts 里跑，结果按项目在进程内缓存，一次运行最多一次。
- **回滚**：一个 PR，revert 合并提交即可；已写进技术方案的新章节留着无害。

## 方案取舍

- **全新的四节走现有章节检查，两条警告另起一个函数**：选这样，因为四节是硬要求、和其他骨架章节同一种失败；两条警告要看内容（条数、有没有正文），放进章节检查会让「缺章节」的含义变杂。没选全部塞进 `flow_doc_problems`。
- **「模块接口」不进 `wanted`**：缺了只警告（Q3 A），进 `wanted` 就成了失败。
- **交审要点不加小项**：选把四节放进「实现方案」一项；没选加小项，因为小项名由契约定，要改得先改契约和 module-crew。
- **版本号在本模块 PR 里改**：按 PR 节奏「一个模块一个 PR，含版本号」；模块 5 那次另开版本号 PR 是因为漏了，不照做。若用户定模块 6、7 一起发，就只在模块 7 的 PR 里改，本模块不改。

## 待定问题

- **发版方式**（交用户定）：模块 6 单独发 0.100.0（本模块 PR 里改版本号与 CHANGELOG），还是和模块 7 一起发（本模块不改版本号，只把 CHANGELOG 写进 `[未发布]`）。

## 外部审查意见

<!-- spec-guard: design-review round=1 blocking=3 sha256=4fc7556e86e9 vendor=openai same-vendor=false criteria=design-v1 report=993cf9fa49019597bf4e7ce329e32d23653a8253ee69460a4c3f59c86065fad0 -->

第 1 轮（Codex，gpt-5.6-sol high，3 条阻断、3 条建议），逐条对照代码核实：
1. （阻断）`node-rules.md` 漏了跨模块的要求 → 采纳：交审一句加上「跨模块的写出接口要点」，由规则测试钉住。
2. （阻断）状态码只放警告种类，条数变了提示不刷新 → 采纳：放规范化记录（含实际条数、缺失还是为空），加「0 条改成 1 条」的用例。
3. （阻断）规则文字把「全新」简写成「有 `overall-design` 行」，比需求宽 → 采纳：三处都写成恰好一行、格式正确、路径有效。
4. （建议）「`important()` 已经跑同样的调用」前提错了 → 采纳：模块 5 起新流程不再调用，改写风险，并按项目在进程内缓存批次结果。
5. （建议）下游结论在审查材料里核不了 → 不改结论：是在本机两个仓库的 `origin/main` 上 `git grep` 后打开命中行核过的，提交号已写在现状调研里；审查快照没带这两个仓库。
6. （建议）发版方式没定，影响面不闭合 → 采纳：版本号文件标为条件影响面；发版方式在你批技术方案时一起定。
