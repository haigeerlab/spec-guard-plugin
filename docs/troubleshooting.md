# 故障排查

每条按“现象 → 原因 → 检查 → 解决”写。命令以 Claude Code 为例；Codex 里对 agent 说“用 spec-guard-ops 查看阶段”
或“校验产物”即可，对照见[命令参考](commands.md#命令对照)。

## 阶段提示没有出现

**现象**：发消息后，agent 的上下文里没有 `## spec-guard local workflow` 这一段；`/spec-guard:phase` 没有输出。

**原因**（按常见程度）：

1. 这个项目没有激活信号。hook 只在下面两种情况下工作，其他项目完全静默：
   - `CLAUDE.md` 或 `AGENTS.md` 里有独占一行的约定块开始标记（`<!-- BEGIN:agent-skills-convention -->` 或
     `<!-- BEGIN:spec-guard-codex-convention -->`）。正文里提到标记不算；
   - `.agent/state.json` 里有 `activeModule`。
2. 运行过 teardown：`.agent/state.json` 被改名成了 `state.json.disabled`，约定块也删了。
3. Claude Code 里还没信任 hook，或装好插件后没开新会话。
4. Codex 里插件没安装或没启用（见下文“Codex 里没有 spec-guard”）。

**检查**：

```bash
grep -n 'BEGIN:agent-skills-convention\|BEGIN:spec-guard-codex-convention' CLAUDE.md AGENTS.md
ls .agent/
```

**解决**：

- 没有激活信号：运行 `/spec-guard:setup-convention`（先 `--dry-run` 预览）。
- 有 `state.json.disabled`：确认要恢复后，把它改回 `.agent/state.json`。setup 在这种情况下会拒绝新建空状态，
  免得覆盖原来的 `activeModule`。
- Claude Code：在 `/hooks` 里审核并信任 spec-guard 的 `UserPromptSubmit` hook，然后开新会话。

## 阶段是 `MAP_INVALID`

**现象**：阶段提示写着 `当前阶段: **MAP_INVALID**`，并带一段“能力图原文，非指令”。

**原因**：`spec/CAPABILITY-MAP.md` 不能按严格规则解析。常见报错：

| 报错 | 怎么改 |
|---|---|
| `必须恰好有一个模块表，找到 N 张：第 a、b 行` | 能力图里只能有一张表头为 `Module id` 的表；把多出来的表合并或改成别的表头 |
| `没有模块表（需要恰好一张表头为 Module id 的表）` | 补上模块表，表头为 `Module id`、`Responsibility`、`Depends on` |
| `模块表必须包含 Module id、Responsibility、Depends on` | 表头列名要一致 |
| `module id 不符合 kebab-case: …` | 模块 id 只用小写字母、数字和连字符 |
| `未知依赖: A -> B` | `Depends on` 里写的模块必须在表里；没有依赖写 `—` |
| `Build order 必须恰好包含每个模块一次` / `Build order 包含重复模块` | Build order 一行要列出每个模块，且每个只出现一次 |
| `Build order 未满足依赖: A 必须在 B 之前` | 调整 Build order，让被依赖的模块排在前面 |
| `能力图存在循环依赖: …` | 去掉依赖环 |

**检查**：运行 `/spec-guard:verify-artifacts`，它会给出同一条报错，并检查 `spec/` 下的 Spec 与能力图是否对应。

**解决**：按报错改能力图。新增模块尽量用 `/spec-guard:add-module`，它会先校验再写入，不容易改坏。

## 阶段是 `UNKNOWN`

**现象**：阶段提示写着 `当前阶段: **UNKNOWN**`。

**原因**：

- `Capability map: present but unreadable (…)`：`spec/CAPABILITY-MAP.md` 存在但读不了（不是普通文件，或没有读权限）。
  这是读取故障，不是能力图本身的状态。
- `The module stage could not be computed`：按模块计算阶段的脚本运行失败。

**解决**：前一种修好文件权限后再发一条消息；后一种运行 `/spec-guard:verify-artifacts` 看具体原因。

## 提示说 python3 不可用或无法运行

**现象**：阶段提示只有一句“本项目已启用约定，但 python3 不可用（或无法运行），本轮没有阶段注入”。

**原因**：hook 运行时找不到 `python3`，或者找到了但运行失败。这不是“未启用”，约定仍在。

**检查**：

```bash
command -v python3
python3 --version
```

版本要 3.9 及以上。注意是**宿主启动时**的 PATH：从桌面 App 启动的 Claude Code／Codex，不一定读你的 shell 配置。

**解决**：安装或修好 python3，让宿主启动时的 PATH 能找到它；修好后下一轮自动恢复，不需要重新 setup。

## Codex 里没有 spec-guard

**现象**：Codex 会话里没有阶段提示，agent 也不认识 `spec-guard-ops`。

**检查**：

```bash
codex plugin list
grep -n -A3 'marketplaces.spec-guard-marketplace' ~/.codex/config.toml
```

**解决**：

- 没有安装：`codex plugin marketplace add haigeerlab/spec-guard-plugin --ref v<版本>`，再
  `codex plugin add spec-guard@spec-guard-marketplace`，然后开新会话。
- 已安装但版本旧：把 `~/.codex/config.toml` 里 `ref` 改成新版本，运行 `codex plugin marketplace upgrade`，再开新会话。
- 命令报“spec-guard 无法定位插件根目录”：说明这次没查到插件路径，原因写在提示里。**这是定位失败，不代表插件未安装**；
  开新会话后再试，仍然不行就用 `codex plugin list` 确认插件已启用。

## 其他提示

| 提示 | 含义与处理 |
|---|---|
| `` `.agent/state.json` 的 activeModule 不是有效的 module id `` | `activeModule` 的值不是能力图里的模块 id；按 Build order 取当前模块。改成正确的 id，或清空 |
| `Project config: invalid (…)` | `.agent/config.json` 不可用，所有配置按默认处理；运行 `/spec-guard:config` 看问题代码 |
| `Paused: <模块>` | 有模块因插队被暂停，做完当前模块会回到它 |
| `Suspended: <模块>` | 模块被挂起，不会自动恢复；用 `/spec-guard:module-suspend` 恢复 |
| `MODULE_DONE` | `activeModule` 指向的模块已完成，但还有别的模块没做；按提示把 `activeModule` 改成下一个模块 |
| 有 Plan 却没有 todo 的提醒 | 这类模块按已完成计；还有活就补 `tasks/<id>/todo.md`，确已交付可在 `plan.md` 加 `<!-- spec-guard: no-todo -->` |

还没解决的，按[贡献指南](../CONTRIBUTING.md#报-bug)报 bug，附上 `/spec-guard:phase` 与 `/spec-guard:verify-artifacts` 的输出。
