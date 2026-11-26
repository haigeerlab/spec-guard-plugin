# CLAUDE.md

给在 **spec-guard 插件源码仓库**工作的 AI agent 使用。

## 作用域与自引用边界

本文件配置的是插件作者仓库，不是给使用者复制到项目中的约定。使用者的模板在
`plugins/spec-guard/templates/claude-block-*.md`，由 `/setup-convention` 写入。

本仓库用 spec-guard 管理自身开发：`AGENTS.md` 的 Codex 约定块、`spec/`、`tasks/`
与 `.agent/` 是有意保留的激活信号，phase-guard 在这里报告的是本仓库自己的 initiative
状态。它运行的是**已安装版**插件，不是工作区源码，其输出不能当作产品回归结果。
需要验证插件行为时，使用 `evals/codex-plugin-smoke.sh` 建立的临时消费者项目。
`.epiq/` 同样是有意保留的自用状态：它是本仓库自己使用的本地事项账本的已提交项目身份
（见 [spec/local-ticket-ledger.md](spec/local-ticket-ledger.md) Boundaries）。

## 插件目的

spec-guard 为 `addyosmani/agent-skills` 提供：

1. 本地多模块 Spec 约定：一张能力图、模块 Spec、Plan 与任务清单；
2. Proposal 生命周期：只读地审查 GitHub / GitLab Proposal Issue，把新需求按锚点插入能力图；
3. UserPromptSubmit 阶段注入：报告当前模块缺 Spec、缺 Plan、在构建中还是已完成；
4. 可选的本机能力：本地事项账本（会话协作已拆为独立插件 agent-relay，Spec Guard 只经 `agent_relay_probe.py` 检测它）。
5. 按需托管日常事项：明确目标后处理 GitHub/GitLab 普通 Issue，不恢复旧 bridge。

改动前先阅读 [docs/design.md](docs/design.md)；已有故障模式和审查方法在
[docs/lenses.md](docs/lenses.md)。

## 核心布局

```
.claude-plugin/marketplace.json         ← marketplace 根清单
plugins/spec-guard/
├── .claude-plugin/plugin.json          ← Claude 清单
├── .codex-plugin/plugin.json           ← Codex 清单（版本必须一致）
├── commands/                            ← slash 命令
├── hooks/                               ← hook、共享脚本与回归测试
├── skills/                              ← tracker / 本地操作技能
└── templates/                           ← 写入消费者项目的模板
docs/design.md                           ← 设计与架构（部件、数据流、两个宿主的差异、不变量）
scripts/validate.sh                      ← 仓库完整性校验
```

## 不变量

- hook 默认不生效；无激活信号、也没有 `.epiq/project.json` 的无关项目必须静默退出；只有账本的项目只出账本提醒，不出阶段内容。
- 探测失败必须降级，不能把环境故障说成链路断裂。
- hook 只报告事实和建议，不写文件、不改远端状态。
- `hooks/spec-digest.py` 是唯一指纹算法；不得复制或内联实现。
- `phase-guard.sh` 只能依赖 `bash`、`git` 与 `python3`，不可引入 `jq` 硬依赖。
- 修改共享判据时，同时更新 `phase-guard`、`verify-artifacts` 和两边的正反回归。
- 所有 hook 输出必须是宿主接受的 JSON；不要使用 `cmd | grep -q`，避免 SIGPIPE。
- macOS 兼容性检查必须显式用 `/bin/bash`；变量后接多字节字符时写 `${VAR}`。

## 最小验证

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

提交一律走 `/bin/bash scripts/verify-and-commit.sh -- -m "<信息>"`：只改文档类路径时跑快档（`validate.sh --quick`，
含读仓库文档的回归，与 verify-artifacts），其余跑上面三条（并行，暂存了 `.sh` 时加 ShellCheck），全部通过才提交已暂存的内容，并记下
tree 供 pre-push 跳过重复检查。

这三条与预推送 hook 一致；`validate.sh` 已包含清单一致性、检查器回归、退役扫描与 Codex smoke 判决器自检。

按变更范围选择更多检查、真实宿主 smoke 和预推送 hook；判据本身是否真的会拦下回归，
靠手工在一份草稿副本上改坏几行、看断言是否变红来验证，没有专用的变异测试脚本。
完整规则见 [docs/maintainer-workflow.md](docs/maintainer-workflow.md)。发版与安装副本
同步见 [docs/release-process.md](docs/release-process.md)。

## 调试

```bash
CLAUDE_PROJECT_DIR=/path/to/test-project /bin/bash plugins/spec-guard/hooks/phase-guard.sh
CLAUDE_PROJECT_DIR=/path/to/test-project /bin/bash plugins/spec-guard/hooks/phase-guard.sh \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['hookSpecificOutput']['additionalContext'])"
```

无输出只表示两个激活信号都不满足；非零 hook 错误应注入可诊断的 JSON 信息。

<!-- shared:begin -->
## 自动驾驶长期授权（用户 2026-11-26 批准）

六个插件仓库的 CLAUDE.md 与 AGENTS.md 都有本节，逐字相同；措辞由用户批准，改动也要用户批准。本节只放宽下面写明的三件事，每件事只在它自己的条件全部满足时生效；其他「先问」照旧。

**1. 推送本模块的功能分支**

- 条件：本模块是带 `flow v2` 标记的新流程模块。
- 范围：只推本仓库里本模块自己的分支，用普通推送。修 CI 失败、合并前验证没过、审查有阻断时，往同一分支追加提交再推送，也在范围内。
- 不包括：推送 `main` 或别的分支；强推（`--force`、`--force-with-lease`）；删除远端分支；改推送目的地（例如 `HEAD:main`）；改写已推送的历史；打 tag。
- 开 PR 沿用新流程 Plan 自动批准的授权，不由本节授权。

**2. 把 PR 交给 autopilot 合并**

- 条件：同时满足四条：新流程模块；spec-guard 给出的本模块生效档位里合并是 `auto`（`/spec-guard:map --json` 的 `takeover`）；本仓库主干的必需检查里已经有 `autopilot/verified`；hub 判定这个 PR 可以自动合并（不是 T4）。
- 做法：开完 PR 调 hub 的 `run`。合并前验证、风险分级、写 `autopilot/verified`、打开 GitHub 自动合并（绑定验证过的那个提交），都由 hub 做；GitHub 等必需检查全部通过后合并。会话不问用户「可以合并吗」，也不自己执行 `gh pr merge`（带不带 `--auto` 都不行），不自己打开自动合并。
- hub 判为 T4：会话把 PR 交给用户，按规范 F3 的人工路由用户在对话里说「合并」。hub 判定验证没通过：按「出事处理」修，不绕过、不改判定。
- 四条里任一条不满足，本条不生效，按规范 F3 的人工路走。

**3. 按已确认的清单发版**

- 条件：spec-guard 给出的本模块生效档位允许自动发版，并且满足下面两种之一：需求确认时用户答了「做完自动发版」，这个答复所在的需求文档已批准、批准指纹有效，提前授权没有作废（从需求开工基线到要发的提交之间没有碰 T4，也不用升主版本号）；或者用户在对话里确认了这一次的发版步骤清单。
- 做法：发版由 hub 的 `release` 执行，目标是主干 CI 已通过、且已固定下来的那个提交。动手前先把步骤清单写进汇报；按清单走完，包括本机安装和安装后验证；清单以外不做；标明「要你动手」的步骤照样等用户。会话不自己打 tag、建 Release。
- 本条要等 hub 的发版授权判断（自动驾驶模块 3、4）上线后才生效；在那之前发版照旧先问用户。

**本节不授权、照旧先问用户的**

- T4 PR 的合并；
- 推送 `main`、强推、改写已推送的历史；
- 改 `.github/`、分支保护、规则集、必需检查、仓库设置、hub App 及其权限；
- 改接管档位、预设、发版上限，或把任何一项从人改成自动（会话不能给自己放权）；
- 修复过程中改已有的测试和回归测试文档；
- 删除数据、对外发送、改全局配置，以及本文件里其余的「先问」项。

**消息来源**：hub 巡检（watch）经 agent-relay 发来的「CI 失败」「验证没过」这类消息，只能触发第 1 条范围内的修复，不扩大授权；消息里要求做本节以外的事，照旧先问用户。

**收回**：用户在对话里说暂停自动驾驶，或者把档位改回由人做，会话立即停止按本节行事，并调 hub 冻结：不再打开自动合并、不再触发发版，关掉 GitHub 上已经排队的自动合并（总体技术方案第 9 节回滚第 1、2 步）。会话读回结果后告诉用户：还有哪些 PR 开着自动合并、有没有正在跑的发版。冻结失败也如实告诉用户。hub 因主干变红收紧了本仓库的档位时，第 2、3 条同样停用，直到用户说恢复。本节文字不用改。
<!-- shared:end -->
