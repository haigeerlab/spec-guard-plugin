# Plan: takeover-redefine

<!-- spec-guard: review approved -->

Spec：[spec/takeover-redefine.md](../../spec/takeover-redefine.md)（2026-11-25 批准，Q1 A、Q2 A、Q3 A）。Codex 审两轮仍有阻断，交用户；2026-11-25 用户「按处理办法改，都批准」（Plan 与 Spec 修订：假设 2、4、C4、AC3、AC8）。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 架构决定

- **两组项，一个读取入口**（`project_config.py`）：
  - `ITEMS` 改为新三项 `design`（`human`／`reviewer`）、`merge`、`release`；`LEGACY_ITEMS = {"spec": ("human","codex"), "plan": ("human","codex")}` 只给老流程模块读。
  - `PRESETS` 改为 `none`／`design`／`merge`；旧预设 `plan` 只读不写。`valid_takeover` 认新旧两种写法（旧预设 `plan`、自定义里的 `spec`／`plan`），取值不合法照旧整个键无效。
  - `expand(value)` 返回新三项（换算后：旧 `plan` → 全 `human`；旧 `merge` → `design=reviewer, merge=auto`；旧自定义去掉 `spec`／`plan`）。
    `legacy(value)` 另返回老流程的 `spec`、`plan`（Spec 假设 5）：`none` → 都 `human`；`plan`、`design` → `plan=codex`；`merge` → 都 `codex`；
    自定义：写了 `spec`／`plan` 的按所写，没写 `plan` 而 `design=reviewer` 时 `plan=codex`，其余 `human`。
  - `module_takeovers` 仍是唯一读取入口，每个模块返回五个键（新三项 + `legacy` 两项），来源不变。
- **每个读取点用哪几项**（R1-2）：
  - `module_stage._takeover_item(…, "spec"|"plan")`、`codex_route`、`effective_review`：老模块读 `legacy` 两项，判定不变；新流程模块本来就不走到这里（需求 `requirement`、Plan `auto`）。
  - `important()` 的 `codex` 判断（决定 `cross-unknown`／`risk-unknown` 算不算）：老模块读 `legacy` 的 `spec`（不变）；新流程模块一律为假——需求永远由用户确认，
    否则没有风险清单的项目在 `design` 档位下每个模块都会被判为重要需求（R2-1）。与现状的差别只在旧 `merge` 预设下的新流程模块：不再因 `cross-unknown`／`risk-unknown` 升为重要需求。
  - 老流程的越界检查（`scope_overreach` 第 2196 行、`module_scope._takeover_module`）：五个键里有一项不是 `human` 就查。`design=reviewer` 对老模块即 `plan=codex`，结果与旧值一致。
  - `merge`、`release` 的读取点（`review_mark` 最终验收、`module_stage` 合并提示）不变。
- **set 拒收旧写法**：`set --key takeover|moduleTakeover` 的值是旧预设 `plan`，或自定义里有 `spec`、`plan`、`requirement` 时，退出 2、不写，拒绝码 `takeover-legacy`，提示改用新取值（`plan` → `design`）。
  预览与写入共用这一个校验；读文件用 `valid_takeover`（认旧值）。
- **`show`**（R1-6）：`summary()` 的 `value` 仍是文件原值；`takeover`、`moduleTakeover` 两项在 JSON 里加 `effective`（新三项）与 `legacy`（老流程两项），文本输出在原行后加一行 `effective: design=… merge=… release=… · old-flow modules: spec=… plan=…`。
  存的是旧预设 `plan` 时加 `note: takeover=plan is read as none; to keep the second reviewer approving, set design (needs the user's words)`；
  自定义含 `spec`／`plan` 时加 `note: spec and plan no longer apply to flow v2 modules; old-flow modules still read them`（Spec 假设 4 写「已不生效」，按 Q1 A 老模块仍读，措辞据此写准）。
  `set` 预览照旧列改前／改后，`takeover:` 一行列新三项再加老流程两项；改前是旧值 `plan` 时同样出上面的 `note:`。
- **收窄**（R1-1，按 Spec 假设 6）：
  - 预设阶梯 `none` → `design` → `merge`；旧预设 `plan` 收一格到 `none`，记录照写 `from: "plan"`；之后用 `set` 设为 `none` 或 `design` 都算恢复、删除记录（Spec 假设 4 修订；`_keep_narrowed` 对这两个值单独处理，含设成与当前相同的 `none`）。
  - 自定义按 `release`、`merge`、`design` 的顺序交还一项，写回新格式（旧 `spec`／`plan` 键去掉）；换算后已是全 `human` 但旧项还有 `codex` 的（如 `{"plan": "codex"}`）收一格到 `none`。
  - 宽严比较（`takeover_wider`、`narrower_or_equal`、`widen_steps`、`widerThanProject`）一律按换算后的新三项；`from: "plan"` 的恢复规则只写在 `_keep_narrowed` 一处。
- **技术方案由谁批**（`module_stage.py`）：`design_requirement` 返回值加 `approver`：重要需求 `user`；否则读模块的 `design`，`reviewer` → `reviewer`，`human` → `user`。
  - `design_approval`：`reviewer-approved` 只在 `approver == "reviewer"` 时算放行。`approver == "user"` 时：`need == "none"` → `pending-user`（Q2 A）；
    `need == "review"`：标记是 `reviewer-approved`（指纹对得上）→ `pending-user`；两轮仍有阻断 → `pending-user`；有阻断未满两轮 → `in-review`；未审（selection none）→ `unreviewed`；其余 → `pending-review`。
    `pending-user` 因此总绑定当前正文：审完无阻断记 `reviewer-approved <指纹>`，用户批之前改了稿就变 `revised`、要重审（R2-2）。`approvedBy` 取值不变。
  - `revised`（R1-4）：按 `need` 与 `approver` 一起分流：`need == "review"` 的先重新审（不论 `approver`），`approver == "user"` 的审完无阻断记 `reviewer-approved`、再交用户；`need == "none"` 或重要需求直接交用户。
  - `design_waits`（R1-5）：除现有规则外，技术方案带 `reviewer-approved` 标记而 `approver == "user"`（档位后来改成了 `human`）时，在 `NEEDS_REGRESSION`、`NEEDS_PLAN`、`BUILDING` 都拦住。
  - `design_hint`（R1-3）：理由表加 `takeover`（`接管档位 design=human` 并写来源：`moduleTakeover`、`takeover` 或默认）；
    `need == "none"` 且 `approver == "user"` 单列一个分支（直接交用户，不先审）；`need == "review"` 且 `approver == "user"` 的待审、复审提示里写「没有阻断就记 `reviewer-approved`，这不算放行，接着交用户批」；
    非重要需求的 `pending-user` 按实际原因写（两轮仍有阻断，或档位要人批），不再一律写「两轮仍有阻断」。
    两条路线（`reviewer` 与 `human`）的提示都写档位来源：`moduleTakeover`、`takeover`、默认，或「继承项目 `takeover`（模块的 `moduleTakeover` 无效）」——
    来源另由 `project_config` 给出一个只供提示用的说明，`/map --json` 的 `source` 取值与含义不变（R2-5、R1-3 遗留）。
  - 状态码（R2-3）：`_describe_body` 的状态事实加上技术方案的 `status` 与轮次数，状态一变就重新注入完整提示；`_role_facts()` 同样读这两项。
  - 模块 checkout 的角色提示（R2-4）：`role_view()` 改写下一步时，按 `design_hint` 给出的批准路线写（`reviewer` 路线由第二审查者放行、`human` 路线审完交用户），协作约束照旧。
  - `design_review_problems` 的警告条件改为 `approver == "user"` 且只有 `reviewer-approved`（重要需求照旧，`design=human` 新增）。
- **review-mark**（Spec C4 修订）：`--target design --state reviewer-approved` 不论 `approver` 都可记；`approver == "user"` 时输出加一句「不算放行，仍要用户批（`--state approved`）」，与重要需求现在的提示同一口径。
- **`/map --json` 的 `takeover`**（R1-7）：`map_view.TAKEOVER_FIELDS` 改为 `design`、`merge`、`release`、`spec`、`plan`、`designForcedBy`、`source`、`widerThanProject`、`narrowed`，行对象按它组装；
  `spec`、`plan` 取 `legacy` 两项（新流程模块也照这样报，Q3 A），`interface.json` 标 deprecated、下一版删除；`design` 报生效值：重要需求的新流程模块报 `human`、`designForcedBy: "important"`，否则 `designForcedBy: null`。
  `widerThanProject` 按配置的新三项比。接口 1.22，`check-interface.py` 比对键集合。
- **验证口径**：老流程的现有回归（Codex 批 Spec／Plan、越界检查）在旧值下行为不变；直接断言旧取值写法、收窄阶梯、预设展开、`/map` 键集合的用例跟着改，原因逐条记在 todo。
  并行边界外的测试文件（`test_important_requirement.py`、`test_module_scope.py`、`test_workflow_checkpoints.py`、`test_stop_rules.py`）不改（R1-8）：新增断言放在边界内的文件里；
  若这些文件的现有用例因本模块变红，停下交用户（改模块范围）。

## 任务

- **Task 0**：提交 Spec 批准、本 Plan 与 todo。验证：`verify-and-commit` 快档。
- **Task 1**：取值、换算、set 拒收、`show`。先改／写会红的 `test_project_config.py` 用例：新预设展开（AC1）；旧值换算、`effective`／`legacy` 字段与两条 `note:`（AC2）；
  `takeover-legacy` 拒绝且文件字节不变（项目键与 `--module` 两种，AC1）；`legacy()` 换算表逐行（含 `{"design": "reviewer"}`、`{"plan": "human", "design": "reviewer"}`）。再实现。
  `test_flow_v2.py` 加：没有风险清单的普通新流程模块，档位在 `none`、`design`、旧 `merge` 之间切换，`important` 都为空、只改变技术方案的批准路线；老模块在旧 `merge` 下照旧有 `risk-unknown`。
  验证：`test_project_config.py`、`test_flow_v2.py`、`test_review_marker.py`、`test-phase-guard.sh`（老流程 Codex 批准与越界检查在旧值、新值 `design` 下不变，AC5）。
- **Task 2**：收窄。`test_project_config.py` 的收窄用例改为新阶梯（`merge` → `design` → `none`）、旧 `plan` → `none`、`from: "plan"` 的记录设 `design` 后删除、自定义按 `release`／`merge`／`design` 收并写回新格式、
  `{"plan": "codex"}` 收到 `none`、`from: "plan"` 的记录在设 `none`（与当前相同）或 `design` 后删除、放宽一次一格在新旧值之间照样成立；先红后实现。验证：同上文件（AC6）。
- **Task 3**：技术方案的批准人。先写会红的 `test_flow_v2.py` 用例：`design=human` 下 待审 → 审过无阻断仍 `pending-user` → 用户批准后 `approved`；不需要审直接 `pending-user`；
  `design=reviewer` 现状不变；重要需求不论档位交用户（AC3、AC4）；`revised` 在 `human` 档位下先出复审提示、复审后 `pending-user`；已有回归文档、档位由 `reviewer` 改成 `human` 时在构建中仍被拦；
  用户批之前改稿 → `revised` → 重审后再 `pending-user`；阶段提示文字（两条路线 × 档位来源 默认／`takeover`／`moduleTakeover`／模块覆盖无效）；
  状态从 `pending-review` 变到 `pending-user` 时状态码改变、下一轮重新注入完整提示；模块 checkout 的角色提示按路线写。
  `test_review_marker.py`：`design=human` 下 `reviewer-approved` 可记、输出写明仍要用户批；`--state approved` 之后放行。
  再实现。验证：这两个文件、`test-phase-guard.sh`。
- **Task 4**：`/map --json` 与接口 1.22。`test_map_view.py`：`takeover` 的精确键集合与 `interface.json` 一致；`designForcedBy`（重要需求 `important`、普通 `null`）；
  老模块的 `spec`／`plan` 在旧值 `plan`、新值 `design`、旧自定义下的取值；新流程模块带旧自定义时照报 `spec`／`plan`（Q3 A）；老模块 `codexRoute`、`reviewApprovedBy` 不变（AC4、AC5、AC7）。
  先红后实现；`interface.json`、`check-interface.py`。验证：`test_map_view.py`、`check-interface.py`。
- **Checkpoint 1（report）**：完整档三条检查全绿；在临时副本里做变异（`legacy()` 去掉 `design → plan=codex`；`reviewer-approved` 不看 `approver`；`designForcedBy` 不看重要需求；收窄不认旧 `plan` 的那一格），各自让对应用例变红，还原后全绿。
- **Task 5**：verify-artifacts。`test-verify-artifacts.sh` 加：`design=human` 而技术方案只有第二审查者放行时警告；旧预设 `plan` 与带 `spec`／`plan` 的旧自定义不判无效。先红后实现。验证：`test-verify-artifacts.sh`。
- **Task 6**：规则与文档。`commands/config.md` 的两行与示例、兼容表与「团队都升级后再设置」；共享检查点规则「技术方案审查」加 `design` 档位一条；`docs/commands.md`、README 的接管档位与新流程段落；
  CHANGELOG「未发布」补 design-review、plan-auto-approve、takeover-redefine 三条。验证：快档（含读规则文件的现有回归）。
- **Checkpoint 2（gate）**（R1-9）：最后一次改动后重跑完整档三条（`validate.sh`、phase-guard、verify-artifacts）并全绿；推送、开 PR、提议宿主 PR 监控；
  最终验收与合并合成一问（merge-ask-no-wait），验收消息写明当前头提交的 `CI required` 结果，还没出结果就写明，合并用只认头提交、必需检查通过才合的自动合并（AC8 修订）；给出给 autopr-design 与 module-crew 的拟回告（Spec 假设 11），发出要用户同意；发 0.95.0 另取授权。

<!-- spec-guard: codex-review round=1 blocking=9 sha256=5f5699f8c6e5 -->

## 外部审查意见

<!-- spec-guard: codex-review round=2 blocking=5 sha256=9cceb45c96fb -->
