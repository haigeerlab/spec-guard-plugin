# Todo: module-suspend

- [x] Task 1：挂起判定与阶段提示（先红） — `test-phase-guard.sh` 新增 7 例（挂起让位并单列、activeModule 指向挂起模块、只剩挂起时 DONE 不说全部完成、领先远端时同样、过期标记按完成计、标记须完全相等）；前 5 例先红后绿，领先远端的 2 例是实现后补的、以变异证明有效。189 例全绿。变异：标记改为包含即可、不跳过挂起、领先时文案、`half` 含挂起，均被抓到；最初 `paused_modules` 另加了一道重复过滤，致两处变异都存活，已删去重复的那道。
- [x] Task 2：`add-module` 不被挂起的模块挡住（先红） — `test_module_insert.py` 新增 1 例；Task 1 后即为绿，去掉挂起逻辑时该例失败（证明有效），module-insert 单测全绿，`module-insert.py` 未改。
- [x] Task 3：`module_suspend.py` 与单测（先红） — 8 例。实现与测试同时写成，先红是事后补证：移开实现时 7 例失败，放回后全绿。变异：不要求未勾选项、允许重复挂起，均被抓到。复用 `module_stage` 判定与 `tracker_default` 原子写入，写后读回。
- [x] Task 4：`verify-artifacts` 校验（先红） — 4 例：正常通过、重复失败、过期警告、无标记不输出；先红后绿（39 例）。判据取自 `module_stage` 的标记与未勾选项。变异：重复改为只警告，被抓到。
- [x] Checkpoint 1（report）：核心回归全绿，ShellCheck 无警告 — 见 Checkpoint 2 的同一条验证链。
- [x] Task 5：命令、Codex 路由与文档 — `commands/module-suspend.md`（规范引导段，含可选提醒：时间与内容由用户说、用宿主持久提醒并读回、不可用时请用户自设、插件不保存）；`spec-guard-ops` 的 module-suspend 一节；命令对照表、`design.md` Local boundary、CHANGELOG `[未发布]`／新增。command-parity／names／table 与检查器回归 91 例通过。临时项目实跑：挂起前当前模块 alpha → 确认挂起后为 beta，计数带 `Suspended 1` 并单列 alpha，verify-artifacts 报挂起标记有效 → 确认恢复后回到 alpha、计数复原。
- [x] Checkpoint 2（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行 — 同一条 `&&` 链：validate.sh、phase-guard、verify-artifacts、module_suspend／module_insert／cost-report／project_config 单测与 ShellCheck 全部通过后才提交并推送；PR 由用户合并。
