# Todo: convention-block-local-lines

- [x] Task 1：回归先行（先红）— `test-setup-teardown.sh` 新增：本地段原样保留在新块末尾且模板正文完整；只有本地段时预览无删除、替换无需接受；预览逐行列出 will remove / will add 且不列本地段；手改行时不带参数退出 1、列出该行、文件不变，带 `--accept-removals` 后替换；本地段两段、颠倒、不成对均拒绝且不改文件；`--accept-removals` 单独给出退出 2。原有“--replace 直接恢复手改行”与“块内提及规则标记”两例改为需接受（行为变化，按 Spec 假设 3）。在旧代码上首例即红
- [x] Task 2：managed-block 与 setup-convention 实现 — `managed-block.py replace` 增加 `--known`、`--accept-removals`、`--dry-run`：识别唯一本地段并原样接到新块末尾，计算删除/新增（忽略空行），模板与规则段之外的删除无接受即退出 3 不写文件；`setup-convention.sh` 解析 `--accept-removals`（不配 `--replace` 退出 2），预览缩进打印清单，拒绝时报未改动并退出 1。setup/teardown 50 例通过。变异均被抓到：去掉本地段保留、去掉删除闸门、忽略 `--known`（`--no-dispatch` 例变红）
- [x] Task 3：文档 — 命令 `setup-convention.md`（含 argument-hint）、Codex skill setup 一节、`docs/workflow.md` 写明本地段标记、预览清单与 `--accept-removals`；命令与 skill 参数一致性检查通过（21 个命令），命令插件根回归通过
- [x] Checkpoint 1（report）：全部套件通过，ShellCheck 无告警 — validate.sh 通过，phase-guard、verify-artifacts、setup/teardown 50 例通过，CI ShellCheck 范围无告警
- [x] Task 4：本仓库 AGENTS.md 迁移（预览给用户后再替换）
- [x] Task 5：CHANGELOG + 0.54.1 + macOS 校验
- [ ] Checkpoint 2（gate）：模块评审；Plan 获批即授权推送与开 PR，合并由用户进行
- [ ] Task 6：发版后证据
