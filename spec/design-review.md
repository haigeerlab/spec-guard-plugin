# Spec: design-review

<!-- spec-guard: review approved 236433a444a4 -->

## Objective

开发流程改版（S110）M2 的第二个模块。新流程模块写完技术方案 `tasks/<id>/design.md` 后，现在直接进入「缺回归」，没有任何审查或批准。
本模块按用法草案 `spec/usage/dev-flow-v2.md`（入口表「技术方案审查」、U1、U2、接口 D 与 D' 节）补上这一步：

- 普通需求：项目开关 `designReview`（默认 `off`）为 `on`，或技术方案碰到老逻辑、跨模块（不论开关），就交第二审查者审一轮、改一轮，审过即放行，不用用户批；
  两者都不是时不审，直接放行。
- 重要需求：技术方案由用户批，第二审查者的意见一并附上。
- `/map --json` 每个模块给出 `designApproval`，供 autopilot 的合规监测读。

给谁用：所有用 spec-guard 新流程的项目里写技术方案的 agent、批技术方案的用户；autopilot（读 `designApproval`）；delegate（被调用审查）。

对外接口与用法草案一致吗：一致。`designReview` 取值与默认值按草案 Q3（`off`）；「碰老逻辑」按 Q5 推荐；审查命令与报告字段按 D 节（delegate #22369、#22372）；
`designApproval` 字段按 D' 节。草案的 `takeover.design`（`human`／`reviewer`）归 takeover-redefine，本模块不读它（见假设 9）。

登记：用法草案 dev-flow-v2（用户 2026-11-24「确认插入，Q1–Q6 按推荐」），M2 里程碑。需求确认沿用草案的确认，本 Spec 交审即确认范围；2026-11-25 用户回「批准；Q1 A；Q2 A」；同日修订轮次行加 `report` 字段，用户「选 A，同意修订 Spec」。

## Assumptions

1. **只管新流程模块**：`spec/<id>.md` 有 `flow v2` 标记、且档位要求技术方案（`normal`／`important`）的模块。bug、small 没有技术方案；老模块照旧。
2. **要不要审**（「审查要求」，按下面顺序判，先中先定）：
   - 档位 `important` → **用户批**（第二审查者照审一轮，意见附在交审正文里）；
   - 技术方案「影响面」一节列出了**已有文件** → **必审**（碰老逻辑）；已有文件 = 本模块开工基线（需求文档首次提交时的父提交）里已存在的路径；读不到基线时按当前 `HEAD` 判；
   - 跨模块（沿用现有判定：并行边界列了公共文件，或与其他未完成模块的独占路径重叠）→ **必审**；
   - `.agent/config.json` 的 `designReview` 为 `on` → **审**；
   - 都不是 → **不审**，技术方案写完即放行。
3. **配置键 `designReview`**：`on`／`off`，默认 `off`，不注入阶段提示（同 `moduleConcurrency`）。0.84.0 起旧版本遇到不认识的键只忽略它。
   `/spec-guard:config` 的说明表加一行；`project_config.py` 校验取值。
4. **审查怎么跑**：阶段提示给出 delegate 的命令（D 节原样）：
   `/delegate:review --profile design --backend auto --author-host <claude-code|codex> --paths tasks/<id>/design.md --spec spec/<id>.md [--spec <影响面里列的已有文件>…]`，
   第二轮加 `--previous-report <上一轮报告>`；`--author-host` 按当前宿主填；不带 `--model` 等参数。报告存在仓库外（如 `$TMPDIR`）。
   开工前可用 `/delegate:doctor --reviewers --json` 看有没有可用审查者，只检查、不阻止。
5. **记录**：用 review-mark 新增 `--target design`，在 `tasks/<id>/design.md` 里写批准标记（与 Spec、Plan 同一格式，指纹用 `spec-digest.py`）和轮次行。
   轮次行沿用 0.93.0 的写法，并补上审查者信息：
   `<!-- spec-guard: design-review round=<n> blocking=<k> sha256=<12 位> vendor=<厂商> same-vendor=<true|false> criteria=design-v1 report=<报告文件的 sha256，64 位> -->`（`report` 为 2026-11-25 修订补上，供假设 8 的 `reportSha256`）；
   **阻断数 = `recheck.items` 里 `unresolved` 的条数 + `findings` 里非 `suggestion` 的条数**（D 节；现有 Codex 轮次只数 `findings`，复审时会把未解决的旧条目记成 0，本模块不沿用这个口径）。
   状态（Q2 A，只用于技术方案，Spec、Plan 的 `codex-*` 不动）：第二审查者审过且阻断为 0 → `reviewer-approved`；有阻断 → `reviewer-reviewed`（改完再审一轮，第二轮只核对上一轮）；
   两轮仍有阻断 → 交用户批；用户批 → `approved`。报告的 `criteria` 两轮必须相同，否则拒绝记录。
6. **没有可用审查者**：报告 `reviewer.selection="none"`（`execution_status=conditions_missing`、诊断 `no_reviewer_available`）时记为「未审」，不当失败；
   之后交用户批（Q1 A）：阶段提示说明没有可用的第二审查者、技术方案交用户批；用户批后为 `approved`、`approvedBy: user`。
7. **阶段**：在 `NEEDS_DESIGN` 与 `NEEDS_REGRESSION` 之间，技术方案已写但还没放行时，阶段提示的「批准」一行写技术方案待审或待批，下一步给出审查命令或交审要求；
   阶段值本身不新增（同 requirement-confirm-gate 的做法：待批时阶段照文档推进，另出一行「批准」，提示先不要往下写回归文档）。
   技术方案在放行后又改过（指纹不符）时，按「批准后已修订」处理：要审的重新审一轮，要用户批的重新批。
8. **`/map --json` 每个模块加 `designApproval`**：老模块与 bug、small 为 `null`；其余为对象：
   - `status`：`not-required`（不审直接放行）／`pending-review`（要审还没审）／`in-review`（有一轮有阻断）／`pending-user`（要用户批）／
     `approved`（已放行）／`unreviewed`（没有可用审查者，见 Q1）／`revised`（放行后又改过）；
   - `approvedBy`：`approved` 时为 `user` 或 `reviewer`，`not-required` 时为 `null`；
   - `reviewerVendor`、`sameVendor`：取最后一轮的 `vendor`、`same-vendor`，没审过为 `null`；
   - `reportSha256`：最后一轮轮次行的 `report`（报告文件的 sha256，完整 64 位），没审过为 `null`；
   - `rounds`：轮次数组，形状同 `reviewRounds` 再加 `vendor`、`sameVendor`。
   接口 1.19 → 1.20，`interface.json` 与 `scripts/check-interface.py` 同步。插件版本不改，M2 在 takeover-redefine 一次发版。
9. **和接管档位的关系**：本模块不读 `takeover`。草案的 `design: human` 会让普通需求也交用户批，那一项由 takeover-redefine 加上，并按草案在 `/map --json` 给出生效档位。
   在那之前：普通需求按假设 2，重要需求用户批。现有 `takeover=plan`（Plan 交 Codex）对技术方案没有作用。
10. **规则文字**：共享检查点规则加「技术方案审查」一小节（假设 2、4～7 的要点）；停点规则 `node-rules.md` 加「技术方案交审」一节（交用户批时正文要写全技术方案六节的要点、第二审查者的意见与处理），
    `module_stage.py` 的停点种类加 `design-review`：技术方案要用户批（`pending-user`、`unreviewed`、`revised` 且要用户批）时就停在这里。
11. **verify-artifacts**：技术方案的批准标记或轮次行写坏 → 失败；轮次行的 `criteria` 两轮不同 → 失败；重要需求的技术方案只有 `reviewer-approved` → 警告「重要需求的技术方案要用户批」。
    修改这些判据时 phase-guard 与 verify-artifacts 两边的正反回归一起改（项目不变量）。
12. **不做**：审查标准本身（归 delegate 的 `design-v1`）；`takeover.design` 与生效档位（takeover-redefine）；Plan 自动批准（plan-auto-approve）；
    回归文档的审查或检查（regression-doc-check）；给老模块补技术方案；判断同厂商审查合不合格（照记，不判定）。

## Contract

- **C1** `hooks/module_stage.py`：审查要求的判定（假设 2）、阶段提示的「批准」一行与下一步（假设 4、7）、`design_approval(root, module)`（假设 8）。
- **C2** `hooks/review_mark.py`：`--target design`、`reviewer-reviewed`／`reviewer-approved` 状态、轮次行与阻断数口径（假设 5、6）。
- **C3** `hooks/map_view.py`：`designApproval` 字段（假设 8）。
- **C4** `hooks/project_config.py` 与 `commands/config.md`：`designReview` 键（假设 3）。
- **C5** `hooks/verify-artifacts.sh`：假设 11 的检查。
- **C6** `references/workflow-checkpoints.md`、`references/node-rules.md`：规则文字（假设 10）。
- **C7** `interface.json` 1.20、`scripts/check-interface.py`、`docs/commands.md` 的 `/map --json` 与 review-mark 说明（假设 8）。

## Acceptance criteria

- **AC1** 老模块与 bug、small：阶段提示、verify-artifacts 输出不变，`/map --json` 只多 `designApproval: null`；现有回归全绿（字段集合的测试加上这个键）。
- **AC2** 审查要求按假设 2 的顺序判定，五种情形各一条正例：重要需求、影响面列了已有文件、跨模块、`designReview: on`、都不是；
  影响面只列新文件且开关 `off` 时为不审。
- **AC3** 不审的普通需求：技术方案写完，阶段提示直接走到「缺回归」，`designApproval.status` 为 `not-required`。
- **AC4** 要审的普通需求：没审时阶段提示给出带 `--author-host` 的审查命令、提示先不写回归；记一轮阻断为 0 后放行，`approvedBy: reviewer`；
  有阻断时为 `in-review`，第二轮带 `--previous-report`；两轮仍有阻断转为 `pending-user`。
- **AC5** 阻断数按假设 5 的口径：报告里只有 `recheck.items` 的 `unresolved`、没有新发现时，阻断数不为 0（回归用一份构造的报告证明）。
- **AC6** 重要需求：不论审查结果都要用户批；只有 `reviewer-approved` 时 verify-artifacts 警告。
- **AC7** `selection="none"` 的报告记为「未审」，不报失败；阶段提示转为交用户批，用户批后 `approvedBy: user`。
- **AC8** 放行后改技术方案：`status` 变为 `revised`，阶段提示要求重新审或重新批。
- **AC9** `designReview` 取值不合法时按「个别键有问题」处理（只这个键失效、按默认 `off`）；`/spec-guard:config` 能设、能取消。
- **AC10** 本机 `validate.sh`、phase-guard、verify-artifacts 全绿；`check-interface.py` 通过；PR 上 `CI required` 通过。

## Boundaries

- **会做**：C1～C7 及回归；写定后把 `designApproval` 的取值发给 autopr-design、把轮次行与阻断数口径发给 delegate-owner 核对（拟回告在验收时给出）。
- **先问再做**：改用法草案的接口约定；超出假设 1～11 的改动；合并。
- **不做**：假设 12 列出的事。

## 并行边界

- 独占：`spec/design-review.md`、`tasks/design-review/`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/review_mark.py`、`plugins/spec-guard/hooks/map_view.py`、`plugins/spec-guard/hooks/project_config.py`、`plugins/spec-guard/hooks/verify-artifacts.sh`、`plugins/spec-guard/commands/config.md`、`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/references/node-rules.md`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`docs/commands.md`、`plugins/spec-guard/hooks/test_flow_v2.py`、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/hooks/test_review_marker.py`、`plugins/spec-guard/hooks/test_project_config.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、`plugins/spec-guard/hooks/test_stop_rules.py`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`
- 公共：无

## Open questions

- **Q1 没有可用审查者（「未审」）之后怎么办？**（2026-11-25 用户选 A）
  - A（推荐）：交用户批。阶段提示说明「没有可用的第二审查者，技术方案交你批」，`designApproval.status` 先为 `unreviewed`，用户批后为 `approved`、`approvedBy: user`。
    代价：没装或没配好审查者的项目，每份要审的技术方案都会打扰用户。
  - B：照草案字面「不当失败」直接放行，`status` 记 `unreviewed`。代价：本该强制审的（碰老逻辑、跨模块）可能一份都没人看过就进入实现。
- **Q2 第二审查者的状态叫什么？**（2026-11-25 用户选 A）
  - A（推荐）：新增 `reviewer-reviewed`／`reviewer-approved`，只用于技术方案。审查后端已不限 Codex（`--backend auto`），厂商记在轮次行里。
    Spec、Plan 上现有的 `codex-reviewed`／`codex-approved` 不动。
  - B：沿用 `codex-reviewed`／`codex-approved`。代价：后端是 Claude 时名字会误导，autopilot 也要另外读厂商才知道是谁审的。

## 文档建议

`docs/commands.md` 补 review-mark 的 `--target design` 与 `/map --json` 的 `designApproval`；`commands/config.md` 补 `designReview` 一行（都在 C4、C7 里）。
README 讲新流程的段落在 M2 发版（takeover-redefine）时一起改。项目没有文档基线。
