# Spec: important-requirement

<!-- spec-guard: review approved eeeca5b6d661 -->

## Objective

「重要需求」由规则判定，不由 AI 自己判：判为重要的模块，Spec 一律由用户批（接管档位对它不生效），并且先做需求拷问；其余模块的 Spec 照档位
（勾了 codex 就交 Codex 审）。同时按用户 11-21「A 合成一轮」改需求确认的节奏：单模块需求在需求确认那一轮就附上能力图新行预览，一次答完，
到合并为止用户只介入这一次。

给谁用：在接管档位下提新需求的用户；推进模块的 agent；读批准状态的 module-crew 与 autopilot。

对外接口与用法草案一致吗：一致。对应 `spec/usage/auto-takeover.md` 入口「阶段提示的重要需求判定」，典型用法 U5。

登记：S101 合并方案 r2 第 2 节与 Q4（用户「按推荐批准」）；「新模块」按用户 11-21「确认插入；Q1 B」（一次需求拆出 2 个及以上模块）；
「A 合成一轮」由 ecosystem-lead #21898 转述；高风险路径接口由 ecosystem-lead #21913 转来（autopilot-hub 切片 4，`397014f`）。账本 T1T36MR。

## Assumptions

1. **三条判据，任一条成立就是重要需求**（判定只在一处：`module_stage.important(root, module)`，返回理由或空）：
   - **多模块**：这个模块和别的模块是同一批插入能力图的（同一提交，或工作区里同一批未提交的行；沿用 `usage_draft.batches`，不论有没有草案）。
   - **跨模块**：Spec 的「并行边界」一节写了公共文件类别，或独占路径与另一个未完成模块的独占路径重叠（沿用 `module_scope.overlap`）。
     没有并行边界一节时按 Q7。
   - **碰高风险路径**：Spec 并行边界的独占路径、或 Plan「预先声明」的公共路径，落在高风险路径清单里（T3 或 T4，按 Q9；通配符 `**` 跨目录、
     `*` 只匹配一层）。清单来源按 Q8；读不到时，档位勾了 spec=codex 的模块按重要处理（不放过），没勾的不受影响。
2. **判为重要时**：`codex_route(spec)` 返回 `important`，Codex 对这份 Spec 的批准不算数（读作待用户批准，写明理由）；阶段提示在 Spec 交审节点
   要求先用 agent-skills 的 `interview-me` 拷问、再交用户评审，并写出命中了哪一条判据。Plan 不受影响（照档位）。
3. **需求确认的节奏**（「A 合成一轮」）：
   - 单模块需求：总结需求时同一轮附上 `add-module` 的能力图新行预览，用户一次回答「说完了，确认插入」；Spec 之后照档位走（人批另交审，
     Codex 批不再打扰用户）。
   - 多模块需求（一次拆出 2 个及以上模块，本身就是重要需求）：仍分两轮——先确认需求说完并做需求拷问，下一轮再出能力图、用法草案与并行评估。
     理由：拷问结束前拆法还会变，先给能力图预览等于让用户批一个会被推翻的拆法；多模块那一轮内容多，和需求确认挤一轮反而难审。
   - 非重要需求也保留「总结需求、问是否说完」这一问（Q4）。
4. **不变的**：bug 只做确认、不拷问（「需求确认」一节的「不触发」照旧）；能力图永远由用户批；已批准的 Spec 不因后来判为重要而作废，只影响之后的批准。
5. **接口**：同在 1.15。`/map --json` 每个模块加 `important`：`null` 或 `{"reasons": [...]}`（`multi-module`、`cross-module`、`risk-path`、
   `risk-unknown`）。版本号不在本模块改。

## Contract

### C1 判定（`hooks/module_stage.py`）

- `important(root, module) -> list[str]`（理由，空表示不重要）；`codex_route` 对 Spec 在 `takeover` 之后、`""` 之前加 `important`。
- 高风险清单读取按 Q8 的方式；格式 `autopilot.risk-paths/v1`：`{"schema", "category", "default", "T4": [...], "T3": [...]}`。

### C2 阶段提示

- Spec 交审节点（Spec 待批准，或 Codex 批过但判为重要）：批准行写明「重要需求（理由）」，建议下一步要求先 `interview-me` 再交用户评审（中英）。
- 不重要、或档位没勾 spec=codex 的模块：输出与改前逐字相同（只有勾了 codex 时才有「Codex 批不算」的差别；没勾时重要与否都由用户批，不加行）。

### C3 `/map --json`

- 每个模块加 `important`（假设 5）；`interface.json` 写明。

### C4 规则与说明

- `references/workflow-checkpoints.md`「需求确认」按假设 3 改「确认后停一轮」那一条；「自治档位与底线」写明重要需求的三条判据。
- `references/node-rules.md`「能力图审阅」开头一条按假设 3 改（单模块合成一轮）；「Spec 交审」加一条重要需求先拷问。
- `commands/add-module.md`、`skills/spec-guard-ops/SKILL.md`（add-module：单模块需求的预览与需求总结同一轮）、`docs/workflow.md`。

## Acceptance criteria

- **AC1** 判据（单测）：同批插入两个模块 → `multi-module`；并行边界写了公共类别或独占路径与另一未完成模块重叠 → `cross-module`；
  独占路径命中 T4 或 T3 的通配 → `risk-path`；清单读不到且 spec=codex → `risk-unknown`；单独插入、无公共、无重叠、不命中 → 空。
- **AC2** 生效：spec=codex 且重要时，Spec 的 `codex-approved` 读作待用户批准并写明理由；不重要时读作已批准；Plan 照档位不受影响。
- **AC3** 阶段提示（`test-phase-guard.sh` 新段）：重要需求的 Spec 交审节点要求先 `interview-me`、写明理由（中英）；不重要或没勾 codex 时输出与改前逐字相同。
- **AC4** `/map --json` 的 `important` 字段（`test_map_view.py`）；`interface.json` 与 `check-interface.py` 一致。
- **AC5** 规则：「需求确认」有单模块合成一轮、多模块仍分两轮及理由、保留确认一问；「能力图审阅」「Spec 交审」相应一条；字节上限内；
  `validate.sh`、phase-guard、verify-artifacts 全绿。

## Boundaries

- **会做**：C1～C4 及回归。
- **先问再做**：增删判据；让 AI 自己判断是否重要；让判为重要影响 Plan 的批准。
- **不做**：调用或改动 autopilot；越界检查（`takeover-scope-check`）；版本号与发版。

## 未决问题

- **Q7 没有「并行边界」一节的 Spec 怎么算跨模块**（2026-11-22 用户选 A）：
  - **A（推荐）**：档位勾了 spec=codex 的模块，没写并行边界就判为重要（`cross-module` 未判定），Spec 由用户批；没勾的不受影响。
  - **B**：没写就当作不跨模块。
- **Q8 高风险路径清单从哪读**（2026-11-22 用户选 A：读 `.agent/risk-paths.json`）：合并方案定的是「调用方向只能是 autopilot → 插件，插件不认识 autopilot」，而清单接口是 autopilot 的命令。
  - **A（推荐）**：autopilot 体检时把清单写成项目里的一个文件（例如 `.agent/risk-paths.json`，格式 `autopilot.risk-paths/v1`），spec-guard 只读这个文件；
    文件随仓库提交，改它属于高风险改动由用户审。需要 autopilot 那边配合写文件（我去和 autopr-design 对齐）。
  - **B**：spec-guard 直接调 autopilot-hub 的 `risk/cli.py`，钉住 hub 的提交。违背上面的调用方向，还要知道 hub 检出在哪。
- **Q9 T3 算不算**（2026-11-22 用户选 A：T3、T4 都算）：
  - **A（推荐）**：T3、T4 都算（autopr-design 的建议）。
  - **B**：只算 T4。

## 并行边界

- 独占：`spec/important-requirement.md`、`tasks/important-requirement/`
- 公共：无

## 文档建议

改 `commands/add-module.md`、`skills/spec-guard-ops/SKILL.md`、`docs/workflow.md`、`docs/commands.md`（`/map` 的 `important`）。CHANGELOG 与 README 在
最后一个模块统一写。项目没有文档基线。
