# 退役：协作实现模块（移到 agent-relay）

状态：已移出当前能力图（2026-10-08，用户确认；模块 `collaboration-map-retirement`，2026-10-08 架构审查 F6）。

## 退役的是什么

四个协作实现模块，它们的代码已在 `collaboration-extraction` 与 `collaboration-dependency` 中迁到独立插件
agent-relay，Spec Guard 只剩 `agent_relay_probe.py` 探测和 `/spec-guard:collaboration` 转交：

| 模块 | 内容 |
|---|---|
| `collaboration-messaging` | 同机私有邮箱与 Claude Code／Codex 宿主适配 |
| `collaboration-safe-defaults` | 默认不绑定唤醒、自动批准会话禁止绑定的安全边界 |
| `authorized-session-delegation` | 按明确授权创建与协调受限的审查／开发会话 |
| `host-native-session-routing` | 同宿主原生双向通道的选择与回退 |

它们仍是当前能力图的行，与 AGENTS.md「退役 Spec 与 Plan 位于 `docs/retirements/`，不加入当前能力图」和
`retired-module-separation` 的先例相冲突；现在从模块表与 Build order 中同时移除。`audit-remediation` 去掉对
`collaboration-messaging` 的依赖，`collaboration-interface` 不再依赖任何模块。

## 用什么代替

- 协作能力：agent-relay 插件（会话通信、受限会话委派、原生路由）。在 Spec Guard 里运行
  `/spec-guard:collaboration` 会检查它是否可用并给出安装与迁移指引。
- 公开接口与拆分对照：仍在当前能力图的 `collaboration-interface`、`collaboration-boundary`、
  `collaboration-extraction`、`collaboration-dependency`。

## 历史材料

每个模块的原 Spec 与全部任务文件（Plan、todo、验收与预检记录）用 `git mv` 逐字归档在
`docs/retirements/<模块 id>/`：Spec 为 `spec.md`，其余保持原文件名。只作历史证据，其中的路径、命令与要求不再适用，
文件内指向旧路径的链接不改写。`spec/proposals/`、`spec/history/`、`spec/CAPABILITY-HISTORY.json`、发布证据与
CHANGELOG 中的旧记录不改写；现行 Spec 与 Plan 里提到旧路径的文字同样作为历史保留。
