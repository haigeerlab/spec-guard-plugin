# Todo: pre-declared-scope

- [x] Task 0：提交已批准的 Spec、能力图两行与 Plan 草稿 — 2026-10-26 用户批准 Plan（「批准 pre-declared-scope 的 Plan」）；Spec、能力图、Plan 草稿在 `4245cd57` 提交，Plan 批准标记随本次提交。
- [x] Task 1：「预先声明」解析与错误码（C1，先红后绿） — `test_module_scope.py` 新增 `ParseDeclared` 8 例（中英标题与行名、缺行与全「无」、去重保序、围栏示例、`bad-path`／`bad-dependency`／`unknown-line`／`duplicate-section` 各种写法、错误不带文件文字）；改前红（导入失败）。`module_scope.py` 加 `DeclaredScope`、`parse_declared`、`DECLARED_ERRORS`，复用 `_visible`、`FIELD`、`_path`。45 例全绿；变异（去掉配置／补丁不许目录）→ 2 例红。
- [x] Task 2：批准判断与 `declared` 命令（C2，先红后绿） — `test_module_scope.py` 新增 `Declared` 7 例：真 git 夹具覆盖 Spec AC3 的六种情况（批准提交、改未提交、改后提交、改回待批准再批准、批准从未提交、不在 git 里），命令退出 0／2／4、JSON 形状、没有 plan.md 或没有这一节时 `declared: false`、错误不回显文件文字。改前红（导入失败）；`plan_approval` 只读 git，判据复用 `module_stage.review_state`。52 例全绿；变异（去掉逐字节比较）→ 批准判断用例红。
- [x] Task 3：接口 1.11 与说明 — `check-interface.py` 的 `ENTRIES` 加 `declaredScope`，核对其脚本存在与 `values.error` 等于 `module_scope.DECLARED_ERRORS`；先改检查器，现有 interface.json 报「缺少入口 declaredScope」（红），再把 interface 升到 1.11 并加入口（绿）。`test-checkers.sh` 加缺入口、少错误码两例，149 例全绿。`docs/design.md` 接口一段补 1.11。注意：两例在入口不存在时会因 KeyError 失败，不能当作红，真正的红是上面检查器那一步。
- [x] Task 4：verify-artifacts 校验这一节（C3，先红后绿） — `test-verify-artifacts.sh` 新增 4 例：没有这一节不提示、格式错判失败（开关没开也查，给出模块 id 与 `bad-dependency`）、格式对计数、已完成模块不追溯；改前红（退出 0）。`module_scope.py validate-declared` 与 `validate` 同一种行协议，verify-artifacts.sh 新增一段。78 例全绿，ShellCheck `-S warning` 无告警。
- [ ] Task 5：规则文字（C4）
- [ ] Checkpoint 1（report）：三套核心回归
- [ ] Task 6：CHANGELOG 未发布段与更新说明
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
