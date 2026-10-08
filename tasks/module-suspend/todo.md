# Todo: module-suspend

- [x] Task 1：挂起判定与阶段提示（先红） — `test-phase-guard.sh` 新增 7 例（挂起让位并单列、activeModule 指向挂起模块、只剩挂起时 DONE 不说全部完成、领先远端时同样、过期标记按完成计、标记须完全相等）；前 5 例先红后绿，领先远端的 2 例是实现后补的、以变异证明有效。189 例全绿。变异：标记改为包含即可、不跳过挂起、领先时文案、`half` 含挂起，均被抓到；最初 `paused_modules` 另加了一道重复过滤，致两处变异都存活，已删去重复的那道。
- [x] Task 2：`add-module` 不被挂起的模块挡住（先红） — `test_module_insert.py` 新增 1 例；Task 1 后即为绿，去掉挂起逻辑时该例失败（证明有效），module-insert 单测全绿，`module-insert.py` 未改。
- [x] Task 3：`module_suspend.py` 与单测（先红） — 8 例。实现与测试同时写成，先红是事后补证：移开实现时 7 例失败，放回后全绿。变异：不要求未勾选项、允许重复挂起，均被抓到。复用 `module_stage` 判定与 `tracker_default` 原子写入，写后读回。
- [x] Task 4：`verify-artifacts` 校验（先红） — 4 例：正常通过、重复失败、过期警告、无标记不输出；先红后绿（39 例）。判据取自 `module_stage` 的标记与未勾选项。变异：重复改为只警告，被抓到。
- [ ] Checkpoint 1（report）：核心回归全绿，ShellCheck 无警告
- [ ] Task 5：命令、Codex 路由与文档
- [ ] Checkpoint 2（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行
