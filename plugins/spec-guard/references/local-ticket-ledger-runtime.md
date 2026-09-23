# Local ticket ledger runtime（第 1 层）

本参考定义可选、本机、本地事项账本的只读运行时合同。它使用固定的
[`epiq@1.11.0`](https://github.com/ljtn/epiq)（MIT）作为未来的 MCP 后端；它不是 GitHub、GitLab
或现有协作邮箱的替代品。

本层只有合同与诊断。它**不会**下载 Epiq、执行 Epiq、创建 `.epiq/`、修改 Git、写入 Claude/Codex
配置、启动服务，或打开网络端口。

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

## Deliberate boundaries

- 同一个 macOS 用户下，已初始化的同一 Git 仓库 linked worktree 能共享 Epiq 项目身份；独立机器不在本层范围。
- Epiq 事项可自由记录 bug、需求、排查和完成结果；Spec Guard 不据此建立项目组、角色、指派锁或排期。
- 若协作邮箱可用，Agent 可以在自由消息中附 Epiq 短编号；邮箱投递和事项写入仍是两次独立动作。
- GitHub/GitLab 恢复后，不会自动创建、导入或同步远端 Issue。保留本地编号并按需显式关联／迁移是后续能力。
