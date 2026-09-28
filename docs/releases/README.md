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
| Codex CLI | `source-verified`：adapter、hook 与 smoke 判决器回归 | `installed-verified` / `host-verified`（v0.20.1）：官方 marketplace 安装副本的新 CLI 会话收到 UserPromptSubmit 阶段注入，见 [v0.20.1-codex.json](v0.20.1-codex.json) | 显式确认；模块严格串行推进 |
| Codex 桌面 | `source-verified`：共享 skill/hook 回归 | `host-verified`（v0.19.0）：原生桌面任务在无远端临时账本中创建、评论、读取并关闭事项，见 [v0.19.0-codex.json](v0.19.0-codex.json)；v0.18.0 联调双向收发另见 [v0.18.0-codex.json](v0.18.0-codex.json) | 遵从桌面批准；模块严格串行推进 |
| Claude Code CLI | `source-verified`：命令、hook 与 bridge 回归 | `installed-verified` / `host-verified`（v0.20.1）：官方 marketplace 安装副本的新 CLI 会话在隔离消费者项目收到 MAP_ONLY 阶段注入，见 [v0.20.1-claude.json](v0.20.1-claude.json) | 显式确认；模块严格串行推进 |
| ChatGPT in Chrome | 不把浏览器访问冒充为插件 hook 源码证据 | `host-verified`（v0.20.1）：升级后在既有 Chrome profile 中成功读取公开 PR，见 [v0.20.1-codex.json](v0.20.1-codex.json) | 只验证既有浏览器能力未受升级影响；不声明 Codex 桌面 hook |
| Claude Code in Chrome | 不把浏览器访问冒充为插件 hook 源码证据 | `host-verified`（v0.20.1）：升级后通过已安装扩展成功读取公开 PR，见 [v0.20.1-claude.json](v0.20.1-claude.json) | 只验证既有浏览器能力未受升级影响；不声明浏览器侧 spec-guard hook |
| Claude Code 桌面模式 | `not-verified`：未把它与 MCPB 混同 | `installed-verified` / `host-verified`（v0.13.0）：重启后的桌面会话收到 UserPromptSubmit 阶段注入，见 [v0.13.0-claude.json](v0.13.0-claude.json) | 不因其他宿主而获得写入结论 |
| Claude Desktop MCPB | 已于 2026-09-28 退役，见 [退役记录](../retirements/claude-desktop-mcpb.md) | `not-verified`：退役前从未记录已安装 MCPB 会话 | 不再提供 |

以上行不等同于 GitHub/GitLab 项目验收；项目验收必须另行记录目标仓库、操作范围和
观察结果。插件不提供并行执行；真实项目、新安装及降级环境的
逐次确认流程见 [acceptance-journeys.md](acceptance-journeys.md)。

v0.20.1 的源码候选证据见 [v0.20.1-source.json](v0.20.1-source.json)，发布包、tag 与
SHA-256 核对见 [v0.20.1-package.json](v0.20.1-package.json)，安装及真实宿主验收分别见
[v0.20.1-codex.json](v0.20.1-codex.json) 与 [v0.20.1-claude.json](v0.20.1-claude.json)。
源码候选记录保留发布前观察时点，不追写发布后状态；GitHub Actions 自动触发仍未验证，
不阻塞已完成的包、安装与宿主验收。

v0.19.0 的源码与发布包见 [v0.19.0-source.json](v0.19.0-source.json)。三种宿主入口均已验证
同仓库本地事项的只读列举；Codex 桌面还在隔离临时仓库完成了创建、评论、读取、关闭，Claude Code
CLI 读到了其评论与关闭状态，并用完整 ID 创建、评论、关闭了另一条测试事项，Codex 桌面也读回了
结果。安装版 v0.19.0 的短编号直接评论失败；源码中的 `ticket` 指引已修正，尚未作为发布版验收。
Codex CLI 的事项写入、跨项目通知仍未验证。v0.18.0 的联调证据不自动延伸到新版本。

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
