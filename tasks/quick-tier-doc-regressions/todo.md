# Todo: quick-tier-doc-regressions

- [x] Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿 — 2026-10-28 用户批准 Spec（「Spec 批准；Q1 A；Q2 A」）与 Plan（「Plan 批准」），能力图新行经 add-module 预览确认后写入；verify-artifacts 0 失败。
- [x] Task 1：快档跑读仓库文档的回归（AC1、AC2，先红后绿） — `test_validate_quick.py` 抽出 `copy_repo`，新增 `test_quick_blocks_a_doc_edit_that_breaks_a_doc_regression`（删副本 workflow.md 的 `rootCauseReviewRequired` 后跑 `--quick`），`QUICK_SECTIONS` 加「读仓库文档的回归」：
  改前 3 例红（快档放行坏文档、缺新一节两处）。`validate.sh` 快档部分加 `DOC_REGRESSIONS` 数组与新一节，全套回归段删掉这三行及变空的「Checkpoint contract discoverability」节标题（全仓库无别处引用）→ 5 例全绿；`check-tests-registered.py` 65 个测试文件都在。
  变异：第一次把数组清空成 `'true'`，用例仍绿——因为三个测试从 validate.sh 消失，`check-tests-registered` 报漏注册，快档另因此失败，是假绿；改为保留条目、循环里不执行（`if out="$(true)"`），用例变红，还原。
  耗时：改前 13.34／13.24／12.72 秒（中位 13.24），改后 14.70／14.97／14.68 秒（中位 14.70），多 1.46 秒。CI 同版 ShellCheck（`scripts/validate.sh`）无告警。
- [x] Task 2：漏列检查器（AC3、AC4，先红后绿） — `test-checkers.sh` 先加 8 例（已列入放行、python 读 README 漏列报错且报出路径、shell 读 `$ROOT/docs` 漏列报错、临时目录 docs 夹具不报、注释掉的清单行不算、没有清单报错、当前仓库通过）：
  检查器不存在时 4 例红。新增 `scripts/check-doc-regressions-listed.py` 并接进 validate 快档（`check-collaboration-boundary.py` 之后）→ 159 例全绿；两个报错用例的输出核对过，是因为漏列而报错。
  变异：`missing = []`（永远放行）→ 4 例红，还原。AC4：按同一写法扫现有测试只找出已列入的那 3 个（`test_workflow_checkpoints.py` 第 396 行的旧词回归也在其中），无需再加。
- [x] Checkpoint 1（report）：三套核心回归与 ShellCheck — `validate.sh` 通过；phase-guard 507 例、verify-artifacts 78 例通过；`npx --yes shellcheck@4.1.0 -S warning` 跑 hooks、scripts、evals 全部 `.sh` 无告警；
  `git diff --stat origin/main -- scripts/verified_trees.py scripts/verify-and-commit.sh .github plugins/spec-guard` 为空。
- [x] Task 3：维护者文档（AC6） — `docs/maintainer-workflow.md` 测试登记一段后加「读仓库文档的测试例外」一段（DOC_REGRESSIONS、为什么、漏列由检查器拦、夹具不算），快档那条写明含 DOC_REGRESSIONS；
  `CLAUDE.md` 讲快档的那句补「含读仓库文档的回归」。本次提交只改文档，走的就是新快档。
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
