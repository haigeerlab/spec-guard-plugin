# Plan: flow-doc-skeletons

<!-- spec-guard: review approved -->

Spec：[spec/flow-doc-skeletons.md](../../spec/flow-doc-skeletons.md)（2026-11-24 批准）。

## 架构决定

- **流程标记分两层解析，避免递归**：`important()` 为跳过已完成模块会对其他模块调 `module_state()`，所以阶段不能依赖 `important()`。
  - `flow_marker(root, module) -> {"v2": bool, "tier": str|None, "problems": [...]}`：只读 `spec/<id>.md` 代码块外的 `<!-- spec-guard: flow v2 tier=<档位> -->`，不调 `important()`；
    档位不在四个值里时 tier 按 `normal`、problems 记 `tier-invalid`；没有标记时 `{"v2": False, "tier": None}`。拆出 `_base_state(root, module)`：现行 `module_state` 的全部计算，阶段按 `flow_marker` 的原始档位定。
  - `effective_tier(root, module)`：在 `flow_marker` 之上加 `important()` 的纠正（有理由而档位不是 `important` 时按 `important`、记 `tier-below-rule`）。
  - 对外的 `module_state` = `_base_state` + 纠正：只有 v2、原始档位是 `bug`／`small`、基础阶段是 `NEEDS_PLAN` 或之后时才调 `effective_tier`；纠正为 `important` 就按完整文档重算阶段（缺技术方案 → `NEEDS_DESIGN`，缺回归 → `NEEDS_REGRESSION`）。
  - `important()` 判断其他模块是否完成改用 `_base_state`，不再调对外的 `module_state`，所以不会递归。
- **阶段只在 `module_state` 里多两步**：v2 且档位是 `normal`／`important` 时，有需求文档、缺 `tasks/<id>/design.md` 为 `NEEDS_DESIGN`，再缺 `tasks/<id>/regression.md` 为 `NEEDS_REGRESSION`，之后同现行。
  新增常量 `BEFORE_PLAN = ("NEEDS_DESIGN", "NEEDS_REGRESSION", "NEEDS_PLAN")`。`module_stage.py` 里 `stage == "NEEDS_PLAN"` 共 10 处，逐处定：
  - 第 647 行 `stop_node()` 的 `plan-review`：**不替换**，仍只在 `NEEDS_PLAN` 触发；两个新阶段在 Spec 已批准时没有交审停点（技术方案的停点归 design-review）；Spec 待批、修订等待的判断（第 644 行）本来就不看阶段，新阶段照样停在 `spec-review`。
  - 第 980、991 行（修订合批的适用范围）、第 1137 行（外部审查提议 Spec）：替换为 `in BEFORE_PLAN`。
  - 第 1016、1062 行的「先不要写 Plan」：新阶段改说「先不要写技术方案／回归文档」（按当前缺的文档）。
  - 第 1020、1066 行（`combined` 节奏）的入口条件 `stage == "NEEDS_PLAN"` 改为 `in BEFORE_PLAN`；第 1020、1066 行与第 1025～1032、1071～1076 行（修订合批）的下一步：v2 模块改为先指向当前缺的文档
    （技术方案 → 回归 → Plan，带骨架引用），说明写齐后再一起交审；老模块原文不变。所有提示写 Plan 的 v2 分支（默认、`combined`、修订合批）共用同一句 Plan 骨架引用。
  - 模块 checkout（第 1225～1233 行）：`review_hint` 返回非空时照现行规则停下交协调会话，v2 模块不另开例外（与老模块在同一情形下的行为一致）；只有没有待批事项时才走新阶段的下一步。
  - 第 1033、1077 行：替换为 `in BEFORE_PLAN`。
  - 第 1237 行（模块会话提示）：新阶段各加一条，指向对应文档与骨架。
  老模块拿不到新阶段，这些分支对它们结果不变。
- **下一步文本**：`next_step` 与模块会话的提示各加 `NEEDS_DESIGN`、`NEEDS_REGRESSION` 两条（中英），写明文件路径与骨架 `references/doc-skeletons.md`；`NEEDS_PLAN` 在 v2 模块上补一句「Plan 只留任务列表」并指向骨架里的 Plan 一节（中英、主 checkout 与模块会话都加）。
- **骨架**：`references/doc-skeletons.md` 列四份文档与 bug、small 两种合一写法的章节名，中英各一套；verify-artifacts 与回归从同一处读章节名（`module_stage.DOC_SECTIONS`），不在 bash 里另写一份。
- **`/map`**：`tier` 取自 `flow_info`；`step` 在两个新阶段上为 `design`、`regression`；表格视图对 v2 进行中模块的「步骤」列显示对应文字。
- **verify-artifacts**：新增一段，调 Python 逐个 v2 模块按档位检查该有的文件与 `DOC_SECTIONS` 里的章节（标题存在即可，正文可以是「不涉及」）；缺失判失败，`tier-invalid`、`tier-below-rule` 判警告。老模块不进这段。

## 任务

编码由我（Claude）在本会话完成，每个任务先写回归、确认失败再实现。

- **Task 0**：提交 Spec、本 Plan 与 todo。验证：`validate.sh --quick`。
- **Task 1**：`references/doc-skeletons.md`、`DOC_SECTIONS`、`flow_marker`、`effective_tier`。回归（新文件 `test_flow_v2.py`）：无标记、四种档位、档位写错、规则判重要而档位较低、代码块里的标记不算。验证：`test_flow_v2`。（AC4 的判定部分）
- **Task 2**：`module_state` 的新阶段、`BEFORE_PLAN` 替换、下一步文本。阶段提示在 `effective_tier` 有 problems 时加一行写明档位问题与按什么处理（AC4）。回归：`test_flow_v2.py` 覆盖 AC2、AC3 的阶段序列、AC4 的提示行与 AC6 的提示文字（中英，含 v2 `NEEDS_PLAN` 指向骨架）；
  另加：原始档位为 `bug`、`small` 但 Spec 声明了公共文件（规则判为重要）的模块，阶段按完整文档推进；两个都声明并行边界、互相重叠的 v2 模块，`module_state` 与阶段提示能结束并给出预期阶段（不递归）；`combined` 节奏下 Spec 待批、有基线的修订 Spec 两种情况，主 checkout 的新阶段下一步指向当前缺的文档并带骨架引用（中英），模块 checkout 照现行规则停下交协调会话；
  Spec 已批准时两个新阶段的停点不是 `plan-review`；`test-phase-guard.sh` 加 v2 项目的端到端用例（阶段提示 JSON 里的阶段与下一步）。
  先跑现有全部回归确认 AC1（老模块不变）。验证：`test_flow_v2`、`test-phase-guard.sh`、`test_module_stage_sanitization`、`test_review_marker`、`test_codex_review`。
- **Task 3**：`/map` 的 `tier`、`step`、表格；`interface.json` 1.18（`mapView.tier`、`stage`／`step` 新取值）、`check-interface.py`。回归：`test_map_view.py` 现有用例只改一处——字段集合常量 `MODULE_KEYS` 加 `tier`。这与 Spec AC1「现有回归不改」冲突，已在 Spec 修订中把 AC1 改为
  「现有回归除字段集合常量加 `tier` 外不改」，随本 Plan 一起交用户批；其余现有断言原样通过。新加的用例在新类里：老模块为 `null`，v2 模块各阶段的 `step`、`tier`、档位纠正。验证：`test_map_view`、`check-interface.py`。
- **Task 4**：verify-artifacts 的 v2 检查。回归：`test-verify-artifacts.sh` 加缺技术方案、缺章节、写「不涉及」、bug／small 只要需求文档、档位警告、老模块不查的用例（AC5）。验证：`test-verify-artifacts.sh`。
- **Task 5**：`workflow-checkpoints.md` 写需求与写 Spec 的停点加「新流程模块」一段（指向骨架、写流程标记与档位）；`docs/commands.md` 的 `/map --json` 一句补 `tier`。验证：`validate.sh`（含读规则文档的回归）。

## 会改哪些文件

- 新增：`spec/flow-doc-skeletons.md`、`tasks/flow-doc-skeletons/{plan,todo}.md`、`plugins/spec-guard/references/doc-skeletons.md`、`plugins/spec-guard/hooks/test_flow_v2.py`。
- 修改：`plugins/spec-guard/hooks/{module_stage,map_view}.py`、`plugins/spec-guard/hooks/verify-artifacts.sh`、`plugins/spec-guard/hooks/{test-phase-guard,test-verify-artifacts}.sh`、`plugins/spec-guard/hooks/test_map_view.py`、
  `plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`plugins/spec-guard/references/workflow-checkpoints.md`、`docs/commands.md`；新测试文件按仓库规则登记到 `validate.sh`（test-registration-check）。
- 新增依赖、锁文件：无。

## 风险

- **漏改某处 `NEEDS_PLAN` 判断**：v2 模块在 `NEEDS_DESIGN` 时 Spec 待批却没被拦。缓解：Task 2 先列出全部比较点逐处判断；回归加「v2 模块 Spec 待批时在 `NEEDS_DESIGN` 提示等批准」的用例。
- **`next_step[stage]` 是字典取值**：新阶段漏写会 KeyError，hook 输出诊断 JSON 而不是提示。缓解：中英两个字典、模块会话提示都加，回归覆盖两种语言。
- **其他插件读 `stage`**：module-crew、autopilot 可能把未知阶段当错误。缓解：只出现在 v2 模块上（发版前没有 v2 模块），接口说明写明新取值；M1 发版时通知各插件。
- **verify-artifacts 是 bash**：中文章节名经命令行传递易出编码问题。缓解：检查逻辑全在 Python，bash 只接结果行；macOS `/bin/bash` 下跑。

## 检查点

- Checkpoint 1（report）：逐项给出 AC8 的证据（macOS 下一律用 `/bin/bash` 跑；`validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh`、`check-interface.py` 的退出码与末行、接口版本）；变异（去掉标记识别、bug／small 不跳过、verify-artifacts 不查章节）各让哪条回归变红；
  在临时项目里用一个 v2 模块从只有需求文档走到 `DONE`，记下每一步的阶段提示与 `/map` 的 `stage`、`step`、`tier`；本仓库跑一次阶段提示与 `/map --json`，与改动前的输出比对：`/map --json` 去掉每个模块的 `tier`（校验其为 `null`）后其余逐字相同；阶段提示逐字相同；
  verify-artifacts 对本仓库与一个老模块夹具的输出和退出码与改动前相同。证据记在 todo 的「证据」一节。
- Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行。本模块不发版（M1 在 project-sections 发版）。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 未决问题

- 无。

## 外部审查意见

<!-- spec-guard: codex-review round=1 blocking=5 sha256=d6de3e5f98d3 -->
<!-- spec-guard: codex-review round=2 blocking=4 sha256=804da85a9910 -->
