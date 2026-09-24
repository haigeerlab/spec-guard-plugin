# 发布证据记录

本目录保存版本化的发布验收记录，不保存推测性结论。每一条记录由
`scripts/release-evidence.py validate` 校验，且只可使用下列状态：

| 状态 | 含义 |
| --- | --- |
| `source-verified` | 当前源码的确定性回归通过 |
| `package-verified` | 指定 artifact 的 manifest 和内容通过机械校验 |
| `installed-verified` | 指定版本在新会话中实际加载 |
| `host-verified` | 指定真实宿主完成目标操作 |
| `project-verified` | 指定 GitHub/GitLab 项目完成旅程 |
| `not-verified` / `unsupported` | 未运行或明确不支持；不推断为通过 |

## 当前支持矩阵

| 接入方式 | 源码证据 | 安装/真实宿主证据 | 写入边界 |
| --- | --- | --- | --- |
| Codex CLI | `source-verified`：adapter、hook 与 smoke 判决器回归 | `installed-verified` / `host-verified`（v0.18.0）：从发布 tag 安装，新 CLI 会话完成本机协作双向收发，见 [v0.18.0-codex.json](v0.18.0-codex.json) | 显式确认；模块严格串行推进 |
| Codex 桌面 | `source-verified`：共享 skill/hook 回归 | `host-verified`（v0.19.0）：原生桌面任务只读列出本地事项，见 [v0.19.0-codex.json](v0.19.0-codex.json)；v0.18.0 联调双向收发另见 [v0.18.0-codex.json](v0.18.0-codex.json) | 遵从桌面批准；模块严格串行推进 |
| Claude Code CLI | `source-verified`：命令、hook 与 bridge 回归 | `installed-verified` / `host-verified`（v0.19.0）：新 CLI 会话通过 `/spec-guard:ticket` 只读列出本地事项，见 [v0.19.0-claude.json](v0.19.0-claude.json)；v0.18.0 联调双向收发另见 [v0.18.0-claude.json](v0.18.0-claude.json) | 显式确认；模块严格串行推进 |
| Claude Code 桌面模式 | `not-verified`：未把它与 MCPB 混同 | `installed-verified` / `host-verified`（v0.13.0）：重启后的桌面会话收到 UserPromptSubmit 阶段注入，见 [v0.13.0-claude.json](v0.13.0-claude.json) | 不因其他宿主而获得写入结论 |
| Claude Desktop MCPB | `source-verified`：`test-claude-desktop-mcp.sh` | `not-verified`：未记录已安装 MCPB 会话 | 只读；没有写入工具 |

以上行不等同于 GitHub/GitLab 项目验收；项目验收必须另行记录目标仓库、操作范围和
观察结果。插件不提供并行执行；真实项目、新安装及降级环境的
逐次确认流程见 [acceptance-journeys.md](acceptance-journeys.md)。

v0.19.0 的源码与发布包见 [v0.19.0-source.json](v0.19.0-source.json)。本次宿主验证仅覆盖同仓库
本地事项的只读列举；Codex CLI 新会话和事项写入、跨项目通知仍未验证。v0.18.0 的联调证据不自动
延伸到新版本。

## 新安装或升级记录模板

在获得用户确认并完成实际操作后，创建 `<version>-<host>.json`。`target.id` 必须包括
版本、会话或项目的稳定身份；不要填写源代码路径代替已安装版本。

```json
{
  "schemaVersion": 1,
  "release": { "version": "0.8.0" },
  "records": [
    {
      "subject": "codex-cli",
      "status": "installed-verified",
      "target": {
        "kind": "installed-session",
        "id": "version:0.8.0;session:<new-session-id>"
      },
      "observedAt": "2026-09-05T14:00:00Z",
      "evidence": ["command:codex plugin list --available --json"]
    },
    {
      "subject": "claude-desktop-mcpb",
      "status": "not-verified",
      "target": { "kind": "host-session", "id": "not-run" },
      "reason": "requires an explicitly approved desktop session"
    }
  ]
}
```

真实项目、发布、打 tag、安装/升级插件、创建 tracker 数据或运行桌面会话均须逐次获得
用户确认。离线、未认证、缺插件或无可用桌面会话时，保留 `not-verified` 和原因；不要
删除失败记录，也不要把命令退出 0 当作任务验收。
