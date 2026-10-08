# Plan: project-config

依据 [`spec/project-config.md`](../../spec/project-config.md)（用户 2026-10-08 确认假设并批准 Spec）。
分支在 0.53.0 发版合入 main 之后，从最新的 `origin/main` 重新开出 `claude/project-config`，重新插入能力图那一行，
本地已写好的 Spec 与本 Plan 原样带过去。本模块不单独发版：版本号、tag 与 Release 留给本批最后一个模块
（`module-suspend`、`runtime-state-layout` 之后）。所有 todo 在本模块的 PR 内勾完。

## 依赖与顺序

`project_config.py` 是唯一的解析实现，其他所有改动都依赖它，所以排在第一；注入、校验和命令三处互不依赖，
可以按任意顺序做，这里按"影响面从小到大"排列。

## Task List

### Task 1：`project_config.py` 与单测（先红）

新增 `plugins/spec-guard/hooks/test_project_config.py`，覆盖 Spec「Testing strategy」列出的全部情况：
`load`、`show` 的来源标注、`set`／`unset` 只预览不写、`--confirm` 写入后读回、`dispatch` 和事项后端只给指引、
`.gitignore` 忽略警告。先确认测试因模块不存在而失败，再实现 `plugins/spec-guard/hooks/project_config.py`
（标准库实现、原子写入、只认首批两项）。
变异：去掉未知键检查；把非法值当成未设置。两处都必须让测试变红。

- 验收：单测全绿，两处变异被抓到。
- 文件：`hooks/project_config.py`、`hooks/test_project_config.py`。

### Task 2：阶段注入（先红）

在 `test-phase-guard.sh` 加用例：设语言出现语言行；`combined` 出现节奏行；`separate` 不出现；配置无效只出现
invalid 行、其余配置项不注入；无配置文件时与现有输出逐字节一致。先红，再在 `module_stage.py` 调用
`project_config.load` 追加这几行。`phase-guard.sh` 不改（配置由 `module_stage.py` 从项目根读取），
其依赖仍只有 bash、git、python3。
变异：`separate` 也注入。

- 验收：phase-guard 回归全绿，原有用例输出不变，变异被抓到。
- 文件：`hooks/module_stage.py`、`hooks/test-phase-guard.sh`。

### Task 3：`verify-artifacts` 校验（先红）

`test-verify-artifacts.sh` 加正反用例：合法配置通过、无效配置失败并列出原因、无配置文件不输出该项。
先红，再在 `verify-artifacts.sh` 调用 `project_config.py` 的校验入口。

- 验收：verify-artifacts 回归全绿；同一判据在 Task 2 与 Task 3 两边都有正反用例。
- 文件：`hooks/verify-artifacts.sh`、`hooks/test-verify-artifacts.sh`。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告

### Task 4：命令与 Codex 路由

新增 `commands/config.md`（规范引导段，调用 `hooks/project_config.py`），`skills/spec-guard-ops/SKILL.md`
新增 `config` 一节，参数与命令一致；`docs/workflow.md` 的「命令对照」表登记 `/spec-guard:config`。
由 `check-command-parity.py`、`check-command-names.py`、`check-command-table.py` 和命令引导段回归兜底，
不另写测试。

- 验收：`scripts/test-checkers.sh` 与 `validate.sh` 通过；在本仓库实跑一次 `show` 与一次只预览的 `set`。
- 文件：`commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/workflow.md`。

### Task 5：规则文本与模板（先红）

`test_workflow_checkpoints.py` 加断言：新一节「评审节奏」的标题，以及 `separate`、`combined`、退回条件、
「合并永远由用户」；两份约定块模板含指向 `.agent/config.json` 与 `/spec-guard:config` 的那一行。先红，再改
`references/workflow-checkpoints.md`、`templates/claude-block-local.md`、`templates/codex-block-local.md`，
并在 `setup-convention.sh` 的输出里加一句可用 `/spec-guard:config` 设置产物语言的提示。

- 验收：该单测与 setup-convention 回归全绿。
- 文件：上面四个文件和测试。

### Task 6：本仓库启用配置

用 Task 4 的命令（预览后 `--confirm`）给本仓库写 `.agent/config.json`：`artifactLanguage = zh-CN`、
`reviewCadence = combined`；运行 `setup-convention --replace` 更新本仓库的约定块。实跑 phase-guard，
确认阶段注入多出两行，其余不变。

- 验收：`verify-artifacts` 通过；注入输出与预期一致。
- 文件：`.agent/config.json`、`CLAUDE.md`／`AGENTS.md` 中的约定块。

### Task 7：文档与 CHANGELOG

`docs/design.md` 补一段项目配置的说明；`CHANGELOG.md` 在 `## [未发布]` 下写条目。在 macOS 的 `/bin/bash` 3.2
上跑一遍最小验证。

### Checkpoint 2（gate）：模块评审

推送前在同一条 `&&` 链里跑 `validate.sh`、两套 hook 断言和 ShellCheck；pre-push 钩子作为兜底。
批准本 Plan 即授权推送本分支并开本模块的 PR；合并由用户进行。

## 风险

| 风险 | 应对 |
|---|---|
| 0.53.0 改动 `module_stage.py` 后再开分支，代码位置变化 | 实现前重读该文件；Task 2 的逐字节用例会暴露意外变化 |
| 注入行影响既有用例 | 无配置时不追加任何内容，并有逐字节用例守住 |
| 配置无效时 hook 报错导致整轮注入失败 | `load` 不抛异常，只返回问题列表；Task 2 覆盖非 JSON 与非对象顶层 |
