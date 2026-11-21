# Todo: takeover-narrow

- [x] Task 0：提交 Plan 与 todo — 2026-11-21 用户批准 Spec（「批准；Q3 A」）与 Plan（「Plan 批准」）。
- [x] Task 1：narrow_step 与 narrow 子命令、takeoverNarrowed 校验 — `project_config.py` 新增 `PRESET_LADDER`、`NARROW_ORDER`（发布、合并、Plan、Spec）、`narrow_step`、`narrower_or_equal`、`widen_steps`、`valid_reason`、`valid_narrowed`，`VALIDATORS` 加 `takeoverNarrowed`（`config set／unset` 不能直接改它，退出 2）；子命令 `narrow --source --reason [--module] [--confirm]`：预览列收窄前后四项，已是最严时不写、退出 0，记录保留第一次的 from；写入部分抽成 `_prepare`／`_print_diff`／`_commit` 供 set 与 narrow 共用。`test_project_config.py` 新增 `Narrow` 9 例（实现前 7 失败 1 错误），62 例全过。
- [x] Task 2：恢复一次一格 — `_change` 在改 `takeover`／`moduleTakeover` 时调 `_keep_narrowed`：有收窄记录的范围放宽超过一格退出 2（`takeover-narrowed: … widen it one step at a time`），一格成功并把记录的 to 更新；回到 from 或更宽时删记录；往严改不受限也更新记录；没有记录的范围不限。`test_project_config.py` 新增 `Restore` 5 例（实现前 4 失败），67 例全过。
- [x] Task 3：`/map --json` 的 narrowed 与接口 — `map_view.py` 的 `takeover` 加 `narrowed`（模块有自己的条目读模块记录，否则读项目记录；只给 from、source、at，不含 reason），`TAKEOVER_FIELDS` 同步；`test_map_view.py` 新增 1 例并把四例的期望补上 `narrowed`（改前 3 失败 1 错误），全过。`interface.json` 新增 `takeoverNarrow`（命令、来源词表、顺序、范围、退出码、说明），`mapView.takeover.fields.narrowed`，`takeover.notes` 写明 `takeoverNarrowed`；`check-interface.py` 核对 `takeoverNarrow` 存在、脚本存在、来源词表与 `SOURCES` 一致；`test-checkers.sh` 加 2 个反例，夹具补 `project_config.py` 占位，175 例通过。`test-phase-guard.sh` 第 25 段加带收窄记录的配置，524 例通过。
- [x] Task 4：说明文字 — `commands/config.md` 加「出事收窄」一段（narrow 用法、顺序、takeoverNarrowed 记录与提交、恢复一次一格、不能直接改记录）；`skills/spec-guard-ops/SKILL.md` config 一节加一条；`docs/commands.md` 加给用户看的说明（自动收一格、记原因、要提交、恢复分次说、`takeover.narrowed`）。`validate.sh --quick` 通过。
- [ ] Checkpoint 1（report）：完整检查、变异验证与临时项目实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
