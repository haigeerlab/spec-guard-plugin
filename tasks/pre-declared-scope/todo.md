# Todo: pre-declared-scope

- [x] Task 0：提交已批准的 Spec、能力图两行与 Plan 草稿 — 2026-10-26 用户批准 Plan（「批准 pre-declared-scope 的 Plan」）；Spec、能力图、Plan 草稿在 `4245cd57` 提交，Plan 批准标记随本次提交。
- [x] Task 1：「预先声明」解析与错误码（C1，先红后绿） — `test_module_scope.py` 新增 `ParseDeclared` 8 例（中英标题与行名、缺行与全「无」、去重保序、围栏示例、`bad-path`／`bad-dependency`／`unknown-line`／`duplicate-section` 各种写法、错误不带文件文字）；改前红（导入失败）。`module_scope.py` 加 `DeclaredScope`、`parse_declared`、`DECLARED_ERRORS`，复用 `_visible`、`FIELD`、`_path`。45 例全绿；变异（去掉配置／补丁不许目录）→ 2 例红。
- [x] Task 2：批准判断与 `declared` 命令（C2，先红后绿） — `test_module_scope.py` 新增 `Declared` 7 例：真 git 夹具覆盖 Spec AC3 的六种情况（批准提交、改未提交、改后提交、改回待批准再批准、批准从未提交、不在 git 里），命令退出 0／2／4、JSON 形状、没有 plan.md 或没有这一节时 `declared: false`、错误不回显文件文字。改前红（导入失败）；`plan_approval` 只读 git，判据复用 `module_stage.review_state`。52 例全绿；变异（去掉逐字节比较）→ 批准判断用例红。
- [x] Task 3：接口 1.11 与说明 — `check-interface.py` 的 `ENTRIES` 加 `declaredScope`，核对其脚本存在与 `values.error` 等于 `module_scope.DECLARED_ERRORS`；先改检查器，现有 interface.json 报「缺少入口 declaredScope」（红），再把 interface 升到 1.11 并加入口（绿）。`test-checkers.sh` 加缺入口、少错误码两例，149 例全绿。`docs/design.md` 接口一段补 1.11。注意：两例在入口不存在时会因 KeyError 失败，不能当作红，真正的红是上面检查器那一步。
- [x] Task 4：verify-artifacts 校验这一节（C3，先红后绿） — `test-verify-artifacts.sh` 新增 4 例：没有这一节不提示、格式错判失败（开关没开也查，给出模块 id 与 `bad-dependency`）、格式对计数、已完成模块不追溯；改前红（退出 0）。`module_scope.py validate-declared` 与 `validate` 同一种行协议，verify-artifacts.sh 新增一段。78 例全绿，ShellCheck `-S warning` 无告警。
- [x] Task 5：规则文字（C4） — `workflow-checkpoints.md` 在「批 Plan 按范围授权」后加「预先声明」一条（何时写、四行写法、批准即授权、不能预先声明的三类、不得自加更严条款、没有这一节时不用写）；`node-rules.md`「Plan 交审」加一条（逐条列出、写 `无` 的行也列、「批准本 Plan 即授权以下公共改动」）。`test_workflow_checkpoints.py` 新增 `test_pre_declared_section`，节点规则的 ELEMENTS／SHARED 各加短语；改前 4 例红，改后 workflow-checkpoints 与 stop-rules 103 例全绿；Plan 交审一节仍在 2600 字节上限内。
- [x] Checkpoint 1（report）：三套核心回归 — Task 5 的 verify-and-commit 全档（validate、phase-guard、verify-artifacts、本仓库 verify-artifacts）通过；CI 同版 `npx shellcheck@4.1.0 -S warning`（hooks、scripts、evals 全部 .sh）无告警。途中两次提交因本机负载（load average 22～43）计时用例超时被拦（phase-guard 第 9 段 stdin 用例、test_session_context 的 open stdin 用例），单独重跑与重试均通过，与改动无关。
- [x] Task 6：CHANGELOG 未发布段与更新说明 — CHANGELOG 顶部新开「未发布」段，新增两条（预先声明一节、declaredScope 接口 1.11）；版本号不动，由 autonomy-tier 一起发 1.11。
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行

## 更新说明

供 `autonomy-tier` 发版时并入 CHANGELOG 版本段（本模块已写在「未发布」段，版本号不动）。

- 新增：Plan「预先声明」一节与 verify-artifacts 格式校验；只读接口 `declaredScope`，interface 1.10 → 1.11。
- 给 module-crew：`planApproved` 用 git 比对判断，批准后改过（含已提交）一律 false；读不到入口时照旧问用户。
