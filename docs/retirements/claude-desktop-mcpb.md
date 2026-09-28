# 退役：Claude Desktop MCPB

状态：已退役（2026-09-28，用户决定）。

## 退役的是什么

`plugins/spec-guard/manifest.json` 与 `mcp/claude_desktop_server.mjs` 组成的 MCP Bundle，为 Claude Desktop 的
普通对话界面提供 5 个只读工具：`phase`、`verify`、`verify_history`、`audit_history`，以及只会拒绝的
`write_operation`。它由 initiative 70 引入，规格见 `spec/history/70/20260903T185103Z-0001/claude-desktop-mcp.md`。

## 为什么退役

- 没有人在更新它：2026-09-28 本机安装的 Desktop 扩展仍是 0.7.51，当时源码是 0.20.1；安装副本还带着早已删除的
  `sync_map_preview`。
- 它从未进入发布流程：`docs/release-process.md` 不打 `.mcpb` 包，也没有任何已安装 MCPB 会话的发布证据。
- 它不是能力图中的模块，却要单独维护清单、版本检查与回归测试。
- 需要这些检查的场景都有其他入口：Claude Code（包括 Claude 桌面应用的 Code 标签页）用斜杠命令与 hook，
  Codex 用 `spec-guard-ops` skill。Claude Desktop 的普通对话界面不在本插件的目标宿主内。

## 移除的内容

- `plugins/spec-guard/manifest.json`、`plugins/spec-guard/mcp/`、`plugins/spec-guard/.mcpbignore`
- `hooks/test-claude-desktop-mcp.sh` 及其在 `scripts/validate.sh` 中的调用
- `scripts/check-manifests.py` 对 Desktop 清单的名称与版本检查及其检查器用例
- `scripts/release-package.py` 对制品中 `manifest.json` 的要求，`evals/test-public-metadata.sh` 对它的断言
- `docs/claude-desktop.md`

历史发布记录（`docs/releases/*.json`）与研究材料保持原样，只作为历史证据。

## 迁移

- 已安装扩展的用户：在 Claude Desktop 的 **Settings → Extensions** 中卸载 spec-guard。它是只读的，卸载不影响
  任何项目文件。
- 需要阶段与产物检查：在 Claude Code 中用 `/spec-guard:phase`、`/spec-guard:verify-artifacts`、
  `/spec-guard:history-integrity`；在 Codex 中用 `spec-guard-ops`。
