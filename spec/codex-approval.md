# Spec: codex-approval

<!-- spec-guard: review approved a37ff55fb207 -->

## Objective

模块的接管档位勾了「Spec：codex」或「Plan：codex」时，Codex 审过、没有阻断意见，就可以记一种和用户批准分开的批准标记
`codex-approved`，阶段提示把它当作已批准、接着往下走；没勾的模块照旧只认用户批准。Codex 的阻断意见改完复审，两轮还没解决、
或者 Codex 不可用，停下来交给用户，绝不退回 Claude 自己审自己。同时把「自治档位与底线」改成「按勾选项」。

给谁用：在接管档位下推进模块的 agent；读批准状态的 module-crew 与 autopilot；设档位的用户。

对外接口与用法草案一致吗：一致。对应 `spec/usage/auto-takeover.md` 入口「`/spec-guard:review-mark --state codex-approved`」与
「阶段提示的批准行与停点」，典型用法 U2。

登记：S101 合并方案 r2 Q1、Q5、Q12（用户「按推荐批准」，总账 `bfce091`）；能力图插入经用户「确认插入；Q1 B」。账本 T1T36MR。

## Assumptions

1. **谁调 Codex**：Claude 主会话按阶段提示用 `/delegate:review`（后端 codex）审 Spec 或 Plan 文件；spec-guard 不调外部进程，只读审查报告。
2. **审查报告怎么给**：agent 把 `/delegate:review` 标准输出的那份 JSON 存成文件，传给 `review-mark --target spec|plan --state codex-approved --review <文件>`
   （delegate 接口 1.5，delegate-owner #21973 确认；标准错误里的 artifacts 路径是私有副本，不用）。spec-guard 读：`execution_status` 必须是 `completed`，
   `review_outcome` 必须是 `findings` 或 `no_findings_in_scope`，否则算没有结论；后端 `backend` 必须是 codex；`findings` 里每条的 `severity`，缺这个字段
   按 `blocking`。报告的 `limitations` 写明审查结论不是合并或交付许可——「Codex 审过即批准」是 spec-guard 按用户设的接管档位采用的策略，不是 delegate 的结论。
3. **报告和文件绑在一起**：被批的文件必须在报告的 `scope.files` 里，且那里记的内容 sha256 等于工作区当前文件的 sha256（delegate 建议的核对方式，
   `--spec`／`--plan` 带进来的上下文文件也在其中）。不需要先提交，也不重算 `blob-pairs-v1`。任何一条对不上就拒绝记录（退出 2）并写明哪一条。
4. **标记**：`<!-- spec-guard: review codex-approved <指纹> -->`，指纹仍由 `spec-digest.py` 算（去掉标记行后的正文）；文件之后再改，读作
   「批准后已修订」，和用户批准一样处理。同一文件里用户批准与 Codex 批准只留一行，后写的替换先写的。
5. **轮次与证据记在哪**：`review-mark --review` 每次（不论有没有阻断）都在文件的「外部审查意见」一节追加一行
   `<!-- spec-guard: codex-review round=<n> blocking=<k> sha256=<被审文件内容 sha256 前 12 位> -->`；轮次由 spec-guard 自己计数（delegate 报告没有轮次字段）；`--state codex-approved` 只在最新一轮 `blocking=0`
   时可写。另用 `--state codex-reviewed`（只记一轮、不记批准）记录有阻断的一轮。建议类意见由 Claude 决定是否采纳，在同一节每条写一句理由（规则文字，
   机器不判）。
6. **两轮上限**：同一文件已有 2 轮 `blocking>0` 的记录、最新一轮仍有阻断时，阶段提示把下一步换成「停下，把两轮的阻断意见交用户决定」；
   `review-mark` 不再接受这个文件的 `codex-reviewed`，只能由用户批准（`--state approved`）。
7. **什么时候算已批准**：阶段提示与 `/map` 读到 `codex-approved` 时，只有该模块生效的接管档位里对应一项是 `codex`，才当作已批准；否则当作
   「待用户批准」，批准行写明「Codex 审过，但本模块的档位要求人批」。用户批准（`approved`）在任何档位下都有效。
8. **Codex 不可用**：没有报告就没有 `codex-approved`，模块停在待批准；阶段提示写明「Codex 不可用时停下等，不要自己审」。
9. **评审节奏**：模块的 Spec 与 Plan 批准人不同（一个 human、一个 codex）时，`reviewCadence=combined` 对这个模块不生效，按分开批；相同时照旧。
10. **底线按勾选项**（Q1）：`workflow-checkpoints.md`「自治档位与底线」改为：能力图永远由用户批；Spec、Plan 按接管档位，没勾 codex 的照旧由用户批；
    判为重要需求的 Spec 由用户批（判定在 `important-requirement`）；最终验收在 `codex-final-acceptance` 落地前照旧由用户做；测试改不红、Spec 没覆盖的决策、
    高风险不可逆改动照旧必停。
11. **接口**：同在 1.15：`reviewMark` 的取值加 `codex-approved`、`codex-reviewed`；`/map --json` 的 `review` 用原值报出 `codex-approved`，另加
    `reviewApprovedBy`（`user`／`codex`／`null`）。版本号不在本模块改。

## Contract

### C1 `hooks/review_mark.py`

- `--state codex-approved|codex-reviewed`、`--review <path>`；按假设 2、3 校验报告（不合格退出 2、写明原因、不写文件）；按假设 5、6 写轮次行与标记；
  预览照旧，`--confirm` 才写。档位不是 codex 时 `codex-approved` 仍可记（只是不生效），预览写明这一点。

### C2 判定（`hooks/module_stage.py`）

- `review_state` 认 `codex-approved`；新函数 `effective_review(root, module, target)` 把档位与轮次合起来给出 `approved`／`pending`／`revised`／`none`
  与 `approvedBy`；阶段提示批准行、`stop_node`、`/map` 都用它。两轮上限与 Codex 不可用按假设 6、8 改建议下一步（中英）。

### C3 规则与说明

- `references/workflow-checkpoints.md`：「自治档位与底线」按假设 10 重写；「批准标记」加 Codex 批准一条（报告、绑定、轮次、两轮上限、建议写理由、不可用就停）。
- `references/node-rules.md`「Spec 交审」「Plan 交审」：档位勾了 codex 时怎么走（先提交、交 Codex、无阻断后 review-mark、交给用户的只剩通知）。
- `commands/review-mark.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`、`interface.json`、`check-interface.py`。

## Acceptance criteria

- **AC1** 报告校验（`test_codex_review.py`／`test_review_marker.py`，手写报告）：codex 报告、`execution_status=completed`、无阻断、文件在 `scope.files`
  且 sha256 一致 → 可记；未完成或没有结论、后端不是 codex、有阻断、`severity` 缺失、文件不在 `scope.files`、sha256 与工作区不同 → 各自退出 2 并写原因、不写文件。
- **AC2** 轮次：每次 `--review` 追加一行轮次；两轮阻断后 `codex-reviewed` 被拒、`approved` 仍可记；最新一轮有阻断时 `codex-approved` 被拒。
- **AC3** 生效：档位 spec=codex 时 Spec 的 `codex-approved` 读作已批准；档位为 human 时读作待批准并写明原因；用户批准任何档位都有效；改文件后读作批准后已修订。
- **AC4** 阶段提示（`test-phase-guard.sh` 新段）：勾了 codex 的模块在 Spec 交审节点建议交 Codex 审；两轮阻断后建议交用户；没勾的模块输出与改前逐字相同；中英各一例。
- **AC5** 节奏：Spec 人批、Plan Codex 批时 combined 不生效；两项同为人批时照旧。
- **AC6** 规则与接口：底线按假设 10、批准标记一节、两个交审节点的规则有断言并过字节上限；`interface.json` 与 `check-interface.py` 一致；
  `validate.sh`、phase-guard、verify-artifacts 全绿。

## Boundaries

- **会做**：C1～C3 及回归。
- **先问再做**：让 spec-guard 自己调用 Codex 或 delegate；放宽两轮上限；让 `codex-approved` 在档位为 human 时生效。
- **不做**：最终验收的 Codex 标记（`codex-final-acceptance`）；重要需求判定（`important-requirement`）；改 delegate 的报告格式；版本号与发版。

## 未决问题

- **Q6 带「预先声明」的 Plan 能不能交 Codex 批**（2026-11-22 用户选 A：有任何一行不是「无」的 Plan 不论档位都由用户批；`codex-approved` 读作待用户批准并写明原因）：Plan 的「预先声明」一节写了公共路径、外部依赖、配置或补丁时，批准它就等于授权这些公共改动。
  - **A（推荐）**：这样的 Plan 不论档位都由用户批（预先声明全是「无」的照常可以交 Codex）。
  - **B**：照档位，Codex 也能批。

## 并行边界

- 独占：`spec/codex-approval.md`、`tasks/codex-approval/`、`plugins/spec-guard/hooks/review_mark.py`、`plugins/spec-guard/hooks/test_review_marker.py`、`plugins/spec-guard/commands/review-mark.md`
- 公共：无

## 文档建议

改 `commands/review-mark.md`、`skills/spec-guard-ops/SKILL.md`（review-mark 一节）、`docs/commands.md`、`docs/workflow.md`（批准一段加接管档位下谁批）。
CHANGELOG 与 README 在最后一个模块统一写。项目没有文档基线。
