# Plan: requirement-confirm-gate

<!-- spec-guard: review pending -->

Spec：[spec/requirement-confirm-gate.md](../../spec/requirement-confirm-gate.md)（2026-11-24 批准）。

## 架构决定

- **一个等待判定，排在所有批准分支前面**：新增 `module_stage.requirement_wait(root, module, raw_spec) -> str | None`，只对新流程模块（`flow_marker(...)["v2"]`）返回
  `"pending"`（原始状态 `none`／`pending`）、`"codex"`（原始状态 `codex-approved`，**不论指纹是否匹配**——`review_state` 对失配的 Codex 标记给 `revised`，所以要另读标记来源：
  有 Codex 标记行而没有用户批准行即为 `"codex"`）、`"revised"`（用户批准后又改过），已确认、老模块返回 `None`。来源判断复用 `review_marker_lines` 的解析结果，不另写正则。
- **提示**：`review_hint` 在 `invalid`／`unreadable` 两个分支之后、`effective_review`／`codex_hint`／`combined`／`pre_build_batch`／最终 gate 各分支之前，
  先看 `requirement_wait`；非 `None` 时直接返回需求确认的一行与下一步，Spec 的状态返回 `pending`（`revised` 时返回 `revised`）。这样合并批准节奏、修订攒批、最终验收都不会盖掉它（B1、B4）。
  `review_hint` 目前只在 `BEFORE_PLAN` 与 `BUILDING` 运行；新流程模块需求待确认时，`MODULE_DONE` 也运行这一判定（B2），`describe` 不把它当完成交接。
  `stop_node` 在 Spec 状态为 `pending`／`revised` 时本来就给 `spec-review`；在 `final` 判断前加一条：新流程需求待确认时停在 `spec-review`，`acceptance_step` 因而不生效（B2）。
  - 一行：「- 批准: 需求文档 `spec/<id>.md` 等用户确认。」；`"codex"` 时「…只有 Codex 的批准，需求要用户在对话里确认。」；`"revised"` 时「…确认后又改过，要用户重新确认。」（英文同义）。
  - 下一步（三种情形共用）：「在对话正文里复述需求（目标、给谁用、使用场景、业务规则和异常情形、不做什么、成功标准、待定问题，加上档位），问用户是否说完；给谁用、为什么做、
    怎样算做成、不做什么有一项写不出来、有你自己补的假设，或是重要需求时，先用 agent-skills 的 interview-me 一次问一个问题，问清再复述。用户在对话里确认后，用 <review-mark> 记下来；
    接管档位不能代替，Codex 的批准不算。确认前不要往下写。」重要需求时在「是重要需求」后附理由（`important()` 的理由码）。英文同义。
  - 模块 checkout：`role_view` 已经把 `review_hint` 的下一步换成「交给协调会话请用户审」，需求确认照此交给协调会话，不另写（B3 中的角色视图部分）；协调会话走普通提示。
- **第 2 轮审查补充**（Codex 第 2 轮后两轮上限，转用户批；以下各条随本 Plan 一起批）：
  - 协调会话：`role_view` 的协调分支已把 `review_step` 原样转交（只追加「在这里呈现给用户」），复述与拷问要求因此在协调会话可见；模块 checkout 只说交给协调会话。回归分别断言两种 checkout 的下一步。
  - 项目级 `DONE`（所有模块已完成、可能没有当前模块）与模块 checkout 的 `DONE` 分支会在 `review_hint` 之前返回：在这两个分支里，按 Build order 找第一个 `requirement_wait` 非 `None` 的新流程模块，
    有则加一行「- 批准: 需求文档 `spec/<id>.md` 等用户确认。」，下一步换成需求确认的那句；其 id 与结果进状态码。阶段值仍是 `DONE`。
  - 里程碑停点、越界（scope）、用法草案停点：需求确认与它们同时出现时，各自的事实行都保留；下一步的优先级为 用法草案停点 > 里程碑停点 > 需求确认 > 越界 > 最终验收——
    前两者讲的是别的模块或整个批次，要先处理；越界与最终验收都在需求确认之后。回归各覆盖一种组合（里程碑、越界）。
  - `reviewCadence=combined`：项目配置那一行（`config_lines`）不改，老模块输出不变；新流程模块需求待确认时，需求确认那一行末尾加「（批准节奏 combined 不适用于需求确认）」，下一步照旧是需求确认。回归断言 `combined` 下完整提示。
  - `/map` 表格与待批汇总：新流程模块的「Spec」列与待批汇总按 `requirementConfirm.status` 显示（`confirmed` 显示已批准，其余显示待确认），不再按原始 `codex-approved` 显示 Codex 勾号；`review.spec` 的 JSON 原始值不变。回归断言表格与汇总。
  - `at` 不用 `-S` 计数：取 `git log --format=%H%x09%cI -- spec/<id>.md`（新到旧），逐个 `git show <commit>:spec/<id>.md` 用 `review_marker_lines` 解析，找到当前批准行连续存在的最早一次提交；
    HEAD 里没有这一行时为 `None`。只对 `confirmed` 的新流程模块跑，提交数以 50 为上限，超过时为 `None`（不报错）。回归加一例：同一行先在代码围栏里作示例、后挪到围栏外生效。
  - 读不到需求文档：`/map --json` 按现有约定整体失败（退出 4），不出 `requirementConfirm`；Spec 假设 3「文档读不到时为 `null`」随本 Plan 修订为「读不到时 `/map --json` 整体失败（退出 4，同 `review`）」，见文末「Spec 修订」。
- **状态码**：`describe` 的 `facts` 加 `requirement_wait(...)` 的结果；`_role_facts` 里模块角色的事实同样加上，`pending`→`codex` 等变化会重发完整提示（B7）。
- **路由**：`codex_route(root, module, "spec")` 对新流程模块返回 `"requirement"`（排在 takeover 判断之前），`effective_review` 因而把 Codex 批准读成待批，`map_view` 的待批清单随之正确。
  `map_view.CODEX_ROUTE` 与 `interface.json` 的 `values.codexRoute` 加 `"requirement"`，`check-interface.py` 已按常量核对（B6）。这是公开取值的扩展，Spec 假设 7 随本 Plan 修订（见文末「Spec 修订」），交用户批。
- **一个取值函数**：`module_stage.requirement_confirm(root, module) -> dict | None`：老模块 `None`；新流程模块的 `status` 由 `requirement_wait` 推出：`None`→`confirmed`、`pending`／`codex`→`pending`、
  `revised`→`revised`，原始状态 `invalid`→`invalid`。`by`、`at`、`sha256` 按 Spec 假设 3；`sha256` 用批准标记的同一函数 `review_digest`。
  读不到需求文档时 `/map --json` 按现有约定整体失败（退出 4，`_review` 抛 `Unreadable`），不会走到这里，所以不另设 `unreadable` 取值（B5）。
- **`at` 的查法**（B3 中的 git 部分）：只在 `confirmed` 时查。先读 `git show HEAD:spec/<id>.md`，按 `review_marker_lines` 取出它的批准行；与工作区当前的批准行不同（还没提交、或删后重写未提交）时为 `None`。
  相同时 `git log -1 --format=%cI -S<该行> -- spec/<id>.md`：HEAD 含这一行，而文件里批准行至多一行，最近一次改变它出现次数的提交必是引入它的那次。git 失败、不在仓库时 `None`。
- **verify-artifacts**：批准标记那段的 python 已经逐文件算状态；新流程需求文档的 `requirement_wait` 为 `"codex"` 时多输出一行，shell 侧报警告
  「新流程需求文档：`spec/<id>.md` 只有 Codex 的批准，需求要用户在对话里确认」，指纹失配时同样报（AC7）。不改判失败的条件。
- **接口**：`interface.json` 加 `mapView.requirementConfirm`（描述）与 `mapView.flow.requirementConfirmStatus` 取值表，版本 1.19；`check-interface._flow` 核对取值表与代码常量一致。

## 任务

编码由我在本会话完成，每个任务先写回归、确认失败再实现。

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`。
- **Task 1**：`requirement_wait`、路由、提示与状态码（C1 的前两项）。回归（`test_flow_v2.py` 新类 `RequirementConfirmHintTest`，用 `describe` 的实际输出）：
  项目 `takeover` 为 `{"spec":"codex"}` 时，新流程模块的 `codex-approved`（指纹匹配与失配两种）不算批准、提示写明，老模块同配置下照旧算（AC3）；
  新流程模块无标记、`pending` 时出「等用户确认」一行与复述各项、拷问三种情形、review-mark（中英，AC6），`approved` 时这一行消失，`revised` 出重新确认的一行；
  `reviewCadence=combined`、有修订基线、todo 已全勾（`MODULE_DONE`）、`merge=auto` 且首个未勾选项是最终 gate 这四种情形下，需求待确认时仍显示需求确认、下一步不往下走（B1、B2）；
  模块 checkout 里需求待确认时下一步是交给协调会话；带 `last_state` 的相邻两次调用在 `pending`→`codex` 时返回完整提示（B7）；老模块无标记不出这一行（AC1）；阶段值与改动前相同（AC2）。
  验证：`test_flow_v2`、`test-phase-guard.sh`。
- **Task 2**：`requirement_confirm`、`/map --json`、接口（C1 第三项、C2、C5）。回归：`test_flow_v2.py` 覆盖四种 `status` 与 `by`（AC2）、`sha256` 等于 `spec-digest.py text`（AC5）、
  `at` 在已提交／未提交／历史上批准过、删掉后在工作区重新写回未提交／非 git 目录五种情形（AC4，用现有 git 夹具模板）；`test_map_view.py` 的 `MODULE_KEYS` 加 `requirementConfirm`、老模块为 `null`，
  新流程模块的 `codexRoute.spec` 为 `requirement` 且属于公开取值；`interface.json` 1.19 与 `check-interface.py`。`docs/commands.md` 的 `/map --json` 一句补字段。
  验证：`test_flow_v2`、`test_map_view`、`check-interface.py`。
- **Task 3**：verify-artifacts 警告（C3）。回归：`test-verify-artifacts.sh` 加三例——新流程需求文档只有 `codex-approved`（指纹匹配、失配各一）时报警告、不判失败；老模块同样标记不出这条警告（AC7、AC1）。验证：`test-verify-artifacts.sh`。
- **Task 4**：规则文字（C4）。`references/workflow-checkpoints.md`「需求确认」一节的「新流程模块的写法」按 Spec 假设 5 改；`test_flow_v2.py` 加一条断言读这一段的关键句（确认不能被接管代替、「不用拷问」只跳过拷问、重要需求不能跳过拷问）。
  `test_workflow_checkpoints.py` 不锁这一段（已核对），不改。验证：`test_flow_v2`、`validate.sh`。

## 会改哪些文件

- 新增：`tasks/requirement-confirm-gate/{plan,todo}.md`。
- 修改：`plugins/spec-guard/hooks/{module_stage,map_view}.py`、`plugins/spec-guard/hooks/verify-artifacts.sh`、`plugins/spec-guard/hooks/{test_flow_v2,test_map_view}.py`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、
  `plugins/spec-guard/hooks/test-phase-guard.sh`（仅当已有用例受影响）、`spec/requirement-confirm-gate.md`（Spec 修订）、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`plugins/spec-guard/references/workflow-checkpoints.md`、`docs/commands.md`。
- 新增依赖、锁文件：无。

## 风险

- **老模块的提示被误改**：所有新分支都以 `flow_marker(...)["v2"]` 为前提。缓解：AC1 的现有回归全绿；Checkpoint 1 用本仓库（全是老模块）新旧输出逐字比对阶段提示、`/map --json`（只多 `requirementConfirm: null`）、verify-artifacts。
- **`/map` 变慢**：`at` 要跑 git。缓解：只对新流程模块、且只在 `confirmed` 时跑一次 `git log -S`；本仓库没有新流程模块，开销为零。
- **递归**：`codex_route` 调 `important`，`important` 不调 `codex_route`；新原因只读 `flow_marker`（不调 `important`），不引入新递归。

## 检查点

- Checkpoint 1（report）：逐项给出 AC9 的证据（`/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 的退出码与末行，`check-interface.py`）；
  AC8 变异（让 Codex 批准对新流程也算、`revised` 当 `confirmed`）各让哪条回归变红；临时项目实跑：新流程模块在 `takeover` spec=codex 下写 `codex-approved` 看提示与 verify-artifacts、无标记看提示、批准后看 `/map --json` 的 `requirementConfirm`；
  本仓库阶段提示、`/map --json`、verify-artifacts 与改动前比对。证据记在 todo 的「证据」一节。
- Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行。`requirementConfirm` 取值发给 autopr-design 核对。本模块不发版（M2 在 takeover-redefine 一次发）。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 未决问题

- 无。

## Spec 修订

Codex 第 1 轮审查指出：新流程需求文档的 Spec 路由是新的取值，会出现在已有的 `/map --json` 字段 `codexRoute.spec` 里。Spec 假设 7 改为：
「`interface.json` 加 `mapView.requirementConfirm`，`values.codexRoute` 加取值 `requirement`（新流程模块的需求文档只由用户确认），接口 1.18 → 1.19」；AC9 加「新流程模块的 `codexRoute.spec` 为 `requirement`」。；假设 3 的 `sha256`「文档读不到时为 `null`」改为「读不到时 `/map --json` 整体失败（退出 4，同 `review`）」。两处都要用户批。

## 外部审查意见

<!-- spec-guard: codex-review round=1 blocking=8 sha256=7c0582c9d8f3 -->
<!-- spec-guard: codex-review round=2 blocking=2 sha256=96aea495b842 -->
