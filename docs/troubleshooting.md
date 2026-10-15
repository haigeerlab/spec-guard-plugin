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
2. 会话开在一个不是项目的目录里（比如需求文档目录），实际开发在别处的仓库。hook 只看会话目录，不推断你在改哪个
   目录，所以每一轮都静默。Codex 里最容易遇到：它的 hook 在会话目录运行。
3. 运行过 teardown：`.agent/state.json` 被改名成了 `state.json.disabled`，约定块也删了。
4. Claude Code 里还没信任 hook，或装好插件后没开新会话。
5. Codex 里插件没安装或没启用（见下文“Codex 里没有 spec-guard”）。

**检查**：

```bash
grep -n 'BEGIN:agent-skills-convention\|BEGIN:spec-guard-codex-convention' CLAUDE.md AGENTS.md
ls .agent/
```

**解决**：

- 没有激活信号：运行 `/spec-guard:setup-convention`（先 `--dry-run` 预览）。
- 会话目录不是项目目录：在会话里运行 `/spec-guard:link-project`（Codex：`spec-guard-ops` 的 link-project 一节），
  `set --project <项目路径>` 先预览、确认后写入 `.agent/spec-guard-link.json`。之后每轮都会收到那个项目的阶段提示，
  多一行 `Linked project`。其他命令目前不自动跟随指向，要显式带上项目路径。
- 有 `state.json.disabled`：确认要恢复后，把它改回 `.agent/state.json`。setup 在这种情况下会拒绝新建空状态，
  免得覆盖原来的 `activeModule`。
- Claude Code：在 `/hooks` 里审核并信任 spec-guard 的 `UserPromptSubmit` hook，然后开新会话。

**压缩后没有阶段注入**（0.61.0 起，上下文压缩后会多一次注入，末尾带一句压缩后的核对提醒）：

- Codex：升级后新增的 `SessionStart` 一项要单独信任一次，未信任时会被跳过、不报错；原有的 `UserPromptSubmit` 一项不受影响。
- 共用会话目录、各做不同项目时，会话要按会话登记自己的项目（`link-project set --session`），否则压缩后注入的是别的项目。
- 压缩后提示的“下一项”来自 todo：任务做完就勾，否则提示的是旧的一项。

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
| `Review: Spec … is awaiting the user's review` | 当前模块的 Spec 或 Plan 标着待审核；你批准后让 agent 运行 `/spec-guard:review-mark` 记录 |
| `Review: Spec … was edited after it was approved` | Spec 在批准后被改过；看过修订内容并批准后，重新运行 `/spec-guard:review-mark` |
| `Review: the review marker in … is invalid` | 该文件的评审标记多于一行或写法不符；运行 `/spec-guard:verify-artifacts` 查看，手工改成一行有效标记 |
| `Next gate: …` | 实现阶段下一个要停下等你确认的检查点。Plan 已记为批准时，它之前的 task 与 `report` 检查点不停；Plan 没有评审标记时只指出这个检查点，并提醒尚未批准就先等批准 |
| 点了 `/compact` 代码块的“运行”，终端报 `no such file or directory: /compact` | `/compact`、`/clear` 是发到对话消息输入框的斜杠命令，不是终端命令。0.57.1 之前的提示没有说明这一点，agent 可能把它放进带 `bash` 标签的代码块，宿主因此给了“运行”按钮。把这行复制到消息输入框发送即可；升级到 0.57.1 后提示会要求代码块不带 shell 语言标签 |
| `Linked project: …` | 会话目录通过 `.agent/spec-guard-link.json` 指向了别处的项目；这一轮的阶段与位置行都是那个项目的。指向按目录生效：同一目录里的每个会话都会收到它。如果这个会话做的是别的项目，这段提示不适用——多个会话共用一个目录、各做不同项目时不要建立指向，用 `/spec-guard:link-project` 的 `unset` 解除，或把会话开在各自的项目目录里 |
| `本目录有指向文件 … 但它的格式无效` | 指向文件既不是版本 1（只含 `version` 与 `project`），也不是版本 2（含 `version`、`sessions`，可选 `project`）；`link-project unset --confirm` 后重新 `set` |
| `本目录有指向文件 … 但它指向的目录不存在或不是目录` | 项目被移动或删除了；重新 `set --project <新路径>`，或 `unset` 解除 |
| `本目录有指向文件 … 但它指向的目录没有启用 spec-guard` | 目标里没有约定块，也没有带 `activeModule` 的 `.agent/state.json`；在那个项目里运行 `/spec-guard:setup-convention`，或改指向别处 |
| `tasks/<模块>/<文件> 有 N 个未勾选项，它们不计入阶段` | `verify-artifacts` 发现任务目录下 `plan.md`、`todo.md` 之外的文件里有没勾的清单项。阶段判定只数 `todo.md`，所以这些项没做完也会显示模块已完成。把仍要做的项移进该模块的 `todo.md`；已经不需要的勾掉或删掉。只是警告，不影响校验结果 |
| `Linked project: … this session is linked to it by its own entry` | 这个会话在共用的会话目录里有自己的登记（`link-project set --session`），阶段与位置行是它登记的项目的；同目录的其他会话不受影响 |
| 共用一个会话目录的几个会话，有的收到别的项目的阶段提示 | 目录里有一份目录级指向，对所有会话生效。让每个会话各自登记：`link-project set --project <路径> --session <会话标识>`；不再需要目录级指向时 `unset`（不带 `--session`）去掉它 |
| `Suspended: <模块>` | 模块被挂起，不会自动恢复；用 `/spec-guard:module-suspend` 恢复 |
| `MODULE_DONE` | `activeModule` 指向的模块已完成，但还有别的模块没做；按提示把 `activeModule` 改成下一个模块 |
| 有 Plan 却没有 todo 的提醒 | 这类模块按已完成计；还有活就补 `tasks/<id>/todo.md`，确已交付可在 `plan.md` 加 `<!-- spec-guard: no-todo -->` |

还没解决的，按[贡献指南](../CONTRIBUTING.md#报-bug)报 bug，附上 `/spec-guard:phase` 与 `/spec-guard:verify-artifacts` 的输出。
