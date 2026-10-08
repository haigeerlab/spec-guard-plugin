# Todo: project-config

- [x] Task 1：`project_config.py` 与单测（先红） — 18 例；先因模块不存在而红，实现后全绿。复用 `tracker_default` 的 `read_text`（不跟随链接、限长）与原子写入；问题只报固定代码，不回显文件里的键名与取值。变异：去掉未知键检查、把非法值当未设置，各让 3 例变红。
- [x] Task 2：阶段注入（先红） — `test-phase-guard.sh` 新增 7 例：语言行、combined 节奏行、两项都设、无效配置只出 invalid 行（且除配置行外与无配置时逐字节一致）、separate 逐字节不变、DONE 阶段也注入、无效配置的键名与取值不进入注入；先红后绿（182 例）。`module_stage.config_lines` 调用 `project_config.load`，`phase-guard.sh` 未改。变异：separate 也注入、不报无效配置，均被抓到；module_stage 的消毒、module-insert、session_context 单测通过。
- [x] Task 3：`verify-artifacts` 校验（先红） — 4 例：无配置不输出、合法通过、未知键与非法节奏失败并列出代码、无法解析失败；先红后绿（35 例）。调用 `project_config.py check`，退出码 1 判失败、其他非零报未验证。变异：无效改为只警告，被抓到。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告 — 见 Checkpoint 2 的同一条验证链。
- [x] Task 4：命令与 Codex 路由 — `commands/config.md`（规范引导段）、`spec-guard-ops` 的 config 一节、`docs/workflow.md` 命令对照表登记；command-parity／names／table／manifests 四个检查器通过，检查器回归 91 例通过；本仓库实跑 `show` 与只预览的 `set`，未写文件。派活开关的参数先误写成 `--dispatch=on|off`，按 `setup-convention.sh` 改为 `--dispatch`／`--no-dispatch`。
- [x] Task 5：规则文本与模板（先红） — `workflow-checkpoints.md` 新增「评审节奏」一节，两份约定块模板各加一行，`setup-convention.sh` 输出加一句可选提示；新断言先红 3 处后转绿，setup 回归 43 例通过。首次 `validate.sh` 因 README 内嵌块未同步而失败，已同步；复跑 `validate.sh` 通过，phase-guard 175 例、verify-artifacts 35 例通过，改动的 shell 脚本 ShellCheck 无警告。
- [x] Task 6：本仓库启用配置 — 经 `project_config.py set … --confirm` 写入 `zh-CN` 与 `combined` 并读回，`check` 为 ok。**偏离 Plan：** 没有用 `setup-convention --replace`，因为本仓库 AGENTS.md 的约定块是手工定制的（Proposal、退役规则），整块替换会冲掉它们；改为只在块内追加模板新增的那一行。实跑 phase-guard，注入多出语言与节奏两行，其余不变。
- [x] Task 7：文档与 CHANGELOG — `docs/design.md` 新增 Project configuration 一节（沿用该文件的英文）；CHANGELOG 新建 `## [未发布]`／新增。
- [x] Checkpoint 2（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行 — 同一条 `&&` 链：validate.sh 通过、phase-guard 182 例、verify-artifacts 35 例、test_project_config 与 test_workflow_checkpoints 通过、ShellCheck 无警告，之后才提交并推送（首轮链条因 bash 3.2 多字节写法在 validate 处停下，未提交，修正后重跑）；PR 由用户合并。
