# Todo: autonomy-tier

- [x] Task 0：提交已批准的 Spec 与 Plan 草稿 — 2026-10-26 用户批准 Plan（「批准 autonomy-tier 的 Plan」）；Spec 与 Plan 草稿在 `269be3ba` 提交，Plan 批准标记随本次提交。
- [x] Task 1：配置项 `autonomyTier`（C1，先红后绿） — `test_project_config.py` 新增 `AutonomyTier` 4 例（三档 set／读回／来源／unset、未设置为 strict／default、`fast` 写不进且文件里的坏值只让这个键回默认并 `check` 失败、`config_lines` 设与不设三档相同）；改前 4 例红（未知键）。`project_config.py` 加 `TIERS`、校验器与默认值；原「汇总列出全部配置项」用例加上新键。配置与阶段注入相关 59 例全绿；变异（TIERS 删掉 relaxed）→ 2 例红。
- [x] Task 2：接口条目（C3，先红后绿） — 先改 `check-interface.py`（`ENTRIES` 加 `autonomyTier`，核对 `values` 等于 `project_config.TIERS`），现有 interface.json 报「缺少入口 autonomyTier」（红）；加入口后通过（绿）。`test-checkers.sh` 加缺入口、少一档两例，151 例全绿。`docs/design.md` 1.11 一段补 autonomyTier。
- [x] Task 3：底线规则与说明（C2、C4） — workflow-checkpoints 在「批准节奏」与「批准标记」之间新增「## 自治档位与底线」（档位与含义归属、不联动 reviewCadence、写入要原话、底线三项批准与三种必停、项目更严以项目为准）；`config.md` 表格加一行、「不注入」的例外加上它；SKILL.md config 一节同步。`test_workflow_checkpoints.py` 新增 `test_autonomy_tier_and_floor`，改前红，改后 104 例全绿。
- [x] Checkpoint 1（report）：三套核心回归 — Task 3 提交时 verify-and-commit 全档（validate、phase-guard、verify-artifacts、本仓库 verify-artifacts）通过；CI 同版 `npx shellcheck@4.1.0 -S warning`（hooks、scripts、evals 全部 .sh）无告警。
- [x] Task 4：版本号 0.85.0 与 CHANGELOG — 两份 `plugin.json` 与 README 中英 `--ref` 改为 0.85.0（`check-readme-sync.py` 通过）；CHANGELOG 顶部「未发布」段改为 `## [0.85.0] - 2026-10-26`，加本版范围、升级须知（旧版本对新键的处理、已有同名一节）与本模块条目。`interface.json` 版本不动（已是 1.11）。
- [ ] Checkpoint 2（gate）：最终验收；通过后同步 main、推送并开本模块 PR，合并由用户进行

## 更新说明

- 0.85.0 = pre-declared-scope（#414）+ autonomy-tier；interface 1.11。发版前告诉 ecosystem-lead 影响面；CHANGELOG 日期若发版跨日要更正。
