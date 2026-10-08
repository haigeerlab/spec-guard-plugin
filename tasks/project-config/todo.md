# Todo: project-config

- [x] Task 1：`project_config.py` 与单测（先红） — 18 例；先因模块不存在而红，实现后全绿。复用 `tracker_default` 的 `read_text`（不跟随链接、限长）与原子写入；问题只报固定代码，不回显文件里的键名与取值。变异：去掉未知键检查、把非法值当未设置，各让 3 例变红。
- [ ] Task 2：阶段注入（先红）
- [x] Task 3：`verify-artifacts` 校验（先红） — 4 例：无配置不输出、合法通过、未知键与非法节奏失败并列出代码、无法解析失败；先红后绿（35 例）。调用 `project_config.py check`，退出码 1 判失败、其他非零报未验证。变异：无效改为只警告，被抓到。
- [ ] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告
- [x] Task 4：命令与 Codex 路由 — `commands/config.md`（规范引导段）、`spec-guard-ops` 的 config 一节、`docs/workflow.md` 命令对照表登记；command-parity／names／table／manifests 四个检查器通过，检查器回归 91 例通过；本仓库实跑 `show` 与只预览的 `set`，未写文件。派活开关的参数先误写成 `--dispatch=on|off`，按 `setup-convention.sh` 改为 `--dispatch`／`--no-dispatch`。
- [x] Task 5：规则文本与模板（先红） — `workflow-checkpoints.md` 新增「评审节奏」一节，两份约定块模板各加一行，`setup-convention.sh` 输出加一句可选提示；新断言先红 3 处后转绿，setup 回归 43 例通过。首次 `validate.sh` 因 README 内嵌块未同步而失败，已同步；复跑 `validate.sh` 通过，phase-guard 175 例、verify-artifacts 35 例通过，改动的 shell 脚本 ShellCheck 无警告。
- [ ] Task 6：本仓库启用配置
- [ ] Task 7：文档与 CHANGELOG
- [ ] Checkpoint 2（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行
