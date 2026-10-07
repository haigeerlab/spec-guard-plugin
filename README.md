# spec-guard

spec-guard 是 [agent-skills](https://github.com/addyosmani/agent-skills) 的配套插件，支持 Claude Code 和 Codex。
agent-skills 默认一个项目只有一份 Spec 和一份 plan；项目一旦拆成多个模块，就会出三类问题。spec-guard 补的就是这三处：

| 问题 | spec-guard 的做法 |
|---|---|
| 多个模块共用一份 `tasks/plan.md` 和 `todo.md`：上游没有模块概念，第二个模块起要么被打断确认覆盖，要么靠人盯住 | 多模块目录约定：一张能力图，每个模块各自的 Spec、Plan、todo |
| agent 不知道现在该做哪个模块、做到哪一步 | 每轮对话开头自动注入当前阶段，例如「`NEEDS_PLAN`：去给 `billing` 写 plan」 |
| 做到一半冒出新需求，不知道插在哪，手改能力图容易改坏 | 快速插入：在检查点（或显式插队）提出新模块，校验、预览后经你确认插进能力图；需要留痕时改走 Proposal |

阶段 hook 只报告事实、给出建议；Local 事项写入需要明确使用 `ticket` 入口，
能力图插入也须预览确认。设计原因见[设计理念与术语](docs/concepts.md)。

## 功能一览

| 功能 | 解决什么问题 | 入口（Claude Code） | 是否默认生效 |
|---|---|---|---|
| 多模块约定 | 模块产物互不覆盖，`/build` 只从当前模块取任务 | `/spec-guard:setup-convention` | 运行 setup 后生效 |
| 阶段提示 | agent 每轮都知道当前模块和下一步 | 自动；`/spec-guard:phase` 查看 | 运行 setup 后生效 |
| 产物校验 | 能力图格式、模块与 Spec 的对应关系是否正确 | `/spec-guard:verify-artifacts` | 按需运行 |
| 快速插入 | 新需求校验后插进能力图，不改坏依赖和顺序 | `/spec-guard:add-module` | 按需运行 |
| 项目审查交接 | 限定审查批次，整理发现并转入事项和修复 | 项目约定与共享检查点 | 安装约定后按需使用 |
| Proposal 流程 | 需要留痕时，新需求按提交、接受、晋级、收尾四步加进能力图（`proposal-submit` 补全并校验草稿） | `/spec-guard:proposal-*` | 可选；需要一次性准备 |
| 会话协作（已移到 agent-relay） | 同一台 Mac 上的会话互相传话、按名字联系、跨宿主委派，现在由独立插件 agent-relay 提供 | 安装 agent-relay；过渡期 `/spec-guard:collaboration` 会转交 | 见[迁移说明](docs/migrations/2026-10-07-collaboration-split.md) |
| 本地事项账本 | 明确选择 Local 时在本地记 bug 和需求 | `/spec-guard:local-ticket-ledger` | 需单独启用 |
| 托管日常事项 | 明确选择 GitHub/GitLab 后逐项查重、授权创建并在交付后对账 | `/spec-guard:ticket`、`hosted-ticket-workflow` skill | 需登录对应 CLI；外部写入逐次授权 |
| 文档治理 | 声明哪些文档是依据、每个模块改了哪些 | `/spec-guard:documentation-*` | 没有文档基线就不生效 |
| 能力历史 | 核验旧版本归档下来的能力图没被改动 | `/spec-guard:history-integrity` | 只对有归档的项目有用 |

Codex 不加载斜杠命令，同样的功能通过 skill 用自然语言调用，对照表见[使用流程](docs/workflow.md#命令对照)。

## 适合谁

- **适合**：已经在用 agent-skills，项目会拆成多个模块，或者有多个 agent、多个 worktree 并行开发。
- **不太需要**：单文件脚本或一次性小改动。agent-skills 自带的单 Spec 流程就够了。

## 安装

**前置条件：**

- 已安装 agent-skills；
- `bash`、`git`、`python3`（3.9 及以上，macOS 自带的即可）；
- 用 Proposal 或托管日常事项流程时，需要登录 `gh`（GitHub）或 `glab`（GitLab）；
- 用本地事项账本时，需要 macOS 和 Node.js。

**Claude Code：**

```text
/plugin marketplace add haigeerlab/spec-guard-plugin
/plugin install spec-guard@spec-guard-marketplace
```

**Codex：**

```bash
codex plugin marketplace add haigeerlab/spec-guard-plugin --ref v0.50.1
codex plugin add spec-guard@spec-guard-marketplace
```

`--ref` 填[最新发布版](https://github.com/haigeerlab/spec-guard-plugin/releases)的版本号。
装好后开一个新会话，在 `/hooks` 里审核并信任 spec-guard 的 `UserPromptSubmit` hook。

**装好之后不会自动生效。** 没有运行过 setup 的项目，hook 完全静默。要在哪个项目用，就在哪个项目里运行一次 setup。

## 5 分钟上手

1. 在项目里运行 `/spec-guard:setup-convention`，看预览，确认后写入。
2. 用 `/spec` 写能力图 `spec/CAPABILITY-MAP.md`：列出模块，写一行 Build order，人工评审。
3. 发一句话给 agent，它会看到类似下面的提示：

   ```text
   当前阶段: **MAP_ONLY**
   Suggested next step: write the first reviewed module spec under `spec/`.
   ```

4. 按提示逐个模块推进：写 Spec，用 `/plan` 生成 plan，用 `/build` 实现。阶段会依次变为 `NEEDS_PLAN`、`BUILDING`、`DONE`；模块做完但还有别的模块时显示 `MODULE_DONE`，`DONE` 表示全部模块都完成。
   模块完成且上下文达到窗口一半、或模块进行中达到窗口 80% 时，提示会建议开新会话——需求、计划与进度都在文件里，新会话接得上；
   每轮提示还带当前分支与 worktree，agent 请你评审或确认时会说明代码在哪。

项目做到一半来了新需求，在检查点（或显式插队）用 `/spec-guard:add-module` 插进能力图。完整流程、每个阶段的含义和两种加需求的方式，
见[使用流程](docs/workflow.md)。

## 文档

| 文档 | 内容 |
|---|---|
| [使用流程](docs/workflow.md) | 新项目从零到交付、快速插入与 Proposal 两种加需求方式、能力图规则、Claude 与 Codex 命令对照 |
| [设计理念与术语](docs/concepts.md) | 为什么这样设计，以及能力图、Proposal、revision 等术语的含义 |
| [可选能力](docs/optional-features.md) | 本地事项账本、文档治理、能力历史：各自解决什么、怎么启用；会话协作已移到 agent-relay |
| [更新日志](CHANGELOG.md) | 每个版本改了什么 |

## 约定块

setup 会往 `CLAUDE.md`（Codex 是 `AGENTS.md`）写入下面这段约定，告诉 agent 多模块的目录规则。不运行 setup 的人，
也可以照着它手工遵守：

<!-- SYNC:claude-block-local BEGIN -->
````markdown
<!-- BEGIN:agent-skills-convention -->
## Agent Skills 集成约定

> 由 `/spec-guard:setup-convention local` 生成。任务托管在**本地 todo.md**（Addy 原生路径）。
> 保留 `<!-- BEGIN/END -->` 标记，`/spec-guard:setup-convention --replace` 靠它升级本块。

- 能力图 `spec/CAPABILITY-MAP.md`，模块 spec `spec/<module-id>.md`（kebab-case，一次选定中途不改名）
- **不要**在项目根建 `SPEC.md` / `SPEC-<module>.md` —— `/build` 只认根 `SPEC.md`、
  `docs/SPEC.md`、`spec/` 三条路径，**只有第三条是通配的**
- 每个模块的产物互相隔离：`tasks/<module-id>/plan.md` + `tasks/<module-id>/todo.md`，
  **不要共用 `tasks/plan.md`**
- `/build` 取任务：读 `.agent/state.json` 的 `activeModule`，从该模块的 `todo.md`
  取第一个未勾选项，**不跨模块取**
- 切换 `activeModule` 前当前模块不能有进行中的 task；切换后重读该模块的 spec 和 plan
- 若项目已启用 Local 事项账本，确认要实现的需求或修复在动代码前先用 `spec-guard:ticket`
  查重并取得事项 ID；探索和无需追踪的小操作例外
- 项目级审查按 `spec-guard:spec-guard-ops` 的共享检查点规则限定批次、收束发现并交接缺陷；
  审查完成后的“继续”推进已预告的问题处理步骤，不重新泛扫
- 明确选用 GitHub/GitLab 普通 Issue 时，用 `spec-guard:hosted-ticket-workflow` 逐项查重、授权写入与交付对账；
  Local 事项仍走 `spec-guard:ticket`，不凭 Git remote 改目标
- 阶段交接或停止时，加载 `spec-guard:spec-guard-ops` 的共享检查点规则，预告已授权下一步。
- Plan 的检查点标 `gate`（停下等确认）或 `report`（记入 todo 后继续），未标注按 `gate`；按需求批量前置审与
  UI 自验按 `spec-guard:spec-guard-ops` 的共享检查点规则
<!-- END:agent-skills-convention -->
````
<!-- SYNC:claude-block-local END -->

## 升级与迁移

- 仓库已从 `yizhongkaimail-collab/spec-guard-plugin` 迁到 `haigeerlab/spec-guard-plugin`。旧安装仍能运行，但要重新添加
  marketplace 才能收到更新，见[仓库迁移说明](docs/migrations/2026-09-27-repository-copy.md)。
- v0.14 之后，可写的 GitHub/GitLab tracker 桥已退役，见[迁移指南](docs/migrations/v0.15-legacy-tracker-retirement.md)。
- Proposal v1 升级到 v2，见 [Proposal v2 迁移](docs/migrations/proposal-mainline-review-v2.md)。

## 参与开发

维护者的工作方式、验证命令和发布流程见 [docs/maintainer-workflow.md](docs/maintainer-workflow.md) 与
[docs/release-process.md](docs/release-process.md)。
