# Spec: takeover-redefine

<!-- spec-guard: review approved 6b87c96e3254 -->

## Objective

开发流程改版（S110）M2 的最后一个模块。用法草案 `spec/usage/dev-flow-v2.md` A 节定了新的接管档位：需求永远由用户确认、Plan 永远自动批准，
能配的只剩技术方案（`design`：`human`／`reviewer`）、合并（`merge`）、发布（`release`）；预设改为 `none`／`design`／`merge`。
现在 `takeover`／`moduleTakeover` 仍是旧的四项 `{spec, plan, merge, release}`、预设 `none`／`plan`／`merge`：新流程模块的需求与 Plan 已由
requirement-confirm-gate、plan-auto-approve 固定，`spec`、`plan` 两项对它们不起作用；而技术方案该由人批还是第二审查者放行，
design-review 目前不看档位（非重要需求审过即放行）。本模块把档位换成新定义，读旧值时按兼容表换算，`/map --json` 给出已算入「重要需求人批」的生效档位。

给谁用：用 spec-guard 新流程的项目里的 agent 与用户；读 `/map --json` 的 autopilot、module-crew；用 `/spec-guard:config` 设档位的用户。

对外接口与用法草案一致吗：取值、预设、兼容表与草案 A 节一致。草案没写的三处在下面补上，见 Q1～Q3：老流程模块怎么读新档位（Q1），
`design=human` 时不需要审的技术方案要不要人批（Q2），`/map --json` 里旧的 `spec`、`plan` 两个字段怎么处理（Q3）。

登记：用法草案 dev-flow-v2（用户 2026-11-24「确认插入，Q1–Q6 按推荐」，草案 Q6 定为「切换时把 `takeover=plan` 映射为 `design`，逐个仓库要用户原话」），M2 里程碑。
需求确认沿用草案的确认，本 Spec 交审即确认范围；2026-11-25 用户回「批准；Q1 A；Q2 A；Q3 A」；写 Plan 时修订假设 2、4、C4、AC3、AC8，用户回「按处理办法改，都批准」。构建中并行边界补入 `test_stop_rules.py`（其中一条用例按旧默认行为断言），用户回「可以，加进边界并改」；同样补入 `skills/spec-guard-ops/SKILL.md`、`docs/concepts.md`（写着旧档位），用户回「可以，加进边界并改」。

## Assumptions

1. **新的档位项**：`design`（`human`／`reviewer`）、`merge`（`human`／`auto`）、`release`（`human`／`prepare`／`auto-confirm`／`auto`），由严到宽排列。
   预设：`none` = 全 `human`；`design` = `design=reviewer`；`merge` = `design=reviewer`、`merge=auto`。自定义对象只写这三项，没写的按 `human`。
   `release` 的取值、限制提示与 autopilot 的拦截都不变。
2. **新流程模块的技术方案**（design-review 的判定加上档位）：
   - 重要需求：永远交用户批，档位不起作用（同现在）。
   - `design=reviewer`：同现在——按 design-review 的规则需要审就交第二审查者，审过无阻断即放行；不需要审的直接放行。
   - `design=human`：需要审的照样先交第二审查者审（最多两轮），审完连同意见交用户批；第二审查者的放行不再算批准。不需要审的也交用户批（Q2 A），不先交第二审查者。
   - `designApproval.approvedBy` 仍只取 `user`／`reviewer`；`design=human` 时第二审查者审过无阻断照样记 `reviewer-approved`（带内容指纹，表示审查者看过这一版，改稿后变 `revised` 要重审），但不算放行，仍等用户批（同重要需求现在的处理：verify-artifacts 警告）。（2026-11-25 写 Plan 时修订：原文 C4 拒绝 `reviewer-approved`，会让用户批之前的改稿沿用上一稿的审查结果。）
3. **需求与 Plan 不可配**：`set` 遇到自定义里的 `spec`、`plan`、`requirement` 项，或预设 `plan`，退出 2、不写文件，提示改用新取值；
   新流程模块的需求确认与 Plan 自动批准不读档位（已是现状）。
4. **旧值兼容**（读的时候换算，文件不改）：
   - 预设 `plan` 读作 `none`；旧预设 `merge` 读作新 `merge`；`none` 不变。
   - 自定义里的 `spec`、`plan` 两项不生效：取值合法时不判无效，`show` 在这一行后标「spec、plan 已不生效」，阶段提示不出这一行（同现在不注入）；取值不合法时照旧整个键无效。
   - `takeoverNarrowed` 里记下的旧值 `from`／`to` 照样合法，比较宽严时按换算后的值；例外：旧值 `plan` 收窄写成 `none` 时记录照写 `from: "plan"`，之后设为 `none` 或 `design` 都算恢复、记录删除（2026-11-25 写 Plan 时补充）。
   - 存的是旧值 `plan` 时，`show` 与 `set` 预览多一行 `note:`：「旧值 plan 已按 none 读；要沿用『第二审查者代批』，设为 design（要用户原话）」。
     切换时把 `plan` 改成 `design`（草案 Q6）是每个仓库各自的一次 `set`，要那个仓库用户的原话；本模块不自动改任何项目的文件。
5. **老流程模块**（没有 `flow v2` 标记）怎么读（Q1 A）：按旧含义换算出 `spec`、`plan` 两项，老模块的 Codex 批准照旧：
   新 `design=reviewer` 对老模块等于旧 `plan=codex`；新 `merge` 预设对老模块等于旧 `merge` 预设（`spec`、`plan` 都是 `codex`）；
   存的旧值照旧含义读（旧 `plan` 对老模块仍是 `plan=codex`，旧自定义的 `spec`、`plan` 对老模块仍生效）。`codex_route`、`effective_review` 对老模块读的是这两项，判定不变。
6. **收窄**：预设阶梯改为 `merge` → `design` → `none`；自定义按发布、合并、技术方案的顺序把一项交还给人。读到旧值时先换算再收一格，写回新值。
   放宽一次只升一格的规则不变。
7. **`/map --json` 的 `takeover`**：每个模块给 `design`、`merge`、`release` 三项的**生效值**——重要需求的新流程模块 `design` 报 `human`，
   另加 `designForcedBy`：`important` 或 `null`（档位里写的值仍可由 `source` 与 `/spec-guard:config` 查到）；`source`、`widerThanProject`、`narrowed` 不变，
   `widerThanProject` 按配置值比（不算重要需求的强制）。旧的 `spec`、`plan` 两个字段本版保留、标为 deprecated，取值是假设 5 的换算结果（新流程模块也照这样报），下一版删除（Q3 A）。接口 1.21 → 1.22，`interface.json` 与 `scripts/check-interface.py` 同步。
8. **阶段提示**：新流程模块技术方案待批时，`design=human` 的下一步写「交用户批」，`reviewer` 写「第二审查者放行即可」；理由一行注明档位来源。
   老模块的 Spec、Plan 提示不变。
9. **规则与文档**：`commands/config.md` 的 `takeover`／`moduleTakeover` 两行与示例改为新取值并写兼容表；共享检查点规则「技术方案审查」一节加 `design` 档位的一条；
   `docs/commands.md`、README 讲接管档位的段落同步。CHANGELOG 的「未发布」补 design-review、plan-auto-approve、takeover-redefine 三条。
10. **发版**：插件版本已是 0.95.0（未发布），本模块不再升版本号；合并后按 `docs/release-process.md` 发 0.95.0 要另取用户授权。
    更旧的 spec-guard（0.84.0～0.94.0）读到新预设 `design` 会把 `takeover` 判为取值不合法、只忽略这个键（按 `none`），其余配置照常；在 `commands/config.md` 写明「团队都升级后再设置」。
11. **对外核对**：写定后把新的 `takeover` 字段（三项、`designForcedBy`、Q3 的处理）发给 autopr-design 与 module-crew 的负责会话核对；拟回告在验收时给出，发出要用户同意。
12. **不做**：回归文档检查（regression-doc-check）；合并前验证（verification-criteria）；改 design-review 判定「要不要审」的规则（`designReview`、老逻辑、跨模块）；
    改动消费者项目的 `.agent/config.json`；autopilot、module-crew 按新字段放行的改动（归各自插件）。

## Contract

- **C1** `hooks/project_config.py`：新 `ITEMS`、`PRESETS`、收窄阶梯；旧值换算（`expand` 与 `valid_takeover` 认旧值）；`set` 拒收旧取值；`show`／预览的 `note:` 与「已不生效」（假设 1、3、4、6）。
- **C2** `hooks/module_stage.py`：老模块的 `spec`、`plan` 由换算得出（假设 5）；`design_approval`、`design_hint`、`design_review_problems` 读 `design` 档位（假设 2、8）。
- **C3** `hooks/map_view.py`：`takeover` 字段（假设 7、Q3）。
- **C4** `hooks/review_mark.py`：`design=human` 与重要需求时 `--target design --state reviewer-approved` 照样可记，提示「不算放行，仍要用户批」（2026-11-25 修订，见假设 2）。
- **C5** `hooks/verify-artifacts.sh`：`design=human` 而技术方案只有第二审查者放行时警告。
- **C6** `commands/config.md`、`references/workflow-checkpoints.md`、`docs/commands.md`、README、CHANGELOG（假设 9）。
- **C7** `interface.json` 1.22、`scripts/check-interface.py`（假设 7）。

## Acceptance criteria

- **AC1** 预设 `none`／`design`／`merge` 与自定义 `{design, merge, release}` 可设可读，`show` 列三项与来源；`set` 对预设 `plan`、自定义 `spec`／`plan`／`requirement` 退出 2、文件不变。
- **AC2** 旧值：`takeover=plan` 读作 `none` 并出 `note:`；旧 `merge` 读作新 `merge`；带 `spec`、`plan` 的旧自定义不判无效、`show` 标「已不生效」；旧值的收窄记录照常读。
- **AC3** 新流程普通需求：`design=reviewer` 时审过无阻断即放行（现有 design-review 回归不变）；`design=human` 时审完仍停在技术方案交审、等用户批，`reviewer-approved` 不算放行，用户批之前改稿要重审。
- **AC4** 新流程重要需求：不论档位都交用户批；`/map --json` 的 `takeover.design` 为 `human`、`designForcedBy` 为 `important`。
- **AC5** 老流程模块：旧值 `plan` 下 Plan 仍可由 Codex 批（`codexRoute.plan` 为 null）；新值 `design` 下同样；`none` 下要人批。阶段提示、`/map --json` 的 `codexRoute`、`reviewApprovedBy` 与现在一致。
- **AC6** 收窄：`merge` → `design` → `none`；旧值 `plan` 收一格到 `none`；自定义按发布、合并、技术方案的顺序交还。
- **AC7** `/map --json` 的 `takeover` 符合 `interface.json` 1.22，`check-interface.py` 通过。
- **AC8** 本机 `validate.sh`、phase-guard、verify-artifacts 全绿；合并前头提交的 `CI required` 通过（按 merge-ask-no-wait，验收不等 CI，自动合并只认通过的头提交；2026-11-25 修订）。

## Boundaries

- **会做**：C1～C7 及回归；拟回告（假设 11）。
- **先问再做**：改用法草案的接口约定；超出假设 1～12 的改动；改任何消费者项目的配置；合并；发版。
- **不做**：假设 12 列出的事。

## 并行边界

- 独占：`spec/takeover-redefine.md`、`tasks/takeover-redefine/`、`plugins/spec-guard/hooks/project_config.py`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/map_view.py`、`plugins/spec-guard/hooks/review_mark.py`、`plugins/spec-guard/hooks/verify-artifacts.sh`、`plugins/spec-guard/commands/config.md`、`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/skills/spec-guard-ops/SKILL.md`、`docs/concepts.md`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`docs/commands.md`、`README.md`、`CHANGELOG.md`、`plugins/spec-guard/hooks/test_project_config.py`、`plugins/spec-guard/hooks/test_flow_v2.py`、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/hooks/test_review_marker.py`、`plugins/spec-guard/hooks/test_stop_rules.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`
- 公共：无

## Open questions

- **Q1 老流程模块怎么读新档位？**（2026-11-25 用户选 A）
  - A（推荐）：按旧含义换算出 `spec`、`plan`（假设 5）：`design=reviewer` 对老模块就是「Codex 批 Plan」，新 `merge` 就是旧 `merge`；存的旧值对老模块照旧含义。
    结果：本仓库和其他还在用老流程的项目，切到 `design` 后老模块的 Plan 仍由 Codex 批，打扰不增加；符合草案「老模块照旧规则，不改、不补」。
    代价：代码里多一张换算表，老模块的 Codex 批准要到所有老模块做完才能删。
  - B：老模块也只认新三项，`spec`、`plan` 一律按 `human`。代价：本仓库剩下的老流程模块（以及消费者项目里的）Plan 都改回由用户批，每个模块多一次打扰。
- **Q2 `design=human` 时，按规则不需要审的技术方案（普通需求、影响面全是新文件、`designReview` 为 `off`）要不要用户批？**（2026-11-25 用户选 A）
  - A（推荐）：要。`human` 就是「技术方案由人批」，不审的也交用户批（不先交第二审查者）。和预设 `none`「全人」的字面一致，用户想少打扰就设 `design`。
    代价：默认档位（没配 `takeover`）的项目，每个普通需求多一次技术方案批准。design-review 还没发版，没有用户已经习惯「不审即放行」。
  - B：不要。不需要审的直接放行，`human` 只管「审过的要不要人再批」。代价：默认档位下有些技术方案谁都没看过就开工，和「全人」的说法不一致。
- **Q3 `/map --json` 的 `takeover.spec`、`takeover.plan` 两个字段（module-crew 现在读它们）？**（2026-11-25 用户选 A）
  - A（推荐）：本版保留、标为 deprecated，取值是老流程的换算结果（Q1 A 的 `spec`、`plan`），新流程模块也照这样报（它们对新流程不起作用，`codexRoute` 已给出真实路径）；下一版删除。
    代价：一版之内字段多两个、对新流程模块没有意义；module-crew 要在这一版里改读 `design` 与 `codexRoute`。
  - B：本版直接删掉。代价：module-crew 在升级前读不到字段，按它的降级处理走（需要先问 module-crew 的负责会话会怎样）。

## 文档建议

`commands/config.md`、`docs/commands.md`、README 的接管档位段落在 C6 里同步；README 讲新流程的段落（plan-auto-approve 约定 M2 发版时一起改）也在这次改。项目没有文档基线。
