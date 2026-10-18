# Spec: stop-rule-and-ac

<!-- spec-guard: review approved 07b04cbc922a -->

## Objective

三处规则文字，外加 verify-artifacts 的一条提示：

1. **外部阻塞的停点太窄。** 现行规则是"同一个 gate 因外部原因再次挡住时停下"。一个真实的前端项目里，一串离线安装试验每次都
   写成新的"准确稿"、新的一次性许可，不算"同一个 gate"，规则一次没触发，三天里没有一次挂起提议。改为看**同一模块、同一目标**，
   不看措辞和许可是不是新的；停下时把"挂起它、先开别的可开工模块"作为现成选项摆出来。
2. **"检查通过就继续"已经能写，但没人提醒。** `report` 检查点就是这个意思，可那个项目把本地提交也写成了 `gate`。未标注仍按
   `gate`（默认值不改，用户在本会话定的），只在写 Plan 与交审 Plan 时提示一句。
3. **验收标准没有稳定编号。** 读取方要把最终验收的证据和验收标准一条条对上，没有编号只能靠文字匹配。规则改为编号写
   `AC1`、`AC2`……；verify-artifacts 对未完成模块缺编号只给提示，不拦。

登记：2026-10-19 经 `/spec-guard:add-module` 插入能力图，依赖 `checkpoint-tiers`、`module-suspend`、`map-startable`。需求来自
接入协调人转述的用户决定 53（S2、S3、S5），用户在本会话审过取舍：N 取 2、不改检查点默认值、AC 只提示不拦且只查未完成模块。

## Assumptions

1. **"同一目标"的判定交给 agent，按要达成的结果算**：比如"装上某个依赖""让某项检查通过""拿到某个许可"。换一种写法、换一份
   草稿、换一次性许可去做同一件事，仍是同一目标。规则写明这一点和两个反例，不做机械计数（hook 只读、不存状态，数不了次数；
   机械计数归读取方的停滞检测）。
2. **触发条件**：同一模块、同一目标，**因外部原因第二次过不去**，或**第二次为它向用户报批**（请求再试一次、再给一次许可）。
   两者先到者为准。只因 agent 自己能修的原因失败（测试没过、写错了）不算，照旧自己修，不在第二次就停。N 固定为 2，不加配置。
3. **停下时给的选项**：照旧给"挂起、接受风险、换方案"及各自代价，并新增一条现成选项——用 `module-suspend --reason` 挂起本
   模块，先开 `/spec-guard:map` 里"🟢 可以开始"的模块（列出模块 id；开关 on 时用 `startable`）；没有可开工模块时照实说没有。
   仍由用户决定，agent 不自己挑。
4. **检查点默认值不改**：未标注仍按 `gate`。新增的提示只有两处：写 Plan 时"范围内靠测试或检查脚本就能判定通过的中间检查点
   可以标 `report`；最终验收、推送、不可逆操作仍标 `gate`"；交审 Plan 时说明哪些检查点标了 `report`。
5. **AC 编号的写法**：验收标准每条以 `AC<数字>` 开头，例如 `- AC1：……`（`**AC1**` 也认）。编号在一个 Spec 内稳定：修订时
   新增的条目用新编号，删掉的编号不复用、不重排。最终验收按编号逐条给证据。
6. **verify-artifacts 怎么找验收标准**：Spec 里标题为 `Success criteria`（不分大小写）、`Acceptance criteria` 或 `验收标准`
   的那一节，节内的列表项（`-`／`*`／`+` 或 `1.`）。有这一节、且有列表项不以 `AC<数字>` 开头时给一条 `⚠️` 提示，列出模块 id；
   没有这一节、或模块已完成（阶段 `DONE`）时不提示。提示不让 verify-artifacts 失败。
7. **只改文字与 verify-artifacts**：`phase-guard.sh` 的每轮注入不变（这条判据不进阶段提示）。约定块两份模板、`docs/convention-block.md`
   与本仓库 `AGENTS.md` 的约定块同步改，`validate.sh` 的一致性检查照旧要过。
8. 发版 0.74.0。

## Contract

### 共享检查点规则 `references/workflow-checkpoints.md`

- 「异常停点」那一项：`同一个 gate 因外部原因再次挡住` 改为 `同一模块、同一目标因外部原因第二次过不去，或第二次为它向用户报批`。
- 原「同一个 gate 因外部原因再次挡住时交用户决定」一条改写为：
  - 什么算同一目标（按要达成的结果算；换写法、换草稿、换一次性许可仍是同一目标）；
  - 什么算外部原因（照旧：上游没修、缺权限或凭据、要用户在质量与进度之间取舍）；agent 自己能修的失败不算；
  - 停下时给出的选项与代价：挂起本模块并先开可开工模块（列出 `/spec-guard:map` 的 🟢 模块，没有就说没有）、接受风险并写明、
    换方案；由用户决定，不按默认推荐继续重试，也不自己选一个接着做。
- 「Plan 检查点分级」加一条：范围内靠测试或检查脚本就能判定的中间检查点可以标 `report`；最终验收、推送与不可逆操作标 `gate`；
  未标注仍按 `gate`。交审 Plan 时说明哪些检查点是 `report`。
- 「交审要让用户看到内容」的 Spec 要点里，"验收标准"改为"验收标准（按 AC1、AC2… 编号）"；新增一条「验收标准编号」：写法、
  编号稳定、最终验收按编号逐条给证据、verify-artifacts 只提示不拦。

### 约定块（两份模板、`docs/convention-block.md`、本仓库 `AGENTS.md`）

- 外部阻塞那一行改为："同一模块、同一目标因外部原因第二次过不去，或第二次为它报批时停下，把挂起（并先开可开工模块）、接受
  风险、换方案等选项与代价交用户决定……"，细则指向共享检查点规则。
- 检查点那一行在"未标注按 `gate`"后补："范围内能自动判定的中间检查点可标 `report`"。
- 新增一行："Spec 的验收标准按 AC1、AC2… 编号，最终验收按编号给证据"，细则指向共享检查点规则。

### `hooks/verify-artifacts.sh`

- 新增一段检查（`python3` 不可用时与其他段一样给"未验证"提示）：对能力图里每个阶段不是 `DONE` 的模块读 `spec/<id>.md`，
  按 Assumptions 第 6 条找验收标准一节；有未编号的列表项时 `warn "<id> 的验收标准有 N 条没有编号（AC1、AC2…）；最终验收要按编号对证据"`；
  都编号了或没有该节时不输出；读不出 Spec 时 `warn "未验证：…"`。
- 不加 `ok` 行（避免每个项目多一行通过记录）；不改其他检查与退出码。

### 文档

CHANGELOG `[0.74.0]`；版本号 0.74.0（两份清单）与中英 README 的 `--ref`。

### 不变

- `phase-guard.sh` 与每轮注入逐字不变；检查点未标注按 `gate`；`module-suspend` 与 `/map` 的行为不变。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash plugins/spec-guard/hooks/verify-artifacts.sh
```

## Testing strategy

- `test_workflow_checkpoints.py`：关键词断言——规则里有"同一模块、同一目标""第二次为它向用户报批""可以开始"、`module-suspend`、
  标 `report` 的提示、AC 编号一节；旧说法"同一个 gate 因外部原因再次挡住"不再出现；约定块各处含新的三行。
- `test-verify-artifacts.sh`：进行中模块的 Spec 有未编号的验收标准 → 出提示且不失败；全部编号（含 `**AC1**`、`1. AC1`）→ 不出；
  标题写 `验收标准`／`Acceptance criteria` 同样识别；没有该节 → 不出；已完成模块未编号 → 不出；围栏代码块里的示例不算。
- 本仓库跑 `verify-artifacts.sh`：123 个已完成模块不出提示。

## Boundaries

- **会做**：上面三处规则文字、约定块各处同步、verify-artifacts 一条提示与回归。
- **先问**：把停点做成 hook 机制或计数；把 AC 检查变成失败；改检查点默认值；给已完成模块补编号。
- **不做**：改 `module-suspend`、`/map`；替读取方判断停滞；改 agent-skills 的 Spec 模板。

## Success criteria

- AC1：共享检查点规则与约定块各处的外部阻塞停点按"同一模块、同一目标、第二次外部失败或第二次报批"写，并给出"挂起并先开可开工模块"选项；旧说法不再出现（关键词断言）。
- AC2：检查点未标注仍按 `gate`；写 Plan 与交审 Plan 处各有一句 `report` 提示（关键词断言）。
- AC3：规则要求验收标准按 AC1、AC2… 编号、编号稳定、最终验收按编号给证据（关键词断言）。
- AC4：verify-artifacts 对未完成模块缺编号给 `⚠️` 提示、不失败；已完成模块、没有该节、全部编号时不提示（回归用例）。
- AC5：本仓库 `verify-artifacts.sh` 不因已完成模块出新提示；`validate.sh` 的约定块一致性检查通过；`phase-guard` 回归逐字不变。

## Open questions

- 无。
