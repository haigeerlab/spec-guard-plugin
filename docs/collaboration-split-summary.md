# 协作能力拆分：总结（2026-10-08）

对应 [docs/collaboration-split-brief.md](collaboration-split-brief.md) 的“最终交付物”最后一项。

## 结论

**接入成功。** agent-relay 0.2.0（加固版，接口 1.0）已发布；Spec Guard 0.50.0 起不再自带协作能力，只通过
`agent_relay_probe.py` 检测 agent-relay（接受接口 `>=1.0,<2.0`），当前为 0.51.3。两轮真实宿主联调与两次定向验收，
对照 `docs/acceptance/checklist.md` 的加固目标栏全部通过；有两项正向路径是在临时 home 里验证的，用户已认可（见“遗留风险”）。

| 版本 | 日期 | 内容 |
|---|---|---|
| agent-relay 0.1.0 | 2026-10-07 | 平移版：行为与拆分前 Spec Guard 0.49.0 的协作能力一致 |
| Spec Guard 0.50.0 | 2026-10-07 | 移除协作实现，保留 `/spec-guard:collaboration` 作为转交入口与迁移指引 |
| agent-relay 0.2.0 | 2026-10-08 | 加固版：12 个模块，修复第一、二轮联调发现 |

宿主版本：Claude Code 2.1.291；codex-cli 0.160.0（ChatGPT.app 26.930.61225 内置 0.160.1）。

本机最终状态（2026-10-08，agent-relay 5d12346 = v0.2.0）：preflight 显示 Claude 加载的源目录与 Codex 缓存 0.2.0 都是
`current`；`doctor` 的 runtime、probe（node v24.18.0，17 个工具）、mailbox（schema 5）、host-entries、old-bridges 为 `ok`，
两条 `warn` 是下面“遗留风险”第 2、6 条的已知情况，不是 0.2.0 引入的。

## 改了什么

**Spec Guard**（haigeerlab/spec-guard-plugin）

- Proposal `spec/proposals/collaboration-split.md`（Issue #221，已晋级并关闭）只记录能力图决定；
  `collaboration-interface`、`collaboration-boundary`、`collaboration-extraction`、`collaboration-dependency` 四个模块完成拆分。
- 协作代码连同逐文件历史迁到 agent-relay（git filter-repo）；Spec Guard 删除 33 个路径，
  `scripts/check-collaboration-boundary.py` 防止协作实现回流。
- 新增 `agent_relay_probe.py`（只读，失败报 `unknown`）；迁移文档 `docs/migrations/2026-10-07-collaboration-split.md`。

**agent-relay**（haigeerlab/agent-relay，PR #1–#17）

- 平移：acceptance-kit、mailbox-core、session-routing、cross-host-delegation、packaging、state-migration。
- 加固：delegation-fixes、test-isolation、bridge-vendoring、delivery-state-machine、durable-ordering、idempotency、
  identity-check、ops-commands、safe-uninstall，以及联调后补的 round2-fixes、acceptance-kit-round2、adapter-node。
  信箱 schema 2 → 5；上游 bridge（8f12c88，MIT）收进仓库；`doctor` 一次只读体检；卸载流程保留历史。

## 交付物位置

| 交付物 | 位置 |
|---|---|
| 新插件仓库（含能力图、18 个模块的 Spec / plan / todo、acceptance-kit） | `haigeerlab/agent-relay`（公开，tag v0.1.0、v0.2.0） |
| Spec Guard 拆分记录（Proposal、四个模块） | `haigeerlab/spec-guard-plugin` main |
| 拆分前备份分支 | 本地 `backup/pre-collaboration-split` |
| 基线 | `docs/baselines/collaboration-pre-split.md` |
| 接口文档（现状与加固目标） | `docs/collaboration-interface.md`（两个仓库各一份） |
| 迁移文档、CHANGELOG | `docs/migrations/2026-10-07-collaboration-split.md`；两个仓库的 `CHANGELOG.md` |
| 验收清单 | agent-relay `docs/acceptance/checklist.md` |
| 联调与验收记录 | agent-relay `docs/acceptance/`：`2026-10-07-round1.md`（平移版，用户判定通过）、`2026-10-07-round2.md`、`2026-10-07-round2-rerun.md`、`2026-10-08-acceptance-kit-round2.md` |

“新插件仓库与拆分分支本地、不 push”是简报阶段的约定；用户在第一轮联调后决定公开发布，两者现在都在 GitHub 上。

## 遗留风险

1. **两条正向路径没在真实宿主上跑。** 在关掉所有会话的真实宿主上做 `uninstall-claude`（R2-10）和保留历史重装
   （D57），只在临时 home 里验证过；真实宿主上验证的是“有会话开着时拒绝”。用户已认可。
2. **Codex 默认设置下没有唤醒。** 本机 `approvals_reviewer = "guardian_subagent"` 被视为自动审批：Codex 的唤醒绑定
   被拒、ping 暂存。要唤醒 Codex 需在 App 里切到“请求批准”，而 App 选择器不写 `config.toml`（R2-2），doctor 以文件为准。
3. **Claude 后续轮次靠 stop + `--resume`。** 生产环境没有原生唤醒，每一轮都可能与 MCP 连接赛跑；round2-fixes 让目标
   等信箱工具就绪再作答，定向复跑 8/8 通过，但这是时序上的缓解，不是消除。
4. **旧 node 的 shell。** PATH 首位是 v12 时 codex CLI 本身起不来，preflight 的 Codex 一栏显示 `unknown`；
   agent-relay 自己的命令都按 D50 顺序选 node，node 过旧时在写任何东西前拒绝。
5. **agent-relay 没有 CI。** 每个 PR 写明本机在 Python 3.9.6 / 3.10.7 / 3.14.3 上的 validate 结果。
6. **本机遗留**（都无害，删不删由用户决定）：测试身份 `ar-acc-round2-design-claude-wt`（1 条未确认）；
   委派信封 `r2-cx-review` e168ea / 269770 停在 unknown；`~/.agent-relay/backups/` 下 4 份只含临时配置的测试备份
   （20261007T163248Z、20261007T163259Z-1、20261007T164520Z、20261007T164520Z-1）；
   Claude 的 7 条 agent-relay 安装记录指向未使用的缓存副本（directory marketplace 从源目录加载，preflight 标为 not loaded）；
   本地账本事项 4G6J987 归 agent-relay。
7. **其他已知限制**（CHANGELOG 0.2.0）：schema 3 之前的旧消息显示为 `queued`；多个 Codex 线程共用一个 bridge 进程时
   共享已证明的身份名。

## 发布顺序

已按此顺序发布：agent-relay 0.1.0 → Spec Guard 0.50.0 → agent-relay 0.2.0。

已有用户的升级建议：

1. Spec Guard 升到 ≥ 0.50.0 与 agent-relay 的版本互不依赖（接口 1.x 内兼容）。
2. 从 Spec Guard 0.49.0 的协作能力迁移：装 agent-relay 后按迁移文档执行 `state_migration.py detect`，再
   `migrate --confirm`（有未结束的旧委派或旧 bridge 在跑时会拒绝）。
3. agent-relay 0.1.0 → 0.2.0：关闭所有用信箱的会话并退出 Codex → `upgrade --confirm`（schema 2 → 5，先备份）→
   两个宿主同时更新插件（Codex 先把 marketplace 的 `ref` 改成 v0.2.0 再 `marketplace upgrade`）→ `doctor` → 各会话重新注册。
   运行时与插件必须一起升级或一起回滚。
4. 以后接口要升到 2.0 时，先发 Spec Guard 放宽 `agent_relay_probe.py` 的范围，再发 agent-relay。
