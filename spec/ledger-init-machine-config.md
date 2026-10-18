# Spec: ledger-init-machine-config

<!-- spec-guard: review approved 623d68277c01 -->

## Objective

本地事项账本的 `initialize` 在机器上已经有 Epiq 设置时会失败，而且只报一句 `MCP tool response is unsuccessful`，看不出原因。

2026-10-18 session-protocol 契约负责人报告（账本事项 CH92E11）：环境是 spec-guard 0.68.0、Epiq 1.11.0，仓库没有 origin，`~/.epiq-global/config.json`
已有 `userName`、`preferredEditor`、`autoSync`。用户按说明给了三项值，其中有和机器不同的，初始化失败。核对 Epiq 1.11.0 的 `epiq_project_init` 实现：

- 三项都是**可选参数**。机器缺哪项就用传入的值补上；机器已有的不改，传了不同的值就拒绝，并返回 message：
  「This machine is already set up with userName "…"; epiq_project_init does not change it. Call again without userName, or let the user change it in the TUI with :config.」
- 都没传、机器也缺时，它在动 Git 之前失败，并在 message 里列出缺的项和该问用户的问题。
- 初始化成功时 `warnings` 是一组字符串，形如 `[init:15] <上游 message>`，可能带原始 Git 错误。

我们这边有两处和它对不上：

1. `hooks/local_ledger_runtime.py` 的 `read_mcp_tool_result` 只要 status 不是 success，就抛 `MCP tool response is unsuccessful`，丢掉了 Epiq 的 message；
2. `project_init_arguments` 与 `initialize` 命令行要求三项都必传，命令、技能、参考文档都让 agent「向用户索取实际值」。机器已经设置过、用户又给了不同的值，就必然失败。

另外，初始化结果里的 `warnings` 被压成 `true`，说不出是什么警告。

本模块让初始化与机器级设置共存：三项改为可选、只传用户给出的；`status` 报告机器已设置了哪几项；Epiq 拒绝时报出清理过的 message；警告报条数与编号。

登记：2026-10-18 经 `/spec-guard:add-module` 插入能力图。来源：session-protocol 契约负责人（会话 local_a9d06942-9b64-4887-b490-0088b10b8c75）转达用户的报告，记在本地账本 CH92E11；用户本人确认插入与下列假设。

## Assumptions

用户已于 2026-10-18 确认以下 5 条：

1. **message 照报但先清理。** Epiq 返回非 success 且带字符串 `message` 时，诊断为 `Epiq refused: <message>`：控制字符换成空格并合并连续空白；文本里任何
   `scheme://userinfo@` 的 userinfo 换成 `***`（同 `remote-credential-redaction` 的标记，但不限于开头）；超过 300 个字符截断并加 `…`。没有 message 或不是字符串时
   保持原来的 `MCP tool response is unsuccessful`。
2. **警告只报编号，不报原文。** 初始化结果新增 `warningCount`（警告条数）与 `warningCodes`（从每条开头的 `[init:N]` 取出的 `init:N`，按出现顺序去重；没有编号的只计数）。
   原有的 `warnings` 布尔值保留不变，已有的读取方不受影响。警告正文仍不回显。文本输出在有警告时多一行「Epiq 初始化有 N 条警告（编号）」。
   （假设 2 原写作 `warnings: {count, codes}`；为不改变已有字段的类型，改为保留布尔、另加两个字段。）
3. **status 只读地读机器级设置。** `status` 新增 `machineSetup`：读 `EPIQ_GLOBAL_DIR`（没有时为 `~/.epiq-global`）下的 `config.json`，只取 `userName`、
   `preferredEditor`、`autoSync` 三项。
   - 文件不存在：`{"state": "absent"}`；
   - 读到合法 JSON 对象：`{"state": "read", "userName": <非空字符串或 null>, "preferredEditor": <同>, "autoSync": <true/false/null>}`；
   - 不是普通文件、超过 64 KiB、读不了或不是合法 JSON 对象：`{"state": "unknown", "diagnostic": ...}`，不判定为「未设置」。
   不写任何文件，不读其他字段（例如 `userId`）。文本输出写明机器已设置了哪几项及取值、缺哪几项。status 原有的状态判断与退出码不变。
4. **说明改为先看 status 再问。** 命令、技能与参考文档：初始化前看 `status` 的 `machineSetup`；机器已有的项告诉用户「这是整机设置，初始化改不了；要改，在 Epiq 的 TUI 里用
   `:config`」，不再传；只向用户索取机器缺的项。`machineSetup` 为 `unknown` 时照旧三项都问，按 Epiq 的拒绝信息调整。仍不猜测、不代填。
5. **版本 0.71.0。** 命令行参数与 status 输出都有变化；未发布的 `stdin-timing-test` 一起发。发版后在账本里关闭 CH92E11，并把版本号告诉 session-protocol 契约负责人
   （原生会话消息，先给用户看草稿）。

## Contract

`hooks/local_ledger_runtime.py`：

- `project_init_arguments(project_dir, user_name=None, preferred_editor=None, auto_sync=None)`：只放入给出的项；给出的字符串去掉首尾空白后为空则报错
  （`Epiq user name must not be empty` / `Epiq preferred editor must not be empty`），`auto_sync` 给出时必须是布尔值。始终带 `repoRoot`。
- `initialize_project(...)` 的三项参数改为可选，原样传给上一条；返回值在原有字段之外加 `warningCount`、`warningCodes`。
- `initialize` 命令行：`--user-name`、`--preferred-editor`、`--auto-sync` 都可省略；去掉 `user-setup-required` 这一拒绝。`--confirm-initialize` 与预检门槛不变。
- `read_mcp_tool_result`：按假设 1 生成诊断；其他失败（无效 JSON、无 content 等）的文字不变。
- `status`：按假设 3 增加 `machineSetup`；文本输出增加对应行。
- 新增的清理函数只在本模块内使用；`redact_url` 的行为不变。

文档：`commands/local-ticket-ledger.md`、`skills/local-ticket-ledger-ops/SKILL.md`、`references/local-ticket-ledger-runtime.md` 按假设 4 改写初始化那一段与示例命令；
CHANGELOG `[0.71.0]`；两份 `plugin.json` 与中英 README 的 `--ref` 改为 0.71.0。

不改 Epiq，不写 `~/.epiq-global`，不替用户改整机设置；账本的其他命令与 MCP 接入不变。

## Commands

```text
python3 -m unittest plugins/spec-guard/hooks/test_local_ledger_runtime.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

单测（`test_local_ledger_runtime.py`，先红后绿）：

- `project_init_arguments`：三项都不给只有 `repoRoot`；只给一项只带那一项；给了空字符串报错；`auto_sync` 非布尔报错。
- `read_mcp_tool_result`：带 message 的拒绝报出 message；message 里的控制字符被替换、URL 凭据被遮掉、超长被截断；没有 message 时文字不变。
- `initialize_project`：警告的条数与编号正确，正文不出现在返回值里（沿用现有的「do not print this」断言）；`warnings` 布尔值不变。
- `initialize` 命令行：不给三项时也会调用 `initialize_project`（不再报 `user-setup-required`），给了的原样传入。
- `status` 的 `machineSetup`：不存在、合法、部分缺失、非法 JSON、不是对象、超过 64 KiB、是目录或符号链接指向目录时各自的结果；读取不改文件修改时间；
  `EPIQ_GLOBAL_DIR` 生效。

真实 Epiq（发版前，临时 `EPIQ_GLOBAL_DIR` 与临时仓库，不碰本机设置）：

- 机器已有 `userName` 为 A，初始化传 B：失败，诊断里有 Epiq 的原话；
- 同样的机器，不传三项：初始化成功，机器设置不变；
- 空的机器设置、三项都传：成功，机器设置被 Epiq 写入。

## Boundaries

- Always：只传用户给出的项；机器已有的值由 Epiq 决定；报 message 前先清理；status 只读。
- Ask first：替用户改整机设置；回显警告正文；改动 Epiq 或它的配置文件；改动账本其他命令的行为。
- Never：猜测或代填三项；把 `machineSetup` 读不了当成「未设置」；把远端地址里的凭据带进输出。

## Success criteria

- 机器已有设置时，不传三项就能初始化；传了不同的值时，诊断里能看到 Epiq 说明的原因。
- `status` 能告诉 agent 机器已设置了哪几项，agent 只问缺的。
- 初始化有警告时能看到条数与编号，看不到原始 Git 错误。
- 全套检查与真实 Epiq 的三种情形通过。

## Open questions

- 无。
