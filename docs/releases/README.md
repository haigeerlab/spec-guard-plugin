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
| Codex CLI | `source-verified`：adapter、hook 与 smoke 判决器回归 | `installed-verified` / `host-verified`（v0.45.0）：codex-cli 0.160.0，`ref` 行改到 v0.45.0 后 `codex plugin marketplace upgrade` 退出 0，临时消费者项目 smoke 退出 0，见 [v0.45.0-codex.json](v0.45.0-codex.json)；v0.44.0 记录：codex-cli 0.160.0，`ref` 行改到 v0.44.0 后 `codex plugin marketplace upgrade` 退出 0，临时消费者项目 smoke 退出 0，见 [v0.44.0-codex.json](v0.44.0-codex.json)；v0.43.0 记录：codex-cli 0.160.0，`ref` 行改到 v0.43.0 后 `codex plugin marketplace upgrade` 退出 0，临时消费者项目 smoke 退出 0，见 [v0.43.0-codex.json](v0.43.0-codex.json)；v0.42.0 记录：codex-cli 0.160.0，改 `~/.codex/config.toml` 的 `ref` 行到 v0.42.0 后 `codex plugin marketplace upgrade`，临时消费者项目 smoke 退出 0，见 [v0.42.0-codex.json](v0.42.0-codex.json)；v0.41.0 记录：codex-cli 0.160.0，marketplace 重钉到 v0.41.0 后 `codex plugin add` 升级安装副本，临时消费者项目 smoke 退出 0，见 [v0.41.0-codex.json](v0.41.0-codex.json)；v0.40.0 记录：app-managed CLI 0.160.0 使用默认模型的仓库 smoke 退出 0，见 [v0.40.0-codex.json](v0.40.0-codex.json)；PATH 旧版 0.154.0 未用于本结论 | 显式确认；模块严格串行推进 |
| Codex 桌面 | `source-verified`：共享 skill/hook 回归 | `host-verified`（v0.40.0）：安装版 native-only 会话完成两轮 Claude→Codex 回传及一次 Codex→Claude→Codex 同线程闭环，见 [v0.40.0-codex.json](v0.40.0-codex.json)；MAP_ONLY hook 证据仍见 v0.38.3 | 遵从桌面批准；模块严格串行推进 |
| Claude Code CLI | `source-verified`：命令、hook 与 bridge 回归 | `installed-verified` / `host-verified`（v0.45.0）：`claude plugin update` 升到 0.45.0（gitCommitSha 即 tag 提交），headless 在系统 python 3.9 下注入 `BUILDING`；安装副本的 cost-report 在 ledgerlite 联调运行上给出与 tier-guard 一致的整次运行金额，见 [v0.45.0-claude.json](v0.45.0-claude.json)；v0.44.0 记录：`claude plugin update` 升到 0.44.0（gitCommitSha 即 tag 提交），用安装副本 `setup-convention --dispatch` 建项目后 headless 注入 `BUILDING` 并逐字复述规则段，见 [v0.44.0-claude.json](v0.44.0-claude.json)；v0.43.0 记录：`claude plugin update` 升到 0.43.0（gitCommitSha 即 tag 提交），headless 在系统 python 3.9 下注入 `BUILDING`，带 no-todo 声明的模块计入 Done、不再出现 `Plan without todo` 行，见 [v0.43.0-claude.json](v0.43.0-claude.json)；v0.42.0 记录：`claude plugin update` 升到 0.42.0（安装副本的 gitCommitSha 即 v0.42.0 的 tag 提交，且含本版新增的 `hooks/defect_guard.py`），headless 运行在系统 python 3.9 下注入 `BUILDING`，见 [v0.42.0-claude.json](v0.42.0-claude.json)；`installed-verified`（v0.41.0）：Claude Code 2.1.286 升级到 0.41.0 后，新进程的阶段注入含本版特有的净化行为，见 [v0.41.0-claude.json](v0.41.0-claude.json)；native repeat-wake `host-verified`（v0.41.0）：同一活会话被连续唤醒两次，两个 wake job 均 `read`、`attempts: 1`；`host-verified`（v0.40.0）：同一 Claude 会话被连续两次唤醒，随后完成反向消息的读取、确认和回复，见 [v0.40.0-claude.json](v0.40.0-claude.json)；MAP_ONLY hook 证据仍见 v0.38.3 | 显式确认；模块严格串行推进 |
| ChatGPT in Chrome | 不把浏览器访问冒充为插件 hook 源码证据 | `host-verified`（v0.20.1）：升级后在既有 Chrome profile 中成功读取公开 PR，见 [v0.20.1-codex.json](v0.20.1-codex.json) | 只验证既有浏览器能力未受升级影响；不声明 Codex 桌面 hook |
| Claude Code in Chrome | 不把浏览器访问冒充为插件 hook 源码证据 | `host-verified`（v0.20.1）：升级后通过已安装扩展成功读取公开 PR，见 [v0.20.1-claude.json](v0.20.1-claude.json) | 只验证既有浏览器能力未受升级影响；不声明浏览器侧 spec-guard hook |
| Claude Code 桌面模式 | `not-verified`：未把它与 MCPB 混同 | `host-verified`（v0.38.3）：新 Code 模式会话在合成项目收到 UserPromptSubmit 的 MAP_ONLY 阶段注入，见 [v0.38.3-claude.json](v0.38.3-claude.json) | 不因其他宿主而获得写入结论 |
| Claude Desktop MCPB | 已于 2026-09-28 退役，见 [退役记录](../retirements/claude-desktop-mcpb.md) | `unsupported`：v0.38.3 不交付 MCPB；退役前从未记录已安装 MCPB 会话 | 不再提供 |

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

v0.39.0 的源码、发布包与两端安装记录见
[`v0.39.0-source.json`](v0.39.0-source.json)、
[`v0.39.0-package.json`](v0.39.0-package.json)、
[`v0.39.0-claude.json`](v0.39.0-claude.json) 与
[`v0.39.0-codex.json`](v0.39.0-codex.json)。A10 的分项对账见
[`v0.39.0-a10.json`](v0.39.0-a10.json)：双向收发和空闲唤醒通过，但回退演练因既有邮箱状态安全阻断，
所以该版本当前不计 R1，连续版本计数仍为 0/2。

v0.40.0 的发布后证据见
[`v0.40.0-source.json`](v0.40.0-source.json)、
[`v0.40.0-package.json`](v0.40.0-package.json)、
[`v0.40.0-claude.json`](v0.40.0-claude.json)、
[`v0.40.0-codex.json`](v0.40.0-codex.json) 与
[`v0.40.0-a10.json`](v0.40.0-a10.json)。该版本按 2026-10-04 的 native-only 决策验收：同一台 Mac
上的安装版完成双向收发、确认回执和同一 Claude 会话的重复空闲唤醒；兼容回退和第二台 Mac 不再属于产品
门槛。v0.39.0 的旧 R1 结论继续作为当时时点事实保留，不反向改写。

v0.41.0 的源码、发布包与两端安装记录见
[`v0.41.0-source.json`](v0.41.0-source.json)、
[`v0.41.0-package.json`](v0.41.0-package.json)、
[`v0.41.0-claude.json`](v0.41.0-claude.json) 与
[`v0.41.0-codex.json`](v0.41.0-codex.json)。该版本新增的三条**写入**能力 ——
Proposal 收尾、Proposal 的 Local 后端、项目级默认事项后端 —— 当时没有留下任何证据记录；
2026-10-05 的只读项目审计发现了这个缺口，现补记为
[`v0.41.0-write-paths.json`](v0.41.0-write-paths.json)，三条均为 `not-verified` 并写明原因。
按本文件的约定，这是**新增**一份未验证记录，不反向改写已有的四份；补记本身不改变任何结论，
也不把回归或变更日志里的叙述当成宿主验收。改动日志中 2026-10-04 的真实运行是**修复前**代码的
观察，不作为已发布行为的证据。

v0.42.0 的发布后证据见
[`v0.42.0-source.json`](v0.42.0-source.json)、
[`v0.42.0-package.json`](v0.42.0-package.json)、
[`v0.42.0-claude.json`](v0.42.0-claude.json)、
[`v0.42.0-codex.json`](v0.42.0-codex.json) 与
[`v0.42.0-write-paths.json`](v0.42.0-write-paths.json)。本版是 2026-10-05 只读项目审计的交付：
23 处吞掉型宽捕获按各模块能支持的方式收窄（全仓库 24 → 1），新增共享的 `hooks/defect_guard.py`，
并带一条行为变更——这些路径里潜藏的代码缺陷现在以 traceback 暴露，不再是柔和的
`unknown` / `partial` / `publication-uncertain`。那几条写入路径仍没有宿主级写入验收，
按本文件的约定补记为 `not-verified` 并写明现有覆盖是注入式与假传输，不反向改写 v0.41.0 的同类记录。

v0.43.0 的发布后证据见
[`v0.43.0-source.json`](v0.43.0-source.json)、
[`v0.43.0-package.json`](v0.43.0-package.json)、
[`v0.43.0-claude.json`](v0.43.0-claude.json) 与
[`v0.43.0-codex.json`](v0.43.0-codex.json)。本版新增 plan.md 中的 `<!-- spec-guard: no-todo -->`
声明：有意不建 todo 的模块不再出现在 plan-without-todo 的提醒与汇总里，完成判据不变。headless
记录直接在安装副本上观察到了这一行为。本版没有新增写入路径，因此不另立写入边界记录。

v0.44.0 的发布后证据见
[`v0.44.0-source.json`](v0.44.0-source.json)、
[`v0.44.0-package.json`](v0.44.0-package.json)、
[`v0.44.0-claude.json`](v0.44.0-claude.json) 与
[`v0.44.0-codex.json`](v0.44.0-codex.json)。本版新增可选的 `setup-convention --dispatch`：`/build` 把 task 交给子代理执行，
派活 prompt 带 tier-guard 档位标记。宿主证据只证明规则段被写入、并被新进程读到；`/build` 是否照做，是
`spec/build-task-dispatch.md` 里由 tier-guard 会话完成的三轮真实验收，不在这里重复声明。Codex 宿主上另由本会话
用安装副本实跑了两组（tier-guard 启用／停用），派活次数与「先提交再派下一个」均通过，见
[v0.44.0-codex.json](v0.44.0-codex.json)；档位标记因 Codex 加密派活正文而无法核验，按已知限制记录。

v0.45.0 的发布后证据见
[`v0.45.0-source.json`](v0.45.0-source.json)、
[`v0.45.0-package.json`](v0.45.0-package.json)、
[`v0.45.0-claude.json`](v0.45.0-claude.json) 与
[`v0.45.0-codex.json`](v0.45.0-codex.json)。本版新增只读的 `/spec-guard:cost-report`，并按 ledgerlite 联调（Claude 10 次、
Codex 8 次，成本与 tier-guard 逐次交叉核对）收紧 `--dispatch` 规则：默认不派、只派改动 3 个以上文件且验收明确的 task、
Codex 一次长等待；联调结论是派活在规格化 task 上不能稳定省钱，`--dispatch` 维持实验性。成本报告的验收以安装副本在真实
联调运行上的结果为准；Codex 宿主上，一次只给自然语言的 `codex exec` 会话经 `spec-guard-ops` 找到并运行了安装版 cost-report，在 X-N1 上
给出同样的 $0.7445。
