---
description: 从当前项目移除 spec-guard 的约定（保留你的 spec 和 plan 内容）
argument-hint: "[--dry-run] [--keep-state] [--accept-removals]"
allowed-tools: Bash
---

移除本项目的 spec-guard 约定。先预览将改动的内容，说明会发生什么；
**只有用户看过预览并明确确认，才能实际拆除**。

## 执行

**每次都先运行 `--dry-run`，原样展示预览**。这是插件里唯一会删除用户
`CLAUDE.md` 受管内容的操作；不要自行模拟脚本行为。若用户已带 `--dry-run`，
直接用原参数运行脚本，只展示预览并停止，不重复追加该选项。否则用原参数加
`--dry-run` 预览。以下命令仅用于**原参数未含 `--dry-run`**的情况：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/teardown-convention.sh" $ARGUMENTS --dry-run
```

预览失败时停止，不执行拆除。用户看过具体预览并明确确认后，才用相同的原参数
去掉 `--dry-run` 执行一次，再原样转述脚本输出：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/teardown-convention.sh" $ARGUMENTS
```

## 它做什么

| 动作 | 说明 |
|---|---|
| 删 `CLAUDE.md` 里 `BEGIN`/`END` 标记之间的内容（含标记） | 标记外一个字节不动；块内本地段的内容留在原位置 |
| `.agent/state.json` → `.agent/state.json.disabled` | **这一步才是真正的「移除」** |
| 实际跑一遍 `phase-guard.sh` 验证 | 而不是让人相信「无输出即为成功」这句话 |

块内本地段（独占一行的 `<!-- BEGIN:spec-guard-local -->` 与 `<!-- END:spec-guard-local -->` 之间）的行
留在块原来的位置，只去掉这两行标记，不需要任何参数。块里本地段以外、又不属于现行模板或派活规则段的行，
预览会逐行列出 `will remove:` 并标 `[needs --accept-removals]`，真正拆除会拒绝（退出 1），`CLAUDE.md` 与
`state.json` 都不改。原样转述这些行，让用户决定先把它们移进本地段，还是明确同意删除后追加 `--accept-removals`；
不要自行追加。从旧版模板装的块，旧模板独有的行也会这样列出。

**不碰**：`spec/`、`tasks/` 里的内容（那是用户的规格和计划），
以及远端 Issue 与本地事项账本。

## 为什么要动 state.json

0.7.0 起 `.agent/state.json` **本身就是 hook 的激活信号**（为 `--no-claude-md`
零足迹模式加的）。只删声明块的话，项目不是「约定被移除」，
而是**变成了零足迹模式** —— 0.7.5 之后 hook 还会每轮注入「先加载 skill」，
比移除前更黏。

改名而不是删除：模块状态与 activeModule 删了就找不回来，改回原名即可恢复。

`--keep-state` 保留原名，**hook 会继续激活**，只在确实想切到零足迹模式时用。

当前的激活判据：`CLAUDE.md`／`AGENTS.md` 中独占一行的 `BEGIN` 标记，或含 `activeModule` 的
`.agent/state.json`。正文里提到标记不会激活。该文件里的 `tracker` 字段已退役，不再是激活信号
（`docs/retirements/state-tracker-field.md`）——删掉它**不会**让 hook 停下，停用请按上面改名
`state.json`，或移除声明块。

## 之后

把脚本输出**原样转述**给用户。退出码 2 表示本项目没启用过约定，什么都没做。
