---
description: 查看或按明确确认启用本地事项账本，并连接 Claude Code／Codex
allowed-tools: Bash, Read
---

这是一个可选的、同机同仓库 linked worktree 共享的持久事项账本入口。它不替代协作邮箱，不是
GitHub/GitLab 的本地克隆，也不包含项目组、角色、派单、排期或自动同步。

普通查看、创建、评论和关闭事项使用 `/spec-guard:ticket`；本命令负责只读状态、显式安装、初始化与
宿主接入。

先定位已安装的 Spec Guard 根目录，并只读检查状态：

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "spec-guard 插件根目录不可用" >&2; exit 2; }
python3 -B "$ROOT/hooks/local_ledger_runtime.py" status --format json
```

- `absent`：Epiq 运行时尚未安装。这是正常的未启用状态；不得自动下载。
- `ready`：受管运行时可用，但当前仓库还没有本地账本。
- `initialized`：当前仓库已有可用的 `.epiq/project.json`，可继续检查 MCP 接入。
- `invalid`：原样说明诊断，不能删除、覆盖或尝试修复现有目录。

只有用户明确要求安装时，才运行：

```bash
python3 -B "$ROOT/hooks/local_ledger_runtime.py" install --confirm-install --format json
```

只有用户明确要求初始化当前仓库时，先运行 `preflight`，说明它会提交 `.epiq/project.json`、创建
`__epiq_state__` 分支；工作树不干净时不得继续。发现 `origin` 时，必须另行向用户解释 Epiq 上游会尝试
推送，并且仅在用户明确许可这一次推送尝试后才追加 `--allow-epiq-push`。`user-name`、
`preferred-editor`、`auto-sync` 不可猜测：向用户索取实际值。

```bash
python3 -B "$ROOT/hooks/local_ledger_runtime.py" preflight --format json
python3 -B "$ROOT/hooks/local_ledger_runtime.py" initialize \
  --confirm-initialize --user-name "用户提供的显示名" \
  --preferred-editor "用户提供的编辑器命令" --auto-sync false --format json
```

初始化或配置任一宿主都不是隐式动作。需要先显示无副作用的配置片段时运行：

```bash
python3 -B "$ROOT/hooks/local_ledger_adapters.py" codex
python3 -B "$ROOT/hooks/local_ledger_adapters.py" claude
```

仅当用户明确指定要为对应宿主写入其用户级 MCP 配置时，才运行下列操作。它们必须带
`--confirm-install`，同名条目已存在时会拒绝覆盖；完成后需重启相应客户端。不得在当前请求中默认执行。

```bash
python3 -B "$ROOT/hooks/local_ledger_adapters.py" install-codex --confirm-install
python3 -B "$ROOT/hooks/local_ledger_adapters.py" install-claude --confirm-install \
  --claude-bin "$(command -v claude)"
```

两个安装命令都会门控 10 个高风险 Epiq 工具（`epiq_sync`、`epiq_project_init`、`epiq_skill_install`、
项目级删除／移除与贡献者邮箱工具）：Claude 写入用户级 `permissions.ask`，逐次确认；Codex 片段的
`enabled_tools` 白名单不包含它们。此前已接入的宿主只有在用户明确要求时才迁移：Claude 运行
`install-claude-guard --confirm-install`；Codex 把 `codex` 打印的 `enabled_tools` 行手动加入现有表。
细节见 `references/local-ticket-ledger-runtime.md`。

接入后的 Agent 可以通过 Epiq MCP 工具用可读名字和当前工作作自由自我说明，先查询可能相关的事项，再按
需要创建 bug、需求、排查记录或完成说明。不要把标签、负责人或状态解释成访问控制或硬性流程。若协作邮箱
也可用，消息可以携带事项短编号，例如“`R85YPWB` 已处理，请拉取后验证”；消息投递和事项改动仍是两个
独立、明确的动作。

GitHub/GitLab 恢复后，本功能不会自动创建、导入或同步远端 Issue；保留本地事项编号作为引用，是否迁移须由
后续独立设计决定。详细安全边界见 `references/local-ticket-ledger-runtime.md`。

本阶段没有“删除账本”命令。不得为了停用而删除 `.epiq/`、`__epiq_state__`、受管运行时或 MCP 条目；这些
动作会影响持久记录或其他项目，必须由单独的、可审查的移除设计处理。
