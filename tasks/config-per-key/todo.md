# Todo: config-per-key

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-22 用户批准 Plan（事项 C9），模块协调在集成分支 `f6e1e77` 记批准标记并提交；`module-crew sync` 合入本分支。
- [x] Task 1：`load` 逐键判定与读取方（先红后绿） — `test_project_config.py` 新增 5 例（未知键只丢自己、非法值只丢自己的键、逐键代码固定顺序、汇总逐键来源、结构问题标全部来源）并改 3 例（`test_module_concurrency_values` 与 `test_everything_else_is_false` 里「别的键有问题」的期望、`test_invalid_documents_return_no_values` 拆为结构类 `test_structural_problems_return_no_values`），只加 `STRUCTURAL` 常量时 6 例红；改 `load`、`module_concurrency`、`summary` 后 32 例全绿。`test_map_view.py` 的「等同无配置」一例原用「`on` 加未知键」，按新规则这是开，改用 `version: 2`，另加 1 例锁住「未知键不影响开关」。`test_python_compat` 通过。
- [ ] Task 2：`check`、`set`／`unset` 与 `show` 文本（先红后绿）
- [ ] Task 3：阶段提示与 verify-artifacts（先红后绿）
- [ ] Checkpoint 1（report）：三套核心回归、ShellCheck 与改坏验证
- [ ] Task 4：说明文字
- [ ] Checkpoint 2（gate）：模块验收

## 更新说明

供模块协调整批合完后写 CHANGELOG（用户 2026-10-22 答复：本模块不改 CHANGELOG 与版本号）。

- 修复：`.agent/config.json` 改为逐键容错。某个键不认识，只忽略这个键；已认识的键取值不对，只有它按未设置处理；其余设置照常生效，
  阶段提示多一行「已忽略」。文件读不了、不是 JSON、顶层不是对象或 `version` 不对时仍整份按默认。只有不认识的键时 `check` 通过并提示，
  verify-artifacts 只警告；`set`／`unset` 只改目标键，不删别的键。旧版本 spec-guard 遇到不认识的键仍会整份失效（审查 F9）。
