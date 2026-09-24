# Local ticket ledger runtime（第 1 层）

本参考定义可选、本机、本地事项账本的只读运行时合同。它使用固定的
[`epiq@1.11.0`](https://github.com/ljtn/epiq)（MIT）作为未来的 MCP 后端；它不是 GitHub、GitLab
或现有协作邮箱的替代品。

默认的合同、状态与预检入口只读。只有用户明确执行写入操作时，才可能下载 Epiq 或准备初始化；它们仍不
写入 Claude/Codex 配置、启动服务或打开网络端口。

## 固定合同

| Field | Value |
| --- | --- |
| Package | `epiq` |
| Package version | `1.11.0` |
| Node prerequisite | Node.js 18+ |
| MCP entrypoint | `node_modules/epiq/dist/mcp.js` |
| Managed default directory | `~/.spec-guard/local-ticket-ledger/runtime/` |
| Project identity | `.epiq/project.json` |
| Epiq state branch | `__epiq_state__` |

运行时安装和项目初始化属于后续显式操作；插件安装、hook 和项目打开均不得隐式触发它们。

## Read-only diagnostics

从已安装的 Spec Guard 根目录执行：

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "spec-guard 插件根目录不可用" >&2; exit 2; }
python3 -B "$ROOT/hooks/local_ledger_runtime.py" status --format json
```

可用状态：

- `absent`：受管 Epiq 运行时尚未安装；这不是错误，也不会创建目录。
- `ready`：固定版本运行时与 Node 前置条件可用，但当前项目未初始化账本。
- `initialized`：运行时可用，当前项目的已提交 `.epiq/project.json` 合法。
- `invalid`：已存在的运行时、Node 或项目配置不符合合同；诊断说明原因，调用方不得删除、覆盖或放宽校验。

输出将 `node`、`runtime` 和 `project` 分开报告，避免把“Node 缺失”“未安装运行时”和“项目尚未初始化”
混成一个原因。诊断只读取文件与 `node --version`；它不读取 token，因为本事项账本没有项目级 secret。

可单独查看固定合同：

```bash
python3 -B "$ROOT/hooks/local_ledger_runtime.py" contract --format json
```

## Explicit runtime installation

安装固定运行时会下载 Epiq 及其 Node 依赖（隔离 POC 约为 119 MB），因此绝不会由状态检查、hook、
项目打开或 MCP 配置自动触发。用户确认后才执行：

```bash
python3 -B "$ROOT/hooks/local_ledger_runtime.py" install --confirm-install --format json
```

它只调用固定的 `npm install --ignore-scripts --prefix <managed-runtime> epiq@1.11.0`，并在完成后重新
核对包名、版本和 `epiq-mcp` 入口。运行时存放在用户级受管目录，绝不写入项目 `node_modules`。

- 没有 `--confirm-install` 时返回 `install-confirmation-required`，不创建目录也不调用 npm。
- 已安装且合同正确的目录拒绝覆盖；已存在但不合法的目录也拒绝覆盖，供用户先审查或显式清理。
- 安装本身不初始化任何项目、不写 Git、不添加 Claude/Codex MCP 配置，也不启动 Epiq。

## Initialization preflight

Epiq 的上游 `epiq_project_init` 会尝试推送普通分支和其状态分支。Spec Guard 因此先提供只读预检：

```bash
python3 -B "$ROOT/hooks/local_ledger_runtime.py" preflight --format json
```

预检只读取 Git worktree 状态与 `origin` URL：

- `ready` + `origin: null`：Git 工作树干净且没有 `origin`。后续显式初始化可以继续；Epiq 仍会尝试
  `origin` 推送，但会作为本地可用的警告失败。
- `push-confirmation-required`：发现 `origin`。不会启动 Epiq；必须让用户为本次初始化单独确认其上游
  推送行为。`--allow-epiq-push` 仅表达该确认给后续显式初始化操作，单独运行预检不会写入或推送。
- `dirty`：工作树含改动，拒绝初始化。
- `not-git` 或 `invalid`：无法取得安全预检所需的 Git 事实。

这条门槛防止“为了启用本地 fallback”意外把 `.epiq/project.json` 或 `__epiq_state__` 推送到已有远端。
它不验证远端是否可达，也不把缺少网络解释为安全许可。

预检通过、运行时已安装后，才可由用户显式初始化：

```bash
python3 -B "$ROOT/hooks/local_ledger_runtime.py" initialize \
  --confirm-initialize \
  --user-name "你的显示名" \
  --preferred-editor "code --wait" \
  --auto-sync false \
  --format json
```

`user-name`、`preferred-editor` 和 `auto-sync` 是 Epiq 首次在当前 macOS 用户下保存的偏好；Spec Guard
不会猜测或代填它们。若预检显示已有 `origin`，还必须明确增加 `--allow-epiq-push`。该标记只允许本次
Epiq 上游初始化尝试推送，不能表示远端操作已经成功；输出只报告是否有警告，不回显上游原始 Git 错误。

成功后 Epiq 会提交 `.epiq/project.json`、创建 `__epiq_state__` 状态分支，并在同一 macOS 用户的 linked
worktree 间共享状态。它不会安装 Claude/Codex MCP 配置；那是独立的后续明确操作。

## Explicit host MCP adapters

安装 Epiq 或初始化项目都不会改变 Claude Code、Codex Desktop 或 ChatGPT in Chrome。先可只读地生成每个
宿主的 stdio 配置片段：

```bash
python3 -B "$ROOT/hooks/local_ledger_adapters.py" codex
python3 -B "$ROOT/hooks/local_ledger_adapters.py" claude
```

它们都指向已验证的受管 `node` 和固定 `epiq` MCP 入口，不包含 token、HTTP 地址、账本内容或项目 secret。
只有用户明确要求写入某一个宿主的用户级配置时，才可运行相应安装命令，而且仍必须带第二层
`--confirm-install`：

```bash
python3 -B "$ROOT/hooks/local_ledger_adapters.py" install-codex --confirm-install
python3 -B "$ROOT/hooks/local_ledger_adapters.py" install-claude --confirm-install \
  --claude-bin "$(command -v claude)"
```

Codex 安装只原子追加 `[mcp_servers.spec_guard_local_ledger]` 表；Claude 安装只通过
`claude mcp add --scope user` 添加同名 stdio server。两者若发现同名条目都会拒绝覆盖，并且客户端重启后才会
加载。Spec Guard 不使用 Codex managed app-server，因此不会影响 ChatGPT in Chrome。

本阶段没有自动或手动的账本移除命令。不得把移除 MCP 配置理解为删除事项，也不得删除 `.epiq/`、
`__epiq_state__` 或受管运行时来“重置”项目；这些路径可能承载其他 worktree 的持久记录，任何移除能力都必须
另立可审查设计。

接入后可以由 Agent 自由地做可读自我说明、查询已有事项，再记录 bug、需求、排查或完成结果。不是强制工作流；
也不会自动分配、路由或要求任何状态。可选协作邮箱消息可以包含事项短编号，但消息投递与 Epiq 写入始终分离。

## 日常事项入口

启用后，在 Claude Code 使用 `/spec-guard:ticket`，在 Codex 直接说“查看本地事项”“记个 bug”或
“给事项加评论”。Agent 使用同一个 `ticket` skill 调用 Epiq MCP；用户不需要填写 MCP 工具名、
看板或泳道 ID。短编号可以在同一仓库的其他 linked worktree 中读取。

例如：“记个 bug：测试环境的接口响应异常，并告诉另一位 Agent 复查。”Agent 先在当前仓库
创建事项，再单独通过 `collab` 发送带短编号的消息，并分别报告账本写入和消息投递结果。若收件人
属于另一个仓库，消息还需说明来源项目和问题内容；仅有本仓库的短编号不足以让对方读取事项。

账本不可用时，日常入口只做状态诊断并给出下一步；安装、初始化、宿主配置仍由
`local-ticket-ledger-ops` 显式执行。

## Deliberate boundaries

- 同一个 macOS 用户下，已初始化的同一 Git 仓库 linked worktree 能共享 Epiq 项目身份；独立机器不在本层范围。
- Epiq 事项可自由记录 bug、需求、排查和完成结果；Spec Guard 不据此建立项目组、角色、指派锁或排期。
- 若协作邮箱可用，Agent 可以在自由消息中附 Epiq 短编号；邮箱投递和事项写入仍是两次独立动作。
- GitHub/GitLab 恢复后，不会自动创建、导入或同步远端 Issue。保留本地编号并按需显式关联／迁移是后续能力。
