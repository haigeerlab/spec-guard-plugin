# 发布后项目级审查收尾（2026-10-03）

## 基准、范围与边界

- 本次先执行 `git fetch --prune origin`，固定远端默认分支为
  `origin/main@e6368e39ad35827fd1da7c605c78b1ca9140758d`（PR #145 合并提交，
  2026-10-03 19:44:15 +08:00）。审查不使用原工作树分支的提交关系推导结论；
  运行验证前另以树对象 `cb9ea556fa67544f4f43ca97a1eb1e74a398a4e5` 证明工作树内容与
  该 `origin/main` 逐字一致。
- 覆盖 2026-10-03 发布前对账报告中的 A01–A13，重点重读 A02、A10、A11、A12 的
  Spec、入口、实现、测试与发布后证据。原报告是 `e79ee81` 时点证据，正文不追写；
  当前状态以本报告和 `docs/releases/v0.38.3-*.json` 裁决。
- 只读核对 GitHub Release、PR #144/#145、最新 main Check，以及获准的私有 GitLab
  合成 Issue / MR。没有创建、评论、关闭或同步任何远端对象；公开报告不记录私有目标标识。
- 没有列举或读取真实 Local 账本中的其他事项，也没有读取、评论或关闭仍开放的合成事项
  本身。只执行不接触真实事项内容的运行时状态检查和隔离临时账本验收；公开报告不记录
  Local 事项标识。
- 未修改全局 Codex/Claude 配置，未增加模型覆盖参数或 `--model` 绕过逻辑，未删除项目。

## A01–A13 最终对账

| 编号 | 分类 | 当前结论与证据 | 后续边界 |
| --- | --- | --- | --- |
| A01 | 有意保留或条件未触发 | 13 个旧模块有 Plan 无 `todo.md`，按完成计是兼容规则，不是 13 个未完成模块。`spec/plan-without-todo.md:20-41` 记录决定，`plugins/spec-guard/hooks/module_stage.py:23-39,127-138` 保持判据和提醒；源码 `verify-artifacts.sh` 实跑为 `3 通过 · 1 警告 · 0 失败`，准确列出 13 个模块。 | 不批量补造 Todo。只有 active module 实际仍有工作时才补对应 `todo.md`；改变完成判据需单独评审。 |
| A02 | 已修且已验证 | `spec/hosted-ticket-workflow.md:72-77` 要求双平台真实往返。GitHub 私有合成链路的历史读回仍有效；GitLab 既有私有合成 Issue 本轮只读确认仍为 closed，关联 MR 为 merged、pipeline `success`；2026-10-03 新评论的稳定标记在全部 5 条 notes 中恰好一次。`git diff 31f55b1..origin/main` 证明创建实现与 GitLab provider 未变，关闭实现仅在 `plugins/spec-guard/hooks/hosted_ticket_actions.py:195` 增加 `verifiedFact`；`git diff a779e11..origin/main -- <A02 目标路径>` 为空。四组聚焦测试 39 项通过。 | 这是可沿用的受控往返，不是“最终提交重新做了一次所有写操作”。目标路径没有影响行为的新改动，重复创建 Issue/MR 或再次关闭只会增加风险，无需进行。以后若创建、provider 或关闭语义变化，再按变化范围补真实写入验收。 |
| A03 | 已修且已验证 | `plugins/spec-guard/commands/teardown-convention.md:7-22` 强制先 `--dry-run`、展示预览、失败即停；`plugins/spec-guard/hooks/test-setup-teardown.sh:104-107` 锁定 dry-run 不改文件。完整回归通过。 | 真正拆除仍需用户看过具体预览后单独确认；无需为当前未变入口重复宿主写操作。 |
| A04 | 已修且已验证 | `plugins/spec-guard/hooks/verify-artifacts.sh:84` 在二次汇总异常时报“未验证”，`test-verify-artifacts.sh:72-94` 有失败注入；本轮 19 个聚焦用例通过。 | 无剩余产品缺口。测试通过只证明检查器行为，不替代宿主事实。 |
| A05 | 已修且已验证 | 评论预览绑定 Issue 内容，变化时返回 `issue-content-changed`（`hosted_ticket_actions.py:103-108`）；关闭后的 `verified` 只表明远端已关闭（`:190-196`），入口在 `hosted-ticket-workflow/SKILL.md:57-65` 明确要求另核 CI/验收。GitLab 当前源码评论发布和幂等读回已实测，动作测试 13 项通过。 | 不把评论读回、Issue closed 或布尔参数解释为 CI 通过。 |
| A06 | 已修且已验证 | CI 明确只跑 Ubuntu（`.github/workflows/ci.yml:11-31`），macOS `/bin/bash` 要求见 `docs/maintainer-workflow.md:19-36`。本轮在与最新 main 相同的树上运行三条 macOS 最低校验均通过；GitHub 上 `e6368e39` 的 `validate (ubuntu-latest)` Check 也为 success。 | 继续把 Ubuntu CI 与 macOS Bash 3.2 验证分开报告。 |
| A07 | 有意保留或条件未触发 | `docs/workflow.md:60-62` 已明确普通 bug 不为统计数字新建模块，只有独立新能力才走 add-module/Proposal；已发布能力图与历史继续保留。 | 不批量删除旧模块；新增模块时继续审查是否为独立用户能力。 |
| A08 | 有意保留或条件未触发 | `spec/capability-history.md:53-59` 将 `history-migration.py import --confirm` 限定为维护者内部工具，日常入口只有只读 preview；`docs/maintainer-workflow.md:38-40` 要求逐次确认。 | 不增加日常导入入口；真实导入仍需新鲜预览和单独确认。 |
| A09 | 已修且已验证 | `spec/module-insert.md:3-6` 和 `spec/proposal-promotion-proof.md:3-4` 均给出现行修订指针并保留原始决策文字；完整校验通过。 | 后续修订继续用指针说明现行契约，不改写历史正文。 |
| A10 | 有意保留或条件未触发 | `docs/decisions/2026-09-28-xats-sunset.md:20-30` 的三个门槛均未全部满足：发布 JSON 中没有连续两个版本、每版至少两主机的 native 收发/空闲唤醒/回退记录；`plugins/spec-guard/hooks/native_collaboration_runtime.py:20-22` 仍是最初固定的 `8f12c880…`，没有一次上游 revision 升级后的唤醒验收；公开 GitHub 当前虽无带 P1/P2 标签或标题/正文含 native 的开放 Issue，但在“不扫描真实 Local 账本”的边界下不能把第三项升级为全局证明。native 聚焦测试 45 项通过，只证明源码契约。 | 保持 XATS 默认和 native 实验性传输，不提出转正 Proposal，不删除传输层。至少前两项门槛补齐且第三项有明确缺陷账本证据后才重新评估。 |
| A11 | 已修且已验证；限定补证完成 | `spec/audit-handoff.md:18-43` 与 `workflow-checkpoints.md:15-25,48-56` 已定义有限批次、冻结、权限与“继续”边界；静态测试 6 项通过。2026-10-03 又在 Claude Code 2.1.288 和 Codex CLI 0.160.0 的隔离三轮会话中补验：冻结批次收到普通“继续”时，两端都只执行最近预告的 `checked-gate`，保持 2/2 且不重扫、不扩批、不写入；随后明确给出新证据与范围扩展时，两端都保留原冻结批次并新开只含新增范围的批次。 | 当前无待补 A11 场景；这是合成宿主证据，不扩大为生产环境保证。规则或相关宿主行为变化后再按同一场景回归。测试数量少不能推断功能失败，也无需新 Spec/Plan。 |
| A12 | 已修且已验证 | `ticket` 入口要求用户回复采用 `《标题》（短编号）` 且不展示完整 ID（`plugins/spec-guard/commands/ticket.md:12-18`、`skills/ticket/SKILL.md:17-24`），契约测试见 `test_ticket_entry.py:63-70`。PR #144 已合并为 `dd68698`；`docs/releases/v0.38.3-claude.json:51-62` 记录安装版对真实 Local 账本中单一合成事项的定向 `epiq_issue_get`，回复包含标题和短编号、没有完整内部 ID，且无写入或同步调用。本轮未重读该事项。 | 发布后真实定向回复缺口已经关闭。该合成事项保持开放；记录结论或关闭仍须对这一具体事项取得明确授权并在写入后读回。 |
| A13 | 已修且已验证 | 本轮用已验证 Epiq 1.11.0 运行时重跑隔离临时项目：`test_local_ledger_acceptance.py` 返回 `state: passed`，`test_local_ticket_restore_acceptance.py` 1 项通过；两命令均退出 0。测试分别用临时目录和隔离 `EPIQ_GLOBAL_DIR`（`test_local_ledger_acceptance.py:59-73`、`test_local_ticket_restore_acceptance.py:35-46`）。 | 仍只证明合成临时项目；不自动迁移、扫描或修改真实用户数据。 |

## 新发现的真实问题

### D01（Required，P2）：发布支持矩阵落后于已合并证据

`docs/releases/README.md:19` 仍把 v0.38.3 的 Codex 默认模型 smoke 写成
`not-verified`，与 PR #145 以及 `docs/releases/v0.38.3-codex.json:37-48` 冲突。
后者明确记录 PATH 选择 Codex CLI v0.160.0、未传模型覆盖、默认 `gpt-6-sol` smoke
退出 0，机器记录包含有效阶段注入；旧 v0.154.0 的 HTTP 400 不证明账户整体不支持该模型。

本报告所在变更直接修正该矩阵文字。它是低风险文档漂移，不是产品代码缺陷；不需要新
Spec/Plan，也不应据此开发 `--model` 参数。

除 D01 外，本批次没有发现新的产品缺陷；A10/A11 的项目分别是门槛未触发和验证增强，
不得转写成当前功能失败。

## A11 补充宿主验收

验收使用全新隔离 Git 仓库，只注入与 `workflow-checkpoints.md:17-23,54-56` 对应的
有限批次规则和合成事实；仓库在验收前后均为 clean，没有读取事项、访问远端或写文件。

- Claude Code 2.1.288：首轮用 `claude -p --output-format json --tools= <scenario>`
  冻结 2/2 批次；同一 session 第二轮只发送“继续”，返回 `checked-gate`、
  `rescanned=false`、`scope_expanded=false`、`writes=false`；第三轮明确提供新增证据并扩展
  范围，返回新批次、仅覆盖新增范围、保留原冻结批次。
- Codex CLI 0.160.0：从首轮开始统一用
  `codex exec --ignore-user-config --json -s read-only -C <isolated-fixture> <scenario>`，后两轮
  用同一 session 的 `codex exec resume --ignore-user-config --json`；结果与 Claude 一致。
  未传 `--model`，也未修改全局配置。一次启动方式不一致的诊断会话不计入验收结论。

这两项补证填补的是先前报告列出的最小正向续接与反向扩批场景；不会把提示词规则冒充
硬闸，也不会替代 A10 的发布／多主机事实。

## 本轮验证状态

| 验证 | 状态 | 结果与边界 |
| --- | --- | --- |
| `git fetch --prune origin` 与 `git rev-parse origin/main` | 通过 | 固定 `e6368e39`；不使用原分支关系作结论。 |
| GitHub Release / PR / Check 只读 API | 通过 | v0.38.3 Release 资产 SHA-256 为 `c89adfd…e68b`；PR #144/#145 merged；最新 main 的 Ubuntu validate success。 |
| 私有 GitLab 合成 Issue / MR 只读 API | 通过 | Issue closed；MR merged、pipeline success；新评论标记唯一。没有远端写入，公开报告不记录私有目标标识。 |
| A02 聚焦测试 | 通过 | 39 项通过。 |
| A10 聚焦测试 | 通过 | 45 项通过。 |
| A11 / A12 聚焦测试 | 通过 | 6 项 / 9 项通过。 |
| `/bin/bash scripts/validate.sh` | 通过 | 最新 main 同树在 macOS 系统 Bash 下退出 0。内部 Codex smoke 是判决器 self-test，不冒充真实宿主运行。 |
| `/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh` | 通过 | 80 个用例。 |
| `/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh` | 通过 | 19 个用例。 |
| 源码 `phase-guard.sh` / `verify-artifacts.sh` 对本仓 | 通过 | 阶段 DONE；33/33 Spec、33/33 Plan；13 个旧模块无 Todo 只记 1 条警告，0 失败。 |
| 隔离 Epiq 本地账本与恢复验收 | 通过 | `state: passed`；恢复 1 项通过；未读取真实事项。 |
| A10 两版本/两主机、上游升级后唤醒 | 未运行 | 所需发布版本和 revision 升级事实尚不存在，不能通过重复当前版本测试补出。 |
| A11 最小正向续接与明确扩批宿主场景 | 通过 | Claude Code 2.1.288 与 Codex CLI 0.160.0 各自同一三轮隔离会话均通过；无重扫、无越界扩批、无写入。只证明所述合成场景。 |
| 已知真实 Local 合成事项的结论记录 | 通过 | 用户对精确目标和已展示内容授权后，只定向读写该事项；评论写入成功并读回为唯一匹配，事项仍保持开放。没有扫描其他事项或同步远端，公开报告不记录其标识。 |
| 已知真实 Local 合成事项的关闭 | 未运行 | 用户仅授权记录并明确要求保持开放；没有调用关闭。 |

本轮没有“失败”或“环境不可用”的验证项；配置的私有 GitLab 主机认证与只读 API 均可用。

## 剩余行动（按优先级）

1. **P2，条件性：** 若未来要推动 native 转正，先累积连续两版、每版至少两主机的
   收发/空闲唤醒/回退发布记录，再升级一次固定上游 revision 并重做唤醒验收；最后用
   明确缺陷账本证明没有开放 P1/P2。条件未齐前不建 Proposal、不删除 XATS。
2. **已完成，无当前行动：** A11 的“唯一已授权下一步 + 继续”和
   “明确新证据/扩展范围 → 新批次”已在 Claude 与 Codex 补验通过。仅在规则或相关宿主
   行为变化后重跑，不为提高验证评级重复执行。
3. **已完成记录；关闭仍需新授权：** 已知的单一真实 Local 合成验收事项已在精确授权后写入
   收尾结论并读回，当前仍开放且没有同步远端。以后若要关闭，须对关闭动作另行明确授权并在关闭后读回。

已经没有必要继续处理：为 13 个旧模块批量造 Todo；重做 A02 的 Issue/MR 创建、评论或关闭；
恢复退役 tracker bridge；为 gpt-6-sol 增加模型绕过；把测试全绿当作 A10/A11 宿主门槛已满足；
重读其他真实 Local 事项；删除任一传输层或项目。
