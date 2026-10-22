# Spec: link-per-session

<!-- spec-guard: review approved 983ceec94cd6 -->

## Objective

0.58.0 的会话目录指向以目录为键。实地使用里，多个长期运行的会话共用同一个会话目录、各自开发不同的仓库，这是该用户的
常态工作方式。在这种方式下，按目录的指向最多服务一个会话：其余会话收到被指向项目的阶段提示（错误的位置、模块与下一步），
有一次正发生在用户批准另一个项目的 Spec 的那一轮，靠 agent 自己察觉才没有记错。0.58.2 只是把这一点写明了。原本要解决的
“这些会话收不到自己项目的阶段提示”，对其余会话仍然无解。

本模块让指向可以按会话登记：每个会话登记一次自己对应的项目，钩子优先按本会话的登记取项目。

登记：2026-10-13 经 `/spec-guard:add-module` 插入能力图。

## Measured host facts (2026-10-13)

| 宿主 | 命令侧（agent 的 shell 环境） | 钩子侧 |
|---|---|---|
| Claude Code 2.1.296 | `CLAUDE_CODE_SESSION_ID`，值等于会话记录文件名（去掉 `.jsonl`） | hook 输入的 `transcript_path` 文件名即会话标识 |
| codex-cli 0.162.1 | `CODEX_THREAD_ID`（与 `CODEX_SESSION_ID` 相同），值等于会话记录文件名末尾的标识，也等于首条 `session_meta` 的 `id` | hook 输入的 `transcript_path` 文件名末尾即会话标识 |

从 Claude 会话里启动的 Codex，环境里同时带着 `CLAUDE_CODE_SESSION_ID` 与 `CODEX_THREAD_ID`，所以命令不能自己判断该用哪一个。
未实测：Codex 的 hook 输入里是否另有 `session_id` 字段；压缩或恢复会话后标识是否变化（Task 1 实测）。

## Assumptions

用户已于 2026-10-13 确认：

1. 指向文件多一个可选部分：按会话标识登记的项目表。目录级指向保留，作为没登记的会话的默认值。
2. 钩子的查找顺序：本会话的登记 → 目录级指向 → 静默。
3. 会话标识由调用方显式传入，命令不猜；命令说明写清每个宿主该传哪个环境变量。
4. 钩子同时认两个来源：hook 输入里的 `session_id` 字段，与 `transcript_path` 文件名里的标识；命中任一个即可。
5. 没登记的会话，在没有目录级指向的目录里保持静默，不提示“尚未登记”。
6. 用到会话登记的文件版本为 2；只有目录级指向的文件仍是版本 1。旧版本插件读到版本 2 会报格式无效的诊断，不会误用。
7. 失效的登记不自动清理；`show` 列出，`unset` 删除。
8. 会话标识在一个会话的生命期内不变。Task 1 实测压缩或恢复后的情况；若会变，停下来找用户。
9. 子代理有自己的标识，按没登记处理。
10. 顺带加一句规则：评审状态只看标记，Spec 与 Plan 的正文不写“待审核／已批准”这类状态。
11. 版本 0.60.0，一个 PR。不做：命令猜当前会话；自动清理登记；其他命令自动跟随指向。

## Contract

### 指向文件

`<会话目录>/.agent/spec-guard-link.json`，两种合法形态：

```json
{"version": 1, "project": "<路径>"}
{"version": 2, "project": "<路径>", "sessions": {"<会话标识>": "<路径>"}}
```

- 版本 1 与现行完全相同。
- 版本 2：`sessions` 必填，是对象，键为会话标识（非空、只含字母数字与 `-_`、不超过 128 字符），值为路径（规则同 `project`）；
  `project` 可省略。除这三个键外不得有别的键；`sessions` 为空对象且没有 `project` 时算格式无效。
- 路径的解析与现行相同：相对路径相对于会话目录，取真实路径。

### 解析

给定会话目录与一组候选会话标识（可为空）：

| 情况 | 结果 |
|---|---|
| 文件不存在 | `none` |
| 格式无效 | `invalid` |
| 候选标识之一在 `sessions` 里 | 用该登记的目标：存在为 `ok`，否则 `missing`；来源记为 `session` |
| 否则有 `project` | 用目录级目标：`ok` 或 `missing`；来源记为 `directory` |
| 否则（版本 2，只有别的会话的登记） | `none` |

目标是否已启用仍由调用方判断，与现行相同。

### 钩子

- 候选标识取自 hook 输入：`session_id` 字段（若是非空字符串），以及 `transcript_path` 的文件名——去掉扩展名后的整段，和其中
  形如 UUID 的结尾一段。取不到时候选为空，行为与现行相同（只看目录级指向）。
- 结果为 `none` 时静默退出；没有指向文件时仍在启动 python3 之前退出。
- 来源为 `session` 时，`Linked project` 行写明这是本会话的登记、同目录的其他会话不受影响；来源为 `directory` 时文字与 0.58.2
  逐字相同。失效诊断的三种文字不变，来源为 `session` 时在诊断里说明是本会话的登记失效。
- 仍然只读，仍只依赖 bash、git 与 python3。

### 命令

```text
project_link.py show   --from <会话目录> [--session <标识>]
project_link.py set    --from <会话目录> --project <路径> [--session <标识>] [--confirm]
project_link.py unset  --from <会话目录> [--session <标识>] [--confirm]
```

- 不带 `--session`：行为与现行逐字相同（操作目录级指向）。对版本 2 的文件，`set` 只改 `project`、保留 `sessions`；`unset` 只去掉
  `project`，`sessions` 仍非空时保留文件。
- 带 `--session`：`set` 写入或替换该会话的登记（文件升为版本 2，保留已有的 `project` 与其他登记）；`unset` 删除该登记，删后
  既无 `project` 也无登记时删除文件，只剩 `project` 时降回版本 1。
- `show` 列出目录级指向与每一条登记及其是否有效；带 `--session` 时另说明该会话实际会用哪一个。
- 标识不合法时拒绝；其余拒绝条件与现行相同（目标不存在、未启用、会话目录自己已启用、目标就是会话目录、文件格式无效）。
- 预览说明：登记只对这个会话生效；标识取自 `CLAUDE_CODE_SESSION_ID`（Claude Code）或 `CODEX_THREAD_ID`（Codex）。

### 规则与文档

- `commands/link-project.md`、`spec-guard-ops` 的 link-project 一节：共用目录时各会话各自登记的用法，各宿主传哪个变量。
- `references/workflow-checkpoints.md`「评审状态标记」补一句：评审状态只看标记，正文不写状态。
- `docs/commands.md`、`docs/troubleshooting.md`、`docs/design.md`、CHANGELOG `[0.60.0]`；版本号 0.60.0。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_project_link.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先写测试并确认在现有代码上失败，再实现。
- `test_project_link.py`：解析表每一行；版本 2 的各种无效写法；版本 1 的全部原有用例不改；命令带与不带 `--session` 的
  `set`／`unset`／`show`，含升到版本 2、降回版本 1、删空即删文件、保留其他登记。
- `test-phase-guard.sh`：同一目录两个会话各自登记不同项目，各自得到自己项目的阶段；没登记的会话跟随目录级指向；只有别的
  会话登记时静默；候选标识分别来自 `session_id` 与两种文件名形态；来源为 `directory` 时 `Linked project` 行与 0.58.2 逐字相同；
  hook 输入取不到标识时行为与现行相同。变异：不优先查会话登记、没登记时也用别人的登记。
- 宿主行为：发版后在一个临时目录里，用 `claude -p` 与 `codex exec` 各起两个会话，分别登记两个项目，确认各自读到自己的项目。

## Boundaries

- Always：没有指向文件的目录静默；只用目录级指向的文件行为逐字不变；钩子只读；命令先预览后确认。
- Ask first：命令自己猜会话标识；自动清理登记；没登记时给提示；改变查找顺序。
- Never：从会话记录内容推断项目；在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、路径、模块或编号。

## Success criteria

- 同一目录下两个会话各自登记不同项目后，各自收到自己项目的阶段提示。
- 没登记的会话：有目录级指向时跟随它，没有时静默。
- 只用目录级指向的现有文件，行为与输出逐字不变。
- 三条最小验证与 ShellCheck 全部通过；两边真实宿主各验证一次。

## Open questions

- 压缩或恢复会话后会话标识是否变化：Task 1 实测。


## 修订：D18 自动跟随（2026-10-22，用户决定）

功能盘点决定 D18：有指向时所有 spec-guard 命令与阶段注入用同一套解析自动跟随。模块 `cost-slim-link-follow` 实现：

- `project_link.py follow --from <会话目录> [--session <标识>]` 复用 `resolve_for`：打印要操作的项目，跟随时在 stderr 写「本次操作的是
  被指向的项目 `<路径>`」与来源；指向失效时退出 2，不退回会话目录。会话目录自己已启用时不跟随。
- 命令按入口所在宿主取会话标识（Claude 命令传 `CLAUDE_CODE_SESSION_ID`，Codex skill 传 `CODEX_THREAD_ID`），放宽了 Boundaries 里
  「命令自己猜会话标识先问」那条：入口已经确定了宿主，不算猜。Assumptions 第 11 条「其他命令自动跟随指向」不做，由本修订取代。
- 阶段注入的「关联项目」四段把「运行命令时把这个路径作为项目传入」改为「spec-guard 命令会自动跟随到这个项目」，目录级那句改为
  「用 `link-project` 给本会话登记自己的项目」；因此「来源为 directory 时与 0.58.2 逐字相同」这一条不再成立。会话登记不自动清理，不变。
