# Todo: doc-chain

- [x] Task 0：同步批准标记，按 C190 修订 Spec — 按开工通知（C198）单独 `module-crew sync` 到集成分支 e41f7df（HEAD d84aecf5），Spec、Plan 取集成分支带批准标记的版本；validate、phase-guard（488 例）、verify-artifacts（74 例）全过。按 C190 改 Spec：改动 4 对 `docs/optional-features.md` 只改基线路径说法（现有两处已是 `docs/DOCUMENTATION-BASELINE.md`，不用改），并行边界独占清单去掉它，重叠一节写明分工，末尾加变更记录；`module_scope.py validate` 通过。Spec 指纹随之变为修订，最终验收附这段差异。
- [x] Task 1：核验按状态区分（改动 1、改动 5 前半） — 回归先写：新增 `StatusAwareVerificationTests`（14 例，临时 git 仓库）——现状类没改为 `unchanged` 且 attention；已提交与只在工作区的改动都算 `changed`；target 没改为 `target-unchanged` 不报；target 只增给行数不报；target 有删除行加 attention（含 approval）；URL 为 `unverified` 且不对它跑 git；`#锚点` 去掉再比；Spec 删除重建取最早加入提交；Spec 未提交、非 git 目录、git 不可运行、git 非零退出都为 `unknown` 带原因；deferred／pending／create 为 `not-checked`；JSON 带 check、added、removed。改前 15 个报错。原有 7 例断言不改；其中两条断言 `ready` 的（`test_delivered_outcome_with_evidence_is_ready`、`test_fenced_example_outcome_table_is_ignored`）按 Plan 风险一改夹具为临时 git 仓库（`committed_then_changed`），原断言照过。实现：`_git()`（列表参数、10 秒超时、不经 shell）、`_changes()`（基点为最早加入 Spec 的提交，`git diff --numstat <基点> -- <路径>`，二进制按改过、行数未知）、`_check()` 按基线状态判定。`test_documentation_verification.py`（21 例）、`test_documentation_impact.py`、`test_documentation_baseline.py`、`test_python_compat.py` 全过。
- [x] Task 2：最终 gate 注入核验要求（改动 2、改动 5 后半） — 回归先写：`test_stop_rules.py` 新增 `DocumentationCheckLine`（4 例）——串行最终 gate 有基线时出「文档核验」一行（中文／英文 × Claude／Codex 入口），在「建议下一步」之前；没有基线时输出与加基线后去掉这一行逐字相同；Spec 待审、Plan 待审、构建途中、中途 gate 不出；模块 checkout 在最终 gate 出（入口带角色模块 id）、构建途中不出，协调 checkout 不出。改前 6 处失败。实现：`module_stage.py` 新增 `documentation_baseline_present()`、`documentation_check_line()` 与各宿主表的 `doc-verify` 键；串行在 `describe()` 的 notes 末尾追加，模块角色在 `role_view()` 里按角色模块自己的 `stop_node` 追加（角色视图看的是自己的模块，不是全项目的当前模块）。`test_stop_rules.py`（20 例）、`test_checkout_role.py`、`test_module_stage_sanitization.py`、`test_module_insert.py`、`test_map_view.py`、`test_python_compat.py`、phase-guard（488 例）全过。
- [ ] Task 3：规则文字（改动 3）
- [ ] Task 4：说明文字（改动 4）
- [ ] Checkpoint 1（report）：变异核对
- [ ] Task 5：临时消费者项目实跑（AC10）
- [ ] Task 6：合入集成分支并跑完整检查
- [ ] 最终验收（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做
