# Spec: ledger-local-only

<!-- spec-guard: review approved 5860b95a4e08 -->

## Objective

本地事项账本的实际使用（2026-10-16，本机 4 个账本与近两周会话调用的只读核对）暴露出：想“只存本地”却被迫推送、数据长期不进 git
而无人知晓、账本标识只在初始化分支上导致别的工作树找不到。本模块让账本可以纯本地启用，并把这些风险在 status 和入口文档里说清楚。

根因（已复核）：

1. 后端 Epiq 1.11.0 只在同步时把 `~pending` 事件提交进 `__epiq_state__`，同步会同时推送；`autoSync` 为 false 时事件一直是状态工作树里的
   未跟踪文件。这是 Epiq 的设计，spec-guard 不改它，也不替它提交（那个工作树由 Epiq 管理，它自己改名、合并 `~pending` 文件）。
   离线归档会原样保存 `~pending` 文件，所以归档能保护这些数据。
2. `initialization_preflight` 遇到 `origin` 只给两条路：`--allow-epiq-push` 或不初始化。Epiq 初始化执行 `git push -u origin HEAD`，
   继承进程环境，推送失败只记为警告。
3. Claude 侧 Epiq MCP 的 `repoRoot` 默认取 MCP 进程的当前目录，与会话目录不一致时报 “No .epiq/project.json found”。
4. `.epiq/project.json` 只提交在初始化时所在的分支；从默认分支开的工作树找不到账本。
5. Closed 看板下的泳道是只读的，ticket skill 只写了“找开放泳道”，没写哪些是只读。

登记：2026-10-16 经 `/spec-guard:add-module` 插入能力图。需求来自会话「ent-relay插件使用观测」（`local_b1a6b3c6-e6c2-424b-9871-4cd370f89657`）
转来的 5 条实测问题，经用户确认范围后开模块。发版后按「需求来源与回告」回告该会话。

## Assumptions

用户已于 2026-10-16 确认范围：

1. **纯本地启用**：新增 `--local-only`，与 `--allow-epiq-push` 互斥。只对这一次 Epiq 子进程设置 `GIT_CONFIG_COUNT` /
   `GIT_CONFIG_KEY_n=remote.origin.pushurl` / `GIT_CONFIG_VALUE_n=<一个必然失败的本地路径>`，让推送在本机失败、作为警告；
   不改仓库或用户的 git 配置。已有的 `GIT_CONFIG_COUNT` 条目保留，新条目追加在后面。
2. **status 只读诊断**：已初始化且状态工作树归本仓库时，报告未提交到状态分支的事件数（`.epiq/events/` 下名字含 `~pending`
   的 `.jsonl` 文件的非空行数，只计行数、不解析内容）；大于 0 时文本输出提醒用离线归档（`local-ticket-portability` 的 archive）
   做备份。不报告“最近归档时间”：归档目录由用户每次用 `--output` 指定，插件无从得知。
3. **标识在别的分支上**：当前检出没有 `.epiq/project.json` 时，status 只读地查本地分支与远端跟踪分支（不含 `__epiq_state__`），
   找到第一个含 `.epiq/project.json` 的分支就报告它，并提示把它合进默认分支或从那里开分支。不联网、不 fetch。
4. **初始化成功后**：文本输出提示“把 `.epiq/project.json` 所在提交合进默认分支，其他工作树才能找到账本”。
5. **只改文档的两条**：ticket 命令与 skill 写明 Claude 调用 Epiq 工具时带 `repoRoot=<当前项目根目录>`；建事项前用
   `epiq_swimlane_list` 选非只读泳道，Closed 看板下的泳道只读。
6. 不写 Epiq 的 `recent-projects.json`，不替 Epiq 提交或推送状态分支，不处理其他仓库已推送的分支。
7. 版本 0.64.0（新增选项），一个 PR。

## Contract

### `hooks/local_ledger_runtime.py`

- `initialization_preflight(project_dir, allow_epiq_push=False, local_only=False)`：
  - 两者同时为真 → 返回 1，`{"state": "invalid", "diagnostic": "--local-only and --allow-epiq-push are mutually exclusive"}`。
  - 有 `origin` 且 `local_only` → 返回 0，`state: ready`，`upstreamPush: "disabled-local-only"`（origin 照常脱敏报告）。
  - 有 `origin` 且两者都没给 → 仍是 `push-confirmation-required`，并新增字段 `localOnly: "available"`；文本输出说明两种选择。
  - 无 `origin`：不变（`will-fail-as-warning`）；`local_only` 在这里不改变结果。
- `initialize_project(..., local_only=False)`：preflight 通过且 `local_only` 时，`mcp_tool_call` 的环境为当前环境加上第 1 条的
  三个变量；返回值 `upstreamPush` 为 `disabled-local-only`。不带 `local_only` 时传给子进程的环境与现在相同。
- `status()`：
  - `initialized` 且 `stateWorktree.state == "owned"` 时，`project.pendingEvents` = 整数；读不了时为 `null` 且不影响 `state`。
  - `uninitialized` 时，`project.identityElsewhere` = 分支名（找到时）；查询失败或没找到时不出现该字段。
  - 返回码与 `state` 的判定不变。
- `main`：新增 `--local-only`（`preflight`、`initialize` 用）；文本输出：
  - status：`未提交到状态分支的事件：N 条` 一行；N > 0 时加一行提醒做离线归档；有 `identityElsewhere` 时加一行说明与处理办法。
  - initialize 成功：加一行合进默认分支的提示；`local_only` 时说明未推送。

### 文档

- `commands/local-ticket-ledger.md`、`skills/local-ticket-ledger-ops/SKILL.md`、`references/local-ticket-ledger-runtime.md`：
  开头写明“本地使用不需要任何推送”；有 `origin` 时默认推荐 `--local-only`，`--allow-epiq-push` 只在用户明确要推送时用；
  说明 `autoSync` 关闭时事件不进 git、status 的未提交事件数与离线归档；说明 `.epiq/project.json` 要合进默认分支。
- `commands/ticket.md`、`skills/ticket/SKILL.md`：Claude 调用带 `repoRoot`；建事项选非只读泳道。
- `spec/local-ticket-ledger.md`：在推送确认那条后补一句 `--local-only` 的第三种选择，并按“变更记录”规则记一行来源。
- CHANGELOG `[0.64.0]`；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.64.0。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_local_ledger_runtime.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

- 先写失败用例再改实现，全部在临时目录、假运行时与打桩的 MCP 调用上跑，不碰真实 `~/.epiq-global` 与运行时：
  - preflight：有 origin + `local_only` → ready / `disabled-local-only`；两者同给 → invalid；都不给 → `push-confirmation-required` 且
    `localOnly: available`；无 origin 时 `local_only` 结果不变。
  - initialize：`local_only` 时传给子进程的环境含三个变量，且已有 `GIT_CONFIG_COUNT=1` 时追加为第 2 条；不带时环境与原来逐项相同。
  - status：owned 工作树里两个 `~pending` 文件共 N 行 → `pendingEvents == N`；无 pending 文件 → 0；事件目录不可读 → `null` 且 state
    不变；uninitialized 且另一分支有 `.epiq/project.json` → `identityElsewhere`；`__epiq_state__` 上的不算；都没有 → 无该字段。
  - 文本输出各新行的正反例。
- 变异：去掉追加的环境变量、把 pending 计数恒为 0、把 `identityElsewhere` 查询去掉，各有断言变红。
- 发版后：在临时仓库配一个本机裸仓库做 `origin`，用安装好的运行时跑 `initialize --local-only`，确认裸仓库里没有任何引用、当前分支
  没有设上游；再对本机已有账本跑 `status` 看未提交事件数。

## Boundaries

- Always：status 与 preflight 只读；`--local-only` 只影响这一次子进程的环境；读不到就降级为不报告，不把读取失败说成数据状态。
- Ask first：替 Epiq 提交或推送 `__epiq_state__`；写 Epiq 的全局文件；改用户或仓库的 git 配置；升级 Epiq。
- Never：删除 `.epiq/`、`__epiq_state__` 或 `~pending` 文件；在仓库、提交或 PR 里写使用方的项目名或会话名。

## Success criteria

1. 有 `origin` 的仓库用 `--local-only` 初始化成功，远端（测试用本机裸仓库）没有收到任何引用。
2. status 报告未提交事件数，大于 0 时提醒离线归档；标识只在别的分支时给出诊断。
3. 不带新选项时，preflight、initialize、status 的现有行为与输出逐字不变（只多字段与行，不改已有字段）。
4. ticket 与账本入口文档写明 repoRoot、只读泳道、纯本地启用。
5. 回归全绿；变异各有断言变红；发版后按 Testing strategy 实测并回告来源会话。

## Open questions

- 无。
