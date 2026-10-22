# Todo: config-per-key

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-22 用户批准 Plan（事项 C9），模块协调在集成分支 `f6e1e77` 记批准标记并提交；`module-crew sync` 合入本分支。
- [x] Task 1：`load` 逐键判定与读取方（先红后绿） — `test_project_config.py` 新增 5 例（未知键只丢自己、非法值只丢自己的键、逐键代码固定顺序、汇总逐键来源、结构问题标全部来源）并改 3 例（`test_module_concurrency_values` 与 `test_everything_else_is_false` 里「别的键有问题」的期望、`test_invalid_documents_return_no_values` 拆为结构类 `test_structural_problems_return_no_values`），只加 `STRUCTURAL` 常量时 6 例红；改 `load`、`module_concurrency`、`summary` 后 32 例全绿。`test_map_view.py` 的「等同无配置」一例原用「`on` 加未知键」，按新规则这是开，改用 `version: 2`，另加 1 例锁住「未知键不影响开关」。`test_python_compat` 通过。
- [x] Task 2：`check`、`set`／`unset` 与 `show` 文本（先红后绿） — `test_project_config.py` 新增 5 例（`set` 保留其余键与顺序、用合法值修好或 `unset` 删掉非法键、结构问题仍拒写、`show` 区分「已忽略」与「整份按默认」、`show`／`check` 不回显未知键）并把 `test_check_exit_codes` 改为三档（只有未知键 0 + `ok (ignored: unknown-key)`；未知键加非法值、结构问题仍为 1，输出格式同原来），先红 4 例；改 `check`、`render`（新增 `rest` 参数）、`_change`（结构问题才拒写，读回核对目标键与其余键）、`_show` 后 37 例全绿；没有其余键时写出与原来逐字节相同（原有 `set`／`unset` 用例未改）。
- [x] Task 3：阶段提示与 verify-artifacts（先红后绿） — `module_stage.py`：`config_lines` 只在结构问题时出原 invalid 行，逐键问题时合法键照常并加一行 ignored（zh-CN 为中文）；`hint_language` 与两处 combined 条件只看自己的键。`verify-artifacts.sh`：`check` 退出 0 且带 ignored 时警告。用例：phase-guard 新增 6 例（结构问题、非 JSON、逐键问题、只有未知键、未知键加 zh-CN、早期阶段的逐键问题），改 4 例期望——第 1049 行与早期阶段那例原用 `zh-CN` + 节奏非法 + 未知键并期望只有 invalid 行，按新规则这是逐键问题，改为结构问题（`version: 2`）保住 invalid 行逐字节不变，另加逐键用例（语言用 `pt-BR`，以便与无配置时的英文输出逐行比对；中文另用一例单测）；Codex 一处 `{"x": 1}` 改为 `version: 2` 测原 invalid 行，另加一例测 ignored 行的 `$spec-guard-ops` 写法；`zh_CN` 一例由「invalid」改为「ignored (artifactLanguage-invalid)」。verify-artifacts 新增 2 例（只有未知键警告不失败、结构问题失败）。在草稿副本换回旧 `module_stage.py` 时新用例红（第 11、12、16、18 段），verify-artifacts 新例在改脚本前红；改后 phase-guard 435 例、verify-artifacts 74 例、map-view 全绿。
- [ ] Checkpoint 1（report）：三套核心回归、ShellCheck 与改坏验证
- [ ] Task 4：说明文字
- [ ] Checkpoint 2（gate）：模块验收

## 更新说明

供模块协调整批合完后写 CHANGELOG（用户 2026-10-22 答复：本模块不改 CHANGELOG 与版本号）。

- 修复：`.agent/config.json` 改为逐键容错。某个键不认识，只忽略这个键；已认识的键取值不对，只有它按未设置处理；其余设置照常生效，
  阶段提示多一行「已忽略」。文件读不了、不是 JSON、顶层不是对象或 `version` 不对时仍整份按默认。只有不认识的键时 `check` 通过并提示，
  verify-artifacts 只警告；`set`／`unset` 只改目标键，不删别的键。旧版本 spec-guard 遇到不认识的键仍会整份失效（审查 F9）。
