# Todo: teardown-local-section

- [x] Task 1：回归先行（先红）— `test-setup-teardown.sh` 新增 6 例：本地段留在原位置、标记去掉、state 停用且完成提示给出行数；预览列出需接受的手写行、不列本地段且不改文件；有手写行时不带参数退出 1、指令文件与 state 不变，带 `--accept-removals` 后移除；本地段两段 / 颠倒 / 不成对均拒绝；无块时 `--accept-removals` 退出 2；只有派活规则段时无需接受且逐字节还原；Codex 宿主一例。旧代码上首例即红
- [x] Task 2：managed-block 与 teardown-convention 实现 — `remove` 增加 `--known`、`--accept-removals`、`--dry-run`，与 `replace` 共用选项解析、已知行与拒绝输出；输出改为“删除行数 保留行数”。setup/teardown 56 例通过。变异均被抓到：去掉本地段保留、去掉删除闸门、teardown 不传 `--known`
- [x] Task 3：文档 — 命令 `teardown-convention.md`（含 argument-hint）、Codex skill teardown 一节、`docs/workflow.md`
- [x] Checkpoint 1（report）：全部套件通过，ShellCheck 无告警
- [x] Task 4：CHANGELOG + 0.54.2 + macOS 校验
- [ ] Checkpoint 2（gate）：模块评审；Plan 获批即授权推送与开 PR，合并由用户进行
- [ ] Task 5：发版后证据
