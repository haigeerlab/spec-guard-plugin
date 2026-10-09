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
2. Proposal 生命周期：只读地评审 GitHub / GitLab Proposal Issue，把新需求按锚点插入能力图；
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

- hook 默认不生效；无激活信号的无关项目必须静默退出。
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

提交一律走 `/bin/bash scripts/verify-and-commit.sh -- -m "<信息>"`：只改文档类路径时跑快档（`validate.sh --quick`
与 verify-artifacts），其余跑上面三条（并行，暂存了 `.sh` 时加 ShellCheck），全部通过才提交已暂存的内容，并记下
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
