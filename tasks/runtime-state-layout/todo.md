# Todo: runtime-state-layout

- [x] Task 1：`state_paths.py` 与单测（先红） — 先因模块不存在而红；默认根、覆盖、空覆盖、三种回退、不创建目录、`legacy_in_use` 共 7 例转绿。变异：回退条件写反、忽略环境变量，均被抓到。
- [x] Task 2：五个使用方改用 `state_paths`（先红） — 迁移项用例先红后绿；默认值不变的用例在改造前后都绿（守住逐字节不变）。hosted ticket、proposal closeout、local ledger、local ticket 共 13 个既有单测文件通过；3 个需要 `SPEC_GUARD_EPIQ_RUNTIME` 的验收测试照常跳过、未在本模块运行。
- [x] Task 3：检查器 `check-state-paths.py`（先红） — `test-checkers.sh` 新增 5 例（允许清单放行、新增家目录写入报错并给出行号、`expanduser` 同样拦下、0 个文件为没找到）；检查器缺失时两条应通过的样例失败，实现后 96 例全绿；真实仓库 90 个文件通过；把 `hosted_ticket.py` 改回旧写法时被拦下（`hosted_ticket.py:13`）。接入 `validate.sh`。变异：漏扫 `expanduser`，被抓到。
- [x] Checkpoint 1（report）：全部单测与检查器回归全绿，ShellCheck 无警告 — 见 Checkpoint 2 的同一条验证链。
- [x] Task 4：`config show` 报告根目录与回退中的旧位置（先红） — `test_project_config.py` 新增 3 例（默认根且无旧位置行、覆盖注明来源、旧位置回退时列出）先红后绿（21 例）；`commands/config.md` 与 `spec-guard-ops` 各补一句。变异：不报旧位置，被抓到。
- [x] Task 5：文件布局文档与 CHANGELOG — `docs/design.md` 新增 File layout（四类位置、是否入库、谁写、能否删除，注明 agent-relay 目录不属于 spec-guard）；CHANGELOG `[未发布]`／新增。本机实跑 `config show`：根目录 `~/.spec-guard`，两个旧位置因新目录不存在而列为回退读取；新目录未被创建，旧目录仍为 0 B，没有移动或删除任何文件。
- [x] Checkpoint 2（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行 — 同一条 `&&` 链：validate.sh、phase-guard、verify-artifacts、10 个相关单测文件与 ShellCheck 全部通过后才提交并推送；PR 由用户合并。
