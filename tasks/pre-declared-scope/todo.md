# Todo: pre-declared-scope

- [x] Task 0：提交已批准的 Spec、能力图两行与 Plan 草稿 — 2026-10-26 用户批准 Plan（「批准 pre-declared-scope 的 Plan」）；Spec、能力图、Plan 草稿在 `4245cd57` 提交，Plan 批准标记随本次提交。
- [x] Task 1：「预先声明」解析与错误码（C1，先红后绿） — `test_module_scope.py` 新增 `ParseDeclared` 8 例（中英标题与行名、缺行与全「无」、去重保序、围栏示例、`bad-path`／`bad-dependency`／`unknown-line`／`duplicate-section` 各种写法、错误不带文件文字）；改前红（导入失败）。`module_scope.py` 加 `DeclaredScope`、`parse_declared`、`DECLARED_ERRORS`，复用 `_visible`、`FIELD`、`_path`。45 例全绿；变异（去掉配置／补丁不许目录）→ 2 例红。
- [x] Task 2：批准判断与 `declared` 命令（C2，先红后绿） — `test_module_scope.py` 新增 `Declared` 7 例：真 git 夹具覆盖 Spec AC3 的六种情况（批准提交、改未提交、改后提交、改回待批准再批准、批准从未提交、不在 git 里），命令退出 0／2／4、JSON 形状、没有 plan.md 或没有这一节时 `declared: false`、错误不回显文件文字。改前红（导入失败）；`plan_approval` 只读 git，判据复用 `module_stage.review_state`。52 例全绿；变异（去掉逐字节比较）→ 批准判断用例红。
- [ ] Task 3：接口 1.11 与说明
- [ ] Task 4：verify-artifacts 校验这一节（C3，先红后绿）
- [ ] Task 5：规则文字（C4）
- [ ] Checkpoint 1（report）：三套核心回归
- [ ] Task 6：CHANGELOG 未发布段与更新说明
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
