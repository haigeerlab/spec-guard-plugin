# 退役：会话交接命令（session-handoff）

状态：已退役（2026-10-08，用户决定；模块 `context-after-compact`，0.52.0）。

## 退役的是什么

`/spec-guard:handoff`（Codex：`spec-guard handoff`）：从仓库文件与 git 拼出一段可直接粘贴到新会话的交接文本，
整条提示词恰好是这条命令时由 UserPromptSubmit hook 本地作答。移除的有命令文件、`hooks/session_handoff.py`
及其测试、`phase-guard.sh` 的本地作答分支、`spec-guard-ops` skill 的 handoff 一节。

## 为什么退役

- 用户不切新会话：新会话会丢掉它正在联系的其他会话；释放上下文用 `/compact`（相关工作，带重点）或 `/clear`
  （不相关工作），这也是 Claude Code 与 Codex 官方文档给的判据。
- 交接文本里的事实（位置、阶段、模块计数、未合并提交）阶段提示每轮都会注入；可续接的状态本来就在 Spec、Plan 与
  todo 里。
- 实测（2026-10-08）：用 `--name` 命名的 Claude Code 会话执行 `/clear` 后保留名字与会话编号，之后发来的跨会话
  消息照常收到。

## 用什么代替

- 释放上下文：`/compact`（可带重点）或 `/clear`；需要被其他会话联系的会话先 `/rename`。
- 查看现状：`/spec-guard:phase`（Codex：`spec-guard-ops` skill 的 phase 一节）。
- 升级后，输入原来的命令不再被 hook 拦截作答，按普通提示词处理。

## 历史材料

原 Spec、Plan 与 todo 逐字归档在 [session-handoff/](session-handoff/)，只作历史证据，其中的路径与要求不再适用。
`spec/CAPABILITY-HISTORY.json`、发布证据与 CHANGELOG 中的旧记录不改写。
