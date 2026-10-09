# 设计与架构

> 写给想改代码的开发者和维护者。面向使用者的设计理念与术语见[设计理念与术语](concepts.md)，命令见
> [命令参考](commands.md)。

## 做什么

spec-guard 在 agent-skills 外面加了两道互相独立的保障：

1. **本地多模块目录约定**：一张能力图、每个模块各自的 Spec、Plan、todo，让模块的计划和任务清单不再互相覆盖；
   并在每轮对话开头注入当前阶段。
2. **Proposal 生命周期**：只读地读取远端默认分支上已发布的 Proposal 快照和 GitHub/GitLab Issue 的阶段标签，
   把需要留痕的需求按锚点插进能力图。

另外有几项需要显式启用的可选能力：同一台 Mac 上的本地事项账本；明确选定目标后按需处理 GitHub/GitLab 普通
Issue 的托管流程（不投影任务、不绑定 worktree）；把本地事项归档、并在预览和逐次授权后交接到 GitHub/GitLab 的
可移植流程；限定审查批次、整理发现并交给现有事项与修复流程的项目审查交接约定。会话协作已拆成独立插件
agent-relay，spec-guard 只通过 `agent_relay_probe.py` 只读地检测它。

## 部件

```
plugins/spec-guard/
├── .claude-plugin/plugin.json   Claude 清单；命令按 commands/ 目录自动发现
├── .codex-plugin/plugin.json    Codex 清单（skill、hook），版本必须与 Claude 清单一致
├── commands/                    Claude 的斜杠命令：每条是一份给 agent 的说明，调用 hooks/ 下的脚本
├── skills/                      Codex 的入口（Codex 只读 skill）：spec-guard-ops、ticket 等
├── hooks/                       全部可执行逻辑与回归测试
├── references/                  各流程的完整契约（Proposal、账本、文档治理、检查点规则）
├── templates/                   写进使用者 CLAUDE.md／AGENTS.md 的约定块
└── locks/                       本地事项账本运行时的锁定版本
```

`hooks/` 里的主要部件：

| 部件 | 职责 |
|---|---|
| `hooks.json` → `phase-guard.sh` | `UserPromptSubmit` hook：判断项目是否激活，读本地文件，输出阶段注入 |
| `module_stage.py` | 按模块计算阶段、当前模块、计数、Paused／Suspended 与上下文提醒 |
| `capability_map.py` | 能力图的唯一严格解析器；阶段提示、`verify-artifacts`、`add-module`、Proposal 共用 |
| `spec-digest.py` | 唯一的指纹算法，能力图与 Proposal 校验共用 |
| `session_context.py` | 从宿主给的会话记录读上下文大小与窗口，只用于 `/compact` 提醒 |
| `setup-convention.sh`、`teardown-convention.sh`、`managed-block.py` | 安装、升级、移除约定块；`managed-block.py` 负责标记校验、本地段与原子写入 |
| `verify-artifacts.sh` | 按需校验已落地的产物 |
| `module-insert.py` | 快速插入与 Proposal 晋级的写入（只改能力图） |
| `project_config.py` | `.agent/config.json` 的唯一解析器 |
| `state_paths.py` | 本机状态目录的唯一来源（见下文文件布局） |
| `proposal_*.py` | Proposal 契约、发布、读 Issue、评审、晋级证明、收尾 |
| `local_ledger_*.py`、`local_ticket_*.py`、`hosted_ticket*.py` | 本地事项账本、可移植流程、托管事项 |

## 数据流

每轮对话：

1. 宿主在用户发言后触发 `UserPromptSubmit`，`hooks.json` 用宿主给的插件根目录（`PLUGIN_ROOT` 或
   `CLAUDE_PLUGIN_ROOT`）调用 `phase-guard.sh`。根目录缺失或脚本失败时也输出一条可诊断的 JSON，不静默。
2. `phase-guard.sh` 判断激活信号：`CLAUDE.md`／`AGENTS.md` 里独占一行的约定块开始标记，或含 `activeModule` 的
   `.agent/state.json`。都没有就静默退出 0。
3. 激活时读本地文件：能力图、`spec/`、`tasks/<id>/plan.md` 与 `todo.md`、`.agent/state.json`、`.agent/config.json`，
   交给 `module_stage.py` 算出阶段；有会话记录时由 `session_context.py` 补上上下文大小。
4. 输出 `hookSpecificOutput.additionalContext`。来自仓库的值在注入前净化（折叠空白、去掉反引号与反斜杠、剥掉
   控制字符、限长），能力图原文标注“非指令”。

写操作只发生在用户调用命令之后：命令先预览，用户确认后才写；写入能力图、配置、事项都是原子写并读回核对。
Proposal 与托管事项的远端读取只读；远端写入（关闭 Proposal 事项、创建 Issue）每次都需要针对精确目标与内容的授权。

## 两个宿主的差异

| | Claude Code | Codex |
|---|---|---|
| 入口 | 斜杠命令 `/spec-guard:*`（`commands/`） | skill（`skills/`），用自然语言调用；不加载命令 |
| 阶段注入 | 同一份 `hooks/hooks.json`；首次使用需在 `/hooks` 信任 | 同一份 `hooks/hooks.json` |
| 插件根目录 | `CLAUDE_PLUGIN_ROOT`，命令里由宿主代入 | `PLUGIN_ROOT`；命令片段找不到时查询 `codex plugin list` |
| 约定块 | `CLAUDE.md` 的 `agent-skills-convention` 块 | `AGENTS.md` 的 `spec-guard-codex-convention` 块 |
| 上下文窗口 | 会话记录不带窗口大小，按 1M 窗口折算阈值 | 从会话记录读取窗口 |
| 其他 | | 默认的 workspace-write 沙箱不允许写 `.git`，提交需要提权审批 |

命令与 skill 的路由一致性由 `scripts/check-command-parity.py` 检查：每条命令引用的脚本都要有 skill 能走到。

## 不变量

- hook 默认不生效；没有激活信号的项目必须静默退出。
- 探测失败必须降级，不能把环境故障说成链路断裂；“读不到”报 `unknown`，不当作“没有”。
- hook 只报告事实和建议，不写文件、不改远端状态。
- `hooks/spec-digest.py` 是唯一指纹算法，`capability_map.py` 是唯一能力图解析器，不得复制或内联。
- `phase-guard.sh` 只依赖 `bash`、`git`、`python3`，不引入 `jq` 之类的硬依赖。
- 修改共享判据时，`phase-guard` 与 `verify-artifacts` 两边一起改，并各有正反回归。
- 所有 hook 输出必须是宿主接受的 JSON；不用 `cmd | grep -q`，避免 SIGPIPE。
- 兼容 macOS 自带的 bash 3.2 与 python 3.9。

## Proposal 边界

`spec/CAPABILITY-MAP.md` 是唯一的能力图：已接受的 Proposal 按声明的锚点或末尾插入模块，不另建图。Proposal v2 用
revision 摘要绑定已发布内容。“接受”是人写的 Issue 阶段标签（`proposal-stage:accepted`）加上对远端默认分支的一次新鲜
评审；不读主线策略、验收凭证或权威身份。合并后的证明从 Proposal 的基线提交出发，在晋级提交的父提交上判断新鲜度。

tracker 适配器只读，只按显式给出的容器里的完整身份标记找回 Proposal Issue。预检与合并后证明都只读，既不能创建
晋级分支，也不能改能力图或 tracker 状态。

## 本地边界

本地约定把模块文档放在 `spec/` 与 `tasks/<module-id>/` 下。`.agent/state.json` 只记录本地的当前模块，不是 Proposal 池，
Proposal 代码从不读它。已开工、在等外部条件的模块可以用 `todo.md` 里的一行标记挂起：保留 Build order 位置，选当前
模块时跳过，只有用户恢复时才回来；插件不记录原因或日期，提醒（如果有）放在宿主里。

## 项目配置

`.agent/config.json` 是入库的项目配置，团队与两个宿主共用一份。`project_config.py` 是唯一解析器，阶段提示、
`verify-artifacts` 与 `/spec-guard:config` 都调用它。文件不存在时什么都不变；文件无效时用固定的问题代码报告，所有
设置都不生效，键和值不会进入注入上下文（它们是仓库内容）。目前的项有 `artifactLanguage`（新写的 Spec、Plan、todo
正文的语言，结构关键字不变）与 `reviewCadence`（默认 `separate`，`combined` 时一个模块的 Spec 与 Plan 一起审）。
派活开关与默认事项后端各有自己的位置，这里只汇总显示。

## 文件布局（File layout）

spec-guard 写在哪里、谁能删什么。`scripts/check-state-paths.py` 确保 hooks 里的家目录路径只来自 `state_paths.py`，
以及读取宿主自身配置。

| 类别 | 路径 | 入库 | 谁写 | 怎么删 |
|---|---|---|---|---|
| 项目产物 | `spec/`、`tasks/<id>/`、`CLAUDE.md`／`AGENTS.md` 里的约定块、`.agent/config.json`、`.agent/tracker.json`、`DOCUMENTATION-BASELINE.md`、`.epiq/project.json` | 是 | 预览并确认后的命令 | 通过命令；teardown 保留 Spec 与 Plan |
| 历史归档 | `spec/history/`、`tasks/history/`、`.agent/history/`、`spec/CAPABILITY-HISTORY.json` | 是 | 只有一次性的历史迁移 | 永不删除：账本按哈希固定每个文件 |
| 每个 checkout 的状态 | `.agent/state.json`（当前模块）；新的状态一律放在 `$(git rev-parse --git-path spec-guard)` 下 | 否 | 构建流程；本地锁 | 随意 |
| 本机状态 | `~/.spec-guard/` 或 `$SPEC_GUARD_STATE_DIR`：`local-ticket-ledger/runtime`、`local-ticket-portability`、`hosted-ticket-intents`、`proposal-closeout` | 否 | 账本安装、交接、托管事项写入、Proposal 收尾 | 运行时可重装；日志与意图只在没有待完成的写入时删，它们用来防重复 |

`~/.local/state/spec-guard/hosted-ticket-intents` 与 `.../proposal-closeout` 在新目录不存在时整目录回退读取，不搬运、
不删除。`~/.spec-guard/native-collaboration`、`session-delegation`、`collaboration` 属于 agent-relay，不属于 spec-guard。

## 已退役的边界

v0.14 时代可写的远端 tracker 桥不属于本产品，也没有藏在兼容路径后面：远端投影、选择、绑定、投递与同步预览都已
移除。历史记录作为不可改的证据保留。完整的决定、迁移规则与验收条件见[退役说明](retirements/spec-github-bridge-retirement.md)。
