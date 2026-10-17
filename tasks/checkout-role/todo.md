# Todo: checkout-role

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：角色标记的读写与命令行（先红后绿） — 新建 `test_checkout_role.py`（`Marker` 9 例：各自 git 目录且不进 git status、`--project` 与 cwd 不同、预览／确认／清除、模块不在能力图与非法 id、父仓库子目录与 bare 与非 git 目录、开关 off 拒写、目录或文件为符号链接与目录与超长、无效内容不回显、读回不一致报 4、off 时零读取），先因模块不存在导入失败；新建 `checkout_role.py`（`role_path`、`read_role`、`role`、`change` 与 CLI；git 包装另写一份以免与 module_stage 循环导入，写入复用 `tracker_default._write_atomic`）后 9 例全绿。测试已登记进 `scripts/validate.sh`。
- [x] Task 2：阶段提示的展示层（先红后绿） — `test_checkout_role.py` 加 `ModuleRoleView` 7 例、`CoordinatorView` 3 例、`RoleOffOrInvalid` 2 例，先红 10 例（「批准后已修订」与 off 忽略两例本来就绿，作防线）；`module_stage.py` 新增 `role_view`，在 `describe()` 里读一次 `checkout_role.role()`：模块角色时全局评审行、外部审查提示与全局 gate 不显示，「本 checkout」块与下一步只指向该模块（已完成只交回、挂起与不在能力图时停下、待审时交协调会话）；协调角色保留 review_step 原文并加呈现说明，否则为统筹措辞，gate 行改为陈述；`COMMANDS` 加 `checkout-role`、`map`。`git diff` 确认改动块不在 `module_state`、`project_stage` 里。`test-phase-guard.sh` 加 1 例：真实 git 仓库里放三种标记，无配置、off、只有 version、取值无效时注入都与没有标记时逐字节相同（另在开关 on 的临时仓库确认会出现角色行，用例不空转）。单元 21 例、phase-guard 369 例全绿。
- [x] Task 3：`/map` 的 worktree 字段与表格后缀（先红后绿） — `test_map_view.py` 加 `Worktrees` 夹具（主仓库加 5 个 worktree：b 有进度、提交与未跟踪文件；c 无 todo 且与主仓库同一提交；第二个 b 为 detached；a 的 todo 是目录；一个已删除目录）与 `WorktreeField` 5 例，先因字段不存在全红；`scan_worktrees` 与表格后缀实现后 map 54 例全绿。与 Plan 的出入：扫描放在 `map_view.py` 而不是 `checkout_role.py`，因为它要用 `module_stage` 的勾选计数，而 `module_stage` 已导入 `checkout_role`，放回去会循环导入；`checkout_role` 只拆出 `read_marker(path)` 供扫描复用。读其他 worktree 的标记只调一次 `rev-parse --git-path`，每个 worktree 最多 3 次 git 调用。上个模块 `test_switch_and_groups` 的「模块只多出 scope」按本模块 Spec 更新为 scope 与 worktree。
- [ ] Checkpoint 1（report）：一次性整份比对、核对选模块代码未动、三套核心回归与改坏验证
- [ ] Task 4：命令说明、Codex 技能、共享规则与文档
- [ ] Checkpoint 2（gate）：模块验收
