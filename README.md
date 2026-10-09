# spec-guard

简体中文 | [English](README.en.md)

spec-guard 是 [agent-skills](https://github.com/addyosmani/agent-skills) 的配套插件，支持 Claude Code 和 Codex。
agent-skills 默认一个项目只有一份 Spec 和一份 plan；spec-guard 让同一个项目可以拆成多个模块，每个模块各有自己的
Spec、Plan 和 todo，并在每轮对话开头告诉 agent 现在该做哪个模块、做到了哪一步。

## 使用场景与边界

**适合**：已经在用 agent-skills，项目会拆成多个模块，或者有多个 agent、多个 worktree 并行开发。

**不太需要**：单文件脚本或一次性小改动，agent-skills 自带的单 Spec 流程就够了。

它解决三个问题：

| 问题 | spec-guard 的做法 |
|---|---|
| 多个模块共用一份 `tasks/plan.md`，第二个模块起互相覆盖 | 多模块目录约定：一张能力图，每个模块各自的 Spec、Plan、todo |
| agent 不知道现在该做哪个模块、做到哪一步 | 每轮对话开头自动注入当前阶段，例如「`NEEDS_PLAN`：去给 `billing` 写 plan」 |
| 做到一半冒出新需求，手改能力图容易改坏 | 快速插入：在检查点提出新模块，校验、预览、经你确认后插进能力图 |

边界：

- 安装后**不会自动生效**，只在运行过 setup 的项目里工作；其他项目完全静默。
- 阶段提示只报告事实、给出建议，不写文件、不改远端。
- 写能力图、建事项、改 GitHub/GitLab 之类的操作都先预览，经你明确确认才执行。

## 核心概念

- **能力图** `spec/CAPABILITY-MAP.md`：一张表列出全部模块、职责与依赖，外加一行 Build order（构建顺序）。
- **模块**：能力图里的一行。每个模块有 `spec/<模块>.md`（Spec）和 `tasks/<模块>/plan.md`、`todo.md`。
- **阶段**：spec-guard 根据这些文件推断当前进度，例如 `MAP_ONLY`（只有能力图）、`NEEDS_PLAN`、`BUILDING`、
  `MODULE_DONE`、`DONE`，每轮注入给 agent。
- **快速插入与 Proposal**：做到一半加需求，可以在检查点直接插入模块；需要留痕、评审时走 Proposal 流程。

术语和设计理由见[设计理念与术语](docs/concepts.md)。

## 前置条件

- 已安装 [agent-skills](https://github.com/addyosmani/agent-skills) 插件；
- `bash`、`git`、`python3`（3.9 及以上，macOS 自带的即可）；
- 宿主：Claude Code，或 Codex（CLI 或桌面 App）；
- 可选：用 Proposal 或托管日常事项时需要登录 `gh`（GitHub）或 `glab`（GitLab）；用本地事项账本时需要 macOS 和
  Node.js。

## 快速开始

**1. 安装插件**

| Claude Code | Codex |
|---|---|
| `/plugin marketplace add haigeerlab/spec-guard-plugin` | `codex plugin marketplace add haigeerlab/spec-guard-plugin --ref v0.55.1` |
| `/plugin install spec-guard@spec-guard-marketplace` | `codex plugin add spec-guard@spec-guard-marketplace` |
| 开新会话，在 `/hooks` 里审核并信任 spec-guard 的 `UserPromptSubmit` hook | 开新会话即可 |

Codex 的 `--ref` 填[最新发布版](https://github.com/haigeerlab/spec-guard-plugin/releases)的版本号。

**2. 在项目里启用**

| Claude Code | Codex |
|---|---|
| 运行 `/spec-guard:setup-convention`，看预览，确认后写入 | 对 agent 说“用 spec-guard-ops 在这个项目里安装约定”，看预览，确认后写入 |

setup 会建 `spec/`、`tasks/`，并在 `CLAUDE.md`（Codex 是 `AGENTS.md`）里写入一段[约定块](docs/convention-block.md)。

**3. 开始一个多模块项目**

用 agent-skills 的 `/spec` 写能力图，然后逐个模块写 Spec、用 `/plan` 生成计划、用 `/build` 实现。每一步该做什么，
阶段提示会告诉 agent。

**最短路径**：装插件 → 在项目里运行一次 setup → 正常和 agent 对话，跟着阶段提示走。

完整流程、每个阶段的含义和两种加需求的方式见[使用流程](docs/workflow.md)。

## 常用命令

| 命令（Claude Code） | 作用 |
|---|---|
| `/spec-guard:setup-convention` | 在项目里安装多模块约定；`--replace` 升级约定块，`--dry-run` 只预览 |
| `/spec-guard:phase` | 查看当前阶段和建议的下一步 |
| `/spec-guard:verify-artifacts` | 校验能力图格式、模块与 Spec 的对应关系 |
| `/spec-guard:add-module` | 在检查点把新需求作为模块插进能力图（预览后确认） |
| `/spec-guard:config` | 查看或设置项目配置：产物语言、评审节奏 |
| `/spec-guard:teardown-convention` | 移除约定，保留你的 Spec 和 plan |

Codex 不加载斜杠命令，同样的功能通过 skill 用自然语言调用（主要是 `spec-guard-ops`）。全部 21 条命令的参数、
输出和 Codex 对照见[命令参考](docs/commands.md)。

## 运行效果与自检

启用后，发一句话给 agent，它会在上下文里看到类似这样的阶段提示：

```text
## spec-guard local workflow

当前阶段: **NEEDS_PLAN**

- Capability map: present
- Current module: `billing` (next in Build order)
- Modules 3 · Specs 2 · Plans 1 · In progress 0 · Done 1

Suggested next step: create `tasks/billing/plan.md` and `tasks/billing/todo.md` (for example with `/plan`).
```

自检：

- 运行 `/spec-guard:phase`，能看到同样的阶段信息；
- 运行 `/spec-guard:verify-artifacts`，结果应为全部通过；
- 在没运行过 setup 的项目里，hook 什么都不输出，这是正常的。

## 更新与卸载

**更新**

| Claude Code | Codex |
|---|---|
| `claude plugin marketplace update spec-guard-marketplace` | 把 `~/.codex/config.toml` 里 `[marketplaces.spec-guard-marketplace]` 的 `ref` 改成新版本 |
| `claude plugin update spec-guard@spec-guard-marketplace`，然后重开会话 | `codex plugin marketplace upgrade`，然后开新会话 |

已经装过旧版约定块的项目，更新插件后先预览 `/spec-guard:setup-convention --replace --dry-run`，确认后再替换。
块里自己写的规则放进本地段（`<!-- BEGIN:spec-guard-local -->` … `<!-- END:spec-guard-local -->`），替换时会保留。

**卸载**

1. 先在每个用过的项目里运行 `/spec-guard:teardown-convention`（先 `--dry-run` 预览），移除约定块并停用阶段提示；
   你的 `spec/`、`tasks/` 会保留。
2. 再卸载插件：Claude Code 用 `claude plugin uninstall spec-guard@spec-guard-marketplace`；Codex 用
   `codex plugin remove spec-guard@spec-guard-marketplace`，不再需要这个来源时再
   `codex plugin marketplace remove spec-guard-marketplace`。

## 故障排查

| 现象 | 先检查 |
|---|---|
| 阶段提示没有出现 | 这个项目运行过 setup 吗？Claude Code 里在 `/hooks` 信任 hook 了吗？装好插件后开新会话了吗？ |
| 阶段是 `MAP_INVALID` | 运行 `/spec-guard:verify-artifacts`，它会指出能力图哪里不对，例如模块表多于一张时列出每张表头的行号 |
| 提示说“python3 不可用”或“python3 无法运行” | 确认 `python3 --version` 是 3.9 以上，且宿主启动时的 PATH 里能找到它；修好后下一轮自动恢复 |
| Codex 里没有 spec-guard | 运行 `codex plugin list`，确认 spec-guard 已安装且启用；改了 `ref` 后要 `codex plugin marketplace upgrade` |

更多情况（`UNKNOWN`、`Paused`、`Suspended` 等提示的含义）见[故障排查](docs/troubleshooting.md)。

## 架构与文档导航

**使用者**

- [使用流程](docs/workflow.md)：从零到交付、两种加需求的方式
- [命令参考](docs/commands.md)：全部命令的参数、输出与 Codex 对照
- [故障排查](docs/troubleshooting.md)
- [设计理念与术语](docs/concepts.md)
- [可选能力](docs/optional-features.md)：本地事项账本、文档治理、能力历史；会话协作已移到独立插件 agent-relay
- [约定块](docs/convention-block.md)：setup 写进 `CLAUDE.md`／`AGENTS.md` 的内容
- [迁移说明](docs/migrations/)、[更新日志](CHANGELOG.md)

**开发者**

- [设计与架构](docs/design.md)
- [贡献指南](CONTRIBUTING.md)
- [设计决定](docs/decisions/)

**维护者**（发版与仓库维护，使用插件不需要读）：[维护者工作方式](docs/maintainer-workflow.md)、
[发版流程](docs/release-process.md)、[故障模式与审查方法](docs/lenses.md)、[上游分析](docs/upstream-analysis.md)。

本仓库也用 spec-guard 管理自己的开发：根目录的 `spec/`、`tasks/` 是本仓库自用的模块记录，不是给使用者复制的模板。

## 开发、贡献与反馈

- 发现 bug 或想提需求：在 [GitHub Issues](https://github.com/haigeerlab/spec-guard-plugin/issues) 用对应模板提交，
  怎么写得清楚见[贡献指南](CONTRIBUTING.md)。
- 想改代码：先读[贡献指南](CONTRIBUTING.md)和[设计与架构](docs/design.md)。
- 维护者文档见上面的“维护者”一组。

## 许可

[MIT](LICENSE)
