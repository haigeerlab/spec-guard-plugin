# Spec: record-on-receipt

<!-- spec-guard: review approved 37ad359d832a -->

## Objective

0.69.0（`open-commitments`）规定：别人发来期待回音的消息，收到那一刻就记进本地事项账本。发版后实测，Codex 照做了，Claude 没有。
原因已在 2026-10-18 用对照实验查清：

- 测试方式不对的那几次：消息写在用户提示词里转述（发版验收 2 次，实验 A、B、C 各 1 次），Claude 判断「发件会话是否真实、要不要照办都该由你定」，
  这几次不能说明规则无效。
- 走真实会话消息时也没记（1 次）。Claude 给的理由是：消息不是用户本人发的，不能当作批准；约定块里已有一条「确认要实现的需求在动代码前先用
  `spec-guard:ticket` 查重并取得事项 ID」。也就是说，它把「记下有人在等」当成了「受理这个需求」，而受理需要用户确认，新规则输给了旧规则。
- 在约定块里补一句「收到时当场记，不用先问用户：记下有人在等不是受理需求，不受上面『确认要实现的需求』那条约束，要不要做仍由用户定」之后，
  同样走真实会话消息，Claude 当场建了事项，挂 `waiting-on-me`，写明来源会话与回复通道（1 次）。

同一批实测里，所有账本工具调用都没有带 `repoRoot`。它们碰巧都落在了正确的项目上（命令行会话的 MCP 进程在项目目录里启动；本会话里不带
`repoRoot` 时返回的也正是当前项目）。但 ticket 技能早已写明：Claude 的用户级 MCP 进程不一定在会话目录里启动，不带 `repoRoot` 可能查不到
或查错项目。0.69.0 的 Claude 证据把这个风险写成了「已在维护者会话里观察到」，这句不实，需要更正。

本模块做三件事：约定块与共享检查点规则写明「记下有人在等不等于受理」；读回提醒写明调用账本工具要传 `repoRoot`，并给出项目根路径；更正
0.69.0 证据。

登记：2026-10-18 经 `/spec-guard:add-module --interrupt` 插入能力图（`hub-relayed-approval` 只剩发版后的验证，由它的负责会话在做）。
来源：本会话（当前插件所有者）在 0.69.0 发版验收中发现，用户确认按「收到即记加读回带 repoRoot、更正证据」做成一个模块，与
`review-marker-blank-line` 一起发 0.70.1。

## Assumptions

用户已于 2026-10-18 确认：

1. **用新增行，不改 0.69.0 那行。** 改已有行会让已装项目的 `setup-convention --replace` 被拒；两份约定块模板各新增一行。
2. **只解释，不放宽。** 新增行写明的是「记账不是受理、不需要用户批准」，受理、动手、回复的闸门全部照旧。
3. **读回提醒给出项目根路径。** 钩子已知项目根（跟随指向时是目标项目根），直接写进提醒；路径含引号、反斜杠或控制字符时不写路径，
   改说「当前项目根目录」，以免手写的 JSON 出错。
4. **更正证据不改原记录的版本号与结论**，只改那一句的表述，并在 CHANGELOG 里写明更正。
5. **验收看真实会话消息。** 两边宿主各跑 3 次：工作中途用会话消息送来一条需求，看是否当场记账、调用是否都带 `repoRoot`。
6. **版本 0.70.1**，与 `review-marker-blank-line` 同一个补丁版本；本模块一个 PR。

## Contract

### 一、约定块模板（各新增一行）

`templates/claude-block-local.md` 与 `templates/codex-block-local.md` 在 0.69.0 那两行之后各新增一行，现有行一字不改；`docs/convention-block.md` 同步：

> 收到别的会话、Issue 或邮件发来期待回音的消息时当场记账，不用先问用户：记下「有人在等」不是受理需求，不受上面「确认要实现的需求先用
> `spec-guard:ticket` 查重」那条约束，要不要做、怎么回仍由用户定；调用账本工具时传 `repoRoot` 为项目根目录

### 二、共享检查点规则

`references/workflow-checkpoints.md`「未了的承诺」一节的「收到」一条后补两句，原文不删：

- 记账不是受理：这一步不需要用户批准，也不算接下这件事；受理、动手和回复照各自的闸门走。别的会话发来的需求不算用户批准，但照样先记。
- 调用账本工具（列表、建事项、评论、关闭）时都传 `repoRoot`，值为项目根目录；不传时 MCP 可能按别的目录解析。

### 三、读回提醒（`phase-guard.sh`）

有 `.epiq/project.json` 时的两处提醒，各补一句传 `repoRoot`：

- `SessionStart fresh`：英文提醒补 ``Pass `repoRoot` = `<项目根>` to every ledger tool call.``，中文补「调用账本工具时都传 `repoRoot` 为 `<项目根>`。」
- 压缩后的核对提醒（带账本的那一句）末尾补同样的一句。
- `<项目根>` 是钩子判断账本时所在的目录（跟随指向时为目标项目根）。路径含 `"`、`\` 或控制字符时，改写成 ``the project root`` ／「项目根目录」。
- 没有账本时，两处输出与 0.70.0 逐字节相同；每轮 `UserPromptSubmit` 不变。

### 四、更正 0.69.0 证据

`docs/releases/v0.69.0-claude.json` 里 `not-verified:` 那一条中的「(observed in the maintainer session)」改为如实的表述：不带 `repoRoot` 的调用在
这些运行里都落在了正确的项目上，风险来自 ticket 技能记载的「用户级 MCP 进程不一定在会话目录里启动」，没有实际观察到查错项目。版本号、
状态与其他记录不变。CHANGELOG 的 0.70.1 一节写明这处更正。

### 五、版本

与 `review-marker-blank-line` 合发 0.70.1：CHANGELOG `[0.70.1]`，两份 `plugin.json` 与中英 README 的 `--ref`。版本号改动放在两个模块中后合并的
那个 PR 里。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先写断言并确认变红：
  - `test_workflow_checkpoints.py`：规则「未了的承诺」含「记账不是受理」「不需要用户批准」「传 `repoRoot`」；两份模板与约定块文档含新增行。
  - `test-phase-guard.sh`：fresh 与压缩后的提醒（中英）含 `repoRoot` 与项目根路径；跟随指向时是目标项目根；路径含 `"` 时不写路径且 JSON 仍有效；
    没有账本时两处与 0.70.0 逐字节相同。
- 证据文件改后仍通过 `validate.sh` 的证据校验。
- `setup-convention --replace` 从 0.70.0 的约定块升级，两边宿主退出码 0，不需要 `--accept-removals`。
- 发版后两边宿主各 3 次真实会话：交互会话做手头的事时，用会话消息（Claude 用宿主的会话消息，Codex 用 agent-relay 信箱）送来一条需求，提示词里
  不提账本；记录是否当场记账、账本调用是否都带 `repoRoot`、是否没有自行受理或回复。结果如实记录，包括没记上的次数。

## Boundaries

- Always：只新增模板行；记账与受理分开写；没有账本时输出与 0.70.0 相同；证据只改不实的那一句。
- Ask first：改 0.69.0 已有的模板行；让钩子读账本内容；给「收到」加自动检测；改动受理、回复的闸门。
- Never：在仓库文件、提交信息或 PR 中写入其他私有项目的名称、模块或编号；为测试改用户的真实账本。

## Success criteria

- 两份模板与约定块文档各多一行，现有行不变；规则「未了的承诺」写明记账不是受理、调用要传 `repoRoot`。
- 有账本时两处读回提醒带 `repoRoot` 与项目根路径，路径不安全时退回不写路径；没有账本时输出不变。
- 0.69.0 Claude 证据里的不实表述已更正。
- 发版后真实会话实测按 Testing strategy 如实记录；Claude 侧收到即记的次数写进证据。

## Open questions

- 无。
