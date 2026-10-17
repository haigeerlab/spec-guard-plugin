# Todo: module-scope-boundary

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：解析与路径归属（先红后绿） — 新建 `test_module_scope.py`（解析 11 例、路径归属 4 例），先因模块不存在导入失败；新建 `module_scope.py` 实现 `parse`／`Scope`／`ScopeError`／`covers` 后 15 例全绿。测试登记进 `scripts/validate.sh`，`check-tests-registered.py`（61 个文件）与 `test_python_compat` 通过。
- [x] Task 2：越界检查 `check`（先红后绿） — 新增 `Check` 6 例（临时 git 仓库里改独占内、流程文件、外部文件，加未跟踪、中文文件名与删除；文本与 JSON；退出码 2／3／4），先红 6 例；实现 `changed_files`（`git diff --no-renames --name-status -z` 加 `ls-files --others --exclude-standard -z`）、`_check` 与命令行入口后全绿。另加一道防线：`--base` 以 `-` 开头直接按无效处理，免得被 git 当成选项（加了对应断言）。
- [x] Task 3：`validate` 与 verify-artifacts（先红后绿） — `test_module_scope.py` 加 `Validate` 3 例（off／未设置无输出；on 时 ok 1、缺失 warn、格式错 bad、已完成与没写 Spec 的模块跳过；能力图读不了出 unverified），先红 3 例；`test-verify-artifacts.sh` 加 4 例，其中「off 时格式错误的并行边界也不改变输出」本来就绿（防线），「on 时格式错误失败」先红。实现 `validate` 与 verify-artifacts 新段落后单元 24 例、verify-artifacts 67 例全绿。能力图读不了时的提示改成明确说能力图，已用一个坏能力图实跑确认。
- [x] Task 4：phase-guard 不受影响的回归 — project-config 段加 1 例：Spec 带并行边界时，无配置与开关 on 两种注入都与原来逐字节一致；预期直接绿，phase-guard 368 例全绿。
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告，并做两次改坏验证
- [ ] Task 5：共享规则（先红后绿）
- [ ] Task 6：设计文档与 CHANGELOG
- [ ] Checkpoint 2（gate）：模块验收
