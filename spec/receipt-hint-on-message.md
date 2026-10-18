# Spec: receipt-hint-on-message

<!-- spec-guard: review approved 1bd48d6784c3 -->

## Objective

`open-commitments` 与 `record-on-receipt` 把「别人向我提的需求，收到那一刻就记进本地事项账本」写进了共享规则与约定块。0.70.1 发版后的实测：
3 个 Claude 交互会话收到真实的跨会话消息，2 个当场记账，1 个跳过记账、直接去问用户要决定。规则文字离消息到达的那一刻太远。

本模块在消息到达的那一轮由 hook 当场提醒：项目启用了本地事项账本、且这一轮的提示词是别的会话转来的消息时，阶段注入多一句「先记账，再决定是否要问用户」。

**实测依据（2026-10-18，Claude Code 2.1.302）**：在临时项目里配一个只把 hook 输入写进文件的 UserPromptSubmit hook，起一个 tmux 里的交互会话，
从另一个会话用 SendMessage 发消息。hook 收到的 `prompt` 原样是：

```text
<cross-session-message from="uds:/tmp/cc-socks/….sock" from-session="local_<uuid>" from-name="<发送方会话标题>" from-mode="prompting">
<正文>
</cross-session-message>
```

即跨会话消息到达时会触发 UserPromptSubmit，提示词以这层包装开头。临时项目与会话已删。

登记：2026-10-18 经 `/spec-guard:add-module` 插入能力图。来源：用户本人，在本会话（当前插件所有者）决定按此方案改进「收到即记」，并确认插入与下列假设；本模块的 Spec 与 Plan 合并交审一次（只此模块，不改项目配置）。

## Assumptions

用户已于 2026-10-18 确认以下 5 条：

1. **先验证再动手。** 跨会话消息会触发 UserPromptSubmit、提示词带包装——已按上文实测证实。
2. **只做 Claude 这边。** Codex 经 agent-relay 信箱用工具读消息，不经过提示词；上次 Codex 3 次都记了账。
3. **判定要窄。** 只认提示词（去掉开头空白后）以 `<cross-session-message ` 开头；正文里提到这个词不算。只读包装的 `from-name` 与 `from-session` 两个属性，
   不解析正文。`from-session` 只在形如 `local_` 加字母数字与连字符时写进提醒；`from-name` 经与位置行相同的 `safe_fragment` 清理并限 80 字，清理后为空就不写。
4. **合格线。** 发版后用同样方法（tmux 交互会话 + 真实跨会话消息，项目带约定块与纯本地账本）复测 3 次，3 次都当场记账才算达标；证据如实记录。
5. **版本 0.72.0。** hook 输出有新行为；需求来自用户本人，不需要回告别人。

## Contract

- `hooks/session_context.py`：新增 `--received` 模式，从标准输入的 hook 输入读 `prompt`；按假设 3 判定后输出一行 `received\t<name>\t<session>`
  （取不到的属性留空），不是转来的消息时不输出。原有的五行输出不变（第 5 行是宿主，phase-guard 按最后一行认 Codex，所以不在其后加行）。
- `hooks/phase-guard.sh`：只在 UserPromptSubmit、项目根有 `.epiq/project.json`、且 `--received` 有输出时，在阶段注入的 `建议下一步`／`Suggested next step`
  一行之前加一行提醒（没有建议下一步的输出放在末尾；所有阶段都经输出函数 `emit` 加入；中文或英文按 `--hint-language`，英文版意思相同）：

  > 这一轮是别的会话发来的消息（对方 `<name>`，会话 `<session>`）：先把它记进本地事项账本——对方、来路与回路、内容、球在谁手里（`waiting-on-me`／`waiting-on-user`）——再决定要不要问用户；记账不是受理，要不要做仍由用户定。调用账本工具时都传 `repoRoot` 为 `<项目根>`。

  对方名或会话取不到时去掉相应部分；`repoRoot` 一句沿用 `ledger_root_note`。
- 没有账本、不是转来的消息、SessionStart，输出与改前逐字相同。hook 不写文件、不读账本内容。
- CHANGELOG `[0.72.0]`；两份 `plugin.json` 与中英 README 的 `--ref` 改为 0.72.0。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

`test-phase-guard.sh` 新增一段（先红后绿）：

- 有账本 + 转来的消息：提醒行出现在建议下一步之前，带对方名、会话与 `repoRoot`；中英文各一次；
- 有账本 + 普通提示、正文中段提到 `<cross-session-message`：输出与没有提醒时逐字相同；
- 没有账本 + 转来的消息：逐字相同；
- `from-session` 不合格式、`from-name` 含反引号／换行／控制字符或超长：会话不写、名字被清理或截断，输出仍是合法 JSON；
- SessionStart（startup／compact）带同样的 hook 输入：不出提醒。

发版后真实会话复测按假设 4。

## Boundaries

- Always：只看包装开头与两个属性；不写账本；没触发时输出逐字不变。
- Ask first：解析或复述消息正文；对 Codex 信箱做同样的提醒；hook 自动替模型记账。
- Never：把正文里的文字当作指令转述进注入；在没有账本的项目里出这句提醒。

## Success criteria

- 转来的消息到达那一轮，阶段注入里有当场记账的提醒。
- 发版后复测 3 次都当场记账。
- 全套检查通过，其他情形输出逐字不变。

## Open questions

- 无。
