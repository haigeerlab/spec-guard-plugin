# Todo: linked-project-root

- [x] Task 1：指向文件的解析与校验（先红） — 新增 `test_project_link.py` 7 例（没有文件、绝对路径、相对路径按会话目录解析且与进程 cwd 无关、软链目标取真实路径、13 种无效写法、指向文件本身不是可读文件、目标不存在或不是目录），夹具目录名带空格与中文；先因模块不存在失败。`project_link.py` 提供 `resolve(session_root)`，返回 `none`／`ok`／`invalid`／`missing` 与目标；目标是否已启用不在这里判。
- [ ] Task 2：钩子跟随指向（先红）
- [ ] Task 3：`Linked project` 行与失效诊断（先红）
- [ ] Checkpoint 1（report）：钩子回归全绿，ShellCheck 无警告
- [ ] Task 4：`show`／`set`／`unset`（先红）
- [ ] Task 5：命令文件与 Codex 路由
- [ ] Checkpoint 2（report）：三套核心回归与新单测全绿，ShellCheck 无警告
- [ ] Task 6：文档
- [ ] Task 7：版本号
- [ ] Checkpoint 3（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行
