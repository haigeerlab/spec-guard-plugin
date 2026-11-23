# Spec: review-rounds-in-map

<!-- spec-guard: review approved 42205de202ca -->

## Objective

让 autopilot 合规监测能只读核对 Codex 审查的事实，不必信任 `review_mark` 自己的兜底：

1. **Codex 批准确有审查报告**：Plan 由 Codex 批准时，autopilot 要核对「确实有审查报告」。现在 `/map --json` 只给出 `reviewApprovedBy`（谁批的）和 `codexRoute`（能不能由 Codex 批），看不到批准依据的审查记录。
2. **两轮仍有阻断已转人批**：有了每轮的轮次和阻断数，autopilot 就能自己核对「审了两轮还有阻断的，已经转给人批」；现在它的报告只能写「未独立核验」。

审查记录已经存在：每轮 Codex 审查由 `review_mark --state codex-approved|codex-reviewed` 在 Spec 或 Plan 的「外部审查意见」一节写一行
`<!-- spec-guard: codex-review round=N blocking=N sha256=<12 位> -->`。本模块只把这些行读出来放进 `/map --json`，不新增记录。

给谁用：autopilot（只读这些字段，不重新判定，调用方向仍是 autopilot → spec-guard）。

对外接口与用法草案一致吗：不属于 `spec/usage/auto-takeover.md` 的里程碑，是 S108 之后 autopilot 合规监测（hub 切片 18）提出的数据补充，不加进草案的里程碑表。

登记：autopr-design #22307 经 ecosystem-lead #22309 转来。需求确认：用户 2026-11-23「说完了，照这样做」。

## Assumptions

1. **字段**：`/map --json` 每个模块在 `codexRoute` 旁边加 `reviewRounds: {"spec": [...], "plan": [...]}`，每项是一轮 `{"round": N, "blocking": N, "sha256": "<12 位十六进制>"}`，按文件里出现的顺序；没有轮次行或文件不存在时为 `[]`。表格视图不变。
2. **sha256 是被审文件的指纹、只有前 12 位**：轮次行记的是这一轮被审的 Spec 或 Plan 内容的 sha256（即审查报告 `scope.files` 里该文件的值），不是报告文件本身的哈希，且只记前 12 位；字段照实给出这 12 位，接口说明写清楚是前缀；不改成记完整值（旧记录补不回来，改了也只有新记录有）。
3. **只报事实，不加判定字段**：不另给「两轮已用完」「批准有依据」这类结论；autopilot 用 `reviewRounds` 配合 `reviewApprovedBy`、`codexRoute` 自己核对。判定规则仍只在 `review_mark` 一处（`ROUND_CAP = 2`）。
4. **读法与现有一致**：与 `module_stage.codex_rounds` 同一个正则、同样跳过代码块里的示例行；Spec 或 Plan 读不了时按 `/map` 现有的读失败处理（与 `review` 字段一致），不悄悄给 `[]`。
   实现上把 `codex_rounds` 拆出一个带 sha256 的读取函数，`codex_rounds` 与 `review_mark` 的行为不变。
5. **轮次行不随修订清空**：Spec 或 Plan 修订后重审，轮次号接着往上数（现有行为）；`reviewRounds` 照文件列出全部轮次，不按当前批准标记筛选。
6. **接口与版本**：`interface.json` 升到 1.17，加 `mapView.reviewRounds`；`scripts/check-interface.py` 与回归同步。插件版本 0.93.0（新增接口字段，次版本），CHANGELOG、README 中英文 `--ref` 随之改。合并后用 `scripts/release.py` 发版，通知 ecosystem-lead，并把字段名和格式告诉 autopr-design、抄送 ecosystem-lead。
7. **不做**：不改轮次行的写法和 `ROUND_CAP`；不改 `review_mark`；不跟进 delegate 0.11.0 的快照复审（`--previous-report`），等它发布后另行评估。

## Contract

- **C1** `hooks/module_stage.py`：带 sha256 的轮次读取函数，`codex_rounds` 改为基于它、返回值不变（假设 4）。
- **C2** `hooks/map_view.py`：每个模块的 `reviewRounds`（假设 1、5）。
- **C3** 接口与文档：`interface.json` 1.17、`check-interface.py`、`docs/commands.md`（`/map --json` 字段一句）、CHANGELOG、版本号、README（假设 6）。

## Acceptance criteria

- **AC1** 有轮次行的模块，`/map --json` 的 `reviewRounds.spec`、`reviewRounds.plan` 按文件顺序给出每轮的 round、blocking、sha256（12 位），与文件里的行逐项相同。
- **AC2** 没有轮次行、文件不存在时为 `[]`；代码块里的示例轮次行不计入。
- **AC3** 回归覆盖三种情形：Codex 批准且最后一轮无阻断；两轮有阻断后由用户批准；只有 `codex-reviewed` 轮次、尚未批准。
- **AC4** `codex_rounds`、`codex_rounds_exhausted` 与 `review_mark` 的现有回归全部不变、全绿。
- **AC5** 变异：`reviewRounds` 写死为 `[]`、丢掉 sha256、不跳过代码块，各让对应回归变红。
- **AC6** `validate.sh`、phase-guard、verify-artifacts 全绿；`interface.json` 为 1.17，`check-interface.py` 通过。

## Boundaries

- **会做**：C1～C3 及回归。
- **先问再做**：改轮次行格式或改记完整 sha256；加判定类字段；改 `review_mark`。
- **不做**：假设 7 列出的事。

## 并行边界

- 独占：`spec/review-rounds-in-map.md`、`tasks/review-rounds-in-map/`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/map_view.py`、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`docs/commands.md`、`plugins/spec-guard/.claude-plugin/plugin.json`、`plugins/spec-guard/.codex-plugin/plugin.json`、`CHANGELOG.md`、`README.md`、`README.en.md`
- 公共：无

## 文档建议

`interface.json` 是 autopilot 读的权威说明，写清 `sha256` 是前 12 位、`[]` 的含义；`docs/commands.md` 在 `codexRoute` 那句后补一句。README 只改 `--ref`。项目没有文档基线。
