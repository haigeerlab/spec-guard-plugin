# Todo: checkout-role

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：角色标记的读写与命令行（先红后绿） — 新建 `test_checkout_role.py`（`Marker` 9 例：各自 git 目录且不进 git status、`--project` 与 cwd 不同、预览／确认／清除、模块不在能力图与非法 id、父仓库子目录与 bare 与非 git 目录、开关 off 拒写、目录或文件为符号链接与目录与超长、无效内容不回显、读回不一致报 4、off 时零读取），先因模块不存在导入失败；新建 `checkout_role.py`（`role_path`、`read_role`、`role`、`change` 与 CLI；git 包装另写一份以免与 module_stage 循环导入，写入复用 `tracker_default._write_atomic`）后 9 例全绿。测试已登记进 `scripts/validate.sh`。
- [ ] Task 2：阶段提示的展示层（先红后绿）
- [ ] Task 3：`/map` 的 worktree 字段与表格后缀（先红后绿）
- [ ] Checkpoint 1（report）：一次性整份比对、核对选模块代码未动、三套核心回归与改坏验证
- [ ] Task 4：命令说明、Codex 技能、共享规则与文档
- [ ] Checkpoint 2（gate）：模块验收
