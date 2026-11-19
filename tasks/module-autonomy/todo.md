# Todo: module-autonomy

- [x] Task 0：提交已批准的 Spec 与 Plan、todo — 2026-11-19 用户批准 Spec（「批准」）与 Plan（「Plan 批准」）；能力图插入经用户「确认插入」。
- [x] Task 1：`project_config.py` 校验、`module_tier` 与 `--module` 写入，单元测试 — `VALIDATORS` 加 `moduleAutonomy`（对象，id 合 `MODULE_ID`、值在 `TIERS`，任一条目坏整个键失效），`DEFAULTS` 为 `{}`；新增 `module_tier()`（条目优先，否则随 `autonomyTier`；`moduleAutonomy` 不合法时来源为 `default (config invalid)`）与 `wider()`；`set`／`unset` 加 `--module`（只对 `moduleAutonomy`，写它必须带；最后一个条目去掉时整个键删除；宽于项目档位时预览多一行 note）。`test_project_config.py` 新增 10 例并把汇总项清单加上新键，实现前 8 失败 2 报错，实现后 51 例通过。
- [x] Task 2：`/map --json` 每个模块的 `autonomy` — `map_view` 每个模块加 `autonomy: {tier, source, widerThanProject}`（常量 `AUTONOMY_FIELDS`），由 `project_config.module_tiers()` 一次读取给出（`module_tier` 改为它的单 id 形式），文字版不变。`test_map_view.py` 新增 `AutonomyTest` 4 例、模块键清单加 `autonomy`，实现前 2 失败 3 报错；并行开关快照与 `reviewCadence` 同样剔除 `autonomy`（整份配置无效时来源报 config invalid 是正确行为，由 `AutonomyTest` 覆盖）；87 例通过。
- [x] Task 3：阶段提示逐字不变的回归与 verify-artifacts 未知 id 警告 — `test-phase-guard.sh` 新增第 25 段（PARTS=25）：设 `moduleAutonomy` 前后阶段提示正文与状态码逐字相同（守护用例，阶段提示代码未改，本来就过）。`verify-artifacts.sh` 在配置检查通过后读 `moduleAutonomy` 与能力图比较，能力图上没有的 id 各报一条 ⚠️，配置或能力图读不了时不报；`test-verify-artifacts.sh` 新增 3 例（两个未知 id 各一条警告、档位写错判无效），97 例通过；ShellCheck 通过。
- [x] Task 4：接口 1.14 与检查器 — `interface.json` 升 1.14：`mapView.autonomy`（出现条件、三个字段、含义：与 `module_tier` 同值、上限由调用方做）与新入口 `moduleAutonomy`（config、key、default `{}`、三档、readFrom、writeWith、notes、contract）。`check-interface.py` 入口清单加 `moduleAutonomy`、取值与 `TIERS` 核对、新增 `_autonomy()` 核对字段与 `map_view.AUTONOMY_FIELDS`；`test-checkers.sh` 加 4 个反例（缺入口、少一档、缺说明、多字段），均变红，检查器回归通过。
- [x] Task 5：说明文字（config、ops 技能、commands、concepts） — `commands/config.md`（frontmatter、可配置项表一行、不注入的例外、`--module` 用法与 note 说明）、`skills/spec-guard-ops/SKILL.md` 的 config 一节、`docs/commands.md`（config 表一行与说明段、`/map` 段的 `autonomy`、verify-artifacts 表的未知模块 ⚠️）、`docs/concepts.md` 自治档位一行。`validate.sh --quick` 通过。
- [x] Task 6：版本号 0.89.0 与 CHANGELOG — 两份 `plugin.json` 改 0.89.0；README 中英 `--ref v0.89.0`；CHANGELOG 加 `## [0.89.0] - 2026-11-20`（新增、变更：#451 的 milestoneStop 措辞修正、升级须知；interface 1.14）。`check-manifests.py`、`check-readme-sync.py` 通过。
- [ ] Checkpoint 1（report）：发布前完整检查、变异验证与临时项目实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
- [ ] 发版（合并后按 Checkpoint 2 授权）：打 tag、发 Release、刷新两个宿主、证据收尾 PR，回告 autopr-design 与 ecosystem-lead
