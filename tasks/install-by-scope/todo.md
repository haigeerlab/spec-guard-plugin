# Todo: install-by-scope

- [x] Task 1：断言改写与反向断言（先红） — `test_plan_approval_authorizes_by_scope` 改为新说法（已批准范围、构建需要的装包、默认放行、愿意写可以写、全局安装与下载脚本直接执行、新增的直接依赖、工作区自己的包、宿主确认），另加退役短语清单（只问一次、一条命令、会对照 Plan、Plan 开头写「需要的外部条件」、Plan 没列的新依赖）对规则与两份模板做 assertNotIn，模板不得出现「需要的外部条件」；`test-verify-artifacts.sh` 删掉两段的 22 例，加 3 例反向（没有这一节且清单新增依赖时 0 警告、不提示这一节、不报依赖改动）。旧规则与旧脚本上都红。
- [x] Task 2：共享检查点规则与四处约定块 — `workflow-checkpoints.md` 五处：「批 Plan 按范围授权」改写并去掉「Plan 开头写需要的外部条件」整条；最终验收那行改为新增的直接依赖、排除工作区自己的包；「只问用户」清单去掉新依赖、高风险补全局安装与下载脚本直接执行；删「Plan 没列的新依赖只问一次」；UI 自验恢复原说法；宿主确认删后半段。四处约定块改两行。第一次断言因「构建需要的装包」被换行拆开而失败，重排后通过；`check-readme-sync.py` 一致。
- [x] Task 3：删掉检查与模块 — `git rm` 了 `dependency_check.py` 与 `test_dependency_check.py`；删 verify-artifacts 两段、`validate.sh` 登记、`commands/verify-artifacts.md` 与 `docs/commands.md` 的说明。复核：`git grep` 只剩测试里的退役断言；`verify-artifacts.sh`、两处文档与 `validate.sh` 与 0883717（0.77.0 之后、scope-authorization 之前）逐字一致。回归 78 例全绿；本仓库实跑 5 通过、0 警告（原先对本模块 Plan 的那条提示消失）。
- [x] Checkpoint 1（report）：规则、约定块与 verify-artifacts 回归全绿 — 随本次提交跑 `verify-and-commit.sh` 全档。
- [ ] Task 4：CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：最终验收；推送与开 PR 在此由用户确认，合并由用户进行
