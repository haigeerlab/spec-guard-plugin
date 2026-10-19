# Todo: scope-authorization

- [x] Task 1：规则与提示的测试（先红） — `test_workflow_checkpoints.py` 加 `test_plan_approval_authorizes_by_scope`（检查点分级一节的关键句含原有停点「测试改不红」「记一份 ADR」、UI 自验并入、宿主确认、两份模板的新句）；`test-verify-artifacts.sh` 加 7 例（缺节提示、标题／行首／英文标题不提示、只在代码块里仍提示、已完成与没有 Plan 不提示）。旧文字与旧脚本上两边都红（规则断言 1 例失败，verify-artifacts 停在第一例）。规则断言随 Task 2–3 提交，verify-artifacts 用例随 Task 4 提交。
- [x] Task 2：共享检查点规则 — `workflow-checkpoints.md`：检查点分级加「批 Plan 按范围授权」「Plan 开头写需要的外部条件」，「异常停点」改为「只在这几类情况停下问用户」的完整清单（保留测试改不红、ADR、权限被拒、结果未知、同一目标第二次）并加「Plan 没列的新依赖只问一次」，第二次报批加「一次列全过这个检查点所需的全部权限」，最终验收清单末尾加依赖与锁文件一行，UI 自验的工具清单并入，权限一节加「宿主确认」。变异：删掉「一次列全过这个检查点所需的全部权限」一句，断言变红，还原后 55 例全绿。
- [x] Task 3：四处约定块 — 两份模板加两行（按范围授权与需要的外部条件；宿主确认）、改两行（最终验收加新增依赖与锁文件改动；第二次报批加一次列全所需权限）；`docs/convention-block.md` 与 `AGENTS.md` 同样四处同步。`check-readme-sync.py` 报一致。
- [x] Task 4：verify-artifacts 提示 — `verify-artifacts.sh` 加「需要的外部条件」一段（仿 AC 编号检查：内嵌 python、跳过代码块、只 warn、读不出给未验证；只看阶段不是 DONE 且有 `tasks/<id>/plan.md` 的模块；认标题、行首一句与英文标题）。回归 82 例全绿。变异：不跳过代码块，「只出现在代码块里仍提示」变红，还原后通过。本仓库实跑 5 通过、0 警告（已完成模块不追溯，本模块 Plan 已写这一节）。
- [x] Checkpoint 1（report）：规则、约定块与提示的回归全绿 — Task 1–3 提交时全档通过；Task 4 随本次提交跑全档。
- [ ] Checkpoint 2（gate）：最终验收；推送与开 PR 在此由用户确认，合并由用户进行
