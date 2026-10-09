# 协作能力拆分为 agent-relay（2026-10-07）

Spec Guard 内置的协作能力——本机协作信箱、统一会话路由、跨宿主会话委派——移到了独立插件 **agent-relay**。
Spec Guard 的工作流（Spec、计划、阶段提示、Proposal、事项账本等）不受影响；不用协作的人什么都不用做。

## 为什么拆

- 只想让会话互相通信的项目（例如设计项目）不必装 Spec Guard 的工作流。
- 通信层跟着 Claude Code／Codex 的原生接口走，迭代节奏和工作流不同，分开发版互不牵连。
- 唤醒与授权是安全敏感部分，单独审计、单独测试。
- 协作需要 macOS 与 Node.js，只用工作流的人不再背这些依赖。

## 变了什么

| 以前（Spec Guard ≤ 0.49.0） | 现在 |
|---|---|
| `/spec-guard:collaboration`、`collab`、`collaboration-ops`、`session-routing`、`session-delegation` skill | agent-relay 的 `/agent-relay:collaboration` 与同名 skill（`agent-relay:collab` 等） |
| MCP 服务 `spec-guard-native-collaboration`（Claude）、`[mcp_servers.spec_guard_native_collaboration]`（Codex） | `agent-relay`、`[mcp_servers.agent_relay]` |
| 权限规则 `mcp__spec-guard-native-collaboration__bridge_*` | `mcp__agent-relay__bridge_*`（十个 `bridge_*` 工具名不变） |
| 运行时与信箱 `~/.spec-guard/native-collaboration/` | `~/.agent-relay/runtime/` |
| 委派记录 `~/.spec-guard/session-delegation/` | `~/.agent-relay/delegation/` |

`/spec-guard:collaboration` 在 0.50.0–0.53.x 期间作为转交入口保留，0.54.0 已移除；协作入口一律用 agent-relay
自己的命令。

## 版本与兼容

- Spec Guard 0.50.0 起不再自带协作能力，只通过只读的 `agent_relay_probe.py` 检测 agent-relay，接受接口
  `>=1.0,<3.0`（0.56.0 起；此前为 `>=1.0,<2.0`）；检测失败报 `unknown`，不当作“未安装”。
- 两者版本互不依赖：接口 1.x、2.x 内，各自升级即可。
- 发布顺序是 agent-relay 0.1.0（平移版，行为与拆分前 Spec Guard 0.49.0 一致）→ Spec Guard 0.50.0 → agent-relay
  0.2.0（加固版，信箱 schema 2 → 5）。agent-relay 自身的升级步骤（例如 0.1.0 → 0.2.0 要先关掉用信箱的会话、
  `upgrade --confirm`、两个宿主同时更新插件，运行时与插件一起升级或一起回滚）以 agent-relay 的 CHANGELOG 为准。
- 以后接口要升到 2.0 时，先发 Spec Guard 放宽 `agent_relay_probe.py` 的范围，再发 agent-relay。

## 迁移步骤

1. **安装 agent-relay**（Codex 的 `--ref` 请换成 agent-relay README 里写的当前版本）。

   ```bash
   claude plugin marketplace add haigeerlab/agent-relay
   claude plugin install agent-relay@agent-relay-marketplace
   codex plugin marketplace add haigeerlab/agent-relay --ref v0.1.0
   codex plugin add agent-relay@agent-relay-marketplace
   ```

2. **安装 agent-relay 的运行时**（在你同意后）：在 Claude Code 运行 `/agent-relay:collaboration`，或在 Codex 让
   `collaboration-ops` skill 处理。它会建一个全新的、空的 `~/.agent-relay/runtime/`。

3. **检查旧数据（只读）：**

   ```bash
   python3 -B <agent-relay 插件目录>/hooks/state_migration.py detect
   ```

   它列出旧信箱与委派记录的数量，以及挡住迁移的原因：
   - 还没结束、且已经启动过的委派：先在旧版里跑完或取消；
   - 还没结束、但从没启动过的委派：确认它已无用后，迁移时加 `--acknowledge-stale <id>`；
   - 仍在运行的旧信箱服务：关掉或重启挂着旧 MCP 条目的会话；
   - agent-relay 运行时没装或信箱不是空的：它只迁到全新的 agent-relay，从不合并两个信箱。

4. **迁移：**

   ```bash
   python3 -B <agent-relay 插件目录>/hooks/state_migration.py migrate --confirm [--acknowledge-stale <id>]
   ```

   先备份到 `~/.agent-relay/backups/<时间>/`，再复制到 agent-relay，逐表核对数量。旧目录原样保留。

5. **切换宿主条目：** 用 agent-relay 的 `collaboration-ops` 接入新条目（`install-claude`／`install-codex`）。确认新条目可用后，
   删除旧条目——Spec Guard 0.49.0 的卸载命令已随拆分移除，所以手动做，只删这两处，别的配置不要动：
   - Claude Code：`claude mcp remove --scope user spec-guard-native-collaboration`
   - Codex：在 `~/.codex/config.toml` 里删除 `[mcp_servers.spec_guard_native_collaboration]` 及其
     `[mcp_servers.spec_guard_native_collaboration.env]` 两段（改之前先复制一份备份）。

6. **改权限规则：** 项目 `.claude/settings.json` 里预批准的 `mcp__spec-guard-native-collaboration__bridge_*` 改成
   `mcp__agent-relay__bridge_*`。Spec Guard 与 agent-relay 都不会替你改权限文件。

7. **清理（可选）：** 确认 agent-relay 一切正常后，`~/.spec-guard/native-collaboration/` 与
   `~/.spec-guard/session-delegation/` 可以由你自己删除；迁移时的备份在 `~/.agent-relay/backups/`。

## 不迁移的东西

- `~/.spec-guard/collaboration/`：早已退役的 XATS 传输留下的历史，不迁移，也不删除。
- 本地事项账本（`~/.spec-guard/local-ticket-ledger/` 等）属于 Spec Guard，留在原处。

## 参考

- agent-relay 的 README 与接口文档（`docs/collaboration-interface.md`，以 agent-relay 仓库里的那份为准）。
- 拆分前基线：[`docs/baselines/collaboration-pre-split.md`](../baselines/collaboration-pre-split.md)。拆分过程的
  简报与总结已从仓库删除，可在 git 历史中查看（删除于 docs-reorganization 模块）。
